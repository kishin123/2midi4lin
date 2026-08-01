# 2midi4lin

把任意音频变成钢琴独奏 MIDI 的桌面工具：转录 / 视频转 MIDI / 下载钢琴谱，一条龙。

基于 [AMT-APC](https://arxiv.org/abs/2409.14086)（hFT-Transformer 微调的钢琴翻奏模型，ONNX 内嵌，纯 CPU 可跑）。

## 功能

| 模块 | 说明 |
|:----|:----|
| 🎹 **转录** | 拖拽/选择音频文件 → 钢琴独奏 MIDI（原生 MIDI 输出，可选轻柔/标准/华丽三档风格） |
| 🎬 **视频转 MIDI** | 粘贴 YouTube/B 站视频链接 → 自动下载音频 → 转录成 MIDI（与本地文件二选一互斥） |
| 📤 **分享** | 转录/视频完成后自动弹出分享窗，从林离软件获取分享码，曲名手动打开时可编辑 |
| 📥 **下载** | 智能搜索栏：歌名搜索多源 MIDI，或粘贴 MuseScore 乐谱链接直接下载 |

所有产物统一保存在 `~/Music/2midi4lin/`（`transcribe` / `videos` / `downloads` 子目录）。

## 快速开始

### 桌面 GUI（正式运行）

```powershell
python -m src.cli gui
```

### 开发模式（改前端热更新，无需打包）

双击 `dev.bat`，或：

```powershell
python -m src.cli dev
```

自动完成：启动 vite dev server（2 秒就绪，端口 5173 可复用）→ 等待端口 → 启动 PyWebView 窗口连 dev server → 改前端代码保存即热更新。

### 命令行子命令

```powershell
python -m src.cli transcribe input.wav        # 音频 → 钢琴 MIDI
python -m src.cli process input.mid            # MIDI 后处理（分轨+限流+踏板）
python -m src.cli download "歌名"              # 多源搜索下载
```

## 打包 exe

```powershell
pyinstaller 2midi4lin.spec
```

产物在 `dist/`。当前体积约 125MB（含 yt-dlp 全量 extractors + 内置精简 ffmpeg 21MB），目标控制在 100MB 内。

## 文档

- [MODEL_RESEARCH.md](MODEL_RESEARCH.md) — 模型选型记录（AMT-APC vs Etude/MuScriptor/Pop2Piano 完整对比）
- [MIDI_SOURCES.md](MIDI_SOURCES.md) — 钢琴 MIDI 资源站汇总与下载源调度
- [GPU_ACCELERATION.md](GPU_ACCELERATION.md) — 可选 GPU 加速（onnxruntime-directml）

## 模型获取

转录所需的 ONNX 权重（apc.onnx 22MB / amt.onnx 22.8MB）**不在本仓库**，从 Release 下载：

- 直接使用：下载 [Releases](https://github.com/kishin123/2midi4lin/releases) 里的 **2midi4lin.exe**（模型已内嵌，双击即用）
- 源码运行：下载同 Release 里的 **models.zip**，解压到 `src/transcription/models/` 即可

权重来源：`apc.onnx` 由 [AMT-APC](https://github.com/310hz/amt-apc) 官方 `apc.pth` 转换；`amt.onnx` 由官方 `amt.pth`（hFT-Transformer MAESTRO 权重）转换。

## 技术栈

- 后端：Python 3.10+ / onnxruntime / PyWebView / yt-dlp / pretty_midi
- 前端：Vue 3 + Vite（开发热更新，生产构建后由 PyWebView 加载）
- 转录模型：AMT-APC ONNX（FP32，纯 numpy mel 谱无 torch 依赖）+ hFT-Transformer ONNX（忠实转录模式）
