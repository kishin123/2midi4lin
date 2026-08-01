"""PyTorch 转录后端（保留原版 AMT-APC，用于训练/实验）。

通过 subprocess 调用 AMT-APC 官方推理（使用 torch 环境）。
需要 torch + CUDA（可选）。
"""
import os
import subprocess

from .base import TranscribeBase

AMT_APC_DIR = os.path.expanduser("~/projects/amt-apc")
AMT_APC_PYTHON = os.path.join(AMT_APC_DIR, ".venv/bin/python3")


class TorchTranscriber(TranscribeBase):
    """PyTorch 版 AMT-APC 音频→MIDI 转录器。

    需要 torch 环境，适合需要高级功能（如自定义 style）的场景。

    Args:
        device: 推理设备 (auto/cuda/cpu)
        style: 翻弹风格 ("level1" / "level2" / "level3")
    """

    def __init__(self, device: str = None, style: str = "level2"):
        self.device = device or "auto"
        self.style = style

    def _check_available(self):
        if not os.path.isdir(AMT_APC_DIR):
            raise RuntimeError(
                "AMT-APC 仓库不存在: " + AMT_APC_DIR + "\n"
                "请先执行: cd ~/projects && git clone https://github.com/310hz/amt-apc.git"
            )
        if not os.path.isfile(AMT_APC_PYTHON):
            raise RuntimeError(
                "AMT-APC 虚拟环境不存在: " + AMT_APC_PYTHON + "\n"
                "请先执行: cd ~/projects/amt-apc && python3 -m venv .venv "
                "&& source .venv/bin/activate && pip install torch torchaudio soundfile pretty-midi tqdm torchcodec"
            )
        weight_path = os.path.join(AMT_APC_DIR, "models/params/apc.pth")
        if not os.path.isfile(weight_path):
            raise RuntimeError(
                "AMT-APC 权重文件不存在: " + weight_path + "\n"
                "请先下载: wget -P ~/projects/amt-apc/models/params/ "
                "https://github.com/310hz/amt-apc/releases/download/beta/apc.pth"
            )

    def is_available(self) -> bool:
        if not os.path.isdir(AMT_APC_DIR):
            return False
        if not os.path.isfile(AMT_APC_PYTHON):
            return False
        weight_path = os.path.join(AMT_APC_DIR, "models/params/apc.pth")
        return os.path.isfile(weight_path)

    def transcribe(self, audio_path: str, output_path: str = None,
                   progress_callback=None) -> str:
        if not output_path:
            base = os.path.splitext(os.path.basename(audio_path))[0]
            output_path = base + ".mid"

        audio_path = os.path.abspath(audio_path)
        output_path = os.path.abspath(output_path)

        if not os.path.isfile(audio_path):
            raise FileNotFoundError("音频文件不存在: " + audio_path)

        self._check_available()

        cmd = [
            AMT_APC_PYTHON, "-m", "infer",
            audio_path,
            "-o", output_path,
            "--style", self.style,
        ]
        if self.device and self.device != "auto":
            cmd.extend(["--device", self.device])

        result = subprocess.run(cmd, cwd=AMT_APC_DIR, capture_output=False, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                "AMT-APC 推理失败 (exit=" + str(result.returncode) + ")\n"
                + result.stderr
            )
        if not os.path.isfile(output_path):
            raise RuntimeError("推理完成但未生成输出文件: " + output_path)
        return output_path
