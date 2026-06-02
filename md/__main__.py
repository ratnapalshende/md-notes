import click, asyncio, webbrowser, socket
from .server import run_server

@click.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--port", default=7070, help="Port to serve on")
@click.option("--no-browser", is_flag=True)
def main(path, port, no_browser):
    """Render a Markdown file or folder in your browser."""
    if not no_browser:
        webbrowser.open(f"http://localhost:{port}")
    asyncio.run(run_server(path, port))


if __name__ == "__main__":
    main()