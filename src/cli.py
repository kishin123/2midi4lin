"""2midi4lin CLI — subcommand entry point.

Usage:
    2midi4lin transcribe <audio> [options]   audio -> piano MIDI
    2midi4lin process <midi> [options]       MIDI post-process (split+limit+pedal)
    2midi4lin download [options]             search & download piano MIDI
"""
import argparse
import sys
import os


def cmd_transcribe(args):
    """audio -> MIDI transcription."""
    from src.transcription import get_transcriber

    output = args.output or (os.path.splitext(os.path.basename(args.input))[0] + ".mid")
    transcriber = get_transcriber(args.backend, device=args.device, style=args.style)
    result = transcriber.transcribe(args.input, output)
    if not args.no_post_process:
        from src.pipeline.postprocess import process_midi
        processed = os.path.splitext(output)[0] + "_pedal.mid"
        stats = process_midi(result, processed)
        print(f"  post-processed: {stats['total_notes']} notes, {stats['cc64_events']} CC64")
        result = processed
    print(f"output: {result}")


def cmd_process(args):
    """MIDI post-process (split + limit + pedal)."""
    from src.pipeline.postprocess import process_midi
    output = args.output or (os.path.splitext(os.path.basename(args.input))[0] + "_pedal.mid")
    stats = process_midi(args.input, output, max_note_dur=args.max_duration,
                         split_point=args.split_point, max_hand=args.max_hand,
                         hand_span=args.hand_span, max_nps=args.max_nps, max_leap=args.max_leap)
    print(f"input: {stats['input_notes']} notes")
    print(f"right: {stats['right_notes']} notes")
    print(f"left: {stats['left_notes']} notes")
    print(f"CC64: {stats['cc64_events']} events")
    print(f"output: {output}")


def cmd_download(args):
    """Search and download piano MIDI from multiple sources."""
    from src.downloader import MusicDownloader
    dl = MusicDownloader(download_dir=args.output_dir)

    if not args.query:
        print("Usage: 2midi4lin download <keyword> [options]")
        print(f"  Available sources: {', '.join(dl.get_all_sources()['midi'])}")
        return

    results = dl.search_midi(args.query, sources=args.source)
    if not results:
        print("No results found")
        return
    shown = results[:args.limit]
    sources = set(r["source"] for r in shown)
    print(f"Found {len(shown)} results (from {len(sources)} sources):")
    for r in shown:
        rating_str = f" (rating: {r['rating']})" if r.get('rating') else ""
        print(f"  [{r['source']}] {r['title']}{rating_str}")

    if args.download_id:
        # Parse "source:id" format (e.g. "midisss:12345")
        if ":" in args.download_id:
            src_name, item_id = args.download_id.split(":", 1)
        else:
            src_name, item_id = "midisss", args.download_id
        item = None
        for r in results:
            if r["id"] == item_id and r["source"] == src_name:
                item = r
                break
        if not item:
            item = {"id": item_id, "source": src_name, "title": item_id}
        path = dl.download_midi(item)
        print(f"Downloaded: {path}")


def cmd_gui(args):
    """Launch desktop GUI (PyWebView)."""
    from src.gui import run_gui
    run_gui()


def cmd_dev(args):
    """开发模式：自动启动 vite dev server + GUI（前端热更新，无需手动设环境变量）。"""
    import os
    import socket
    import subprocess
    import sys
    import time
    from pathlib import Path

    port = int(args.port)
    frontend_dir = Path(__file__).resolve().parent / "gui" / "frontend"
    vite_log = frontend_dir.parent.parent.parent / "vite_dev.log"

    def port_open(port):
        s = socket.socket()
        s.settimeout(0.5)
        try:
            s.connect(("127.0.0.1", port))
            return True
        except Exception:
            return False
        finally:
            s.close()

    # 若端口已被占用，视为 dev server 已在运行，直接复用
    if port_open(port):
        print(f"[dev] 端口 {port} 已有服务，直接复用")
    else:
        print(f"[dev] 启动 vite dev server (port {port}) ...")
        log_f = open(str(vite_log), "w", encoding="utf-8")
        subprocess.Popen(
            ["npx.cmd", "vite", "--port", str(port), "--strictPort"],
            cwd=str(frontend_dir),
            stdout=log_f, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
        )
        # 等待端口就绪（最长 20s）
        for _ in range(40):
            if port_open(port):
                break
            time.sleep(0.5)
        if not port_open(port):
            print(f"[dev] vite 启动失败，日志见 {vite_log}")
            sys.exit(1)
        print(f"[dev] vite 就绪: http://127.0.0.1:{port}/")

    os.environ["2MIDI4LIN_DEV"] = str(port)
    print(f"[dev] 启动 GUI（连 dev server，前端改代码保存即热更新）...")
    from src.gui import run_gui
    run_gui()


def main():
    parser = argparse.ArgumentParser(
        description="2midi4lin - Piano MIDI toolset", prog="2midi4lin",
    )
    parser.add_argument("--version", action="version", version="2midi4lin 0.1.0")

    sub = parser.add_subparsers(dest="cmd", help="subcommand")

    # transcribe
    p = sub.add_parser("transcribe", help="audio -> piano MIDI")
    p.add_argument("input", help="input audio (mp3/wav/flac/ogg)")
    p.add_argument("-o", "--output", help="output MIDI path")
    p.add_argument("--model", choices=["amt-apc", "muscriptor"], default="amt-apc",
                   help="transcription model (default: amt-apc)")
    p.add_argument("--backend", choices=["onnx", "torch"], default="onnx",
                   help="transcription backend (default: onnx)")
    p.add_argument("--device", default="auto", help="device (auto/cuda/cpu)")
    p.add_argument("--style", choices=["level1", "level2", "level3"], default="level2",
                   help="cover style (default: level2)")
    p.add_argument("--no-post-process", action="store_true", default=False,
                   help="skip auto post-process after transcription")
    p.set_defaults(func=cmd_transcribe)

    # process
    p = sub.add_parser("process", help="MIDI post-process (split+limit+pedal)")
    p.add_argument("input", help="input MIDI file")
    p.add_argument("-o", "--output", help="output MIDI path")
    p.add_argument("--max-duration", type=float, default=0.8, help="max note duration in seconds (default: 0.8)")
    p.add_argument("--split-point", type=int, default=60, help="hand split pitch (default: 60=C4)")
    p.add_argument("--max-hand", type=int, default=5, help="max simultaneous notes per hand (default: 5)")
    p.add_argument("--hand-span", type=int, default=12, help="max hand span in semitones (default: 12)")
    p.add_argument("--max-nps", type=int, default=14, help="max notes per second per hand (default: 14)")
    p.add_argument("--max-leap", type=int, default=24, help="max leap in semitones (default: 24)")
    p.set_defaults(func=cmd_process)

    # download
    p = sub.add_parser("download", help="search and download piano MIDI")
    p.add_argument("query", nargs="?", default="", help="search keyword")
    p.add_argument("-o", "--output-dir", help="download directory")
    p.add_argument("--source", nargs="*", help="MIDI sources (default: all); options: bitmidi freemidi piano-midi vgmusic midisss")
    p.add_argument("--limit", type=int, default=10, help="max results (default: 10)")
    p.add_argument("--download-id", help="download by source:id (e.g. midisss:12345)")
    p.set_defaults(func=cmd_download)

    # gui subcommand
    p = sub.add_parser("gui", help="launch desktop GUI (PyWebView)")
    p.set_defaults(func=cmd_gui)

    # dev subcommand: vite dev server + GUI 热更新
    p = sub.add_parser("dev", help="开发模式：vite 热更新 + GUI（自动起 dev server）")
    p.add_argument("--port", type=int, default=5173, help="vite dev server 端口（默认 5173）")
    p.set_defaults(func=cmd_dev)

    args = parser.parse_args()
    if args.cmd is None:
        # 无参数时默认启动 GUI（小白用户双击 exe 直接进界面）
        cmd_gui(args)
        return
    args.func(args)


if __name__ == "__main__":
    main()
