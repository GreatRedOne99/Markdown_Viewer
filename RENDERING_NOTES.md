# Markdown Rendering — Session Notes
_Updated 2026-06-26 — migrated from Streamlit to Flask_

## Architecture

Single-file Flask app (`app.py`) that converts Markdown to a full HTML page with client-side KaTeX and Mermaid rendering. No iframe — the rendered document is served directly as the page content.

```
.md file → extract_mermaid_blocks() → render_body() → build_page() → browser
```

---

## Key: LaTeX with KaTeX

### Why `mdx_math` doesn't work with MathJax 3
`python-markdown-math` (`mdx_math`) outputs MathJax 2-style `<script type="math/tex">` tags. MathJax 3 does not process these by default. The combination silently drops all equations.

### Working approach: protect math, then render with KaTeX

**Step 1 — protect math before the markdown parser runs:**

```python
_MATH_DISPLAY_RE = re.compile(r'\$\$(.*?)\$\$', re.DOTALL)
_MATH_INLINE_RE  = re.compile(r'(?<!\$)\$([^$\n]+?)\$(?!\$)')

def _protect_math(text):
    # Replace $...$ and $$...$$ with NUL-delimited placeholders
    # Restore after markdown processing
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
```

KaTeX auto-render fires via `defer` + `onload` pattern after KaTeX itself loads.

---

## Key: Mermaid Diagrams

### Preserve document order
Extract mermaid blocks as ordered `(kind, content)` segments rather than stripping them all out. Otherwise diagrams always appear at the bottom.

```python
def extract_mermaid_blocks(text):
    # Returns list of ("markdown", content) and ("mermaid", content) tuples
    # in document order
```

### Render inline in the HTML

```python
for kind, chunk in segments:
    if kind == "markdown":
        ...
    else:
        parts.append(f'<div class="mermaid">{escape_html(chunk)}</div>')
```

Load the Mermaid CDN **after** the body content, **after** KaTeX. Load order matters — Mermaid last.

---

## Migration from Streamlit

### Why we moved
Streamlit reruns the entire script on every widget interaction. This caused:
- Search bar inside an iframe couldn't stay fixed (sticky/fixed positioning failed)
- Moving search to Streamlit widgets caused full page rerenders on every keystroke/button click
- Recent file selection required `session_state` hacks to work on first click
- File upload state persisted across interactions, blocking other load paths

### What changed
| Before (Streamlit) | After (Flask) |
|---|---|
| `st.iframe(html_string)` | Direct HTML page served by Flask |
| `st.sidebar` widgets | HTML sidebar with native form elements |
| `st.file_uploader` | Drag & drop + `<input type="file">` |
| `st.session_state` hacks | Standard HTTP request/response |
| Search in iframe or Streamlit widgets | In-page JS search, no rerenders |

### What stayed the same
- `extract_mermaid_blocks()` — unchanged
- `_protect_math()` / `_restore_math()` — unchanged
- KaTeX + Mermaid CDN loading pattern — unchanged
- `.recent_files.json` / `.uploaded_files/` — unchanged

---

## Pitfalls Summary

| Pitfall | Fix |
|---|---|
| `mdx_math` + MathJax 3 silently drops equations | Use KaTeX auto-render + manual math protection |
| Mermaid diagrams displaced to bottom of document | Return ordered segments, not stripped blocks |
| Streamlit reruns on every interaction | Migrated to Flask — standard request/response model |

---

## Dependencies (runtime)

```
flask>=3.1
markdown>=3.10
```

KaTeX and Mermaid load from CDN at runtime — no Python packages needed for rendering.
