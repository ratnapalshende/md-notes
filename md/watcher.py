import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import asyncio

def start_watcher(path: str, callback):
    loop = asyncio.get_event_loop()

    class Handler(FileSystemEventHandler):
        def on_modified(self, event):
            if event.src_path.endswith('.md'):
                loop.call_soon_threadsafe(
                    lambda: asyncio.ensure_future(callback())
                )

    observer = Observer()
    abs_path = os.path.abspath(path)
    watch_path = abs_path if os.path.isdir(abs_path) else os.path.dirname(abs_path)
    observer.schedule(Handler(), watch_path, recursive=True)
    observer.start()
