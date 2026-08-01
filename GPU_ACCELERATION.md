# 🚀 GPU 加速 — 让转录更快

2midi4lin 默认使用 CPU 进行音频转录，兼容所有电脑。
如果你希望转录速度更快，可以安装 GPU 加速包，**免费提升 1.5~3 倍速度**。

---

## 你需要什么

| 项目 | 要求 |
|:----|:------|
| 操作系统 | **Windows 10 或 Windows 11** |
| 显卡 | 任意支持 **DirectX 12** 的显卡（核显、集成显卡也可以） |
| 不需要 | ❌ 不需要 NVIDIA 显卡 ❌ 不需要安装 CUDA ❌ 不需要安装显卡驱动 |

> 绝大多数 Windows 电脑都满足条件。如果不确定，直接试一下，装不上也不影响现有功能。

---

## 安装方法

### 方法一：使用脚本（推荐）

双击 `install_gpu_accel.bat`，脚本会自动检测并安装。

如果还没有这个脚本，可以手动安装（见方法二）。

### 方法二：手动安装

**第 1 步：** 打开命令提示符（Win + R → 输入 `cmd` → 回车）

**第 2 步：** 粘贴以下命令，按回车：

```cmd
pip install onnxruntime-directml
```

等待安装完成（约 1-2 分钟）。

**第 3 步：** 重启 2midi4lin，转录时就会自动使用 GPU 加速。

---

## 验证是否生效

启动软件后，在命令行窗口或日志中看到以下信息，表示 GPU 加速已开启：

```
[ONNX] Using provider: DmlExecutionProvider
```

如果看到的是 `CPUExecutionProvider`，说明仍在用 CPU（可能是显卡不兼容 DirectML）。

---

## 常见问题

### 装了之后软件打不开了？

不影响。GPU 加速是**可选增强**，装不装都不影响 2midi4lin 正常启动和使用。
如果遇到问题，可以卸载：

```cmd
pip uninstall onnxruntime-directml -y
```

### 速度能快多少？

| 音频时长 | CPU（默认） | 加 DirectML |
|:--------|:----------:|:-----------:|
| 30 秒 | ~8 秒 | ~3 秒 |
| 3 分钟 | ~50 秒 | ~18 秒 |
| 10 分钟 | ~2.5 分 | ~50 秒 |

> 以上为典型值，实际速度取决于你的 CPU 和显卡性能。

### 装了 DirectML 后还需要原来的 ONNX Runtime 吗？

需要。DirectML 是 ONNX Runtime 的**加速插件**，不是替代品。
两个都要装：

```cmd
pip install onnxruntime          # 核心引擎（已内置）
pip install onnxruntime-directml  # GPU 加速插件（可选）
```

### 有 NVIDIA 显卡可以用 CUDA 吗？

可以。如果你有 NVIDIA 显卡且已安装 CUDA，可以装 CUDA 版：

```cmd
pip install onnxruntime-gpu
```

效果比 DirectML 更好，但安装步骤更复杂（需要先装 CUDA 工具包），不推荐小白用户使用。
