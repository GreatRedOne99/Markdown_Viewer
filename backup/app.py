import os
import re
import json
import threading
import streamlit as st
import markdown as md
from pathlib import Path

RECENT_FILES_PATH = Path(__file__).parent / ".recent_files.json"
UPLOAD_CACHE_DIR = Path(__file__).parent / ".uploaded_files"
MAX_RECENT_FILES = 20

MERMAID_CDN     = "https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"
KATEX_CSS       = "https://cdn.jsdelivr.net/npm/katex@0.16/dist/katex.min.css"
KATEX_JS        = "https://cdn.jsdelivr.net/npm/katex@0.16/dist/katex.min.js"
KATEX_AUTORENDER = "https://cdn.jsdelivr.net/npm/katex@0.16/dist/contrib/auto-render.min.js"

_MATH_DISPLAY_RE = re.compile(r'\$\$(.*?)\$\$', re.DOTALL)
_MATH_INLINE_RE  = re.compile(r'(?<!\$)\$([^$\n]+?)\$(?!\$)')


def load_recent_files() -> list[str]:
    if RECENT_FILES_PATH.exists():
        try:
            return json.loads(RECENT_FILES_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return []


def save_recent_file(name: str):
    recents = load_recent_files()
    if name in recents:
        recents.remove(name)
    recents.insert(0, name)
    recents = recents[:MAX_RECENT_FILES]
    RECENT_FILES_PATH.write_text(json.dumps(recents), encoding="utf-8")


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
    search_bar_html = (
        '<div id="search-bar" style="position:fixed;top:0;left:0;right:0;z-index:9999;'
        'background:#fff;padding:6px 10px;border-bottom:1px solid #ddd;'
        'display:flex;align-items:center;gap:8px;box-shadow:0 2px 4px rgba(0,0,0,0.1);">'
        '<input id="search-input" type="text" placeholder="Search document…" '
        'style="flex:1;padding:4px 8px;font-size:14px;border:1px solid #ccc;border-radius:4px;">'
        '<label style="font-size:13px;color:#666;display:flex;align-items:center;gap:3px;'
        'cursor:pointer;white-space:nowrap;">'
        '<input id="regex-toggle" type="checkbox" style="cursor:pointer;"> Regex</label>'
        '<span id="search-count" style="font-size:13px;color:#666;min-width:70px;text-align:center;"></span>'
        '<button onclick="searchNav(-1)" style="padding:2px 8px;cursor:pointer;border:1px solid #ccc;'
        'border-radius:3px;background:#f5f5f5;">▲</button>'
        '<button onclick="searchNav(1)" style="padding:2px 8px;cursor:pointer;border:1px solid #ccc;'
        'border-radius:3px;background:#f5f5f5;">▼</button>'
        '<button onclick="clearSearch()" style="padding:2px 8px;cursor:pointer;border:1px solid #ccc;'
        'border-radius:3px;background:#f5f5f5;">✕</button>'
        '</div>'
    )
    search_script = """
<script>
let searchIndex = -1, marks = [];
function doSearch() {
  clearMarks();
  const q = document.getElementById('search-input').value.trim();
  if (!q) { document.getElementById('search-count').textContent = ''; return; }
  const useRegex = document.getElementById('regex-toggle').checked;
  let regex;
  if (useRegex) {
    try { regex = new RegExp(q, 'gi'); }
    catch(e) { document.getElementById('search-count').textContent = 'Bad regex'; return; }
  }
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const hits = [];
  while (walker.nextNode()) {
    const node = walker.currentNode;
    if (node.parentElement && node.parentElement.closest('#search-bar')) continue;
    const text = node.textContent;
    if (useRegex) {
      regex.lastIndex = 0;
      let m;
      while ((m = regex.exec(text)) !== null) {
        if (m[0].length === 0) { regex.lastIndex++; continue; }
        hits.push({node, idx: m.index, len: m[0].length});
      }
    } else {
      let idx, start = 0, lower = text.toLowerCase(), ql = q.toLowerCase();
      while ((idx = lower.indexOf(ql, start)) !== -1) {
        hits.push({node, idx, len: q.length});
        start = idx + q.length;
      }
    }
  }
  for (let i = hits.length - 1; i >= 0; i--) {
    const h = hits[i], r = document.createRange();
    r.setStart(h.node, h.idx);
    r.setEnd(h.node, h.idx + h.len);
    const mark = document.createElement('mark');
    mark.style.background = '#ffeb3b';
    mark.style.padding = '0';
    r.surroundContents(mark);
    marks.unshift(mark);
  }
  searchIndex = marks.length > 0 ? 0 : -1;
  updateCount();
  if (searchIndex >= 0) scrollToMark();
}
function clearMarks() {
  marks.forEach(m => { const p = m.parentNode; p.replaceChild(document.createTextNode(m.textContent), m); p.normalize(); });
  marks = []; searchIndex = -1;
}
function scrollToMark() {
  marks.forEach((m, i) => m.style.background = i === searchIndex ? '#ff9800' : '#ffeb3b');
  marks[searchIndex].scrollIntoView({behavior:'smooth', block:'center'});
  updateCount();
}
function updateCount() {
  document.getElementById('search-count').textContent = marks.length ? (searchIndex+1)+'/'+marks.length : 'No results';
}
function searchNav(dir) {
  if (!marks.length) return;
  searchIndex = (searchIndex + dir + marks.length) % marks.length;
  scrollToMark();
}
function clearSearch() {
  clearMarks();
  document.getElementById('search-input').value = '';
  document.getElementById('search-count').textContent = '';
}
document.addEventListener('DOMContentLoaded', function() {
  let timer;
  document.getElementById('search-input').addEventListener('input', function() {
    clearTimeout(timer);
    timer = setTimeout(doSearch, 250);
  });
  document.getElementById('regex-toggle').addEventListener('change', doSearch);
  document.getElementById('search-input').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') { e.preventDefault(); searchNav(e.shiftKey ? -1 : 1); }
  });
});
</script>
"""
    return (
        f'<html><head><meta charset="utf-8">'
        f'<link rel="stylesheet" href="{KATEX_CSS}">'
        f'<script defer src="{KATEX_JS}"></script>'
        f'<script defer src="{KATEX_AUTORENDER}" onload="{katex_autorender_init}"></script>'
        f'</head><body style="font-family:sans-serif;padding:40px 1rem 1rem 1rem">'
        f'{search_bar_html}{html_body}'
        f'<script src="{MERMAID_CDN}"></script>'
        f'<script>mermaid.initialize({{startOnLoad:true}});</script>'
        f'{search_script}'
        f'</body></html>'
    )



def main():
    st.set_page_config(page_title="Markdown Viewer", layout="wide")
    st.title("Markdown Viewer — Streamlit")

    st.sidebar.header("Load Markdown")
    uploaded = st.sidebar.file_uploader("Upload a .md file", type=["md", "markdown"])
    use_example = st.sidebar.checkbox("Use example markdown", value=True)

    recents = load_recent_files()
    st.sidebar.header("Recent Files")
    if recents:
        st.sidebar.selectbox(
            "Open a recent file",
            options=[""] + recents,
            format_func=lambda x: "— select —" if x == "" else Path(x).name,
            key="recent_select",
        )
        selected_recent = st.session_state.get("recent_select", "")
    else:
        selected_recent = ""
        st.sidebar.caption("No recent files yet.")

    try:
        readme_path = Path(__file__).parent / "README.md"
        if readme_path.exists():
            with st.sidebar.expander("README", expanded=False):
                st.markdown(readme_path.read_text(encoding="utf-8"))
    except Exception:
        pass

    content = ""
    active_name = None
    if selected_recent:
        recent_path = Path(selected_recent)
        if recent_path.exists():
            content = recent_path.read_text(encoding="utf-8")
            active_name = selected_recent
        else:
            st.sidebar.warning(f"File not found: {selected_recent}")
    elif uploaded is not None:
        content = uploaded.read().decode("utf-8")
        if content:
            UPLOAD_CACHE_DIR.mkdir(exist_ok=True)
            cached = UPLOAD_CACHE_DIR / uploaded.name
            cached.write_text(content, encoding="utf-8")
            active_name = str(cached.resolve())
    elif use_example:
        sample = Path(__file__).parent / "example.md"
        if sample.exists():
            content = sample.read_text(encoding="utf-8")

    if active_name:
        save_recent_file(active_name)

    if not content:
        st.info("Upload a markdown file or enable 'Use example markdown' in the sidebar.")
        return

    segments = extract_mermaid_blocks(content)

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
        st.session_state['html_bytes'] = to_html(segments).encode('utf-8')
        st.session_state['html_filename'] = f"{html_filename}.html"
        st.session_state['html_ready'] = True

    if st.session_state.get('html_ready') and st.session_state.get('html_bytes'):
        st.sidebar.download_button("Download HTML", data=st.session_state['html_bytes'], file_name=st.session_state['html_filename'], mime="text/html")
        if st.sidebar.button("Clear"):
            st.session_state['html_ready'] = False
            st.session_state['html_bytes'] = None
            st.session_state['html_filename'] = ''

    st.subheader("Rendered Document")

    html = to_html(segments)
    st.iframe(html)

    st.sidebar.divider()
    if st.sidebar.button("Shutdown App", type="primary"):
        threading.Timer(0.5, lambda: os._exit(0)).start()
        st.sidebar.success("Shutting down… you can close this tab.")
        st.stop()


if __name__ == "__main__":
    main()
