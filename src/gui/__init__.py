"""2midi4lin GUI — PyWebView 入口。

启动原生 Windows 窗口，内嵌 Vue3 前端。
通过本地 HTTP 服务器加载前端，确保 pywebview JS API 正常工作。
"""
import sys
import os
import threading
from pathlib import Path


# ---- 前端路径 ----
if getattr(sys, "frozen", False):
    _FRONTEND_DIR = Path(sys._MEIPASS) / "gui"
else:
    _FRONTEND_DIR = Path(__file__).resolve().parent / "frontend" / "dist"

# dev 模式：GUI 直接加载 vite dev server（前端热更新 + 真实 API）
_DEV_SERVER = os.environ.get("2MIDI4LIN_DEV", "").strip()


def _start_server():
    """启动本地 HTTP 服务器提供前端文件。"""
    import http.server
    import socketserver

    socketserver.TCPServer.allow_reuse_address = True

    class _Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(_FRONTEND_DIR), **kwargs)

    handler = _Handler
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return port


def run_gui():
    """启动 GUI 窗口。"""
    try:
        import webview
    except ImportError:
        print("需要安装 pywebview：pip install pywebview")
        sys.exit(1)

    from .api import Api
    api = Api()

    # 检查前端文件是否存在
    index_html = _FRONTEND_DIR / "index.html"
    if not index_html.is_file():
        print(f"[GUI] 前端文件未找到: {index_html}")
        print("请先构建前端: cd src/gui/frontend && npm run build")
        sys.exit(1)

    # 启动本地 HTTP 服务器（避免 file:// 协议下 JS API 失效）
    if _DEV_SERVER:
        # dev 模式：加载 vite dev server，前端改代码保存即热更新
        url = f"http://127.0.0.1:{_DEV_SERVER}/"
        print(f"[GUI] dev 模式: {url}")
    else:
        port = _start_server()
        url = f"http://127.0.0.1:{port}/index.html"

    window = webview.create_window(
        title="2midi4lin - 钢琴 MIDI 转录",
        url=url,
        width=900,
        height=680,
        resizable=True,
        js_api=api,
    )
    api.set_window(window)  # 供选目录对话框使用

    # 原生拖拽支持：用 webview.dom 注册 document drop 事件
    # （PyWebView 会把完整文件路径注入到事件对象 pywebviewFullPath 字段）
    def _on_drop(event):
        files = event.get("dataTransfer", {}).get("files", [])
        if files:
            full = files[0].get("pywebviewFullPath", "")
            print(f"[drop] 收到完整路径: {full!r}", flush=True)
            api.set_dropped_file(full)

    # dom 需等页面加载完成后才可用，挂到 loaded 事件上
    def _on_loaded():
        try:
            window.dom.document.events.drop += _on_drop
            print("[drop] document drop 监听器已注册", flush=True)
        except Exception as e:
            print(f"[drop] dom 注册失败（不影响点击选文件）: {e}", flush=True)

    try:
        window.events.loaded += _on_loaded
    except Exception as e:
        print(f"[drop] loaded 事件注册失败: {e}", flush=True)

    webview.start(debug=not getattr(sys, "frozen", False))
