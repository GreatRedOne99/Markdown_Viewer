# Markdown Viewer

A Flask web app for viewing rich Markdown documents outside of an IDE — with full support for LaTeX equations, Mermaid diagrams, tables, and fenced code blocks.

## Why

Markdown documents with embedded math and diagrams look great in VS Code but are unreadable in Word, Acrobat, or a browser's raw view. This app renders them properly and lets you save a clean, self-contained HTML file for sharing or printing.

## Features

- **LaTeX equations** — inline `$...$` and display `$$...$$` rendered via KaTeX
- **Mermaid diagrams** — flowcharts, Gantt charts, sequence diagrams, rendered inline in document order
- **Markdown** — tables, fenced code blocks, headings, lists, emphasis
- **In-page search** — keyword and regex search with match highlighting and navigation
- **Drag & drop upload** — drop a `.md` file onto the sidebar or click to browse
- **Recent files** — quick access to previously opened documents
- **HTML export** — self-contained file with KaTeX and Mermaid baked in; opens correctly in any browser
- **Shutdown button** — cleanly stop the server from the UI

## Quick start

1. Install dependencies:

```bash
uv sync
```

1. Run the app:

```bash
uv run python app.py
```

The browser opens automatically to `http://127.0.0.1:5000`.

3. Drop a `.md` file onto the upload area, or the example document loads by default.

## How to use

| Control | Location | Purpose |
| --- | --- | --- |
| Drop / browse `.md` file | Sidebar | Load your document |
| Recent Files | Sidebar | Reopen a previously viewed file |
| Search bar | Top of content area | Keyword or regex search with prev/next navigation |
| Download as HTML | Sidebar | Export a self-contained HTML file |
| Shutdown App | Sidebar (bottom) | Stop the Flask server |

The rendered document fills the main panel. Diagrams appear inline where they are in the source, not at the bottom.

## Technology

| Component | Role |
| --- | --- |
| [Flask](https://flask.palletsprojects.com) | Web framework |
| [Python-Markdown](https://python-markdown.github.io) | Markdown to HTML conversion |
| [KaTeX](https://katex.org) (CDN) | LaTeX equation rendering |
| [Mermaid](https://mermaid.js.org) (CDN) | Diagram rendering |

No server-side LaTeX or diagram installation required — both render client-side via CDN.

## Requirements

```text
flask>=3.1
markdown>=3.10
```

See [requirements.txt](requirements.txt) for the full list.
