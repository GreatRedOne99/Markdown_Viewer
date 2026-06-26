# Streamlit Markdown Rendering — Session Notes
_Captured 2026-06-12_

## Problem
Streamlit's built-in `st.markdown()` has two failure modes for rich documents:

1. **LaTeX**: Using `unsafe_allow_html=True` conflicts with KaTeX in the frontend — equations render as raw text.
2. **Mermaid diagrams**: There is no native Streamlit API for rendering Mermaid. `st.components.v1.html()` was deprecated in 1.58.0.

## Solution: Single HTML Pipeline

Render the entire document — markdown, LaTeX, and Mermaid diagrams — in one `st.iframe()` call using a self-contained HTML page built server-side.

```python
st.iframe(to_html(segments))
```

The iframe auto-sizes to content height because `st.iframe()` defaults to `height="content"`.

---

## Key: `st.iframe()` in Streamlit 1.58.0

```python
st.iframe(src, *, width="stretch", height="content", tab_index=None)
```

- `src` is **positional** — no `srcDoc` keyword argument (that raises `TypeError`).
- If `src` contains `<`, Streamlit detects it as HTML and embeds it as `srcdoc` automatically.
- `height="content"` auto-sizes the iframe to its rendered content — including after JavaScript runs.
- `scrolling` is always `True` in the new API (hardcoded in the source).

**Do not use** `st.components.v1.html()` — deprecated since 1.58.0, removed after 2026-06-01.

---

## Key: LaTeX with KaTeX

### Why `mdx_math` doesn't work with MathJax 3
`python-markdown-math` (`mdx_math`) outputs MathJax 2-style `<script type="math/tex">` tags. MathJax 3 does not process these by default. The combination silently drops all equations.

### Working approach: protect math, then render with KaTeX

**Step 1 — protect math before the markdown parser runs:**

```python
_MATH_DISPLAY_RE = re.compile(r'\$\$(.*?)\$\$', re.DOTALL)
_MATH_INLINE_RE  = re.compile(r'(?<!\$)\$([^$\n]+?)\$(?!\$)')

def _protect_math(text: str) -> tuple:
    store = {}
    counter = [0]

    def _save(latex: str) -> str:
        key = f"\x00MATH{counter[0]}\x00"
        store[key] = latex
        counter[0] += 1
        return key

    text = _MATH_DISPLAY_RE.sub(lambda m: _save(f'$${m.group(1)}$$'), text)
    text = _MATH_INLINE_RE.sub(lambda m: _save(f'${m.group(1)}$'), text)
    return text, store

def _restore_math(html: str, store: dict) -> str:
    for key, val in store.items():
        html = html.replace(key, val)
    return html
```

`\x00`-delimited keys are safe because they never appear in normal markdown text and the markdown parser ignores them.

**Step 2 — process markdown without the `mdx_math` extension:**

```python
protected, store = _protect_math(chunk)
html_part = md.markdown(protected, extensions=["fenced_code", "tables"])
html_part = _restore_math(html_part, store)
```

**Step 3 — KaTeX CDN in the HTML head:**

```python
KATEX_CSS        = "https://cdn.jsdelivr.net/npm/katex@0.16/dist/katex.min.css"
KATEX_JS         = "https://cdn.jsdelivr.net/npm/katex@0.16/dist/katex.min.js"
KATEX_AUTORENDER = "https://cdn.jsdelivr.net/npm/katex@0.16/dist/contrib/auto-render.min.js"

katex_init = (
    "renderMathInElement(document.body,{"
    "delimiters:["
    "{left:'$$',right:'$$',display:true},"
    "{left:'$',right:'$',display:false}"
    "]});"
)

head = (
    f'<link rel="stylesheet" href="{KATEX_CSS}">'
    f'<script defer src="{KATEX_JS}"></script>'
    f'<script defer src="{KATEX_AUTORENDER}" onload="{katex_init}"></script>'
)
```

KaTeX is the same engine Streamlit uses internally. The `defer` + `onload` pattern ensures auto-render fires after KaTeX itself loads.

---

## Key: Mermaid Diagrams

### Preserve document order
Extract mermaid blocks as ordered `(kind, content)` segments rather than stripping them all out. Otherwise diagrams always appear at the bottom.

```python
def extract_mermaid_blocks(text: str):
    pattern = re.compile(r"```mermaid\n(.*?)\n```", re.DOTALL | re.IGNORECASE)
    segments = []
    last_end = 0
    for match in pattern.finditer(text):
        if match.start() > last_end:
            segments.append(("markdown", text[last_end:match.start()]))
        segments.append(("mermaid", match.group(1)))
        last_end = match.end()
    if last_end < len(text):
        segments.append(("markdown", text[last_end:]))
    return segments
```

### Render inline in the HTML

```python
for kind, chunk in segments:
    if kind == "markdown":
        ...
    else:
        parts.append(f'<div class="mermaid">{escape_html(chunk)}</div>')
```

Then at the bottom of `<body>`:

```python
MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"

f'<script src="{MERMAID_CDN}"></script>'
f'<script>mermaid.initialize({{startOnLoad:true}});</script>'
```

Load the Mermaid CDN **after** the body content, **after** KaTeX. Load order matters — Mermaid last.

---

## Complete `to_html` function

```python
def to_html(segments: list) -> str:
    parts = []
    for kind, chunk in segments:
        if kind == "markdown":
            protected, store = _protect_math(chunk)
            html_part = md.markdown(protected, extensions=["fenced_code", "tables"])
            parts.append(_restore_math(html_part, store))
        else:
            parts.append(f'<div class="mermaid">{escape_html(chunk)}</div>')
    html_body = "".join(parts)
    katex_init = (
        "renderMathInElement(document.body,{"
        "delimiters:["
        "{left:'$$',right:'$$',display:true},"
        "{left:'$',right:'$',display:false}"
        "]});"
    )
    return (
        f'<html><head><meta charset="utf-8">'
        f'<link rel="stylesheet" href="{KATEX_CSS}">'
        f'<script defer src="{KATEX_JS}"></script>'
        f'<script defer src="{KATEX_AUTORENDER}" onload="{katex_init}"></script>'
        f'</head><body style="font-family:sans-serif;padding:1rem">{html_body}'
        f'<script src="{MERMAID_CDN}"></script>'
        f'<script>mermaid.initialize({{startOnLoad:true}});</script>'
        f'</body></html>'
    )
```

---

## Pitfalls Summary

| Pitfall | Fix |
|---|---|
| `st.components.v1.html()` deprecated | Use `st.iframe(html_string)` |
| `st.iframe(srcDoc=...)` raises `TypeError` | Pass HTML as plain positional arg: `st.iframe(html)` |
| `mdx_math` + MathJax 3 silently drops equations | Use KaTeX auto-render + manual math protection |
| `unsafe_allow_html=True` breaks KaTeX in `st.markdown()` | Move rendering to `st.iframe()` entirely |
| Mermaid diagrams displaced to bottom of document | Return ordered segments, not stripped blocks |
| Diagram height cut off | `st.iframe()` with `height="content"` auto-sizes after JS renders |
| Temp file leak on every PDF failure | Pass bytes directly to `st.download_button(data=...)` |

---

## Dependencies (runtime)

```
streamlit>=1.58.0
markdown>=3.10.2
```

KaTeX and Mermaid load from CDN at runtime — no Python packages needed for rendering.
