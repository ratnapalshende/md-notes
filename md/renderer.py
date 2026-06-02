from pathlib import Path
from markdown_it import MarkdownIt
from mdit_py_plugins.front_matter import front_matter_plugin
from mdit_py_plugins.tasklists import tasklists_plugin
from mdit_py_plugins.footnote import footnote_plugin
from .extensions import callout_plugin, wikilink_plugin, embed_plugin, tag_plugin

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


def _render_nav_tree(tree: dict, active_title: str, depth: int = 0) -> str:
    """Recursively render the nav tree as nested HTML with collapsible folders."""
    html_parts = []
    # Sort: folders first, then files
    folders = sorted([k for k, v in tree.items() if isinstance(v, dict)])
    files = sorted([k for k, v in tree.items() if isinstance(v, str)])

    for folder in folders:
        # Check if active note is inside this folder
        is_open = _folder_contains_active(tree[folder], active_title)
        open_class = "open" if is_open else ""
        html_parts.append(f'<li class="nav-folder {open_class}">')
        html_parts.append(
            f'<div class="nav-folder-title">'
            f'<i class="ti ti-chevron-right nav-folder-chevron"></i>'
            f'<i class="ti ti-folder nav-folder-icon"></i>'
            f'<span>{folder}</span>'
            f'</div>'
        )
        html_parts.append('<ul class="nav-folder-children">')
        html_parts.append(_render_nav_tree(tree[folder], active_title, depth + 1))
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


def wrap_in_template(body: str, title: str, nav: list[str] | None = None) -> str:
    sidebar_html = ""
    body_class = "no-sidebar"
    
    if nav:
        body_class = ""
        tree = _build_nav_tree(nav)
        tree_html = _render_nav_tree(tree, title)
        home_active = "active" if title.lower() == "index" else ""
        sidebar_html = f"""
    <div class="sidebar">
        <h2>Notes</h2>
        <ul class="nav-tree">
            <li><a href="/" class="nav-file {home_active}"><i class="ti ti-home nav-file-icon"></i>Home</a></li>
            {tree_html}
        </ul>
    </div>
    """
    else:
        sidebar_html = """
    <div class="sidebar">
        <h2>Notes</h2>
        <ul class="nav-tree">
            <li><a href="/" class="nav-file active"><i class="ti ti-home nav-file-icon"></i>Home</a></li>
        </ul>
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
    <!-- Prevent sidebar flash: apply collapsed state before paint -->
    <script>
        (function() {{
            if (window.innerWidth > 768 && localStorage.getItem('sidebar-collapsed') === 'true') {{
                document.documentElement.classList.add('sidebar-collapsed');
            }}
        }})();
    </script>
    <style>
        :root {{
            --bg-primary: #ffffff;
            --bg-secondary: #f8f9fa;
            --text-primary: #1a1a1a;
            --text-secondary: #64748b;
            --border-color: #e2e8f0;
            --primary-color: #3b82f6;
            --primary-hover: #2563eb;
            --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            --font-mono: 'Fira Code', monospace;
            --sidebar-width: 260px;
        }}

        @media (prefers-color-scheme: dark) {{
            :root {{
                --bg-primary: #0f172a;
                --bg-secondary: #1e293b;
                --text-primary: #f8fafc;
                --text-secondary: #94a3b8;
                --border-color: #334155;
                --primary-color: #60a5fa;
                --primary-hover: #3b82f6;
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
            padding-left: 1.25rem;
            border-left: 1px solid var(--border-color);
            margin-left: 0.55rem;
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
        article h2 {{ font-size: 1.75rem; margin-top: 2rem; margin-bottom: 1rem; }}
        article h3 {{ font-size: 1.4rem; margin-top: 1.5rem; margin-bottom: 0.75rem; }}
        article p {{ margin-bottom: 1.25rem; }}
        article a {{ color: var(--primary-color); text-decoration: none; }}
        article a:hover {{ text-decoration: underline; }}

        /* Code highlight and blocks */
        pre {{
            background-color: var(--bg-secondary);
            border: 1px solid var(--border-color);
            padding: 1.25rem;
            border-radius: 0.5rem;
            overflow-x: auto;
            margin-bottom: 1.5rem;
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
        }}
    </style>
</head>
<body class="{body_class}">
    <button id="sidebar-toggle" class="sidebar-toggle" title="Toggle Sidebar">
        <i class="ti ti-menu-2"></i>
    </button>
    <div id="sidebar-backdrop" class="sidebar-backdrop"></div>
    {sidebar_html}
    <div class="content-wrapper">
        <article>
            {body}
        </article>
    </div>
    
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
</body>
</html>
"""

def render_file(path: str, all_notes: list[str] | None = None, note_id: str | None = None) -> str:
    text = Path(path).read_text(encoding="utf-8")
    body = _parser.render(text)
    title = note_id if note_id else Path(path).stem
    return wrap_in_template(body, title=title, nav=all_notes)

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
