import re
import streamlit as st
import markdown as md
from pathlib import Path

MERMAID_CDN     = "https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"
KATEX_CSS       = "https://cdn.jsdelivr.net/npm/katex@0.16/dist/katex.min.css"
KATEX_JS        = "https://cdn.jsdelivr.net/npm/katex@0.16/dist/katex.min.js"
KATEX_AUTORENDER = "https://cdn.jsdelivr.net/npm/katex@0.16/dist/contrib/auto-render.min.js"

_MATH_DISPLAY_RE = re.compile(r'\$\$(.*?)\$\$', re.DOTALL)
_MATH_INLINE_RE  = re.compile(r'(?<!\$)\$([^$\n]+?)\$(?!\$)')


def escape_html(text: str) -> str:
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))


def _protect_math(text: str) -> tuple:
    """Replace $...$ and $$...$$ with NUL-delimited placeholders before markdown processing."""
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


def extract_mermaid_blocks(text: str):
    """Return ordered list of ('markdown'|'mermaid', content) segments."""
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
    katex_autorender_init = (
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
        f'<script defer src="{KATEX_AUTORENDER}" onload="{katex_autorender_init}"></script>'
        f'</head><body style="font-family:sans-serif;padding:1rem">{html_body}'
        f'<script src="{MERMAID_CDN}"></script>'
        f'<script>mermaid.initialize({{startOnLoad:true}});</script>'
        f'</body></html>'
    )



def main():
    st.set_page_config(page_title="Markdown Viewer", layout="wide")
    st.title("Markdown Viewer — Streamlit")

    st.sidebar.header("Load Markdown")
    uploaded = st.sidebar.file_uploader("Upload a .md file", type=["md", "markdown"])
    use_example = st.sidebar.checkbox("Use example markdown", value=True)

    try:
        readme_path = Path(__file__).parent / "README.md"
        if readme_path.exists():
            with st.sidebar.expander("README", expanded=False):
                st.markdown(readme_path.read_text(encoding="utf-8"))
    except Exception:
        pass

    content = ""
    if uploaded is not None:
        content = uploaded.read().decode("utf-8")
    elif use_example:
        sample = Path(__file__).parent / "example.md"
        if sample.exists():
            content = sample.read_text(encoding="utf-8")

    if not content:
        st.info("Upload a markdown file or enable 'Use example markdown' in the sidebar.")
        return

    segments = extract_mermaid_blocks(content)
    html = to_html(segments)

    default_name = "document"
    if uploaded is not None and hasattr(uploaded, 'name'):
        default_name = Path(uploaded.name).stem

    st.sidebar.header("Export")

    if 'html_ready' not in st.session_state:
        st.session_state['html_ready'] = False
        st.session_state['html_bytes'] = None
        st.session_state['html_filename'] = ''

    html_filename = st.sidebar.text_input("Filename", value=default_name, key='html_filename_input')

    if st.sidebar.button("Save as HTML"):
        st.session_state['html_bytes'] = html.encode('utf-8')
        st.session_state['html_filename'] = f"{html_filename}.html"
        st.session_state['html_ready'] = True

    if st.session_state.get('html_ready') and st.session_state.get('html_bytes'):
        st.sidebar.download_button("Download HTML", data=st.session_state['html_bytes'], file_name=st.session_state['html_filename'], mime="text/html")
        if st.sidebar.button("Clear"):
            st.session_state['html_ready'] = False
            st.session_state['html_bytes'] = None
            st.session_state['html_filename'] = ''

    st.subheader("Rendered Document")
    st.iframe(html)


if __name__ == "__main__":
    main()
