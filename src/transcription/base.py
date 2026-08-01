"""Abstract base class for transcription backends."""
from abc import ABC, abstractmethod


class TranscribeBase(ABC):
    """所有转录后端的抽象基类。

    Args:
        style: 翻弹风格 ("level1" / "level2" / "level3")
    """

    @abstractmethod
    def transcribe(self, audio_path: str, output_path: str = None,
                   progress_callback=None) -> str:
        """将音频文件转录为钢琴 MIDI。

        Args:
            audio_path: 输入音频文件路径
            output_path: 输出 MIDI 路径，None 则自动生成
            progress_callback: 进度回调函数，接收 0-100 整数

        Returns:
            输出 MIDI 文件的绝对路径
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """检查后端是否可用（模型文件存在等）。"""
        ...
