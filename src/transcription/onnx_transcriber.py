"""ONNX Runtime 转录后端（内联版）。

纯 numpy mel 谱 + onnxruntime 直接推理，零 subprocess 依赖。
模型和资源文件内嵌为包资源，打包后可独立运行。
"""

import os
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort
import soundfile as sf

from .base import TranscribeBase

# 包资源目录（兼容 PyInstaller 打包后路径）
if getattr(sys, 'frozen', False):
    _MODELS_DIR = Path(sys._MEIPASS) / "models"
else:
    _MODELS_DIR = Path(__file__).resolve().parent / "models"

# ---- 常量 ----
N_FFT = 2048
HOP_LENGTH = 256
SR_TARGET = 16000
LOG_OFFSET = 1e-08
MIN_VALUE = -18.0

MARGIN_B = 32
MARGIN_F = 32
NUM_FRAME = 512
N_BINS = 256
NUM_NOTE = 88
THRESHOLD_ONSET = 0.5
THRESHOLD_OFFSET = 1.0
THRESHOLD_FRAME = 0.5
MIN_DURATION = 0.08

# 预存 mel 滤波器矩阵
_FB = np.load(str(_MODELS_DIR / "mel_fb.npy")).astype(np.float32)

# Hann 窗
_WINDOW = (0.5 - 0.5 * np.cos(2 * np.pi * np.arange(2048) / 2048)).astype(np.float32)

# ---- 风格向量采样（替换预计算固定向量，匹配原始 SVSampler 行为） ----
_SV_PRESETS = {
    "level1": (0., 0.9, -0.5),
    "level2": (0., 1., 0.),
    "level3": (0.5, 1.05, 0.5),
}
_SV_WINDOWS = (0.5, 0.1, 0.5)  # (vel_window, pitch_window, onset_window)


def _load_style_vectors():
    """延迟加载 style_vectors.json，仅加载一次。"""
    if _load_style_vectors.cache is None:
        import json
        path = _MODELS_DIR / "style_vectors.json"
        with open(str(path)) as f:
            data = json.load(f)
        vectors = {
            k: np.array(v, dtype=np.float32)
            for k, v in data["style_vectors"].items()
        }
        _load_style_vectors.cache = (vectors, data["style_features"])
    return _load_style_vectors.cache


_load_style_vectors.cache = None


def _sample_style_vector(style="level2"):
    """随机采样风格向量（纯 numpy，匹配原始 SVSampler 行为）。"""
    vectors, features = _load_style_vectors()
    mean_vel, mean_pitch, mean_onset = _SV_PRESETS[style]
    w_vel, w_pitch, w_onset = _SV_WINDOWS
    r_vel = (mean_vel - w_vel / 2, mean_vel + w_vel / 2)
    r_pitch = (mean_pitch - w_pitch / 2, mean_pitch + w_pitch / 2)
    r_onset = (mean_onset - w_onset / 2, mean_onset + w_onset / 2)

    keys_vel, keys_pitch, keys_onset = [], [], []
    for key, f in features.items():
        f_vel, f_pitch, f_onset = f
        if r_vel[0] <= f_vel <= r_vel[1]:
            keys_vel.append(key)
        if r_pitch[0] <= f_pitch <= r_pitch[1]:
            keys_pitch.append(key)
        if r_onset[0] <= f_onset <= r_onset[1]:
            keys_onset.append(key)

    def summarize(keys):
        if not keys:
            return np.zeros(24, dtype=np.float32)
        weights = np.ones(len(keys), dtype=np.float32)
        weights /= np.sum(weights)
        sv = np.zeros(24, dtype=np.float32)
        for key, w in zip(keys, weights):
            sv += vectors[key] * w
        return sv

    sv_vel = summarize(keys_vel)[:8]
    sv_pitch = summarize(keys_pitch)[8:16]
    sv_onset = summarize(keys_onset)[16:24]
    return np.concatenate([sv_vel, sv_pitch, sv_onset]).astype(np.float32)


def _load_audio(path):
    wave, sr = sf.read(path)
    if wave.ndim > 1:
        wave = np.mean(wave, axis=1)
    return wave.astype(np.float32), sr


def _resample(y, orig_sr, target_sr):
    if orig_sr == target_sr:
        return y
    ratio = target_sr / orig_sr
    n_out = int(round(len(y) * ratio))
    indices = np.arange(n_out) / ratio
    x0 = indices.astype(np.int64)
    x1 = np.minimum(x0 + 1, len(y) - 1)
    frac = indices - x0
    return (y[x0] * (1 - frac) + y[x1] * frac).astype(np.float32)


def _melspectrogram(y):
    y = np.pad(y, (N_FFT // 2, N_FFT // 2), mode="constant", constant_values=MIN_VALUE)
    n_frames = (len(y) - N_FFT) // HOP_LENGTH + 1
    stft = np.zeros((N_FFT // 2 + 1, n_frames), dtype=np.complex64)
    for i in range(n_frames):
        start = i * HOP_LENGTH
        stft[:, i] = np.fft.rfft(y[start:start + N_FFT] * _WINDOW)
    power = np.abs(stft) ** 2
    mel = _FB.T @ power
    return np.log(mel.T + LOG_OFFSET)


def _transcript(feature, ort_session, sv, progress_callback=None, pct_start=0, pct_end=100):
    """推理主循环。sv 为 None 时走 AMT 模式（无 style 注入，忠实转录）。"""
    len_s = int(np.ceil(feature.shape[0] / NUM_FRAME) * NUM_FRAME) - feature.shape[0]
    pad_b = np.full([MARGIN_B, N_BINS], MIN_VALUE, dtype=np.float32)
    pad_f = np.full([len_s + MARGIN_F, N_BINS], MIN_VALUE, dtype=np.float32)
    a_input = np.concatenate([pad_b, feature, pad_f], axis=0)

    out_len = feature.shape[0] + len_s
    outputs = {
        "onset": np.zeros((out_len, NUM_NOTE), dtype=np.float32),
        "offset": np.zeros((out_len, NUM_NOTE), dtype=np.float32),
        "mpe": np.zeros((out_len, NUM_NOTE), dtype=np.float32),
        "velocity": np.zeros((out_len, NUM_NOTE), dtype=np.int32),
    }

    for i in range(0, feature.shape[0], NUM_FRAME):
        if progress_callback:
            progress_callback(int(pct_start + (i / max(feature.shape[0], 1)) * (pct_end - pct_start)))
        end = i + MARGIN_B + NUM_FRAME + MARGIN_F
        segment = a_input[i:end].T[np.newaxis, ...]

        feed = {"mel_spec": segment.astype(np.float32)}
        if sv is not None:
            feed["style_vec"] = sv
        result = ort_session.run(None, feed)
        o_on, o_off, o_mpe, o_vel = result[0][0], result[1][0], result[2][0], result[3][0]
        o_on2, o_off2, o_mpe2, o_vel2 = result[5][0], result[6][0], result[7][0], result[8][0]

        out_end = min(i + NUM_FRAME, out_len)
        seg_end = min(NUM_FRAME, out_end - i)
        outputs["onset"][i:out_end] = np.maximum(o_on[:seg_end], o_on2[:seg_end])
        outputs["offset"][i:out_end] = np.minimum(o_off[:seg_end], o_off2[:seg_end])
        outputs["mpe"][i:out_end] = np.maximum(o_mpe[:seg_end], o_mpe2[:seg_end])
        outputs["velocity"][i:out_end] = np.where(
            o_vel[:seg_end].argmax(2) > 0,
            o_vel[:seg_end].argmax(2),
            o_vel2[:seg_end].argmax(2),
        )

    for k in outputs:
        outputs[k] = outputs[k][:feature.shape[0]]
    if progress_callback:
        progress_callback(pct_end)
    return outputs


def _mpe2note(onset, offset, mpe, velocity):
    hop_sec = HOP_LENGTH / SR_TARGET
    total_sec = len(onset) * hop_sec  # 音频总时长（秒），用于最后一个音符的默认结束时间
    notes = []

    for j in range(NUM_NOTE):
        onsets = []
        for i in range(len(onset)):
            if onset[i, j] >= THRESHOLD_ONSET:
                left = onset[i - 1, j] if i > 0 else 0
                right = onset[i + 1, j] if i < len(onset) - 1 else 0
                if onset[i, j] >= left and onset[i, j] >= right:
                    if i == 0 or i == len(onset) - 1:
                        t = i * hop_sec
                    else:
                        if left == right:
                            t = i * hop_sec
                        elif left > right:
                            t = i * hop_sec - 0.5 * hop_sec * (left - right) / (onset[i, j] - right)
                        else:
                            t = i * hop_sec + 0.5 * hop_sec * (right - left) / (onset[i, j] - left)
                    onsets.append({"loc": i, "time": t})

        if not onsets:
            continue

        offsets = []
        for i in range(len(offset)):
            if offset[i, j] >= THRESHOLD_OFFSET:
                left = offset[i - 1, j] if i > 0 else 0
                right = offset[i + 1, j] if i < len(offset) - 1 else 0
                if offset[i, j] >= left and offset[i, j] >= right:
                    if i == 0 or i == len(offset) - 1:
                        t = i * hop_sec
                    else:
                        if left == right:
                            t = i * hop_sec
                        elif left > right:
                            t = i * hop_sec - 0.5 * hop_sec * (left - right) / (offset[i, j] - right)
                        else:
                            t = i * hop_sec + 0.5 * hop_sec * (right - left) / (offset[i, j] - left)
                    offsets.append({"loc": i, "time": t})

        off_idx = 0
        for idx_on, on in enumerate(onsets):
            next_on_time = onsets[idx_on + 1]["time"] if idx_on + 1 < len(onsets) else total_sec

            off_time = next_on_time
            while off_idx < len(offsets) and offsets[off_idx]["loc"] <= on["loc"]:
                off_idx += 1
            if off_idx < len(offsets):
                off_time = min(offsets[off_idx]["time"], next_on_time)

            mpe_off_time = next_on_time
            for ii in range(on["loc"] + 1, min(len(mpe), int(next_on_time / hop_sec))):
                if mpe[ii, j] < THRESHOLD_FRAME:
                    mpe_off_time = ii * hop_sec
                    break

            off_time = min(off_time, mpe_off_time)

            if off_time > on["time"] + MIN_DURATION:
                vel = int(max(1, min(127, velocity[on["loc"], j])))
                notes.append({
                    "pitch": j + 21,
                    "start": on["time"],
                    "end": off_time,
                    "velocity": vel,
                })

    return notes


def _note2midi(notes, path_output):
    import pretty_midi

    midi = pretty_midi.PrettyMIDI()
    inst = pretty_midi.Instrument(program=0)
    for n in notes:
        if n["end"] - n["start"] >= MIN_DURATION:
            inst.notes.append(pretty_midi.Note(
                velocity=n["velocity"],
                pitch=n["pitch"],
                start=n["start"],
                end=n["end"],
            ))
    midi.instruments.append(inst)
    midi.write(path_output)


class ONNXTranscriber(TranscribeBase):
    """ONNX Runtime 音频→MIDI 转录器（内联版）。

    两种模式：
    - mode="apc"（默认）：翻奏改编，注入 style vector（apc.onnx）
    - mode="amt"：忠实转录，无 style 注入（amt.onnx），适合钢琴独奏输入

    模型和资源文件内嵌在包中，零 subprocess 依赖。
    """

    def __init__(self, style="level2", mode="apc"):
        if mode not in ("apc", "amt"):
            raise ValueError(f"unknown mode: {mode}, available: apc, amt")
        if style not in _SV_PRESETS:
            raise ValueError(f"unknown style: {style}, available: {list(_SV_PRESETS.keys())}")
        self.style = style
        self.mode = mode
        self._ort_session = None
        # 实际使用的推理设备（provider），供界面提示
        self.device_info = "cpu"
        # AMT 模式无 style 注入（模型本身没有 style 输入）
        self._sv = None if mode == "amt" else _sample_style_vector(style).reshape(1, -1)

    @staticmethod
    def detect_device() -> dict:
        """探测实际可用的推理设备（不依赖模型文件，可提前调用）。

        返回 {"provider": "DmlExecutionProvider"|"CUDAExecutionProvider"|"CPUExecutionProvider",
              "gpu": bool, "label": "DirectML (GPU)"|"CUDA (GPU)"|"CPU"}
        """
        try:
            available = ort.get_available_providers()
        except Exception:
            return {"provider": "CPUExecutionProvider", "gpu": False, "label": "CPU"}
        for prov, label in (("DmlExecutionProvider", "DirectML"),
                            ("CUDAExecutionProvider", "CUDA")):
            if prov in available:
                return {"provider": prov, "gpu": True, "label": label}
        return {"provider": "CPUExecutionProvider", "gpu": False, "label": "CPU"}

    def _get_session(self):
        if self._ort_session is None:
            onnx_name = "amt.onnx" if self.mode == "amt" else "apc.onnx"
            onnx_path = str(_MODELS_DIR / onnx_name)
            if not os.path.isfile(onnx_path):
                raise RuntimeError(f"ONNX model not found: {onnx_path}")
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 2
            opts.inter_op_num_threads = 1

            # 自动选择 GPU provider：DirectML > CUDA > CPU
            preferred = ["DmlExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"]
            available = ort.get_available_providers()
            providers = [p for p in preferred if p in available]
            if not providers:
                providers = ["CPUExecutionProvider"]

            self._ort_session = ort.InferenceSession(onnx_path, opts, providers=providers)
            # 记录实际选中的 provider（界面提示用）
            active = getattr(self._ort_session, "get_providers", None)
            self.device_info = (active()[0] if active else providers[0]) or providers[0]
        return self._ort_session

    def is_available(self):
        onnx_name = "amt.onnx" if self.mode == "amt" else "apc.onnx"
        onnx_path = _MODELS_DIR / onnx_name
        mel_path = _MODELS_DIR / "mel_fb.npy"
        if self.mode == "amt":
            return all(p.is_file() for p in [onnx_path, mel_path])
        sv_path = _MODELS_DIR / "style_vectors.json"
        return all(p.is_file() for p in [onnx_path, mel_path, sv_path])

    def transcribe(self, audio_path, output_path=None, progress_callback=None):
        if not output_path:
            base = os.path.splitext(os.path.basename(audio_path))[0]
            output_path = base + ".mid"

        audio_path = os.path.abspath(audio_path)
        output_path = os.path.abspath(output_path)

        if not os.path.isfile(audio_path):
            raise FileNotFoundError(f"audio not found: {audio_path}")

        # Load audio
        if progress_callback:
            progress_callback(5)
        wave, sr = _load_audio(audio_path)

        # Resample to 16kHz
        if progress_callback:
            progress_callback(10)
        if sr != SR_TARGET:
            wave = _resample(wave, sr, SR_TARGET)

        # Mel spectrogram
        if progress_callback:
            progress_callback(15)
        feature = _melspectrogram(wave)

        # ONNX inference (15% -> 85%)
        ort_session = self._get_session()
        sv = self._sv
        outputs = _transcript(feature, ort_session, sv, progress_callback, 15, 85)

        # Post-process to MIDI
        if progress_callback:
            progress_callback(90)
        notes = _mpe2note(
            outputs["onset"], outputs["offset"],
            outputs["mpe"], outputs["velocity"],
        )
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.isdir(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        _note2midi(notes, output_path)

        if not os.path.isfile(output_path):
            raise RuntimeError(f"MIDI output not generated: {output_path}")

        if progress_callback:
            progress_callback(100)
        return output_path
