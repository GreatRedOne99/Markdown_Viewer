import re
import uuid
import streamlit as st
import markdown as md
from pathlib import Path
import io
import tempfile
import traceback

MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"


def escape_html(text: str) -> str:
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))


def render_mermaid(diagram_code: str, key: str = None):
    uid = key or f"m-{uuid.uuid4().hex}"
    html = f"""
    <div class="mermaid" id="{uid}">{escape_html(diagram_code)}</div>
    <script src="{MERMAID_CDN}"></script>
    <script>document.addEventListener("DOMContentLoaded", function() {{
      if (window.mermaid) {{ mermaid.initialize({{ startOnLoad: true }}); }}
    }});</script>
    """
    try:
        st.iframe(srcDoc=html, height=300)
    except TypeError:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        tmp.write(html.encode("utf-8"))
        tmp.close()
        st.iframe(tmp.name, height=300)


def extract_mermaid_blocks(text: str):
    pattern = re.compile(r"```mermaid\n(.*?)\n```", re.DOTALL | re.IGNORECASE)
    blocks = pattern.findall(text)
    cleaned = pattern.sub("", text)
    return blocks, cleaned


def to_html(full_markdown: str, mermaid_blocks):
    html_body = md.markdown(full_markdown, extensions=["fenced_code", "tables"])
    mermaid_html = "".join([
        f"<div class=\"mermaid\">{escape_html(b)}</div>" for b in mermaid_blocks
    ])
    full = f"<html><head><meta charset=\"utf-8\"></head><body>{html_body}{mermaid_html}<script src=\"{MERMAID_CDN}\"></script><script>if(window.mermaid){{mermaid.initialize({{startOnLoad:true}})}};</script></body></html>"
    return full


def export_pdf_bytes(html: str) -> bytes | None:
    """Return PDF bytes generated from HTML, or None on failure."""
    try:
        import pdfkit
        result = pdfkit.from_string(html, False)
        if isinstance(result, (bytes, bytearray)):
            return bytes(result)
    except Exception:
        pass

    try:
        from playwright.sync_api import sync_playwright
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(args=["--no-sandbox"]) 
                page = browser.new_page()
                page.set_content(html, wait_until='networkidle')
                pdf_bytes = page.pdf(format='A4')
                browser.close()
                if isinstance(pdf_bytes, (bytes, bytearray)):
                    return bytes(pdf_bytes)
        except Exception:
            print("Playwright PDF generation failed:")
            traceback.print_exc()
            return None
    except Exception:
        return None


def main():
    st.set_page_config(page_title="Markdown Viewer", layout="wide")
    st.title("Markdown Viewer — Streamlit")

    st.sidebar.header("Load Markdown")
    uploaded = st.sidebar.file_uploader("Upload a .md file", type=["md", "markdown"] )
    use_example = st.sidebar.checkbox("Use example markdown", value=True)

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

    mermaid_blocks, cleaned = extract_mermaid_blocks(content)

    col1, col2 = st.columns([3,1])
    with col1:
        st.subheader("Rendered Document")
        st.markdown(md.markdown(cleaned, extensions=["fenced_code", "tables"]), unsafe_allow_html=True)
        if mermaid_blocks:
            st.markdown("---")
            st.subheader("Diagrams")
            for i, block in enumerate(mermaid_blocks):
                st.markdown(f"**Diagram {i+1}**")
                render_mermaid(block, key=f"mermaid-{i}")

    with col2:
        st.subheader("Export")
        html = to_html(cleaned, mermaid_blocks)
        # Determine default filename base from uploaded file if present
        default_name = "document"
        if uploaded is not None and hasattr(uploaded, 'name'):
            default_name = Path(uploaded.name).stem
        # HTML export: generate bytes and offer download like PDF
        # Initialize session state for HTML
        if 'html_ready' not in st.session_state:
            st.session_state['html_ready'] = False
            st.session_state['html_bytes'] = None
            st.session_state['html_filename'] = ''

        default_html_name = default_name
        html_filename = st.text_input("HTML filename", value=default_html_name, key='html_filename_input')

        if st.button("Save as HTML"):
            st.session_state['html_ready'] = False
            st.session_state['html_bytes'] = None
            st.session_state['html_filename'] = ''
            html_bytes = html.encode('utf-8')
            st.session_state['html_bytes'] = html_bytes
            st.session_state['html_filename'] = f"{html_filename}.html"
            st.session_state['html_ready'] = True
            st.success("HTML generated — click Download to save the file")

        # Show download button only after HTML is ready
        if st.session_state.get('html_ready') and st.session_state.get('html_bytes'):
            st.download_button("Download HTML", data=st.session_state['html_bytes'], file_name=st.session_state['html_filename'], mime="text/html")
            if st.button("Clear HTML"):
                st.session_state['html_ready'] = False
                st.session_state['html_bytes'] = None
                st.session_state['html_filename'] = ''

        # Initialize session state for PDF storage
        if 'pdf_ready' not in st.session_state:
            st.session_state['pdf_ready'] = False
            st.session_state['pdf_bytes'] = None
            st.session_state['pdf_filename'] = ''

        filename = st.text_input("PDF filename", value=default_name, key='pdf_filename_input')

        if st.button("Save as PDF"):
            st.session_state['pdf_ready'] = False
            st.session_state['pdf_bytes'] = None
            st.session_state['pdf_filename'] = ''
            pdf_bytes = export_pdf_bytes(html)
            if pdf_bytes:
                st.session_state['pdf_bytes'] = pdf_bytes
                st.session_state['pdf_filename'] = f"{filename}.pdf"
                st.session_state['pdf_ready'] = True
                st.success("PDF generated — click Download to save the file")
            else:
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
                tmp.write(html.encode("utf-8"))
                tmp.close()
                st.warning("PDF export failed — saved HTML instead. You can print to PDF from your browser.")
                with open(tmp.name, "rb") as f:
                    st.download_button("Download HTML", f, file_name=Path(tmp.name).name)

        if st.session_state.get('pdf_ready') and st.session_state.get('pdf_bytes'):
            st.download_button("Download PDF", data=st.session_state['pdf_bytes'], file_name=st.session_state['pdf_filename'], mime="application/pdf")
            if st.button("Clear PDF"):
                st.session_state['pdf_ready'] = False
                st.session_state['pdf_bytes'] = None
                st.session_state['pdf_filename'] = ''


if __name__ == "__main__":
    main()
