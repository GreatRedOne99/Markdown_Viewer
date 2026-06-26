# Markdown Viewer

A Streamlit app for viewing rich Markdown documents outside of an IDE — with full support for LaTeX equations, Mermaid diagrams, tables, and fenced code blocks.

## Why

Markdown documents with embedded math and diagrams look great in VS Code but are unreadable in Word, Acrobat, or a browser's raw view. This app renders them properly and lets you save a clean, self-contained HTML file for sharing or printing.

## Features

- **LaTeX equations** — inline `$...$` and display `$$...$$` rendered via KaTeX
- **Mermaid diagrams** — flowcharts, Gantt charts, sequence diagrams, rendered inline in document order
- **Markdown** — tables, fenced code blocks, headings, lists, emphasis
- **HTML export** — self-contained file with KaTeX and Mermaid baked in; opens correctly in any browser
- **Sidebar controls** — upload, example toggle, export, and README all in the sidebar; full-width document view

## Quick start

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run the app:

```bash
streamlit run app.py
```

3. Upload a `.md` file via the sidebar, or enable **Use example markdown** to see a demo document with diagrams.

## How to use

| Control | Location | Purpose |
| --- | --- | --- |
| Upload `.md` file | Sidebar | Load your document |
| Use example markdown | Sidebar | Toggle the built-in demo |
| Filename / Save as HTML | Sidebar | Generate a self-contained HTML file |
| Download HTML | Sidebar | Save after generating |
| README | Sidebar (collapsed) | This file |

The rendered document fills the main panel. Diagrams appear inline where they are in the source, not at the bottom.

## Technology

| Component | Role |
| --- | --- |
| [Streamlit](https://streamlit.io) | UI framework |
| [Python-Markdown](https://python-markdown.github.io) | Markdown → HTML conversion |
| [KaTeX](https://katex.org) (CDN) | LaTeX equation rendering |
| [Mermaid](https://mermaid.js.org) (CDN) | Diagram rendering |

No server-side LaTeX or diagram installation required — both render client-side via CDN inside a `st.iframe`.

## Requirements

```text
streamlit>=1.58.0
markdown>=3.10.2
```

See [requirements.txt](requirements.txt) for the full list.
