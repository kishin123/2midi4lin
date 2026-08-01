"""Transcription backend factory.

Usage:
    from src.transcription import get_transcriber

    # ONNX Runtime backend (default, lightweight, for distribution)
    t = get_transcriber("onnx", style="level2")
    t.transcribe("song.mp3", "piano.mid")

    # PyTorch backend (requires torch, for advanced users)
    t = get_transcriber("torch", device="cuda", style="level3")
"""


def get_transcriber(backend="onnx", device=None, style="level2", mode="apc"):
    """获取转录后端实例。

    Args:
        backend: "onnx" 或 "torch"
        device: 推理设备 (auto/cuda/cpu)，仅 torch 后端生效
        style: 翻弹风格 ("level1" / "level2" / "level3")，仅 apc 模式生效
        mode: "apc"（翻奏改编，默认）或 "amt"（忠实转录，适合钢琴独奏）

    Returns:
        TranscribeBase 子类实例
    """
    if backend == "onnx":
        from .onnx_transcriber import ONNXTranscriber
        return ONNXTranscriber(style=style, mode=mode)
    elif backend == "torch":
        from .torch_transcriber import TorchTranscriber
        return TorchTranscriber(device=device, style=style)
    else:
        raise ValueError(f"未知后端: {backend}，可用: onnx, torch")
