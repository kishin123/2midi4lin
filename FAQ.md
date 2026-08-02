# 2midi4lin 常见问题（FAQ）

> 使用中遇到问题先看这里。找不到答案可以到 GitHub Issues 反馈。

---

## 1. YouTube 下载报错：`Sign in to confirm you're not a bot`

**现象**：视频转 MIDI 粘贴 YouTube 链接后，提示：

```
ERROR: [youtube] xxxxx: Sign in to confirm you're not a bot.
Use --cookies-from-browser or --cookies for the authentication.
```

**原因**：YouTube 对未登录的下载请求做反机器人验证（服务器 IP / 频繁访问更容易触发）。这是 YouTube 的限制，不是软件 bug。

**解决办法**（任选其一）：

- **换用 B 站链接**：大部分钢琴演奏视频 B 站都有，直接粘贴 B 站链接即可，不受此限制。
- **使用 cookies 认证**：
  1. Chrome 安装扩展「Get cookies.txt LOCALLY」（导出 YouTube 登录 cookies）
  2. 打开 YouTube 并登录你的账号
  3. 用扩展导出 cookies.txt 文件
  4. 把文件放到 `~/Music/2midi4lin/cookies.txt`（即保存目录下），重新下载
  5. 软件检测到该文件会自动使用，之后 YouTube 下载不再弹验证

> 提示：cookies.txt 包含你的登录凭证，请勿把文件发给他人。

---

## 2. 弹窗报错：`Failed loading SDL3 library`

**现象**：下载视频转 MIDI 过程中弹出错误框「Failed loading SDL3 library.」

**原因**：这是 **v0.2.0 之前旧版本**的打包缺陷——内置 ffmpeg 带了一个 SDL 兼容库（SDL2.dll），它需要系统存在 SDL3.dll 才能工作；部分电脑没有 SDL3.dll 就会弹窗。**你的电脑没问题，是软件包的问题**。

**解决办法**：**更新到最新版 exe**（v0.2.0 及以后已修复，打包时移除了该依赖）。重新从 GitHub Release 下载即可，无需安装任何额外组件。

---

## 3. 产物保存到哪？怎么改目录？

**默认位置**：exe 所在目录下的子文件夹：

```
exe 同目录/
├── transcribe/   ← 音频转录的 MIDI
├── videos/       ← 视频转 MIDI 的产物
└── downloads/    ← 搜索下载的 MIDI
```

- exe 放在只读位置（如 Program Files）时，自动回退到 `~/Music/2midi4lin/`
- **自定义目录**：软件界面底部「📁 保存目录」→「选择目录」，重启后依然生效（配置保存在 `~/.2midi4lin/config.json`）
- 「恢复默认」可随时还原为 exe 所在目录

---

## 4. 源码运行提示模型文件缺失

**现象**：用源码（`python -m src.cli gui`）运行时转录报找不到 `apc.onnx` / `amt.onnx`。

**说明**：
- **exe 用户**：模型已内置在安装包中，无需任何操作
- **源码用户**：模型权重约 46MB 未进 git 仓库，需从 GitHub Release 页面下载 `models.zip`，解压后把 `models` 文件夹放到 `src/transcription/models/` 下

---

## 5. 其他常见提示

| 提示 | 含义与处理 |
|:----|:----|
| `视频不可用` | 视频被删除、设私密或受地区限制，换个视频试试 |
| `无法识别的链接` | 请粘贴完整的视频页面地址（浏览器地址栏复制） |
| `未找到 ffmpeg` | 软件文件不完整，重新下载完整版 exe |

---

*最后更新：2026-08-03（v0.2.0）*
