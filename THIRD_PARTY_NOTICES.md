# 第三方开源项目许可声明（Third-Party Notices）

2midi4lin 基于以下开源项目构建，在此致以谢意。各项目版权归其作者所有，许可证全文见各项目仓库。

---

## 模型与算法

### AMT-APC（模型基础权重 / 微调来源）
- **项目**：AMT-APC: Automatic Piano Cover by Fine-Tuning an Automatic Music Transcription Model
- **来源**：https://github.com/310hz/amt-apc · 论文 arXiv:2409.14086
- **许可证**：MIT License（Copyright (c) 2024 Komiya）
- **用途**：2midi4lin 的翻奏改编（APC）模型基于 AMT-APC 的预训练权重微调/ONNX 化

### hFT-Transformer（模型架构）
- **项目**：Automatic Piano Transcription with Hierarchical Frequency-Time Transformer
- **来源**：https://github.com/sony/hFT-Transformer · ISMIR 2023 · arXiv:2307.04305
- **许可证**：MIT License（© 2023 Sony）
- **作者**：Keisuke Toyama, Taketo Akama, Yukara Ikemiya, Yuhta Takida, Wei-Hsiang Liao, Yuki Mitsufuji
- **用途**：2midi4lin 的忠实转录（AMT）模型基于 hFT-Transformer 架构与预训练权重

---

## Python 依赖

| 项目 | 许可证 | 来源 |
|:-----|:-------|:-----|
| onnxruntime | MIT | https://github.com/microsoft/onnxruntime |
| onnxruntime-directml | MIT | https://onnxruntime.ai |
| numpy | BSD-3-Clause | https://numpy.org |
| soundfile | BSD-3-Clause | https://pypi.org/project/SoundFile/ |
| pretty_midi | MIT | https://github.com/craffel/pretty-midi |
| pywebview | BSD-3-Clause | https://pywebview.flowrl.com |
| yt-dlp | Unlicense | https://github.com/yt-dlp/yt-dlp |
| requests | Apache-2.0 | https://requests.readthedocs.io |

---

## 前端

| 项目 | 许可证 | 来源 |
|:-----|:-------|:-----|
| Vue.js | MIT | https://vuejs.org |
| Vite | MIT | https://vitejs.dev |
| TypeScript | Apache-2.0 | https://www.typescriptlang.org |

---

## 内置工具

### FFmpeg（静态构建）
- **来源**：https://www.gyan.dev/ffmpeg/builds/（essentials build 7.1，经 imageio-ffmpeg 分发）
- **许可证**：**GPL-2.0-or-later**（构建启用 libx264/libx265 等 GPL 组件）
- **用途**：视频转 MIDI 的音频抽取、yt-dlp 下载合并
- **说明**：2midi4lin 通过命令行（subprocess）以独立进程方式调用 ffmpeg，未与其链接。
  FFmpeg 源码：https://ffmpeg.org/download.html

---

## 分享网站

- **作品分享站**：2midi4lin.kesug.com（托管于 InfinityFree / kesug，非开源项目）
