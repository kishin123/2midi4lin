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

产物默认保存在 **exe 所在目录**（`transcribe` / `videos` / `downloads` 子目录），界面「📁 保存目录」可自定义；exe 目录不可写时自动回退到 `~/Music/2midi4lin/`。

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

产物在 `dist/`。当前体积约 151MB（含 yt-dlp 全量 extractors + 内置精简 ffmpeg + ONNX 模型）。

## 常见问题（FAQ）

- **YouTube 报错 `Sign in to confirm you're not a bot`** → YouTube 反爬验证，见 [FAQ.md](FAQ.md) 第 1 条
- **弹窗 `Failed loading SDL3 library`** → 旧版本问题（v0.2.0 已修复），更新到最新版即可
- **产物保存到哪 / 怎么改目录** → 默认 exe 所在目录，界面「📁 保存目录」可自定义，见 [FAQ.md](FAQ.md) 第 3 条

完整排查指南见 [FAQ.md](FAQ.md)。

## 文档

- [USER_GUIDE.md](USER_GUIDE.md) — 面向用户的使用说明（转录/视频/下载/分享完整流程）
- [FAQ.md](FAQ.md) — 常见问题排查（YouTube 反爬 / SDL3 弹窗 / 保存目录）
- [MODEL_RESEARCH.md](MODEL_RESEARCH.md) — 模型选型记录（AMT-APC vs Etude/MuScriptor/Pop2Piano 完整对比）
- [MIDI_SOURCES.md](MIDI_SOURCES.md) — 钢琴 MIDI 资源站汇总与下载源调度
- [GPU_ACCELERATION.md](GPU_ACCELERATION.md) — 内置 DirectML GPU 加速（开箱即用，自动回退 CPU）

## 技术栈

- 后端：Python 3.10+ / onnxruntime / PyWebView / yt-dlp / pretty_midi
- 前端：Vue 3 + Vite（开发热更新，生产构建后由 PyWebView 加载）
- 转录模型：AMT-APC ONNX（`src/transcription/models/apc.onnx`，22MB FP32，纯 numpy mel 谱无 torch 依赖）
