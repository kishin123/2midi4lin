"""MuScriptor 转录引擎封装。

MuScriptor: 钢琴曲音频 → 钢琴 MIDI，多乐器转录。
适用于已有钢琴曲音频，提取钢琴部分并结构化。
"""


class MuScriptorTranscriber:
    """MuScriptor 钢琴曲音频→MIDI 转录器。"""

    def __init__(self, device: str = None):
        self.device = device  # None = auto

    def is_available(self) -> bool:
        """检查模型是否已安装。"""
        # TODO: 检查模型文件是否存在
        return False

    def transcribe(self, audio_path: str, output_path: str = None) -> str:
        """将钢琴曲音频转录为钢琴 MIDI。

        Args:
            audio_path: 输入音频文件路径
            output_path: 输出 MIDI 路径

        Returns:
            输出 MIDI 文件的绝对路径
        """
        raise NotImplementedError(
            "MuScriptor 引擎尚未接入。如需使用，请先安装依赖。"
        )
