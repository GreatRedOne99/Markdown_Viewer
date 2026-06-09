# Markdown_Viewer
Streamlit Python Basic Markdown Viewer

## Premise
Markdown documents and imbedded flowcharts, Gann charts are powerful tools to display project information.  The problem is viewing them in standard tools, Word, Acrobat, etc. outside of IDE evironments like VS Code are horrible and lacking.  This app is a Streamlit app that takes a markdown document and displays it nicely on screen and allows the user to save the markdown document in a clean format for printing like PDF.  

## How to use

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run the Streamlit app:

```bash
streamlit run app.py
```

3. Use the sidebar to upload a Markdown file or select the included example. The app will render Markdown, Mermaid flowcharts, and Gantt diagrams. Use the Export panel to save HTML or (if `wkhtmltopdf`/`pdfkit` are available) export a PDF.

## Technology

- Streamlit for the UI
- Python-Markdown for Markdown → HTML conversion
- Mermaid (via CDN) for diagrams
 - Optional `pdfkit` + `wkhtmltopdf` for PDF export
 - Fallback using headless Chromium via `playwright` if `wkhtmltopdf` is unavailable

Playwright note:

1. Install the Python package and browsers:

```bash
pip install playwright
python -m playwright install chromium
```

2. CI: installing browsers in CI may be necessary if you use Playwright-based PDF generation in tests.

## Modifications

This repository now includes a minimal Streamlit app at [app.py](app.py) and an example document at [example.md](example.md). The app focuses on a clean rendering of Markdown documents with embedded Mermaid diagrams and provides simple HTML/PDF export. A GitHub Actions CI workflow (`.github/workflows/ci.yml`) runs linting and the basic test on push/PR.

