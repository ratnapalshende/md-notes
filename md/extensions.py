import re
from pathlib import Path
from markdown_it import MarkdownIt

# Constants
CALLOUT_RE = re.compile(r"^\[!(\w+)\]\s*(.*)?$")
WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
EMBED_RE = re.compile(r"!\[\[([^\]]+)\]\]")
TAG_RE = re.compile(r"(?<!\w)#([\w/]+)")

CALLOUT_ICONS = {
    "note": "ti-info-circle",
    "warning": "ti-alert-triangle",
    "tip": "ti-bulb",
    "important": "ti-star",
    "caution": "ti-flame",
    "danger": "ti-skull",
    # user-defined types fall back to ti-bookmark
}


def callout_plugin(md: MarkdownIt) -> None:
    """Renders Obsidian-style callouts from markdown blockquotes."""
    original_blockquote_open = md.renderer.rules.get("blockquote_open")
    original_blockquote_close = md.renderer.rules.get("blockquote_close")

    def render_blockquote_open(self, tokens, idx, options, env):
        if env is None:
            env = {}
        if not isinstance(env, dict):
            env = {}

        # Peek at next token's inline children for [!TYPE]
        inline_token = tokens[idx + 2] if idx + 2 < len(tokens) else None
        m = None
        if inline_token and inline_token.children:
            first_child = inline_token.children[0]
            if first_child.type == "text":
                m = CALLOUT_RE.match(first_child.content.strip())

        if not m:
            if original_blockquote_open:
                return original_blockquote_open(self, tokens, idx, options, env)
            return "<blockquote>"

        ctype = m.group(1).lower()
        title = m.group(2) or ctype.capitalize()
        icon = CALLOUT_ICONS.get(ctype, "ti-bookmark")

        # Consume the [!TYPE] header and following softbreak from children
        inline_token.children.pop(0)
        if inline_token.children and inline_token.children[0].type == "softbreak":
            inline_token.children.pop(0)

        # Record callout status on stack
        if "callout_stack" not in env:
            env["callout_stack"] = []
        env["callout_stack"].append(True)

        return (
            f'<div class="callout callout-{ctype}" data-callout="{ctype}">'
            f'<div class="callout-title"><i class="ti {icon}"></i> {title}</div>'
            f'<div class="callout-body">'
        )

    def render_blockquote_close(self, tokens, idx, options, env):
        if env is None:
            env = {}
        if isinstance(env, dict) and env.get("callout_stack") and env["callout_stack"].pop():
            return "</div></div>"
        if original_blockquote_close:
            return original_blockquote_close(self, tokens, idx, options, env)
        return "</blockquote>"

    md.add_render_rule("blockquote_open", render_blockquote_open)
    md.add_render_rule("blockquote_close", render_blockquote_close)


def wikilink_plugin(md: MarkdownIt) -> None:
    """Renders Obsidian-style wikilinks [[Note Title|Custom Label]]."""
    def tokenize(state, silent):
        if state.src[state.pos : state.pos + 2] != "[[":
            return False
        m = WIKILINK_RE.match(state.src[state.pos :])
        if not m:
            return False
        if not silent:
            token = state.push("wikilink", "", 0)
            token.attrSet("target", m.group(1))
            token.attrSet("label", m.group(2) or m.group(1))
        state.pos += m.end()
        return True

    def render_wikilink(self, tokens, idx, options, env):
        target = tokens[idx].attrGet("target")
        label = tokens[idx].attrGet("label")
        slug = target.replace(" ", "-").lower()
        return f'<a href="/{slug}" class="wikilink">{label}</a>'

    md.inline.ruler.push("wikilink", tokenize)
    md.add_render_rule("wikilink", render_wikilink)


def embed_plugin(md: MarkdownIt) -> None:
    """Recursively embeds files referencing ![[Note Title]]."""
    def tokenize(state, silent):
        if state.src[state.pos : state.pos + 3] != "![[":
            return False
        m = EMBED_RE.match(state.src[state.pos :])
        if not m:
            return False
        if not silent:
            token = state.push("embed", "", 0)
            token.attrSet("target", m.group(1))
        state.pos += m.end()
        return True

    def render_embed(self, tokens, idx, options, env):
        target = tokens[idx].attrGet("target")
        if env is None:
            env = {}
        if not isinstance(env, dict):
            env = {}

        current_dir = env.get("current_dir")
        if not current_dir:
            current_dir = Path.cwd()
        else:
            current_dir = Path(current_dir)

        target_path = current_dir / target
        if not target_path.suffix:
            target_path = target_path.with_suffix(".md")

        if not target_path.exists():
            return f'<div class="embed-error">Embedded file not found: {target}</div>'

        embed_depth = env.get("embed_depth", 0)
        if embed_depth > 5:
            return '<div class="embed-error">Max embed depth exceeded</div>'

        try:
            content = target_path.read_text(encoding="utf-8")
            child_env = env.copy()
            child_env["embed_depth"] = embed_depth + 1
            child_env["current_dir"] = target_path.parent

            rendered = md.render(content, child_env)
            return f'<div class="embed" data-target="{target}">{rendered}</div>'
        except Exception as e:
            return f'<div class="embed-error">Error rendering embed: {str(e)}</div>'

    md.inline.ruler.push("embed", tokenize)
    md.add_render_rule("embed", render_embed)


def tag_plugin(md: MarkdownIt) -> None:
    """Renders hashtags #hashtag as clickable elements."""
    def tokenize(state, silent):
        if state.src[state.pos] != "#":
            return False
        
        # Ensure no word character precedes the '#' (e.g. not a part of another word)
        if state.pos > 0 and re.match(r"\w", state.src[state.pos - 1]):
            return False
            
        m = re.match(r"^#([\w/]+)", state.src[state.pos :])
        if not m:
            return False

        if not silent:
            token = state.push("tag", "", 0)
            token.attrSet("tagname", m.group(1))
        state.pos += m.end()
        return True

    def render_tag(self, tokens, idx, options, env):
        tagname = tokens[idx].attrGet("tagname")
        return f'<a href="/?tag={tagname}" class="tag">#{tagname}</a>'

    md.inline.ruler.push("tag", tokenize)
    md.add_render_rule("tag", render_tag)