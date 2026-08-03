"""Multi-source MIDI search and download.

Sources:
  - freemidi.org: 150K+ MIDIs (pop, rock, classical), search + getter download
  - piano-midi.de: 400+ classical piano MIDIs, direct .mid links by composer
  - bitmidi.com: 50K+ MIDIs (games, pop, classical), SSR search
  - midisss.com: REST API, ~200 musical-theater MIDIs
  - vgmusic.com: 30K+ video game MIDIs, piano directory focused
"""
import json
import re
import os
import urllib.request
import urllib.error
from urllib.parse import quote


class BaseSource:
    name = "base"
    label = "Base"

    def search(self, keyword: str) -> list:
        raise NotImplementedError

    def download(self, item: dict, output_dir: str) -> str:
        raise NotImplementedError


class FreeMIDISource(BaseSource):
    """freemidi.org — 150K+ MIDIs (pop, rock, classical, etc).

    Search returns /download3-{id}-{slug} links; actual MIDI is at /getter-{id}
    with proper Referer header. Uses requests for cookie/session support.
    """
    name = "freemidi"
    label = "FreeMIDI"
    _BASE = "https://freemidi.org"
    _UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    def search(self, keyword):
        url = f"{self._BASE}/search?q={quote(keyword)}"
        req = urllib.request.Request(url, headers={"User-Agent": self._UA})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="replace")
        except Exception:
            return []
        results = []
        # Find download3-{id}-{slug} links (note: href=download3-... without quotes)
        for match in re.finditer(
            r'href=download3-(\d+)-([^\s>]+)[^>]*>([^<]+)</a>',
            html,
        ):
            midi_id = match.group(1)
            slug = match.group(2)
            title = match.group(3).strip()
            results.append({
                "id": midi_id,
                "title": title,
                "source": self.name,
                "slug": slug,
                "url": f"{self._BASE}/download3-{midi_id}-{slug}",
                "notes": "FreeMIDI.org",
                "rating": 0,
            })
        # Deduplicate by id
        seen = set()
        unique = []
        for r in results:
            if r["id"] not in seen:
                seen.add(r["id"])
                unique.append(r)
        return unique[:50]

    def download(self, item, output_dir):
        midi_id = item["id"]
        slug = item.get("slug", f"{midi_id}-unknown")
        os.makedirs(output_dir, exist_ok=True)
        safe = re.sub(r'[\\/:*?"<>|]', "_", item.get("title", midi_id))
        dest = os.path.join(output_dir, f"freemidi_{safe}.mid")

        # Need requests for session/cookie support
        import requests as req_lib
        session = req_lib.Session()
        session.headers.update({"User-Agent": self._UA})

        # Step 1: visit song page to get cookies
        song_url = f"{self._BASE}/download3-{midi_id}-{slug}"
        session.get(song_url, timeout=10)

        # Step 2: access getter endpoint with Referer
        getter_url = f"{self._BASE}/getter-{midi_id}"
        resp = session.get(
            getter_url,
            headers={"Referer": song_url},
            timeout=12,
        )
        data = resp.content
        if data[:4] != b"MThd":
            raise RuntimeError(f"not valid MIDI (id={midi_id})")
        with open(dest, "wb") as f:
            f.write(data)
        return os.path.abspath(dest)


class PianoMIDIDESource(BaseSource):
    """piano-midi.de — 400+ classical piano MIDIs by Bernd Krueger.

    Organized by composer (bach, beeth, chopin, etc). Each composer page lists
    MIDI files with descriptive filenames. Search filters filenames in-memory.
    """
    name = "piano-midi"
    label = "Piano-MIDI"
    _BASE = "http://piano-midi.de"
    _UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    _COMPOSER_PAGES = [
        "bach", "beeth", "borodin", "brahms", "burgm", "chopin",
        "debuss", "godowsky", "grana", "grieg", "haydn", "liszt",
        "mozart", "ravel", "sinding",
    ]
    _composer_cache: dict = {}

    def _scrape_composer(self, page: str) -> list:
        if page in self._composer_cache:
            return self._composer_cache[page]

        url = f"{self._BASE}/{page}.htm"
        req = urllib.request.Request(url, headers={"User-Agent": self._UA})
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                html = resp.read().decode("utf-8", errors="replace")
        except Exception:
            return []

        results = []
        seen_paths = set()
        # Find all .mid links and use filename as title
        for match in re.finditer(r'href="([^"]*\.mid)"', html, re.I):
            href = match.group(1)
            if not href.startswith("http"):
                href = f"{self._BASE}/{href}"
            if href in seen_paths:
                continue
            seen_paths.add(href)

            # Build a clean title from the filename
            fname = href.rstrip("/").split("/")[-1].replace(".mid", "")
            # Convert underscores to spaces and capitalize
            title = fname.replace("_", " ").title()
            # Add composer context from page name
            results.append({
                "id": href,
                "title": title,
                "source": self.name,
                "url": href,
                "notes": f"Classical piano ({page})",
                "rating": 0,
            })
        self._composer_cache[page] = results
        return results

    def search(self, keyword):
        kw = keyword.lower()
        all_results = []
        # 并发抓取全部作曲家页面，避免串行 15×8s 超时拖慢整体搜索
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def _fetch(page):
            return self._scrape_composer(page)

        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(_fetch, p) for p in self._COMPOSER_PAGES]
            for fut in as_completed(futures):
                try:
                    entries = fut.result()
                except Exception:
                    continue
                for entry in entries:
                    if kw in entry["title"].lower():
                        all_results.append(entry)
        return all_results[:50]

    def download(self, item, output_dir):
        midi_url = item["id"]
        os.makedirs(output_dir, exist_ok=True)
        fname = midi_url.split("/")[-1]
        dest = os.path.join(output_dir, f"pianomidi_{fname}")
        req = urllib.request.Request(midi_url, headers={"User-Agent": self._UA})
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = resp.read()
        except urllib.error.URLError as e:
            raise RuntimeError(f"piano-midi.de download failed: {e}")
        with open(dest, "wb") as f:
            f.write(data)
        return os.path.abspath(dest)


class BitMidiSource(BaseSource):
    """bitmidi.com — 50K+ MIDIs (games, pop, classical). SSR search via initStore."""
    name = "bitmidi"
    label = "BitMidi"
    _BASE = "https://bitmidi.com"
    _UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    def search(self, keyword):
        url = f"{self._BASE}/search?q={quote(keyword)}"
        req = urllib.request.Request(url, headers={"User-Agent": self._UA})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="replace")
        except Exception:
            return []

        start = html.find("initStore =")
        if start < 0:
            return []
        json_start = html.index("{", start)
        depth = 0
        for i in range(json_start, len(html)):
            if html[i] == "{":
                depth += 1
            elif html[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        data = json.loads(html[json_start : i + 1])
                    except Exception:
                        return []
                    break
        else:
            return []

        midis_dict = data.get("data", {}).get("midis", {})
        results = []
        for slug, midi in midis_dict.items():
            midi_id = midi.get("id")
            name = midi.get("name", slug)
            results.append({
                "id": str(midi_id),
                "title": name.replace(".mid", ""),
                "source": self.name,
                "url": f"{self._BASE}{midi.get('url', '')}",
                "notes": f"👁{midi.get('views', 0)} ▶{midi.get('plays', 0)}",
                "rating": midi.get("views", 0),
            })
        results.sort(key=lambda r: int(r.get("rating", 0)), reverse=True)
        return results[:50]

    def download(self, item, output_dir):
        midi_id = item["id"]
        os.makedirs(output_dir, exist_ok=True)
        safe = re.sub(r'[\\/:*?"<>|]', "_", item.get("title", midi_id))
        dest = os.path.join(output_dir, f"bitmidi_{safe}.mid")
        url = f"{self._BASE}/uploads/{midi_id}.mid"
        req = urllib.request.Request(
            url, headers={"User-Agent": self._UA, "Referer": self._BASE}
        )
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = resp.read()
        except urllib.error.URLError as e:
            raise RuntimeError(f"BitMidi download failed: {e}")
        with open(dest, "wb") as f:
            f.write(data)
        return os.path.abspath(dest)


class MidisssSource(BaseSource):
    """midisss.com — REST API, ~200 musical-theater MIDIs."""
    name = "midisss"
    label = "MIDIsss"
    _UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    def search(self, keyword):
        url = f"https://midisss.com/api.php?action=search&q={quote(keyword)}"
        req = urllib.request.Request(url, headers={"User-Agent": self._UA})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                items = json.loads(resp.read().decode("utf-8", errors="replace"))
        except Exception:
            return []
        results = []
        for item in items:
            midi_id = item.get("id")
            if midi_id is None:
                continue
            results.append({
                "id": str(midi_id),
                "title": item.get("name", ""),
                "source": self.name,
                "url": f"https://midisss.com/midi/{midi_id}",
                "notes": item.get("notes", ""),
                "rating": item.get("average_rating", 0),
            })
        return results

    def download(self, item, output_dir):
        midi_id = item["id"]
        os.makedirs(output_dir, exist_ok=True)
        safe = re.sub(r'[\\/:*?"<>|]', "_", item.get("title", midi_id))
        dest = os.path.join(output_dir, f"{safe}.mid")
        url = f"https://midisss.com/api.php?action=get_midi&id={midi_id}"
        req = urllib.request.Request(url, headers={"User-Agent": self._UA})
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = resp.read()
        except urllib.error.URLError as e:
            raise RuntimeError(f"download failed (id={midi_id}): {e}")
        if data[:4] != b"MThd":
            raise RuntimeError(f"not valid MIDI (id={midi_id})")
        with open(dest, "wb") as f:
            f.write(data)
        return os.path.abspath(dest)


class VGMusicSource(BaseSource):
    """vgmusic.com — 30K+ game MIDIs. Scrapes multiple platform directories."""
    name = "vgmusic"
    label = "VGMusic"
    _BASE = "https://www.vgmusic.com"
    _UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    # Platform directories: (path, short_label)
    # ~15s timeout per dir; slow dirs are skipped silently after timeout.
    _SEARCH_DIRS = [
        ("/music/other/miscellaneous/piano/", "Piano"),
        ("/music/console/nintendo/nes/", "NES"),
        ("/music/console/nintendo/snes/", "SNES"),
        ("/music/console/nintendo/n64/", "N64"),
        ("/music/console/nintendo/gameboy/", "GB"),
        ("/music/console/nintendo/gba/", "GBA"),
        ("/music/console/nintendo/gamecube/", "GC"),
        ("/music/console/nintendo/ds/", "DS"),
        ("/music/console/sony/ps1/", "PS1"),
        ("/music/console/sega/genesis/", "Genesis"),
        ("/music/console/sega/dreamcast/", "Dreamcast"),
        ("/music/other/miscellaneous/arcade/", "Arcade"),
        ("/music/other/miscellaneous/medley/", "Medley"),
    ]
    _dir_cache: dict = {}
    _lock: "threading.Lock" = None

    def __init__(self):
        super().__init__()
        import threading
        self._lock = threading.Lock()

    def _scrape_dir(self, path: str, label: str) -> list:
        cache_key = f"{path}|{label}"
        with self._lock:
            if cache_key in self._dir_cache:
                return self._dir_cache[cache_key]
        url = f"{self._BASE}{path}"
        req = urllib.request.Request(url, headers={"User-Agent": self._UA})
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                html = resp.read().decode("utf-8", errors="replace")
        except Exception:
            with self._lock:
                self._dir_cache[cache_key] = []
            return []
        results = []
        for match in re.finditer(
            r'href="([^"]*\.mid)"[^>]*>([^<]+)</a>', html, re.I
        ):
            href = match.group(1)
            title = match.group(2).strip()
            if not href.startswith("/"):
                href = path + href
            results.append({
                "id": href,
                "title": title,
                "source": self.name,
                "url": f"{self._BASE}{href}",
                "notes": f"VGMusic {label}",
                "rating": 0,
            })
        with self._lock:
            self._dir_cache[cache_key] = results
        return results

    def search(self, keyword):
        kw = keyword.lower()
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # 整体限时 8s：慢目录直接跳过，不拖慢整体搜索
        deadline = time.time() + 8.0

        def fetch(path_label):
            dir_path, label = path_label
            return self._scrape_dir(dir_path, label)

        all_results = []
        ex = ThreadPoolExecutor(max_workers=8)
        futures = {ex.submit(fetch, pl): pl for pl in self._SEARCH_DIRS}
        try:
            for fut in as_completed(futures, timeout=8.0):
                if time.time() > deadline:
                    break
                try:
                    entries = fut.result()
                except Exception:
                    continue
                for entry in entries:
                    if kw in entry["title"].lower():
                        all_results.append(entry)
        except Exception:
            pass
        finally:
            # 取消未完成目录抓取，不等待（避免慢目录拖死）
            for fut in futures:
                fut.cancel()
            ex.shutdown(wait=False, cancel_futures=True)
        return all_results[:50]

    def download(self, item, output_dir):
        midi_path = item["id"]
        os.makedirs(output_dir, exist_ok=True)
        safe = re.sub(r'[\\/:*?"<>|]', "_", item.get("title", "unknown"))
        dest = os.path.join(output_dir, f"vgm_{safe}.mid")
        url = f"{self._BASE}{midi_path}"
        req = urllib.request.Request(url, headers={"User-Agent": self._UA})
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = resp.read()
        except urllib.error.URLError as e:
            raise RuntimeError(f"VGMusic download failed: {e}")
        with open(dest, "wb") as f:
            f.write(data)
        return os.path.abspath(dest)


class MuseScoreSource(BaseSource):
    """MuseScore.com — 百万级用户上传乐谱库。

    通过 py-librescore 下载。不支持关键词搜索（搜索需 JS 渲染），
    用户需提供乐谱 URL。
    """
    name = "musescore"
    label = "MuseScore"
    _UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    def search(self, keyword):
        return []

    def download(self, item, output_dir):
        from py_librescore import MuseScore, FileType
        from pathlib import Path
        url = item["id"]
        ms = MuseScore()
        score = ms.get_score(url)
        score.save(FileType.MIDI, Path(output_dir))
        midi_dir = Path(output_dir)
        midis = list(midi_dir.glob("*.mid"))
        if midis:
            return str(midis[0].resolve())
        raise RuntimeError(f"MuseScore MIDI download failed: {url}")


# Source registry — search order: fastest/most relevant first
SOURCES = {
    "bitmidi": BitMidiSource(),
    "freemidi": FreeMIDISource(),
    "piano-midi": PianoMIDIDESource(),
    "vgmusic": VGMusicSource(),
    "midisss": MidisssSource(),
    "musescore": MuseScoreSource(),
}
