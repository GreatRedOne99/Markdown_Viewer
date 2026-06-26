import os
import re
import json
import signal
import markdown as md
from pathlib import Path
from flask import Flask, request, redirect, url_for, send_file, make_response
from markupsafe import Markup
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

BASE_DIR = Path(__file__).parent
RECENT_FILES_PATH = BASE_DIR / ".recent_files.json"
UPLOAD_DIR = BASE_DIR / ".uploaded_files"
UPLOAD_DIR.mkdir(exist_ok=True)
MAX_RECENT_FILES = 20

MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"
KATEX_CSS = "https://cdn.jsdelivr.net/npm/katex@0.16/dist/katex.min.css"
KATEX_JS = "https://cdn.jsdelivr.net/npm/katex@0.16/dist/katex.min.js"
KATEX_AUTORENDER = "https://cdn.jsdelivr.net/npm/katex@0.16/dist/contrib/auto-render.min.js"

_MATH_DISPLAY_RE = re.compile(r'\$\$(.*?)\$\$', re.DOTALL)
_MATH_INLINE_RE = re.compile(r'(?<!\$)\$([^$\n]+?)\$(?!\$)')


# ── Recent files ──────────────────────────────────────────────

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


# ── Markdown → HTML rendering ────────────────────────────────

def escape_html(text: str) -> str:
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))


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


def render_body(segments: list) -> str:
    parts = []
    for kind, chunk in segments:
        if kind == "markdown":
            protected, store = _protect_math(chunk)
            html_part = md.markdown(protected, extensions=["fenced_code", "tables"])
            parts.append(_restore_math(html_part, store))
        else:
            parts.append(f'<div class="mermaid">{escape_html(chunk)}</div>')
    return "".join(parts)


# ── Page templates ────────────────────────────────────────────

SEARCH_SCRIPT = """
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
  const walker = document.createTreeWalker(
    document.getElementById('doc-content'), NodeFilter.SHOW_TEXT);
  const hits = [];
  while (walker.nextNode()) {
    const node = walker.currentNode;
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
  marks.forEach(m => {
    const p = m.parentNode;
    p.replaceChild(document.createTextNode(m.textContent), m);
    p.normalize();
  });
  marks = []; searchIndex = -1;
}
function scrollToMark() {
  marks.forEach((m, i) => m.style.background = i === searchIndex ? '#ff9800' : '#ffeb3b');
  marks[searchIndex].scrollIntoView({behavior:'smooth', block:'center'});
  updateCount();
}
function updateCount() {
  document.getElementById('search-count').textContent =
    marks.length ? (searchIndex+1)+'/'+marks.length : 'No results';
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
"""

DRAG_DROP_SCRIPT = """
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const uploadForm = document.getElementById('upload-form');

['dragenter','dragover'].forEach(e =>
  dropZone.addEventListener(e, ev => { ev.preventDefault(); dropZone.classList.add('drag-over'); }));
['dragleave','drop'].forEach(e =>
  dropZone.addEventListener(e, ev => { ev.preventDefault(); dropZone.classList.remove('drag-over'); }));

dropZone.addEventListener('drop', function(e) {
  const file = e.dataTransfer.files[0];
  if (file) { fileInput.files = e.dataTransfer.files; uploadForm.submit(); }
});
dropZone.addEventListener('click', function() { fileInput.click(); });
fileInput.addEventListener('change', function() { if (fileInput.files.length) uploadForm.submit(); });
"""


def build_page(body_html: str, filename: str = "") -> str:
    recents = load_recent_files()
    recent_options = ""
    for path in recents:
        name = Path(path).name
        encoded = path.replace("\\", "/")
        selected = ' selected' if path == filename else ''
        recent_options += f'<option value="{Markup.escape(encoded)}"{selected}>{Markup.escape(name)}</option>\n'

    katex_autorender_init = (
        "renderMathInElement(document.getElementById('doc-content'),{"
        "delimiters:["
        "{left:'$$',right:'$$',display:true},"
        "{left:'$',right:'$',display:false}"
        "]});"
    )

    display_name = Path(filename).name if filename else "No file loaded"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Markdown Viewer</title>
  <link rel="stylesheet" href="{KATEX_CSS}">
  <script defer src="{KATEX_JS}"></script>
  <script defer src="{KATEX_AUTORENDER}" onload="{katex_autorender_init}"></script>
  <style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           display:flex; height:100vh; overflow:hidden; }}
    #sidebar {{ width:280px; min-width:280px; background:#f8f9fa; border-right:1px solid #ddd;
                padding:16px; overflow-y:auto; display:flex; flex-direction:column; gap:16px; }}
    #sidebar h1 {{ font-size:18px; color:#333; }}
    #sidebar h2 {{ font-size:14px; color:#666; margin-bottom:4px; text-transform:uppercase;
                   letter-spacing:0.5px; }}
    #sidebar select, #sidebar input[type=text] {{
      width:100%; padding:6px 8px; font-size:13px; border:1px solid #ccc; border-radius:4px; }}
    #sidebar button {{ width:100%; padding:8px; font-size:13px; cursor:pointer;
                       border:1px solid #ccc; border-radius:4px; background:#fff; }}
    #sidebar button:hover {{ background:#e9ecef; }}
    #sidebar button.danger {{ background:#dc3545; color:#fff; border-color:#dc3545; }}
    #sidebar button.danger:hover {{ background:#c82333; }}
    #drop-zone {{ border:2px dashed #ccc; border-radius:8px; padding:20px; text-align:center;
                  cursor:pointer; color:#888; font-size:13px; transition:all 0.2s; }}
    #drop-zone.drag-over {{ border-color:#4a9eff; background:#e8f0fe; color:#333; }}
    #main {{ flex:1; display:flex; flex-direction:column; overflow:hidden; }}
    #search-bar {{ display:flex; align-items:center; gap:8px; padding:8px 16px;
                   background:#fff; border-bottom:1px solid #ddd;
                   box-shadow:0 1px 3px rgba(0,0,0,0.08); }}
    #search-input {{ flex:1; padding:6px 10px; font-size:14px; border:1px solid #ccc;
                     border-radius:4px; }}
    #search-bar label {{ font-size:13px; color:#666; cursor:pointer; white-space:nowrap;
                         display:flex; align-items:center; gap:3px; }}
    #search-count {{ font-size:13px; color:#666; min-width:70px; text-align:center; }}
    #search-bar button {{ padding:4px 10px; cursor:pointer; border:1px solid #ccc;
                          border-radius:3px; background:#f5f5f5; font-size:14px; }}
    #search-bar button:hover {{ background:#e0e0e0; }}
    #doc-content {{ flex:1; overflow-y:auto; padding:24px 32px; font-family:sans-serif;
                    line-height:1.6; }}
    #doc-content h1 {{ margin: 1em 0 0.5em; }}
    #doc-content h2 {{ margin: 0.8em 0 0.4em; }}
    #doc-content h3 {{ margin: 0.6em 0 0.3em; }}
    #doc-content pre {{ background:#f4f4f4; padding:12px; border-radius:4px; overflow-x:auto; }}
    #doc-content code {{ background:#f4f4f4; padding:2px 4px; border-radius:3px; font-size:0.9em; }}
    #doc-content pre code {{ background:none; padding:0; }}
    #doc-content table {{ border-collapse:collapse; margin:1em 0; }}
    #doc-content th, #doc-content td {{ border:1px solid #ddd; padding:8px 12px; }}
    #doc-content th {{ background:#f4f4f4; }}
    #doc-content blockquote {{ border-left:4px solid #ddd; margin:1em 0; padding:0.5em 1em;
                               color:#666; }}
    #doc-content img {{ max-width:100%; }}
    .section {{ border-bottom:1px solid #eee; padding-bottom:12px; }}
    .file-label {{ font-size:12px; color:#999; margin-top:4px; word-break:break-all; }}
    .spacer {{ flex:1; }}
  </style>
</head>
<body>
  <div id="sidebar">
    <h1>Markdown Viewer</h1>

    <div class="section">
      <h2>Upload File</h2>
      <form id="upload-form" action="/upload" method="post" enctype="multipart/form-data">
        <input type="file" id="file-input" name="file" accept=".md,.markdown" hidden>
        <div id="drop-zone">Drop .md file here or click to browse</div>
      </form>
    </div>

    <div class="section">
      <h2>Recent Files</h2>
      {'<select id="recent-select" onchange="if(this.value)window.location.href=&#x27;/view?file=&#x27;+encodeURIComponent(this.value)">'
       '<option value="">— select —</option>'
       f'{recent_options}</select>' if recents else '<p style="font-size:13px;color:#999;">No recent files yet.</p>'}
    </div>

    <div class="section">
      <h2>Current File</h2>
      <p class="file-label">{Markup.escape(display_name)}</p>
    </div>

    {f'''<div class="section">
      <h2>Export</h2>
      <a href="/export?file={Markup.escape(filename.replace(chr(92), "/"))}" style="text-decoration:none;">
        <button type="button">Download as HTML</button>
      </a>
    </div>''' if filename else ''}

    <div class="spacer"></div>

    <button class="danger" onclick="if(confirm('Shut down the viewer?'))fetch('/shutdown',{{method:'POST'}}).then(()=>document.body.innerHTML='<h2 style=padding:2em>Server stopped. You can close this tab.</h2>')">
      Shutdown App
    </button>
  </div>

  <div id="main">
    <div id="search-bar">
      <input id="search-input" type="text" placeholder="Search document…">
      <label><input id="regex-toggle" type="checkbox"> Regex</label>
      <span id="search-count"></span>
      <button onclick="searchNav(-1)">&#9650;</button>
      <button onclick="searchNav(1)">&#9660;</button>
      <button onclick="clearSearch()">&#10005;</button>
    </div>
    <div id="doc-content">
      {body_html}
    </div>
  </div>

  <script src="{MERMAID_CDN}"></script>
  <script>mermaid.initialize({{startOnLoad:true}});</script>
  <script>{SEARCH_SCRIPT}</script>
  <script>{DRAG_DROP_SCRIPT}</script>
</body>
</html>"""


# ── Routes ────────────────────────────────────────────────────

@app.route("/")
def index():
    example = BASE_DIR / "example.md"
    if example.exists():
        content = example.read_text(encoding="utf-8")
        segments = extract_mermaid_blocks(content)
        body = render_body(segments)
        return build_page(body)
    return build_page("<p>Upload a markdown file to get started.</p>")


@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("file")
    if not file or not file.filename:
        return redirect(url_for("index"))
    filename = secure_filename(file.filename)
    save_path = UPLOAD_DIR / filename
    file.save(str(save_path))
    full_path = str(save_path.resolve())
    save_recent_file(full_path)
    return redirect(url_for("view", file=full_path))


@app.route("/view")
def view():
    file_path = request.args.get("file", "")
    if not file_path:
        return redirect(url_for("index"))
    p = Path(file_path)
    if not p.exists():
        return build_page(f"<p style='color:red;'>File not found: {Markup.escape(file_path)}</p>")
    content = p.read_text(encoding="utf-8")
    save_recent_file(str(p.resolve()))
    segments = extract_mermaid_blocks(content)
    body = render_body(segments)
    return build_page(body, filename=str(p.resolve()))


@app.route("/export")
def export():
    file_path = request.args.get("file", "")
    if not file_path:
        return redirect(url_for("index"))
    p = Path(file_path)
    if not p.exists():
        return "File not found", 404
    content = p.read_text(encoding="utf-8")
    segments = extract_mermaid_blocks(content)
    body = render_body(segments)
    katex_init = (
        "renderMathInElement(document.body,{"
        "delimiters:["
        "{left:'$$',right:'$$',display:true},"
        "{left:'$',right:'$',display:false}"
        "]});"
    )
    export_html = (
        f'<!DOCTYPE html><html><head><meta charset="utf-8">'
        f'<link rel="stylesheet" href="{KATEX_CSS}">'
        f'<script defer src="{KATEX_JS}"></script>'
        f'<script defer src="{KATEX_AUTORENDER}" onload="{katex_init}"></script>'
        f'</head><body style="font-family:sans-serif;padding:1rem;max-width:900px;margin:0 auto">'
        f'{body}'
        f'<script src="{MERMAID_CDN}"></script>'
        f'<script>mermaid.initialize({{startOnLoad:true}});</script>'
        f'</body></html>'
    )
    response = make_response(export_html)
    response.headers["Content-Disposition"] = f"attachment; filename={p.stem}.html"
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    return response


@app.route("/shutdown", methods=["POST"])
def shutdown():
    os.kill(os.getpid(), signal.SIGTERM)
    return "OK"


if __name__ == "__main__":
    import webbrowser
    import threading
    threading.Timer(1.0, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    app.run(debug=False, port=5000)
