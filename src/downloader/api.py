"""MIDI search and download manager (multi-source MIDI)."""
import os
from . import config
from .sources import SOURCES


class MusicDownloader:
    """MIDI search/download manager with multi-source support."""

    def __init__(self, download_dir: str = None):
        self.download_dir = download_dir or config.DOWNLOAD_DIR
        os.makedirs(self.download_dir, exist_ok=True)

    # ── Multi-source MIDI search & download ──

    def search_midi(self, keyword: str, sources: list = None, timeout: float = 12.0,
                    on_result: callable = None) -> list:
        """Search MIDI across multiple sources (并发，整体限时，流式回调).

        Args:
            keyword: Search keyword
            sources: Source name list, None = all sources
            timeout: 整体搜索超时秒数（默认 12s，超时后未完成源直接丢弃）
            on_result: 可选回调 on_result(source_name, results)，
                       每个源完成时立即调用（用于流式展示"先到先显示"）

        Returns:
            list[dict]: Each item has id, title, source, url, notes, rating
        """
        import concurrent.futures

        if sources is None:
            # 默认搜索源：仅快速源（响应快、曲库互补）
            #  - bitmidi: 50K+ 游戏/流行/古典
            #  - freemidi: 150K+ 流行/摇滚/古典
            #  - midisss: 音乐剧
            # 慢源（piano-midi 古典、vgmusic 游戏大目录）暂不参与默认搜索
            sources = ["bitmidi", "freemidi", "midisss"]
        results = []

        def _search_one(name: str) -> list:
            src = SOURCES.get(name)
            if src is None:
                return []
            try:
                return src.search(keyword)
            except Exception as e:
                print(f"  [{name}] search error: {e}")
                return []

        ex = concurrent.futures.ThreadPoolExecutor(max_workers=len(sources))
        futures = {ex.submit(_search_one, name): name for name in sources}
        try:
            for fut in concurrent.futures.as_completed(futures, timeout=timeout):
                name = futures[fut]
                try:
                    rs = fut.result()
                    if rs and on_result:
                        on_result(name, rs)
                    results.extend(rs)
                except Exception:
                    pass
        except concurrent.futures.TimeoutError:
            pass  # 超时：下面的取消逻辑处理剩余 futures
        finally:
            # 取消未完成的任务，shutdown 不等待（避免被慢源拖死）
            for fut in futures:
                fut.cancel()
            ex.shutdown(wait=False, cancel_futures=True)
        results.sort(key=lambda r: r.get("rating", 0), reverse=True)
        return results

    def download_midi(self, item: dict, output_dir: str = None) -> str:
        """Download MIDI from the specified source.

        Args:
            item: Search result item (with id, source, title keys)
            output_dir: Output directory

        Returns:
            Absolute path to downloaded file
        """
        source_name = item.get("source", "midisss")
        src = SOURCES.get(source_name)
        if src is None:
            raise RuntimeError(f"Unsupported MIDI source: {source_name}")
        out_dir = output_dir or self.download_dir
        return src.download(item, out_dir)

    def get_all_sources(self) -> dict:
        return {"midi": list(SOURCES.keys())}
