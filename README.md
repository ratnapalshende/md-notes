# mdnotes

A fast, lightweight, and beautiful Markdown viewer with live-reload, nested folders, wikilinks, and callouts. It spins up a local server to render your markdown files into a modern, responsive web app instantly.

## Features

- **Live Reload**: Instantly updates the browser when you save a file.
- **Responsive UI**: A gorgeous, modern sidebar design that works perfectly on both desktop and mobile.
- **Wikilinks**: Supports Obsidian-style `[[wikilinks]]`.
- **Callouts**: Supports GitHub-style callouts (`[!note]`, `[!warning]`, etc.).
- **Code Highlighting**: Syntax highlighting for your code blocks.

## Installation

### Ubuntu / Debian (Recommended)

On modern Ubuntu/Debian systems, it is highly recommended to install Python applications using `pipx` to avoid conflicts with system packages. 

If you don't have `pipx` installed, you can install it first:

```bash
sudo apt update
sudo apt install pipx
pipx ensurepath
```

Then install `mdnotes`:

```bash
pipx install mdnotes
```

### Other Systems / Standard Pip

You can also install `mdnotes` using standard pip if you prefer:

```bash
pip install mdnotes
```

## Usage

You can run `mdnotes` on a single file or a whole directory using the `md` command.

```bash
# Serve a single markdown file
md file.md

# Serve a directory of markdown files
md notes-folder
```

This will start a local server (default: `http://localhost:7070`).

## Development

If you want to contribute or modify the project, you can set it up for local development by installing it in "editable" mode.

```bash
# 1. Clone the repository and cd into it
git clone https://github.com/ratnapalshende/md-notes.git
cd md-notes

# 2. Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate

# 3. Install the package in editable mode
pip install -e .
```

Once installed, the `md` command is linked to your local source code, meaning any changes you make will be immediately reflected when you run the command.
