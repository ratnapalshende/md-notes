import asyncio
import signal
from pathlib import Path
from aiohttp import web
from .renderer import render_file, render_index
from .watcher import start_watcher


async def run_server(path: str, port: int):
    app = web.Application()
    clients = set()  # connected WebSocket clients
    base_path = Path(path).resolve()

    async def ws_handler(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        clients.add(ws)
        try:
            async for _ in ws:
                pass
        except asyncio.CancelledError:
            pass
        finally:
            clients.discard(ws)
        return ws

    async def reload_callback():
        for ws in list(clients):
            try:
                await ws.send_str("reload")
            except Exception:
                pass

    # When given a single file, use its parent to discover all sibling notes
    search_dir = base_path.parent if base_path.is_file() else base_path

    def get_all_notes() -> list[str]:
        notes = []
        for p in search_dir.rglob("*.md"):
            if any(part.startswith(".") for part in p.relative_to(search_dir).parts):
                continue
            rel_path = p.relative_to(search_dir).with_suffix("")
            notes.append(str(rel_path))
        return sorted(notes)

    def resolve_path(slug: str) -> Path | None:
        if slug == "":
            return None

        for p in search_dir.rglob("*.md"):
            if any(part.startswith(".") for part in p.relative_to(search_dir).parts):
                continue
            rel_slug = str(p.relative_to(search_dir).with_suffix("")).replace(" ", "-").lower()
            stem_slug = p.stem.replace(" ", "-").lower()
            if slug == rel_slug or slug == stem_slug:
                return p
        return None

    async def handle_request(request):
        slug = request.match_info.get("slug", "").strip("/")

        if slug == "ws":
            return await ws_handler(request)

        if slug == "api/render" and request.method == "POST":
            return await api_render(request)

        if slug == "api/save" and request.method == "POST":
            return await api_save(request)

        all_notes = get_all_notes()

        # Root path: show the target file if single-file mode, or index if directory
        if slug == "" or (slug in ("index", "index.html") and resolve_path(slug) is None):
            if base_path.is_file():
                note_id = str(base_path.relative_to(search_dir).with_suffix(""))
                try:
                    html = render_file(str(base_path), all_notes=all_notes, note_id=note_id)
                    return web.Response(text=html, content_type="text/html")
                except Exception as e:
                    return web.Response(text=f"Error rendering file: {e}", status=500)
            else:
                try:
                    html = render_index(all_notes)
                    return web.Response(text=html, content_type="text/html")
                except Exception as e:
                    return web.Response(text=f"Error rendering index: {e}", status=500)

        # Resolve slug to a file in the search directory
        target_file = resolve_path(slug)
        if target_file and target_file.exists():
            note_id = str(target_file.relative_to(search_dir).with_suffix(""))
            try:
                html = render_file(str(target_file), all_notes=all_notes, note_id=note_id)
                return web.Response(text=html, content_type="text/html")
            except Exception as e:
                return web.Response(text=f"Error rendering file: {e}", status=500)

        return web.Response(text="Note not found", status=404)

    # Watcher
    start_watcher(path, reload_callback)

    # API endpoints
    async def api_render(request):
        try:
            data = await request.json()
            text = data.get("content", "")
            from .renderer import _parser
            html = _parser.render(text)
            return web.json_response({"html": html})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def api_save(request):
        try:
            data = await request.json()
            note_path = data.get("path")
            content = data.get("content")
            
            if not note_path or content is None:
                return web.json_response({"error": "Missing path or content"}, status=400)
            
            target_file = Path(note_path)
            if not target_file.is_absolute():
                target_file = search_dir / target_file
                
            try:
                target_file.resolve().relative_to(search_dir.resolve())
            except ValueError:
                return web.json_response({"error": "Access denied. Cannot write outside of workspace."}, status=403)
                
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text(content, encoding="utf-8")
            
            return web.json_response({"success": True})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    # Routes
    app.router.add_get("/ws", ws_handler)
    app.router.add_post("/api/render", api_render)
    app.router.add_post("/api/save", api_save)
    app.router.add_get("/{slug:.*}", handle_request)

    # Runner setup
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    print(f"Server started on http://0.0.0.0:{port}")

    # Graceful shutdown on Ctrl+C
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _signal_handler():
        stop_event.set()

    loop.add_signal_handler(signal.SIGINT, _signal_handler)
    loop.add_signal_handler(signal.SIGTERM, _signal_handler)

    await stop_event.wait()

    # Close all WebSocket connections gracefully
    print("\nShutting down...")
    for ws in list(clients):
        await ws.close()
    clients.clear()

    await runner.cleanup()
