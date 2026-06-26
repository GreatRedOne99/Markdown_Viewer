# Markdown Viewer — Build Prompt

Build a local web application that renders Markdown documents with full support for LaTeX equations and Mermaid diagrams. The app runs as a local web server and opens in the user's default browser. Use any language and web framework appropriate to the target platform.

## Functional Requirements

### Document Rendering

1. Accept `.md` / `.markdown` files as input.
1. Convert Markdown to HTML with support for: headings, paragraphs, emphasis, lists, tables, fenced code blocks, blockquotes, images, and links.
1. Render LaTeX equations inline (`$...$`) and display (`$$...$$`) using KaTeX loaded from CDN.
1. Render Mermaid diagram blocks (` ```mermaid `) as inline diagrams using Mermaid.js loaded from CDN.
1. Mermaid diagrams must appear at their position in the document, not collected at the bottom.

### Math Protection Pipeline

LaTeX delimiters (`$`, `$$`) conflict with most Markdown parsers. The rendering pipeline must:

1. **Before** Markdown parsing: scan the raw text and replace all `$...$` and `$$...$$` spans with unique placeholders (e.g., NUL-delimited tokens). Store the original LaTeX in a lookup table.
1. Run the Markdown-to-HTML converter on the placeholder text.
1. **After** Markdown parsing: restore the original LaTeX strings from the lookup table into the HTML output.
1. Let KaTeX auto-render find and render the restored `$...$` / `$$...$$` spans client-side.

Do NOT use MathJax. Do NOT rely on Markdown math extensions — they produce markup that MathJax 3 and KaTeX ignore silently.

### Mermaid Pipeline

1. Before Markdown parsing, extract fenced code blocks tagged `mermaid` as ordered segments: `[(type, content), ...]` where type is `"markdown"` or `"mermaid"`.
1. Convert each markdown segment through the math-protection pipeline above.
1. Wrap each mermaid segment in `<div class="mermaid">` with HTML-escaped content.
1. Reassemble in document order.
1. Load the Mermaid CDN script **after** the body content and **after** KaTeX. Call `mermaid.initialize({startOnLoad:true})`. Load order matters — Mermaid must be last.

### CDN Resources

Use these CDN URLs for client-side rendering (no server-side LaTeX or diagram tools needed):

```
KaTeX CSS:        https://cdn.jsdelivr.net/npm/katex@0.16/dist/katex.min.css
KaTeX JS:         https://cdn.jsdelivr.net/npm/katex@0.16/dist/katex.min.js
KaTeX Auto-render: https://cdn.jsdelivr.net/npm/katex@0.16/dist/contrib/auto-render.min.js
Mermaid JS:       https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js
```

KaTeX initialization (place as `onload` on the auto-render script, using `defer` on all KaTeX scripts):

```javascript
renderMathInElement(document.body, {
  delimiters: [
    {left: '$$', right: '$$', display: true},
    {left: '$', right: '$', display: false}
  ]
});
```

### File Upload

1. Provide a drag-and-drop zone in the sidebar that accepts `.md` files.
1. Also provide a click-to-browse button (can be the same element).
1. On upload, save the file to a local cache directory (e.g., `.uploaded_files/`) and render it.
1. Upload must not cause the entire page to re-render or lose UI state beyond the document content area.

### Recent Files

1. Persist a list of recently opened file paths (up to 20) in a JSON file (e.g., `.recent_files.json`).
1. Display recent files in the sidebar as a dropdown showing **filenames only** (not full paths).
1. Selecting a recent file loads and renders it immediately — no double-click, no confirmation.
1. The underlying value must be the full absolute path so the file can be reopened.
1. Save to the recent list whenever a file is uploaded or viewed.

### In-Page Search

1. Place a search bar above or at the top of the document content area. It must remain visible and stable while the user scrolls the document.
1. Search is client-side JavaScript — no server round-trips.
1. Default mode: case-insensitive keyword (substring) matching.
1. Regex mode: toggled by a checkbox. Invalid regex shows an error message, does not crash.
1. Highlight all matches with a yellow background (`#ffeb3b`).
1. The current match is highlighted orange (`#ff9800`).
1. Provide prev/next navigation buttons (and Enter/Shift+Enter keyboard shortcuts).
1. Display a match counter showing `current/total`.
1. Provide a clear button that removes all highlights and resets the search input.
1. Use debounced input (250ms) to avoid excessive DOM manipulation while typing.

### HTML Export

1. Provide a "Download as HTML" button in the sidebar for the currently loaded document.
1. The exported file must be self-contained: it includes the rendered HTML body with KaTeX and Mermaid CDN links so it opens correctly in any browser.
1. The export must NOT include the search bar, sidebar, or app UI — just the document content.
1. Serve the file as a download attachment with the original filename stem + `.html`.

### Shutdown

1. Provide a shutdown button in the sidebar that stops the web server.
1. Require user confirmation before shutting down (e.g., a browser confirm dialog).
1. After shutdown, display a message telling the user they can close the tab.

## Layout

```
┌──────────────┬──────────────────────────────────────┐
│              │  [Search input] [Regex] [n/n] [▲▼✕]  │
│   SIDEBAR    ├──────────────────────────────────────┤
│              │                                      │
│  Title       │         Rendered Document             │
│  Upload      │         (scrollable)                  │
│  Recent      │                                      │
│  Current     │                                      │
│  Export      │                                      │
│              │                                      │
│  [Shutdown]  │                                      │
└──────────────┴──────────────────────────────────────┘
```

- Sidebar: fixed width (~280px), full height, scrollable if content overflows.
- Main area: fills remaining width. Search bar fixed at top. Document content scrolls independently below.
- The entire layout fills the viewport with no page-level scrollbar.

## Data Files (gitignored)

- `.recent_files.json` — JSON array of absolute file path strings.
- `.uploaded_files/` — directory for cached uploaded files.

## Behavior on Startup

1. Start the web server on `localhost:5000` (or configurable port).
1. Auto-open the default browser to the app URL.
1. If an `example.md` file exists in the app directory, render it as the default document.
1. If no example file exists, show a placeholder message prompting the user to upload a file.

## What NOT to Do

- Do NOT use MathJax — use KaTeX exclusively.
- Do NOT use Markdown math extensions (e.g., `mdx_math`, `markdown-katex`) — they produce markup that renderers ignore.
- Do NOT collect Mermaid diagrams at the bottom — preserve document order.
- Do NOT use a framework that reruns the entire application on every UI interaction (e.g., Streamlit).
- Do NOT require server round-trips for search — it must be pure client-side JavaScript.
- Do NOT expose the app to the public internet without adding authentication.
