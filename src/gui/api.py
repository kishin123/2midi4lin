"""PyWebView API — GUI 后端接口（类封装，兼容 pywebview 6.x）。

通过 pywebview.create_window(js_api=Api()) 暴露给前端 JS 调用。
所有重量级导入延迟到实际调用时进行，避免阻塞 GUI 启动。
"""
import os
import threading


class Api:
    """PyWebView JS API — 所有 public 方法自动暴露给 window.pywebview.api。"""

    def __init__(self):
        self._progress = 0
        self._status = "idle"  # idle | running | done | error
        self._result_path = None
        self._error_msg = None
        self._dropped_file = None
        self._stage = ""  # 阶段提示：下载中/转换中/转录中

    def set_dropped_file(self, path: str):
        print(f"[drop] on_drop 收到: {path!r}", flush=True)
        self._dropped_file = path

    def get_dropped_file(self) -> str:
        return self._dropped_file or ""

    # ---- 前端调用的公开方法 ----

    def transcribe(self, audio_path: str, style: str = "level2", mode: str = "apc") -> str:
        """启动异步转录。输出到统一目录 ~/Music/2midi4lin/transcribe。

        mode: "apc"（翻奏改编，默认）| "amt"（忠实转录，适合钢琴独奏）
        """
        audio_path = os.path.abspath(audio_path)
        if not os.path.isfile(audio_path):
            self._status = "error"
            self._error_msg = f"文件不存在: {audio_path}"
            return ""

        base = os.path.splitext(os.path.basename(audio_path))[0]
        output_dir = os.path.join(self._get_output_dir(), "transcribe")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, base + ".mid")

        self._status = "running"
        self._progress = 0
        self._result_path = None
        self._error_msg = None

        t = threading.Thread(
            target=self._run_transcribe,
            args=(audio_path, style, output_path, mode),
            daemon=True,
        )
        t.start()
        return output_path

    def get_status(self) -> dict:
        """返回当前状态，供前端轮询。"""
        return {
            "status": self._status,
            "progress": self._progress,
            "result": self._result_path,
            "error": self._error_msg,
            "stage": self._stage,
        }

    def open_file_dialog(self, file_types: str = "audio") -> str:
        """打开系统文件选择对话框。"""
        try:
            import webview
            if file_types == "midi":
                ft = ("MIDI 文件 (*.mid;*.midi)", "所有文件 (*.*)")
            else:
                ft = ("音频文件 (*.wav;*.mp3;*.flac;*.ogg)", "所有文件 (*.*)")
            result = webview.windows[0].create_file_dialog(
                webview.OPEN_DIALOG, allow_multiple=False, file_types=ft,
            )
            if result and len(result) > 0:
                return result[0]
            return ""
        except Exception:
            return ""

    def open_file(self, path: str):
        """在文件管理器中打开指定路径。"""
        import subprocess
        subprocess.Popen(["explorer", "/select,", os.path.abspath(path)])

    def open_browser(self, url: str):
        """在默认浏览器中打开 URL。"""
        import webbrowser
        webbrowser.open(url)

    def process_midi(self, input_path: str, **kwargs) -> dict:
        """后处理 MIDI 文件。"""
        try:
            from src.pipeline.postprocess import process_midi
            output_path = os.path.splitext(input_path)[0] + "_pedal.mid"
            stats = process_midi(input_path, output_path, **kwargs)
            stats["output"] = output_path
            return stats
        except Exception as e:
            return {"error": str(e)}

    def transcribe_and_process(self, audio_path: str, style: str = "level2") -> str:
        """一键林离版本：转录 + 自动后处理，共享进度条。"""
        audio_path = os.path.abspath(audio_path)
        if not os.path.isfile(audio_path):
            self._status = "error"
            self._error_msg = f"文件不存在: {audio_path}"
            return ""

        base = os.path.splitext(os.path.basename(audio_path))[0]
        out_dir = os.path.join(self._get_output_dir(), "transcribe")
        os.makedirs(out_dir, exist_ok=True)
        output_midi = os.path.join(out_dir, base + ".mid")
        output_lin = os.path.join(out_dir, base + "_lin.mid")

        self._status = "running"
        self._progress = 0
        self._result_path = None
        self._error_msg = None

        t = threading.Thread(
            target=self._run_transcribe_and_process,
            args=(audio_path, style, output_midi, output_lin),
            daemon=True,
        )
        t.start()
        return output_lin

    # ---- download（搜索下载 MIDI） ----

    def search_midi(self, query: str) -> list:
        """搜索 MIDI（同步版，兼容外部调用）。"""
        try:
            from src.downloader import MusicDownloader
            dl = MusicDownloader()
            return dl.search_midi(query)
        except Exception as e:
            return [{"error": str(e)}]

    # ---- 流式搜索（先到先显示） ----

    def search_midi_start(self, query: str):
        """启动流式搜索：后台线程跑多源搜索，每个源完成即写入增量缓冲。

        结果通过 search_midi_poll 增量获取。前端轮询实现"先搜索到的先显示"。
        """
        self._search_buf = []
        self._search_done = False

        def run():
            try:
                from src.downloader import MusicDownloader
                dl = MusicDownloader()
                dl.search_midi(query, on_result=self._search_on_result)
            except Exception as e:
                self._search_buf.append([{"error": str(e)}])
            finally:
                self._search_done = True

        threading.Thread(target=run, daemon=True).start()
        return "started"

    def _search_on_result(self, source_name: str, results: list):
        """每个源完成时的回调：写入增量缓冲。"""
        self._search_buf.append(results)

    def search_midi_poll(self) -> dict:
        """取增量结果。每次返回自上次调用以来的新结果，done=True 表示全部源完成。

        Returns:
            {"new": list, "done": bool}
        """
        new = []
        while self._search_buf:
            new.extend(self._search_buf.pop(0))
        return {"new": new, "done": self._search_done}

    def download_midi(self, item: dict, output_dir: str = "") -> str:
        """下载指定 MIDI。"""
        try:
            from src.downloader import MusicDownloader
            dl = MusicDownloader(download_dir=output_dir or None)
            return dl.download_midi(item, output_dir or None)
        except Exception as e:
            return f"下载失败: {e}"

    def download_musescore_url(self, url: str) -> str:
        """通过 URL 下载 MuseScore 乐谱为 MIDI。"""
        try:
            from src.downloader import MusicDownloader
            from src.downloader.sources import SOURCES
            dl = MusicDownloader()
            src = SOURCES["musescore"]
            item = {"id": url, "source": "musescore", "title": url.split("/")[-1]}
            path = src.download(item, dl.download_dir)
            return path
        except Exception as e:
            return f"MuseScore 下载失败: {e}"

    def video_to_midi(self, url: str, style: str = "level2", mode: str = "apc") -> str:
        """从钢琴演奏视频链接直接转 MIDI（B站/YouTube）。

        流程：yt-dlp 下载音频 → ffmpeg 转 wav → ONNX 转录（apc 翻奏 / amt 忠实）。
        异步执行，进度通过 get_status 轮询。
        """
        if not url or not url.strip():
            self._status = "error"
            self._error_msg = "请输入视频链接"
            return ""
        url = url.strip()

        self._status = "running"
        self._progress = 0
        self._result_path = None
        self._error_msg = None

        t = threading.Thread(
            target=self._run_video_to_midi,
            args=(url, style, mode),
            daemon=True,
        )
        t.start()
        return ""

    # ---- 内部方法 ----

    def _run_transcribe(self, audio_path: str, style: str, output_path: str, mode: str = "apc"):
        try:
            from src.transcription import get_transcriber
            self._status = "running"

            def on_progress(pct):
                self._progress = pct

            on_progress(0)
            transcriber = get_transcriber("onnx", style=style, mode=mode)
            on_progress(2)
            result = transcriber.transcribe(audio_path, output_path, progress_callback=on_progress)
            self._progress = 100
            self._status = "done"
            self._result_path = result
        except Exception as e:
            self._status = "error"
            self._error_msg = str(e)

    def _run_transcribe_and_process(self, audio_path, style, output_midi, output_lin):
        """内部：串行执行转录(0-70%) + 后处理(70-100%)。"""
        try:
            from src.transcription import get_transcriber
            from src.pipeline.postprocess import process_midi

            # 阶段 1: 转录 (0-70%)
            self._status = "running"

            def on_progress(pct):
                self._progress = int(pct * 0.7)

            on_progress(0)
            transcriber = get_transcriber("onnx", style=style)
            on_progress(2)
            midi_path = transcriber.transcribe(audio_path, output_midi, progress_callback=on_progress)
            self._progress = 70

            # 阶段 2: 后处理 (70-100%)
            kwargs = {
                "max_note_dur": None,  # None=动态阈值，按整曲时长分布自动判断
                "split_point": 60,
                "max_hand": 5,
                "hand_span": 12,
                "max_nps": 14,
                "max_leap": 24,
            }
            stats = process_midi(midi_path, output_lin, **kwargs)
            self._progress = 100
            self._status = "done"
            self._result_path = stats.get("output", output_lin)
        except Exception as e:
            self._status = "error"
            self._error_msg = str(e)

    # ---- 视频链接转 MIDI ----

    def _find_ffmpeg(self) -> str:
        """定位 ffmpeg 可执行文件：优先内置（PyInstaller），其次系统 PATH。"""
        import sys as _sys
        if hasattr(_sys, "_MEIPASS"):
            candidates = [
                os.path.join(_sys._MEIPASS, "ffmpeg", "ffmpeg.exe"),
                os.path.join(_sys._MEIPASS, "ffmpeg.exe"),
            ]
            for c in candidates:
                if os.path.isfile(c):
                    return c
        local = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "ffmpeg_min", "ffmpeg.exe",
        )
        if os.path.isfile(local):
            return local
        import shutil
        return shutil.which("ffmpeg") or ""

    def _get_output_dir(self) -> str:
        """统一输出目录：用户 Music/2midi4lin（打包后不依赖临时目录）。"""
        home = os.path.expanduser("~")
        music = os.path.join(home, "Music", "2midi4lin")
        try:
            os.makedirs(music, exist_ok=True)
            return music
        except Exception:
            fallback = os.path.join(home, "2midi4lin")
            os.makedirs(fallback, exist_ok=True)
            return fallback

    def _run_video_to_midi(self, url: str, style: str, mode: str = "apc"):
        """后台线程：下载视频音频 → 转 wav → 转录（原生 MIDI 输出）。"""
        try:
            import yt_dlp
            import subprocess

            out_dir = os.path.join(self._get_output_dir(), "videos")
            os.makedirs(out_dir, exist_ok=True)

            # 阶段 1: 下载音频 (0-30%)
            self._stage = "下载音频中..."
            def progress_hook(d):
                if d.get("status") == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                    down = d.get("downloaded_bytes", 0)
                    self._progress = int(down / total * 30) if total else 0
                elif d.get("status") == "finished":
                    self._progress = 30

            ydl_opts = {
                "format": "bestaudio[ext=m4a]/bestaudio",
                "outtmpl": os.path.join(out_dir, "%(title)s.%(ext)s"),
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "progress_hooks": [progress_hook],
            }
            # 解决 YouTube 反爬验证：用户把浏览器导出的 cookies.txt 放到输出目录即自动使用
            cookie_file = os.path.join(self._get_output_dir(), "cookies.txt")
            if os.path.isfile(cookie_file):
                ydl_opts["cookiefile"] = cookie_file

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                audio_path = ydl.prepare_filename(info)
                # prepare_filename 可能带错误扩展名，扫描实际下载文件
                if not os.path.isfile(audio_path):
                    candidates = [
                        os.path.join(out_dir, f)
                        for f in os.listdir(out_dir)
                        if f.endswith((".m4a", ".webm", ".mp3", ".opus", ".flac"))
                    ]
                    if candidates:
                        audio_path = max(candidates, key=os.path.getmtime)
                if not os.path.isfile(audio_path):
                    raise RuntimeError("音频下载失败，未找到输出文件")

            # 阶段 2: 转 wav (30-40%)
            ffmpeg = self._find_ffmpeg()
            if not ffmpeg or not os.path.isfile(ffmpeg):
                raise RuntimeError("未找到 ffmpeg，无法转换音频格式")

            self._stage = "转换音频格式中..."
            wav_path = os.path.splitext(audio_path)[0] + ".wav"
            proc = subprocess.run(
                [ffmpeg, "-y", "-i", audio_path, "-ac", "1", "-ar", "44100", wav_path],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300,
            )
            if proc.returncode != 0:
                raise RuntimeError(f"音频转换失败: {proc.stderr[-200:]}")
            self._progress = 40

            # 阶段 3: 转录 (40-100%)
            from src.transcription import get_transcriber

            self._stage = "转录中..."
            midi_path = os.path.splitext(wav_path)[0] + ".mid"

            def on_progress(pct):
                self._progress = int(40 + pct * 0.6)

            transcriber = get_transcriber("onnx", style=style, mode=mode)
            transcriber.transcribe(wav_path, midi_path, progress_callback=on_progress)
            self._progress = 100
            self._status = "done"
            self._result_path = midi_path
        except Exception as e:
            self._status = "error"
            self._error_msg = self._friendly_video_error(e)

    def _friendly_video_error(self, e: Exception) -> str:
        """把 yt-dlp/下载的原始报错转成用户能看懂的中文提示。"""
        msg = str(e)
        if "Sign in to confirm you're not a bot" in msg or "not a bot" in msg:
            return (
                "YouTube 检测到未登录下载请求，要求验证身份（反机器人验证）。\n"
                "解决办法（任选其一）：\n"
                "1. 换用 B 站等其他平台的视频链接\n"
                "2. 用浏览器导出 YouTube 的 cookies.txt，放到\n"
                "   ~/Music/2midi4lin/cookies.txt 后重试\n"
                "   （Chrome 装 Get cookies.txt LOCALLY 扩展即可导出）"
            )
        if "Video unavailable" in msg:
            return "视频不可用：可能已被删除、设为私密或受地区限制。"
        if "Unsupported URL" in msg or "is not a valid URL" in msg:
            return f"无法识别的链接，请粘贴视频页面地址。\n原始错误：{msg[:150]}"
        if "ffmpeg" in msg.lower() and "not found" in msg.lower():
            return "未找到 ffmpeg 组件，请重新安装软件或检查文件完整性。"
        return msg

    # ---- 音频适配度检测 ----

    def analyze_audio(self, audio_path: str) -> dict:
        """分析音频文件，评估钢琴转录适配度（1-5星）。向量化版本，纯 numpy 运算。"""
        import os as _os, numpy as np, soundfile as sf

        if not _os.path.isfile(audio_path):
            return {"error": "文件不存在", "stars": 0}

        # 只读前30秒，避免大文件全读
        try:
            with sf.SoundFile(audio_path) as f:
                sr = f.samplerate
                n_read = min(len(f), int(30 * sr))
                data = f.read(n_read)
        except Exception as e:
            return {"error": "无法读取音频: " + str(e), "stars": 0}

        if len(data) == 0:
            return {"error": "音频文件为空", "stars": 0}

        if data.ndim > 1:
            data = data.mean(axis=1)

        dur = float(len(data)) / sr
        if dur <= 0:
            return {"error": "音频时长为零", "stars": 0}

        # ---- 频谱特征 (单次 FFT 全向量化) ----
        n = len(data)
        fft = np.fft.rfft(data * np.hanning(n))
        freqs = np.fft.rfftfreq(n, 1.0 / sr)
        spec = np.abs(fft)
        spec_norm = spec / (np.sum(spec) + 1e-10)

        centroid = float(np.sum(freqs * spec_norm))
        spread = float(np.sqrt(np.sum(((freqs - centroid) ** 2) * spec_norm)))

        piano_mask = (freqs >= 55) & (freqs <= 4186)
        piano_energy = float(np.sum(spec[piano_mask] ** 2))
        total_energy = float(np.sum(spec ** 2)) + 1e-10
        piano_ratio = piano_energy / total_energy

        # ---- 零交叉率 (向量化) ----
        zcr = float(np.sum(np.abs(np.diff(np.signbit(data))))) / n

        # ---- 瞬态密度 (向量化: reshape 帧矩阵) ----
        frame_len = int(sr * 0.05)
        n_frames = n // frame_len
        if n_frames > 1:
            frames_data = data[:n_frames * frame_len].reshape(n_frames, frame_len)
            frame_energies = np.sqrt(np.mean(frames_data ** 2, axis=1))
            onset_thresh = float(np.mean(frame_energies) + 1.5 * np.std(frame_energies))
            onsets = int(np.sum(np.diff((frame_energies > onset_thresh).astype(np.float64)) > 0))
        else:
            onsets = 0
        onset_density = onsets / dur

        # ---- 频谱峰值密度 (向量化: 比较相邻三点) ----
        max_spec = float(np.max(spec))
        peaks_mask = (spec[1:-1] > spec[:-2]) & (spec[1:-1] > spec[2:]) & (spec[1:-1] > max_spec * 0.01)
        peaks = int(np.sum(peaks_mask))
        peak_density = peaks / dur

        # ---- 综合评分 ----
        spread_score = max(0.0, 1.0 - (spread - 500) / 1500) if spread > 500 else 1.0
        piano_score = min(1.0, max(0.0, (piano_ratio - 0.3) / 0.5))
        perc_score = max(0.0, 1.0 - zcr / 0.15) if zcr > 0.05 else 1.0
        onset_score = max(0.0, 1.0 - onset_density / 8) if onset_density > 2 else 1.0
        peak_score = max(0.0, 1.0 - peak_density / 20) if peak_density > 5 else 1.0

        weights = [0.25, 0.25, 0.15, 0.15, 0.20]
        raw_scores = [spread_score, piano_score, perc_score, onset_score, peak_score]
        total = sum(w * s for w, s in zip(weights, raw_scores))
        stars = max(1, min(5, round(total * 4 + 1)))

        reasons = []
        if piano_ratio < 0.5:
            reasons.append("非钢琴成分较多")
        if zcr > 0.1:
            reasons.append("打击乐/高频多")
        if onset_density > 5:
            reasons.append("节奏密集")
        if peak_density > 15:
            reasons.append("和声复杂")
        if spread > 1500:
            reasons.append("乐器多/频段宽")

        tips = {
            5: "非常适合！纯钢琴或简单编曲，转录效果会很好",
            4: "较适合，主旋律和和弦能清晰提取",
            3: "还行，能提取旋律骨架，细节会有丢失",
            2: "不太适合，建议选编曲更简单的歌曲",
            1: "不适合，乐器太多或编曲过于复杂",
        }

        return {
            "stars": stars,
            "tips": tips[stars],
            "detail": reasons if reasons else ["编曲较干净"],
        }
    # ============================================================
    #  分享 — kesug.com 抗 bot 挑战处理
    # ============================================================

    _kesug_cookie = None
    _kesug_cookie_ts = 0

    def _solve_challenge_from_html(self, html: str) -> str:
        """从挑战页 HTML 中提取 AES-128-CBC 参数，返回 __test cookie。"""
        import re
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend

        m = re.search(
            r'var a=toNumbers\("([^"]+)"\),b=toNumbers\("([^"]+)"\),c=toNumbers\("([^"]+)"\)',
            html,
        )
        if not m:
            raise RuntimeError("无法解析防bot挑战")

        key = bytes.fromhex(m.group(1))
        iv = bytes.fromhex(m.group(2))
        ct = bytes.fromhex(m.group(3))

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        plain = cipher.decryptor().update(ct) + cipher.decryptor().finalize()
        pad = plain[-1]
        return (plain[:-pad] if 1 <= pad <= 16 else plain).hex()

    def _kesug_request(self, url: str, data: bytes | None = None) -> str:
        """向 kesug.com 发请求，自动处理 JS anti-bot 挑战。

        核心逻辑：从失败响应的 HTML 中提取挑战参数求解，保证 c 值匹配。
        """
        import time, urllib.request

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        if data is not None:
            headers["Content-Type"] = "application/json"

        now = time.time()
        if self._kesug_cookie and now - self._kesug_cookie_ts < 18000:
            headers["Cookie"] = f"__test={self._kesug_cookie}"

        for _ in range(2):
            req = urllib.request.Request(url, data=data, headers=headers)
            try:
                resp = urllib.request.urlopen(req, timeout=15)
                body = resp.read().decode()
            except urllib.error.HTTPError as e:
                body = e.read().decode()

            if "slowAES" not in body:
                return body

            cookie = self._solve_challenge_from_html(body)
            self._kesug_cookie = cookie
            self._kesug_cookie_ts = now
            headers["Cookie"] = f"__test={cookie}"

        return body

    def share_midi(self, share_code: str, title: str, author: str = "") -> dict:
        """提交分享到集合站。"""
        import json, urllib.error

        try:
            SHARE_API = "https://2midi4lin.kesug.com/api.php"

            data = json.dumps({
                "share_code": share_code.strip(),
                "title": title.strip(),
                "author": author.strip(),
                "source": "2midi4lin",
            }).encode("utf-8")

            body = self._kesug_request(SHARE_API, data=data)
            result = json.loads(body)
            return result if isinstance(result, dict) else {"error": str(result)}
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            try:
                return json.loads(body)
            except Exception:
                return {"error": f"HTTP {e.code}: {body}"}
        except Exception as e:
            return {"error": str(e)}
