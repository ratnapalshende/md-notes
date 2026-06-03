from pathlib import Path
from markdown_it import MarkdownIt
from mdit_py_plugins.front_matter import front_matter_plugin
from mdit_py_plugins.tasklists import tasklists_plugin
from mdit_py_plugins.footnote import footnote_plugin
from .extensions import callout_plugin, wikilink_plugin, embed_plugin, tag_plugin, inject_linenumbers_plugin

def make_parser() -> MarkdownIt:
    md = (
        MarkdownIt("gfm-like", {"linkify": False, "highlight": None})  # highlight=None → Shiki handles it
        .enable("table")
        .enable("strikethrough")
        .use(front_matter_plugin)
        .use(tasklists_plugin)
        .use(footnote_plugin)
        .use(callout_plugin)
        .use(wikilink_plugin)
        .use(embed_plugin)
        .use(tag_plugin)
        .use(inject_linenumbers_plugin)
    )
    return md

_parser = make_parser()

def _build_nav_tree(notes: list[str]) -> dict:
    """Build a nested dict tree from flat note paths like 'devops/docker/intro'."""
    tree = {}
    for note in notes:
        parts = note.split("/")
        node = tree
        for part in parts[:-1]:
            if part not in node:
                node[part] = {}
            node = node[part]
        # Leaf node: store as string value
        node[parts[-1]] = note  # full path as value
    return tree


def _render_nav_tree(tree: dict, active_title: str, depth: int = 0, current_path: str = "") -> str:
    """Recursively render the nav tree as nested HTML with collapsible folders."""
    html_parts = []
    # Sort: folders first, then files
    folders = sorted([k for k, v in tree.items() if isinstance(v, dict)])
    files = sorted([k for k, v in tree.items() if isinstance(v, str)])

    for folder in folders:
        folder_path = f"{current_path}{folder}/" if current_path else f"{folder}/"
        # Check if active note is inside this folder
        is_open = _folder_contains_active(tree[folder], active_title)
        open_class = "open" if is_open else ""
        html_parts.append(f'<li class="nav-folder {open_class}">')
        html_parts.append(
            f'<div class="nav-folder-title" title="{folder}">'
            f'<i class="ti ti-chevron-right nav-folder-chevron"></i>'
            f'<i class="ti ti-folder nav-folder-icon"></i>'
            f'<span class="nav-text">{folder}</span>'
            f'<button class="folder-new-file-btn" title="New File" style="background: none; border: none; cursor: pointer; color: var(--text-secondary); opacity: 0; transition: opacity 0.2s; padding: 0.2rem; display: flex; align-items: center; flex-shrink: 0;" onclick="event.stopPropagation(); window.createNoteInFolder(\'{folder_path}\');">'
            f'<i class="ti ti-file-plus"></i></button>'
            f'</div>'
        )
        html_parts.append('<ul class="nav-folder-children">')
        html_parts.append(_render_nav_tree(tree[folder], active_title, depth + 1, folder_path))
        html_parts.append('</ul>')
        html_parts.append('</li>')

    if depth == 0 and folders and files:
        html_parts.append('<li style="height: 0.5rem;"></li>')

    for file_name in files:
        full_path = tree[file_name]
        slug = full_path.replace(" ", "-").lower()
        is_active = "active" if full_path.lower() == active_title.lower() else ""
        display = file_name.replace("-", " ").replace("_", " ")
        html_parts.append(
            f'<li><a href="/{slug}" class="nav-file {is_active}" title="{display}">'
            f'<i class="ti ti-file-text nav-file-icon"></i>'
            f'<span class="nav-text">{display}</span></a></li>'
        )

    return "\n".join(html_parts)


def _folder_contains_active(subtree: dict, active_title: str) -> bool:
    """Check if any leaf in the subtree matches the active title."""
    for k, v in subtree.items():
        if isinstance(v, str) and v.lower() == active_title.lower():
            return True
        if isinstance(v, dict) and _folder_contains_active(v, active_title):
            return True
    return False


def wrap_in_template(body: str, title: str, nav: list[str] | None = None, raw_text: str = "", note_id: str = "") -> str:
    sidebar_footer = """
        <div class="sidebar-footer" style="margin-top: 2rem; padding-top: 1rem; border-top: 1px solid var(--border-color);">
            <label for="highlighter-select" style="font-size: 0.8rem; color: var(--text-secondary);">Code Highlighter:</label>
            <select id="highlighter-select" style="width: 100%; padding: 0.3rem; margin-top: 0.3rem; background: var(--bg-primary); border: 1px solid var(--border-color); color: var(--text-primary); border-radius: 0.25rem;">
                <option value="highlightjs">Highlight.js (VS Code Dark)</option>
                <option value="prismjs">PrismJS (Okaidia)</option>
                <option value="shiki">Shiki (VS Code Dark+)</option>
            </select>
        </div>
    """
    sidebar_html = ""
    body_class = "no-sidebar"
    
    if nav:
        body_class = ""
        tree = _build_nav_tree(nav)
        tree_html = _render_nav_tree(tree, title)
        home_active = "active" if title.lower() == "index" else ""
        sidebar_html = f"""
    <div class="sidebar">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <h2 style="margin-bottom: 0;">Notes</h2>
            <button id="btn-new-note" class="btn btn-secondary" style="padding: 0.25rem 0.5rem; font-size: 0.75rem;"><i class="ti ti-plus"></i> New</button>
        </div>
        <ul class="nav-tree">
            <li><a href="/" class="nav-file {home_active}" title="Home"><i class="ti ti-home nav-file-icon"></i><span class="nav-text">Home</span></a></li>
            {tree_html}
        </ul>
        {sidebar_footer}
    </div>
    """
    else:
        sidebar_html = f"""
    <div class="sidebar">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <h2 style="margin-bottom: 0;">Notes</h2>
            <button id="btn-new-note" class="btn btn-secondary" style="padding: 0.25rem 0.5rem; font-size: 0.75rem;"><i class="ti ti-plus"></i> New</button>
        </div>
        <ul class="nav-tree">
            <li><a href="/" class="nav-file active" title="Home"><i class="ti ti-home nav-file-icon"></i><span class="nav-text">Home</span></a></li>
        </ul>
        {sidebar_footer}
    </div>
    """
    body_class = ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
    <!-- Tabler Icons -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/tabler-icons.min.css">
    
    <!-- CodeMirror -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/codemirror.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/theme/material-ocean.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/codemirror.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/mode/markdown/markdown.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/addon/edit/continuelist.min.js"></script>
    
    <!-- Highlighter Themes -->
    <link id="theme-highlightjs" class="highlighter-theme" rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/vs2015.min.css">
    <link id="theme-prismjs" class="highlighter-theme" rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-okaidia.min.css" disabled>

    <!-- Highlighter Scripts -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js" data-manual></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/plugins/autoloader/prism-autoloader.min.js"></script>
    <!-- Prevent sidebar flash: apply collapsed state before paint -->
    <script>
        (function() {{
            if (window.innerWidth > 768 && localStorage.getItem('sidebar-collapsed') === 'true') {{
                document.documentElement.classList.add('sidebar-collapsed');
            }}
            const savedTheme = localStorage.getItem('md-theme');
            if (savedTheme) {{
                document.documentElement.setAttribute('data-theme', savedTheme);
            }}
        }})();
    </script>
    <style>
        :root {{
            --bg-primary: #ffffff;
            --bg-secondary: #f6f8fa;
            --text-primary: #24292f;
            --text-secondary: #57606a;
            --border-color: #d0d7de;
            --primary-color: #0969da;
            --primary-hover: #0349b4;
            --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
            --font-mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
            --sidebar-width: 260px;
        }}

        :root[data-theme="dark"] {{
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --text-primary: #c9d1d9;
            --text-secondary: #8b949e;
            --border-color: #30363d;
            --primary-color: #58a6ff;
            --primary-hover: #79c0ff;
        }}

        @media (prefers-color-scheme: dark) {{
            :root:not([data-theme="light"]) {{
                --bg-primary: #0d1117;
                --bg-secondary: #161b22;
                --text-primary: #c9d1d9;
                --text-secondary: #8b949e;
                --border-color: #30363d;
                --primary-color: #58a6ff;
                --primary-hover: #79c0ff;
            }}
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: var(--font-sans);
            background-color: var(--bg-primary);
            color: var(--text-primary);
            display: flex;
            min-height: 100vh;
            line-height: 1.6;
            overflow-x: hidden;
        }}

        /* Sidebar Toggle Button */
        .sidebar-toggle {{
            position: fixed;
            top: 1.25rem;
            left: 1.25rem;
            background-color: var(--bg-secondary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            width: 2.5rem;
            height: 2.5rem;
            border-radius: 0.5rem;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            z-index: 1100;
            transition: all 0.3s ease;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }}

        .sidebar-toggle:hover {{
            background-color: var(--border-color);
            color: var(--primary-color);
        }}

        /* Theme Toggle Button */
        .theme-toggle {{
            position: fixed;
            top: 1.25rem;
            right: 1.25rem;
            background-color: var(--bg-secondary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            width: 2.5rem;
            height: 2.5rem;
            border-radius: 0.5rem;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            z-index: 1100;
            transition: all 0.3s ease;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }}

        .theme-toggle:hover {{
            background-color: var(--border-color);
            color: var(--primary-color);
        }}

        /* Buttons */
        .btn {{
            padding: 0.4rem 0.8rem;
            border-radius: 0.375rem;
            border: 1px solid transparent;
            font-size: 0.875rem;
            font-weight: 500;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 0.4rem;
            transition: all 0.2s;
            font-family: var(--font-sans);
        }}
        .btn-primary {{ background: var(--primary-color); color: white; }}
        .btn-primary:hover {{ background: var(--primary-hover); }}
        .btn-success {{ background: #1f883d; color: white; }}
        .btn-success:hover {{ background: #1a7f37; }}
        .btn-secondary {{ background: var(--bg-secondary); border-color: var(--border-color); color: var(--text-primary); }}
        .btn-secondary:hover {{ border-color: #8b949e; }}

        /* CodeMirror overrides */
        .CodeMirror {{
            height: 100% !important;
            font-family: var(--font-mono) !important;
            font-size: 0.95rem;
            background: transparent !important;
            color: var(--text-primary) !important;
        }}
        .cm-s-material-ocean.CodeMirror {{
            background: #0d1117 !important;
            color: #c9d1d9 !important;
        }}
        
        .editor-pane .CodeMirror {{
            border-radius: 0.5rem;
        }}

        /* Split View Layout */
        .split-view {{
            height: calc(100vh - 12rem);
            gap: 1rem;
            flex-direction: row;
        }}
        .editor-pane, .preview-pane {{
            flex: 1;
            border: 1px solid var(--border-color);
            border-radius: 0.5rem;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }}
        .preview-pane {{
            overflow-y: auto;
            padding: 1.5rem;
            background: var(--bg-primary);
        }}

        /* Sidebar styling */
        .sidebar {{
            width: var(--sidebar-width);
            background-color: var(--bg-secondary);
            border-right: 1px solid var(--border-color);
            position: fixed;
            top: 0;
            bottom: 0;
            left: 0;
            overflow-y: auto;
            padding: 5rem 1.5rem 2rem 1.5rem;
            transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 1050;
        }}

        .sidebar h2 {{
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-secondary);
            margin-bottom: 1rem;
        }}

        /* Nav Tree */
        .nav-tree, .nav-tree ul {{
            list-style: none;
            margin: 0;
            padding: 0;
        }}

        .nav-tree li {{
            margin-bottom: 0.125rem;
        }}

        /* Folder title row */
        .nav-folder-title {{
            display: flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.4rem 0.6rem;
            border-radius: 0.375rem;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 500;
            color: var(--text-secondary);
            transition: all 0.15s ease;
            user-select: none;
        }}

        .nav-folder-title:hover {{
            background-color: var(--border-color);
            color: var(--text-primary);
        }}
        
        .nav-folder-title:hover .folder-new-file-btn {{
            opacity: 1 !important;
        }}
        .folder-new-file-btn:hover {{
            color: var(--primary-color) !important;
        }}

        .nav-folder-chevron {{
            font-size: 0.75rem;
            transition: transform 0.2s ease;
            flex-shrink: 0;
        }}

        .nav-folder.open > .nav-folder-title .nav-folder-chevron {{
            transform: rotate(90deg);
        }}

        .nav-folder-icon {{
            font-size: 1rem;
            color: var(--primary-color);
            opacity: 0.7;
            flex-shrink: 0;
        }}

        /* Folder children — collapsed by default */
        .nav-folder-children {{
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.25s ease;
            margin-left: 1rem;
            padding-left: 0;
            list-style: none;
        }}

        .nav-folder.open > .nav-folder-children {{
            max-height: 2000px;
        }}

        /* Tree branches */
        .nav-folder-children > li {{
            position: relative;
            padding-left: 1.1rem;
        }}

        .nav-folder-children > li::before {{
            content: '';
            position: absolute;
            top: 0;
            bottom: 0;
            left: 0;
            width: 1px;
            background-color: var(--border-color);
        }}

        .nav-folder-children > li:last-child::before {{
            bottom: auto;
            height: 1.05rem;
        }}

        .nav-folder-children > li::after {{
            content: '';
            position: absolute;
            top: 1.05rem;
            left: 0;
            width: 0.75rem;
            height: 1px;
            background-color: var(--border-color);
        }}

        /* File links */
        .nav-file {{
            display: flex;
            align-items: center;
            gap: 0.4rem;
            color: var(--text-primary);
            text-decoration: none;
            padding: 0.35rem 0.6rem;
            border-radius: 0.375rem;
            font-size: 0.9rem;
            transition: all 0.15s ease;
        }}

        .nav-text {{
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            min-width: 0;
            flex-grow: 1;
        }}

        /* Floating Toolbar */
        .floating-toolbar {{
            position: absolute;
            display: none;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 0.5rem;
            padding: 0.25rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 1000;
            gap: 0.25rem;
            align-items: center;
        }}
        .floating-toolbar button {{
            background: transparent;
            border: none;
            color: var(--text-primary);
            padding: 0.4rem;
            border-radius: 0.25rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background 0.2s, color 0.2s;
        }}
        .floating-toolbar button:hover {{
            background: color-mix(in srgb, var(--primary-color) 15%, transparent);
            color: var(--primary-color);
        }}

        /* Context Menu */
        .context-menu {{
            position: absolute;
            display: none;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 0.5rem;
            padding: 0.5rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 1000;
            flex-direction: column;
            min-width: 200px;
        }}
        .context-menu .menu-item {{
            position: relative;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem;
            cursor: pointer;
            border-radius: 0.25rem;
            color: var(--text-primary);
            transition: background 0.2s;
            font-size: 0.9rem;
        }}
        .context-menu .menu-item:hover {{
            background: color-mix(in srgb, var(--primary-color) 15%, transparent);
            color: var(--primary-color);
        }}
        
        .context-menu .submenu {{
            display: none;
            position: absolute;
            top: -0.5rem;
            left: 100%;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 0.5rem;
            padding: 0.5rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            flex-direction: column;
            min-width: 180px;
            margin-left: 0.25rem;
            z-index: 1001;
            max-height: 80vh;
            overflow-y: auto;
        }}
        .context-menu .submenu-up .submenu {{
            top: auto;
            bottom: -0.5rem;
        }}
        .context-menu.menu-left .submenu {{
            left: auto;
            right: 100%;
            margin-left: 0;
            margin-right: 0.25rem;
        }}
        .context-menu .has-submenu:hover > .submenu {{
            display: flex;
        }}

        .nav-tree > li > .nav-file {{
            padding-left: 1.75rem;
        }}

        .nav-file:hover {{
            background-color: var(--border-color);
            color: var(--primary-color);
        }}

        .nav-file.active {{
            background-color: color-mix(in srgb, var(--primary-color) 15%, transparent);
            color: var(--primary-color);
            font-weight: 500;
        }}

        .nav-file-icon {{
            font-size: 0.9rem;
            opacity: 0.6;
            flex-shrink: 0;
        }}

        .nav-file.active .nav-file-icon {{
            opacity: 0.9;
        }}

        /* Backdrop Overlay for Mobile */
        .sidebar-backdrop {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.4);
            backdrop-filter: blur(2px);
            z-index: 1040;
        }}

        /* Content Area */
        .content-wrapper {{
            flex: 1;
            padding: 5rem 2rem 3rem 2rem;
            transition: margin-left 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            width: 100%;
        }}

        article {{
            font-size: 1.05rem;
            max-width: 800px;
            margin: 0 auto;
        }}

        article h1 {{ font-size: 2.25rem; margin-bottom: 1.5rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem; }}
        article h2 {{ font-size: 1.75rem; margin-top: 2rem; margin-bottom: 1rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.3em; }}
        article h3 {{ font-size: 1.4rem; margin-top: 1.5rem; margin-bottom: 0.75rem; }}
        article p {{ margin-bottom: 1.25rem; }}
        article a {{ color: var(--primary-color); text-decoration: none; }}
        article a:hover {{ text-decoration: underline; }}
        
        article hr {{
            height: 0.25em;
            padding: 0;
            margin: 24px 0;
            background-color: var(--border-color);
            border: 0;
        }}

        article blockquote {{
            padding: 0 1em;
            color: var(--text-secondary);
            border-left: 0.25em solid var(--border-color);
            margin: 0 0 1rem 0;
        }}

        article table {{
            border-spacing: 0;
            border-collapse: collapse;
            margin-bottom: 1rem;
            width: 100%;
        }}

        article table th, article table td {{
            padding: 6px 13px;
            border: 1px solid var(--border-color);
        }}

        article table tr:nth-child(2n) {{
            background-color: var(--bg-secondary);
        }}

        /* Lists */
        article ul, article ol {{
            padding-left: 2rem;
            margin-bottom: 1.25rem;
        }}
        article li {{
            margin-bottom: 0.5rem;
        }}
        article li > ul, article li > ol {{
            margin-bottom: 0;
            margin-top: 0.5rem;
        }}

        /* Task Lists */
        article li.task-list-item {{
            list-style-type: none;
        }}
        article li.task-list-item input[type="checkbox"] {{
            margin: 0 0.5rem 0 -1.5rem;
            vertical-align: middle;
            transform: translateY(-0.075em) scale(1.15);
            accent-color: var(--primary-color);
        }}

        /* Code highlight and blocks */
        pre {{
            border: 1px solid var(--border-color);
            border-radius: 0.5rem;
            margin-bottom: 1.5rem;
            overflow: hidden;
            position: relative;
        }}
        pre code {{
            padding: 1.25rem !important;
            overflow-x: auto;
            display: block;
        }}
        code {{
            font-family: var(--font-mono);
            font-size: 0.9rem;
        }}
        :not(pre) > code {{
            background-color: var(--bg-secondary);
            padding: 0.2rem 0.4rem;
            border-radius: 0.25rem;
            border: 1px solid var(--border-color);
        }}

        /* Copy Button */
        .copy-btn {{
            position: absolute;
            top: 0.5rem;
            right: 0.5rem;
            background: rgba(40, 43, 46, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: #e0e2e4;
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            font-size: 0.75rem;
            cursor: pointer;
            opacity: 0.6;
            transition: opacity 0.2s, background 0.2s;
            z-index: 10;
        }}
        pre:hover .copy-btn {{
            opacity: 1;
        }}
        .copy-btn:hover {{
            background: rgba(255, 255, 255, 0.15);
        }}
        .copy-btn.copied {{
            background: #10b981;
            border-color: #10b981;
            color: #fff;
        }}

        /* Tables */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 1.5rem;
        }}
        th, td {{
            border: 1px solid var(--border-color);
            padding: 0.75rem;
            text-align: left;
        }}
        th {{
            background-color: var(--bg-secondary);
        }}

        /* Callouts */
        .callout {{
            border-left: 4px solid var(--border-color);
            background-color: var(--bg-secondary);
            padding: 1rem 1.25rem;
            border-radius: 0 0.5rem 0.5rem 0;
            margin-bottom: 1.5rem;
        }}
        .callout-title {{
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 0.5rem;
        }}
        .callout-title i {{
            font-size: 1.2rem;
        }}
        .callout-body {{
            font-size: 1rem;
        }}

        /* Callout Types */
        .callout-note {{ border-left-color: #3b82f6; }}
        .callout-note .callout-title {{ color: #3b82f6; }}
        
        .callout-warning {{ border-left-color: #f59e0b; }}
        .callout-warning .callout-title {{ color: #f59e0b; }}

        .callout-tip {{ border-left-color: #10b981; }}
        .callout-tip .callout-title {{ color: #10b981; }}

        .callout-important {{ border-left-color: #8b5cf6; }}
        .callout-important .callout-title {{ color: #8b5cf6; }}

        .callout-caution {{ border-left-color: #ec4899; }}
        .callout-caution .callout-title {{ color: #ec4899; }}

        .callout-danger {{ border-left-color: #ef4444; }}
        .callout-danger .callout-title {{ color: #ef4444; }}
        
        .callout-question {{ border-left-color: #d97706; }}
        .callout-question .callout-title {{ color: #d97706; }}

        .callout-todo {{ border-left-color: #0ea5e9; }}
        .callout-todo .callout-title {{ color: #0ea5e9; }}

        .callout-example {{ border-left-color: #a855f7; }}
        .callout-example .callout-title {{ color: #a855f7; }}

        /* Tags */
        .tag {{
            display: inline-block;
            background-color: var(--bg-secondary);
            border: 1px solid var(--border-color);
            padding: 0.1rem 0.5rem;
            border-radius: 0.25rem;
            font-size: 0.85rem;
            color: var(--text-secondary) !important;
            text-decoration: none;
            margin-right: 0.25rem;
        }}
        .tag:hover {{
            border-color: var(--primary-color);
            color: var(--primary-color) !important;
        }}

        /* Wikilink */
        .wikilink {{
            font-weight: 500;
            border-bottom: 1px dashed var(--primary-color);
        }}
        .wikilink:hover {{
            border-bottom-style: solid;
        }}

        .index-list {{
            list-style-type: disc;
            margin-left: 2rem;
            margin-top: 1rem;
        }}
        .index-list li {{
            margin-bottom: 0.5rem;
        }}

        /* Desktop Media Query */
        @media (min-width: 769px) {{
            .content-wrapper {{
                margin-left: var(--sidebar-width);
            }}

            .sidebar-collapsed .sidebar {{
                transform: translateX(-100%);
            }}

            .sidebar-collapsed .content-wrapper {{
                margin-left: 0;
            }}
        }}

        /* Mobile Media Query */
        @media (max-width: 768px) {{
            .sidebar {{
                transform: translateX(-100%);
            }}

            .content-wrapper {{
                margin-left: 0;
                padding: 5rem 1.25rem 3rem 1.25rem;
            }}

            body.mobile-sidebar-open .sidebar {{
                transform: translateX(0);
            }}

            body.mobile-sidebar-open .sidebar-backdrop {{
                display: block;
            }}

            /* Mobile Split View */
            .split-view {{
                flex-direction: column !important;
                height: calc(100vh - 9rem) !important;
            }}
            .editor-pane, .preview-pane {{
                min-height: 40vh;
            }}
        }}
    </style>
</head>
<body class="{body_class}">
    <button id="theme-toggle" class="theme-toggle" title="Toggle Theme">
        <i class="ti ti-moon"></i>
    </button>
    <button id="sidebar-toggle" class="sidebar-toggle" title="Toggle Sidebar">
        <i class="ti ti-menu-2"></i>
    </button>
    <div id="sidebar-backdrop" class="sidebar-backdrop"></div>
    <div id="floating-toolbar" class="floating-toolbar">
        <button onmousedown="event.preventDefault(); window.toggleCMFormat('**')" title="Bold (Ctrl+B)"><i class="ti ti-bold"></i></button>
        <button onmousedown="event.preventDefault(); window.toggleCMFormat('*')" title="Italic (Ctrl+I)"><i class="ti ti-italic"></i></button>
        <button onmousedown="event.preventDefault(); window.toggleCMFormat('~~')" title="Strikethrough (Ctrl+Shift+X)"><i class="ti ti-strikethrough"></i></button>
        <button onmousedown="event.preventDefault(); window.toggleCMFormat('`')" title="Code (Ctrl+E)"><i class="ti ti-code"></i></button>
    </div>
    <div id="editor-context-menu" class="context-menu">
        <div class="menu-item has-submenu">
            <i class="ti ti-bulb"></i> Insert Callout <i class="ti ti-chevron-right" style="margin-left: auto;"></i>
            <div class="submenu">
                <div class="menu-item" onmousedown="event.preventDefault(); event.stopPropagation(); window.insertTemplate('> [!note]\\n> ')"><i class="ti ti-info-circle"></i> Note</div>
                <div class="menu-item" onmousedown="event.preventDefault(); event.stopPropagation(); window.insertTemplate('> [!warning]\\n> ')"><i class="ti ti-alert-triangle"></i> Warning</div>
                <div class="menu-item" onmousedown="event.preventDefault(); event.stopPropagation(); window.insertTemplate('> [!tip]\\n> ')"><i class="ti ti-bulb"></i> Tip</div>
                <div class="menu-item" onmousedown="event.preventDefault(); event.stopPropagation(); window.insertTemplate('> [!important]\\n> ')"><i class="ti ti-alert-circle"></i> Important</div>
                <div class="menu-item" onmousedown="event.preventDefault(); event.stopPropagation(); window.insertTemplate('> [!caution]\\n> ')"><i class="ti ti-hand-stop"></i> Caution</div>
                <div class="menu-item" onmousedown="event.preventDefault(); event.stopPropagation(); window.insertTemplate('> [!danger]\\n> ')"><i class="ti ti-flame"></i> Danger</div>
                <div class="menu-item" onmousedown="event.preventDefault(); event.stopPropagation(); window.insertTemplate('> [!question]\\n> ')"><i class="ti ti-help"></i> Question</div>
                <div class="menu-item" onmousedown="event.preventDefault(); event.stopPropagation(); window.insertTemplate('> [!todo]\\n> ')"><i class="ti ti-checkbox"></i> Todo</div>
                <div class="menu-item" onmousedown="event.preventDefault(); event.stopPropagation(); window.insertTemplate('> [!example]\\n> ')"><i class="ti ti-list"></i> Example</div>
            </div>
        </div>
        <div class="menu-item" onmousedown="event.preventDefault(); window.insertTemplate('[[  ]]', 3)"><i class="ti ti-link"></i> Insert Wikilink</div>
        <div class="menu-item" onmousedown="event.preventDefault(); window.insertTemplate('[ ]()', 3)"><i class="ti ti-external-link"></i> Insert Link</div>
        <div class="menu-item" onmousedown="event.preventDefault(); window.insertTemplate('| Column 1 | Column 2 |\\n| -------- | -------- |\\n| Text     | Text     |\\n')"><i class="ti ti-table"></i> Insert Table</div>
        <div class="menu-item" onmousedown="event.preventDefault(); window.insertTemplate('```\\n\\n```', 4)"><i class="ti ti-code"></i> Insert Code Block</div>
        <div class="menu-item" onmousedown="event.preventDefault(); window.insertTemplate('- [ ] ')"><i class="ti ti-checkbox"></i> Insert Task List</div>
    </div>
    {sidebar_html}
    <div class="content-wrapper">
        <div class="toolbar" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 1px solid var(--border-color);">
            <div style="font-size: 0.9rem; color: var(--text-secondary); font-family: var(--font-mono);">
                {note_id if note_id else "index"}
            </div>
            <div style="display: flex; gap: 0.5rem;">
                {f'''<button id="btn-edit" class="btn btn-primary" title="Edit Note"><i class="ti ti-edit"></i> Edit</button>
                <button id="btn-save" class="btn btn-success" title="Save Note" style="display: none;"><i class="ti ti-device-floppy"></i> Save</button>
                <button id="btn-cancel" class="btn btn-secondary" title="Cancel Editing" style="display: none;"><i class="ti ti-x"></i> Cancel</button>''' if note_id else ""}
            </div>
        </div>
        
        {f'''<div id="split-view" class="split-view" style="display: none;">
            <div id="editor-pane" class="editor-pane">
                <textarea id="markdown-editor"></textarea>
            </div>
            <div id="preview-pane" class="preview-pane">
                <article id="live-preview"></article>
            </div>
        </div>''' if note_id else ""}

        <article id="markdown-viewer">
            {body}
        </article>
    </div>
    
    <script type="text/plain" id="raw-markdown">{raw_text.replace("</script>", "<\\/script>")}</script>
    
    <script>
        document.addEventListener('mousedown', function(e) {{
            const menu = document.getElementById('editor-context-menu');
            if (menu && menu.style.display === 'flex' && !menu.contains(e.target)) {{
                menu.style.display = 'none';
            }}
        }});
        
        window.insertTemplate = function(text, cursorBackOffset = 0) {{
            if (!window.cmEditor) return;
            const cm = window.cmEditor;
            const doc = cm.getDoc();
            const cursor = doc.getCursor();
            doc.replaceRange(text, cursor);
            
            if (cursorBackOffset > 0) {{
                const index = doc.indexFromPos(doc.getCursor());
                doc.setCursor(doc.posFromIndex(index - cursorBackOffset));
            }}
            
            cm.focus();
            const menu = document.getElementById('editor-context-menu');
            if (menu) menu.style.display = 'none';
        }};

        window.toggleCMFormat = function(prefix, suffix) {{
            if (!window.cmEditor) return;
            if (!suffix) suffix = prefix;
            
            const cm = window.cmEditor;
            const from = cm.getCursor("start");
            const to = cm.getCursor("end");
            const selection = cm.getSelection();
            
            if (selection.length > 0 && selection.startsWith(prefix) && selection.endsWith(suffix)) {{
                const newText = selection.slice(prefix.length, selection.length - suffix.length);
                cm.replaceSelection(newText, "around");
                cm.focus();
                return;
            }}
            
            const before = cm.getRange({{line: from.line, ch: from.ch - prefix.length}}, from);
            const after = cm.getRange(to, {{line: to.line, ch: to.ch + suffix.length}});
            
            if (before === prefix && after === suffix) {{
                cm.replaceRange("", to, {{line: to.line, ch: to.ch + suffix.length}});
                cm.replaceRange("", {{line: from.line, ch: from.ch - prefix.length}}, from);
                cm.focus();
                return;
            }}
            
            if (selection.length > 0) {{
                cm.replaceSelection(prefix + selection + suffix, "around");
            }} else {{
                cm.replaceSelection(prefix + suffix);
                cm.setCursor({{line: from.line, ch: from.ch + prefix.length}});
            }}
            cm.focus();
        }};
    </script>
    
    <!-- Sidebar Toggle Script -->
    <script>
        (function() {{
            const toggle = document.getElementById('sidebar-toggle');
            
            function updateIcon() {{
                const isMobileOpen = document.body.classList.contains('mobile-sidebar-open');
                const isDesktopCollapsed = document.body.classList.contains('sidebar-collapsed');
                const icon = toggle.querySelector('i');
                if (!icon) return;
                
                if (window.innerWidth <= 768) {{
                    if (isMobileOpen) {{
                        icon.className = 'ti ti-x';
                    }} else {{
                        icon.className = 'ti ti-menu-2';
                    }}
                }} else {{
                    if (isDesktopCollapsed) {{
                        icon.className = 'ti ti-menu-2';
                    }} else {{
                        icon.className = 'ti ti-chevron-left';
                    }}
                }}
            }}

            toggle.addEventListener('click', function() {{
                if (window.innerWidth <= 768) {{
                    document.body.classList.toggle('mobile-sidebar-open');
                }} else {{
                    const willCollapse = !document.body.classList.contains('sidebar-collapsed');
                    document.body.classList.toggle('sidebar-collapsed', willCollapse);
                    document.documentElement.classList.toggle('sidebar-collapsed', willCollapse);
                    localStorage.setItem('sidebar-collapsed', willCollapse);
                }}
                updateIcon();
            }});

            const backdrop = document.getElementById('sidebar-backdrop');
            if (backdrop) {{
                backdrop.addEventListener('click', function() {{
                    document.body.classList.remove('mobile-sidebar-open');
                    updateIcon();
                }});
            }}

            // Close mobile sidebar on link click
            document.querySelectorAll('.sidebar a').forEach(link => {{
                link.addEventListener('click', () => {{
                    document.body.classList.remove('mobile-sidebar-open');
                    updateIcon();
                }});
            }});

            // Initialize state: transfer class from <html> (set by head script) to <body>
            if (window.innerWidth > 768) {{
                if (document.documentElement.classList.contains('sidebar-collapsed')) {{
                    document.body.classList.add('sidebar-collapsed');
                }} else if (localStorage.getItem('sidebar-collapsed') === 'true') {{
                    document.body.classList.add('sidebar-collapsed');
                    document.documentElement.classList.add('sidebar-collapsed');
                }}
            }}
            updateIcon();

            // Handle resize
            window.addEventListener('resize', updateIcon);
        }})();
    </script>

    <!-- Folder toggle script -->
    <script>
        (function() {{
            document.querySelectorAll('.nav-folder-title').forEach(title => {{
                title.addEventListener('click', function() {{
                    const folder = this.closest('.nav-folder');
                    folder.classList.toggle('open');
                }});
            }});
        }})();
    </script>
    <script>
        (function() {{
            let socketUrl = "ws://" + window.location.host + "/ws";
            let socket;
            
            function connect() {{
                socket = new WebSocket(socketUrl);
                socket.onmessage = function(event) {{
                    if (event.data === "reload") {{
                        if (window.isSaving) return;
                        if (window.isDirty) {{
                            console.log("External modification detected, but local changes exist. Ignoring auto-reload.");
                            return;
                        }}
                        window.location.reload();
                    }}
                }};
                socket.onclose = function() {{
                    console.log("WebSocket connection closed. Reconnecting in 2s...");
                    setTimeout(connect, 2000);
                }};
            }}
            connect();
        }})();
    </script>

    <!-- Copy button script -->
    <script>
        document.addEventListener('DOMContentLoaded', () => {{
            document.querySelectorAll('pre').forEach(pre => {{
                const btn = document.createElement('button');
                btn.className = 'copy-btn';
                btn.innerHTML = '<i class="ti ti-copy"></i> Copy';
                
                btn.addEventListener('click', () => {{
                    const code = pre.querySelector('code');
                    if (code) {{
                        navigator.clipboard.writeText(code.innerText).then(() => {{
                            const originalHTML = btn.innerHTML;
                            btn.innerHTML = '<i class="ti ti-check"></i> Copied!';
                            btn.classList.add('copied');
                            setTimeout(() => {{
                                btn.innerHTML = originalHTML;
                                btn.classList.remove('copied');
                            }}, 2000);
                        }});
                    }}
                }});
                
                pre.appendChild(btn);
            }});
        }});
    </script>

    <!-- Highlighter Switch Script -->
    <script src="https://unpkg.com/shiki@0.14.7"></script>
    <script>
        window.applyHighlighter = async function(type, root = document) {{
            const preBlocks = root.querySelectorAll('pre');
            
            preBlocks.forEach(pre => {{
                if (!pre.dataset.raw) {{
                    const code = pre.querySelector('code');
                    if (code) {{
                        pre.dataset.raw = code.innerText;
                        const classes = Array.from(code.classList);
                        const langClass = classes.find(c => c.startsWith('language-'));
                        pre.dataset.lang = langClass ? langClass.replace('language-', '') : 'text';
                        pre.dataset.originalHtml = code.innerHTML; 
                    }}
                }}
            }});

            document.querySelectorAll('.highlighter-theme').forEach(link => {{
                link.disabled = link.id !== 'theme-' + type;
            }});

            if (type === 'highlightjs' || type === 'prismjs') {{
                preBlocks.forEach(pre => {{
                    const code = pre.querySelector('code');
                    if (code && pre.dataset.originalHtml) {{
                        code.innerHTML = pre.dataset.originalHtml;
                        code.className = 'language-' + pre.dataset.lang;
                        pre.className = '';
                        pre.style.backgroundColor = '';
                        pre.style.color = '';
                    }}
                }});
            }}

            if (type === 'highlightjs') {{
                if (root === document) hljs.highlightAll();
                else preBlocks.forEach(pre => hljs.highlightElement(pre.querySelector('code')));
            }} else if (type === 'prismjs') {{
                preBlocks.forEach(pre => {{
                    pre.classList.add('language-' + pre.dataset.lang);
                }});
                Prism.highlightAllUnder(root);
            }} else if (type === 'shiki') {{
                try {{
                    const langs = Array.from(new Set(Array.from(preBlocks).map(p => p.dataset.lang)));
                    const supported = shiki.BUNDLED_LANGUAGES.map(l => l.id).concat(shiki.BUNDLED_LANGUAGES.flatMap(l => l.aliases || []));
                    const validLangs = langs.filter(l => l !== 'text' && supported.includes(l));
                    
                    const highlighter = await shiki.getHighlighter({{
                        theme: 'dark-plus',
                        langs: validLangs
                    }});

                    preBlocks.forEach(pre => {{
                        const lang = pre.dataset.lang;
                        const raw = pre.dataset.raw;
                        if (validLangs.includes(lang)) {{
                            try {{
                                const html = highlighter.codeToHtml(raw, {{ lang }});
                                const temp = document.createElement('div');
                                temp.innerHTML = html;
                                const shikiPre = temp.querySelector('pre');
                                const shikiCode = temp.querySelector('code');
                                
                                if (shikiPre && shikiCode) {{
                                    const code = pre.querySelector('code');
                                    code.innerHTML = shikiCode.innerHTML;
                                    pre.style.backgroundColor = shikiPre.style.backgroundColor;
                                    pre.style.color = shikiPre.style.color;
                                }}
                            }} catch(e) {{ console.error(e); }}
                        }} else {{
                            pre.style.backgroundColor = '#1E1E1E'; // dark-plus bg
                            pre.style.color = '#D4D4D4';
                            const code = pre.querySelector('code');
                            if (code) code.innerHTML = pre.dataset.originalHtml;
                        }}
                    }});
                }} catch (err) {{
                    console.error('Shiki error:', err);
                    window.applyHighlighter('highlightjs', root);
                    const select = document.getElementById('highlighter-select');
                    if (select) select.value = 'highlightjs';
                }}
            }}
        }};

        document.addEventListener('DOMContentLoaded', () => {{
            const select = document.getElementById('highlighter-select');
            if (!select) return;

            const currentHighlighter = localStorage.getItem('md-highlighter') || 'highlightjs';
            select.value = currentHighlighter;
            window.applyHighlighter(currentHighlighter);

            select.addEventListener('change', (e) => {{
                const val = e.target.value;
                localStorage.setItem('md-highlighter', val);
                window.applyHighlighter(val);
            }});
        }});
    </script>
    
    <!-- Theme Toggle Script -->
    <script>
        (function() {{
            const themeToggle = document.getElementById('theme-toggle');
            const root = document.documentElement;
            
            function isDark() {{
                const theme = root.getAttribute('data-theme');
                if (theme === 'dark') return true;
                if (theme === 'light') return false;
                return window.matchMedia('(prefers-color-scheme: dark)').matches;
            }}

            function updateIcon() {{
                const icon = themeToggle.querySelector('i');
                if (icon) {{
                    icon.className = isDark() ? 'ti ti-sun' : 'ti ti-moon';
                }}
            }}

            updateIcon();

            themeToggle.addEventListener('click', () => {{
                const newTheme = isDark() ? 'light' : 'dark';
                root.setAttribute('data-theme', newTheme);
                localStorage.setItem('md-theme', newTheme);
                updateIcon();
            }});
            
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', updateIcon);
        }})();
    </script>

    <!-- Editor Script -->
    <script>
        (function() {{
            const btnEdit = document.getElementById('btn-edit');
            const btnSave = document.getElementById('btn-save');
            const btnCancel = document.getElementById('btn-cancel');
            const btnNewNote = document.getElementById('btn-new-note');
            const splitView = document.getElementById('split-view');
            const mdViewer = document.getElementById('markdown-viewer');
            const currentNoteId = "{note_id}";
            
            let cmEditor = null;
            let isDirty = false;
            let debounceTimer = null;

            if (btnNewNote) {{
                btnNewNote.addEventListener('click', () => {{
                    let currentFolder = "";
                    if (currentNoteId) {{
                        const parts = currentNoteId.split('/');
                        if (parts.length > 1) {{
                            parts.pop();
                            currentFolder = parts.join('/') + "/";
                        }}
                    }}
                    window.createNoteInFolder(currentFolder);
                }});
            }}

            window.createNoteInFolder = function(folderPath) {{
                const filename = prompt(`Create new file in $${{folderPath ? folderPath : 'root'}}/ :`, "new_note");
                if (filename) {{
                    let name = filename.trim();
                    if (!name.endsWith('.md')) name += '.md';
                    
                    const fullPath = folderPath + name;
                    
                    fetch('/api/save', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ path: fullPath, content: "# " + name.replace('.md', '') }})
                    }}).then(res => res.json()).then(data => {{
                        if (data.success) {{
                            window.location.href = "/" + fullPath.replace(".md", "");
                        }} else {{
                            alert("Error creating note: " + (data.error || "Unknown"));
                        }}
                    }});
                }}
            }};

            if (btnEdit) {{
                btnEdit.addEventListener('click', () => {{
                    mdViewer.style.display = 'none';
                    splitView.style.display = 'flex';
                    btnEdit.style.display = 'none';
                    btnSave.style.display = 'flex';
                    btnCancel.style.display = 'flex';

                    if (!cmEditor) {{
                        const rawText = document.getElementById('raw-markdown').textContent;
                        cmEditor = CodeMirror.fromTextArea(document.getElementById('markdown-editor'), {{
                            mode: 'markdown',
                            theme: document.documentElement.getAttribute('data-theme') === 'dark' || 
                                  (!document.documentElement.getAttribute('data-theme') && window.matchMedia('(prefers-color-scheme: dark)').matches)
                                  ? 'material-ocean' : 'default',
                            lineNumbers: true,
                            lineWrapping: true,
                            extraKeys: {{
                                "Enter": "newlineAndIndentContinueMarkdownList",
                                "Ctrl-B": (cm) => window.toggleCMFormat("**"),
                                "Cmd-B": (cm) => window.toggleCMFormat("**"),
                                "Ctrl-I": (cm) => window.toggleCMFormat("*"),
                                "Cmd-I": (cm) => window.toggleCMFormat("*"),
                                "Ctrl-E": (cm) => window.toggleCMFormat("`"),
                                "Cmd-E": (cm) => window.toggleCMFormat("`"),
                                "Ctrl-Shift-X": (cm) => window.toggleCMFormat("~~"),
                                "Cmd-Shift-X": (cm) => window.toggleCMFormat("~~")
                            }}
                        }});
                        window.cmEditor = cmEditor;
                        cmEditor.setValue(rawText);
                        
                        cmEditor.on('change', () => {{
                            isDirty = true;
                            window.isDirty = true;
                            const btnSave = document.getElementById('btn-save');
                            if (btnSave) btnSave.disabled = false;
                            clearTimeout(debounceTimer);
                            debounceTimer = setTimeout(() => {{
                                updatePreview(cmEditor.getValue());
                            }}, 300);
                        }});
                        
                        cmEditor.on("cursorActivity", (cm) => {{
                            const toolbar = document.getElementById("floating-toolbar");
                            if (!toolbar) return;
                            
                            if (cm.somethingSelected()) {{
                                const from = cm.getCursor("start");
                                const coords = cm.cursorCoords(from, "page");
                                toolbar.style.display = "flex";
                                const toolbarRect = toolbar.getBoundingClientRect();
                                
                                let top = coords.top - toolbarRect.height - 10;
                                let left = coords.left - (toolbarRect.width / 2) + 10;
                                
                                if (left < 10) left = 10;
                                if (left + toolbarRect.width > window.innerWidth) left = window.innerWidth - toolbarRect.width - 10;
                                if (top < window.scrollY) top = coords.bottom + 10;
                                
                                toolbar.style.top = top + "px";
                                toolbar.style.left = left + "px";
                            }} else {{
                                toolbar.style.display = "none";
                            }}
                        }});

                        cmEditor.getWrapperElement().addEventListener('contextmenu', function(e) {{
                            if (cmEditor.somethingSelected()) {{
                                return; // default context menu
                            }}
                            e.preventDefault();
                            
                            const coords = cmEditor.coordsChar({{left: e.clientX, top: e.clientY}}, "window");
                            cmEditor.setCursor(coords);
                            
                            const menu = document.getElementById("editor-context-menu");
                            if (!menu) return;
                            
                            menu.style.display = "flex";
                            const menuRect = menu.getBoundingClientRect();
                            let top = e.clientY;
                            let left = e.clientX;
                            
                            if (top + menuRect.height > window.innerHeight) {{
                                top = window.innerHeight - menuRect.height - 10;
                            }}
                            if (left + menuRect.width > window.innerWidth) {{
                                left = window.innerWidth - menuRect.width - 10;
                            }}
                            
                            if (left > window.innerWidth / 2) {{
                                menu.classList.add('menu-left');
                            }} else {{
                                menu.classList.remove('menu-left');
                            }}
                            
                            menu.style.top = top + window.scrollY + "px";
                            menu.style.left = left + window.scrollX + "px";
                            
                            const hasSubmenu = menu.querySelector('.has-submenu');
                            const submenu = menu.querySelector('.submenu');
                            if (hasSubmenu && submenu) {{
                                submenu.style.display = 'flex';
                                submenu.style.visibility = 'hidden';
                                const subRect = submenu.getBoundingClientRect();
                                submenu.style.display = '';
                                submenu.style.visibility = '';
                                
                                if (subRect.bottom > window.innerHeight) {{
                                    hasSubmenu.classList.add('submenu-up');
                                }} else {{
                                    hasSubmenu.classList.remove('submenu-up');
                                }}
                            }}
                        }});

                        // Interpolated Source Map Scroll Sync
                        let isSyncingLeft = false;
                        let isSyncingRight = false;
                        
                        cmEditor.on('scroll', () => {{
                            if (!isSyncingLeft) {{
                                isSyncingRight = true;
                                
                                const scrollInfo = cmEditor.getScrollInfo();
                                const previewPane = document.getElementById('preview-pane');
                                if (previewPane) {{
                                    if (scrollInfo.top <= 10) {{
                                        previewPane.scrollTop = 0;
                                    }} else if (scrollInfo.top >= scrollInfo.height - scrollInfo.clientHeight - 10) {{
                                        previewPane.scrollTop = previewPane.scrollHeight - previewPane.clientHeight;
                                    }} else {{
                                        const elements = Array.from(previewPane.querySelectorAll('[data-line]'));
                                        const containerRect = previewPane.getBoundingClientRect();
                                        
                                        let prevY = 0;
                                        let prevYPrime = 0;
                                        let nextY = scrollInfo.height;
                                        let nextYPrime = previewPane.scrollHeight;
                                        
                                        for (let i = 0; i < elements.length; i++) {{
                                            const line = parseInt(elements[i].getAttribute('data-line'));
                                            const y = cmEditor.heightAtLine(line, 'local');
                                            const elementRect = elements[i].getBoundingClientRect();
                                            const yPrime = previewPane.scrollTop + elementRect.top - containerRect.top;
                                            
                                            if (y <= scrollInfo.top) {{
                                                prevY = y;
                                                prevYPrime = yPrime;
                                            }} else {{
                                                nextY = y;
                                                nextYPrime = yPrime;
                                                break;
                                            }}
                                        }}

                                        let percentage = 0;
                                        if (nextY > prevY) {{
                                            percentage = (scrollInfo.top - prevY) / (nextY - prevY);
                                        }}
                                        previewPane.scrollTop = prevYPrime + percentage * (nextYPrime - prevYPrime);
                                    }}
                                }}
                                window.requestAnimationFrame(() => {{ isSyncingRight = false; }});
                            }}
                        }});

                        const previewPane = document.getElementById('preview-pane');
                        if (previewPane) {{
                            previewPane.addEventListener('scroll', () => {{
                                if (!isSyncingRight) {{
                                    isSyncingLeft = true;
                                    
                                    const scrollInfo = cmEditor.getScrollInfo();
                                    const scrollTop = previewPane.scrollTop;
                                    
                                    if (scrollTop <= 10) {{
                                        cmEditor.scrollTo(null, 0);
                                    }} else if (scrollTop >= previewPane.scrollHeight - previewPane.clientHeight - 10) {{
                                        cmEditor.scrollTo(null, scrollInfo.height - scrollInfo.clientHeight);
                                    }} else {{
                                        const elements = Array.from(previewPane.querySelectorAll('[data-line]'));
                                        const containerRect = previewPane.getBoundingClientRect();
                                        
                                        let prevYPrime = 0;
                                        let prevY = 0;
                                        let nextYPrime = previewPane.scrollHeight;
                                        let nextY = scrollInfo.height;

                                        for (let i = 0; i < elements.length; i++) {{
                                            const line = parseInt(elements[i].getAttribute('data-line'));
                                            const elementRect = elements[i].getBoundingClientRect();
                                            const yPrime = previewPane.scrollTop + elementRect.top - containerRect.top;
                                            const y = cmEditor.heightAtLine(line, 'local');
                                            
                                            if (yPrime <= scrollTop) {{
                                                prevYPrime = yPrime;
                                                prevY = y;
                                            }} else {{
                                                nextYPrime = yPrime;
                                                nextY = y;
                                                break;
                                            }}
                                        }}

                                        let percentage = 0;
                                        if (nextYPrime > prevYPrime) {{
                                            percentage = (scrollTop - prevYPrime) / (nextYPrime - prevYPrime);
                                        }}
                                        cmEditor.scrollTo(null, prevY + percentage * (nextY - prevY));
                                    }}
                                    window.requestAnimationFrame(() => {{ isSyncingLeft = false; }});
                                }}
                            }});
                        }}
                        
                        updatePreview(cmEditor.getValue());
                    }}
                }});
            }}

            if (btnCancel) {{
                btnCancel.addEventListener('click', () => {{
                    if (isDirty && !confirm("You have unsaved changes. Are you sure you want to cancel?")) return;
                    mdViewer.style.display = 'block';
                    splitView.style.display = 'none';
                    btnEdit.style.display = 'flex';
                    btnSave.style.display = 'none';
                    btnCancel.style.display = 'none';
                    isDirty = false;
                    window.isDirty = false;
                    if (cmEditor) cmEditor.setValue(document.getElementById('raw-markdown').textContent);
                }});
            }}

            if (btnSave) {{
                btnSave.addEventListener('click', async () => {{
                    if (!cmEditor) return;
                    const content = cmEditor.getValue();
                    window.isSaving = true;
                    const res = await fetch('/api/save', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ path: currentNoteId + ".md", content: content }})
                    }});
                    const data = await res.json();
                    if (data.success) {{
                        isDirty = false;
                        window.isDirty = false;
                        
                        const originalHTML = btnSave.innerHTML;
                        btnSave.innerHTML = '<i class="ti ti-check"></i> Saved!';
                        btnSave.style.backgroundColor = 'var(--success-color, #28a745)';
                        btnSave.style.color = '#fff';
                        btnSave.disabled = true;
                        
                        const rawTag = document.getElementById('raw-markdown');
                        if (rawTag) rawTag.textContent = content;
                        
                        setTimeout(() => {{
                            btnSave.innerHTML = originalHTML;
                            btnSave.style.backgroundColor = '';
                            btnSave.style.color = '';
                            window.isSaving = false;
                        }}, 1500);
                    }} else {{
                        window.isSaving = false;
                        alert("Error saving file: " + (data.error || "Unknown"));
                    }}
                }});
            }}

            async function updatePreview(text) {{
                const res = await fetch('/api/render', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ content: text }})
                }});
                if (res.ok) {{
                    const data = await res.json();
                    const preview = document.getElementById('live-preview');
                    preview.innerHTML = data.html;
                    if (typeof window.applyHighlighter === 'function') {{
                        window.applyHighlighter(localStorage.getItem('md-highlighter') || 'highlightjs', preview);
                    }}
                }}
            }}

            window.addEventListener('beforeunload', (e) => {{
                if (isDirty) {{
                    e.preventDefault();
                    e.returnValue = '';
                }}
            }});
            
            // Listen to theme changes to update CodeMirror theme
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {{
                if (cmEditor) {{
                    const isDark = document.documentElement.getAttribute('data-theme') === 'dark' || 
                                  (!document.documentElement.getAttribute('data-theme') && window.matchMedia('(prefers-color-scheme: dark)').matches);
                    cmEditor.setOption('theme', isDark ? 'material-ocean' : 'default');
                }}
            }});
            
            document.getElementById('theme-toggle')?.addEventListener('click', () => {{
                if (cmEditor) {{
                    setTimeout(() => {{
                        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
                        cmEditor.setOption('theme', isDark ? 'material-ocean' : 'default');
                    }}, 10);
                }}
            }});
        }})();
    </script>
</body>
</html>
"""
def render_file(path: str, all_notes: list[str] | None = None, note_id: str | None = None) -> str:
    text = Path(path).read_text(encoding="utf-8")
    body = _parser.render(text)
    title = note_id if note_id else Path(path).stem
    return wrap_in_template(body, title=title, nav=all_notes, raw_text=text, note_id=note_id or "")

def render_index(all_notes: list[str]) -> str:
    links = "".join(f'<li><a href="/{note.replace(" ", "-").lower()}">{note}</a></li>' for note in all_notes)
    body = f"""
    <h1>All Notes</h1>
    <p>Welcome to mdnotes! Select a note from the list below:</p>
    <ul class="index-list">
        {links}
    </ul>
    """
    return wrap_in_template(body, title="Index", nav=all_notes)
