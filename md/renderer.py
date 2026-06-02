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
            f'<div class="nav-folder-title">'
            f'<i class="ti ti-chevron-right nav-folder-chevron"></i>'
            f'<i class="ti ti-folder nav-folder-icon"></i>'
            f'<span style="flex-grow: 1;">{folder}</span>'
            f'<button class="folder-new-file-btn" title="New File" style="background: none; border: none; cursor: pointer; color: var(--text-secondary); opacity: 0; transition: opacity 0.2s; padding: 0.2rem; display: flex; align-items: center;" onclick="event.stopPropagation(); window.createNoteInFolder(\'{folder_path}\');">'
            f'<i class="ti ti-file-plus"></i></button>'
            f'</div>'
        )
        html_parts.append('<ul class="nav-folder-children">')
        html_parts.append(_render_nav_tree(tree[folder], active_title, depth + 1, folder_path))
        html_parts.append('</ul>')
        html_parts.append('</li>')

    for file_name in files:
        full_path = tree[file_name]
        slug = full_path.replace(" ", "-").lower()
        is_active = "active" if full_path.lower() == active_title.lower() else ""
        display = file_name.replace("-", " ").replace("_", " ")
        html_parts.append(
            f'<li><a href="/{slug}" class="nav-file {is_active}">'
            f'<i class="ti ti-file-text nav-file-icon"></i>'
            f'{display}</a></li>'
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
            <li><a href="/" class="nav-file {home_active}"><i class="ti ti-home nav-file-icon"></i>Home</a></li>
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
            <li><a href="/" class="nav-file active"><i class="ti ti-home nav-file-icon"></i>Home</a></li>
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
            padding-left: 1.5rem;
            border-left: 1px solid var(--border-color);
            margin-left: 0.75rem;
        }}

        .nav-folder.open > .nav-folder-children {{
            max-height: 2000px;
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
            let socket = new WebSocket(socketUrl);
            socket.onmessage = function(event) {{
                if (event.data === "reload") {{
                    window.location.reload();
                }}
            }};
            socket.onclose = function() {{
                console.log("WebSocket connection closed. Reconnecting...");
                setTimeout(function() {{
                    window.location.reload();
                }}, 2000);
            }};
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
                            extraKeys: {{"Enter": "newlineAndIndentContinueMarkdownList"}}
                        }});
                        cmEditor.setValue(rawText);
                        
                        cmEditor.on('change', () => {{
                            isDirty = true;
                            clearTimeout(debounceTimer);
                            debounceTimer = setTimeout(() => {{
                                updatePreview(cmEditor.getValue());
                            }}, 300);
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
                    if (cmEditor) cmEditor.setValue(document.getElementById('raw-markdown').textContent);
                }});
            }}

            if (btnSave) {{
                btnSave.addEventListener('click', async () => {{
                    if (!cmEditor) return;
                    const content = cmEditor.getValue();
                    const res = await fetch('/api/save', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ path: currentNoteId + ".md", content: content }})
                    }});
                    const data = await res.json();
                    if (data.success) {{
                        isDirty = false;
                        window.location.reload();
                    }} else {{
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
