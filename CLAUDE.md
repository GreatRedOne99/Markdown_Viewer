# Markdown Viewer — Claude Code Build Prompt

## What this is

A single-file Flask web app (`app.py`) that renders Markdown documents with full LaTeX equation and Mermaid diagram support. Runs locally at `http://127.0.0.1:5000`.

## Rules


# NASA Power of Ten — Coding Prohibitions (Language Agnostic)
# Negated from NASA's 10 Rules for Safety-Critical Code.
# All items are SHALL NOT unless marked *should not*.

- Do not use unstructured control flow: no goto-equivalents, no non-local jumps, no exception/condition mechanisms used as control flow substitutes, no direct or indirect recursion.
- Do not write loops without a statically determinable upper bound. Every loop over external, dynamic, or recursively-structured data must have an explicit cap enforced in code. The bound must be a named constant with a documented rationale. If a static analysis tool cannot prove the bound, the rule is violated.
- Do not allocate memory dynamically after initialization. Pre-allocate all required data structures at startup. Do not grow collections, buffers, or strings in runtime hot paths.
- Do not write functions longer than 60 lines at one statement per line and one declaration per line. No exceptions.
- Do not write any function without at least two assertions. Assertions must be side-effect free, Boolean, and trigger an explicit recovery action on failure — not a crash or silent continuation. Do not write assertions that a static tool can prove always pass or always fail.
- Do not declare data objects at broader scope than their first use requires. No mutable global state.
- Do not ignore return values of non-void functions. Do not write functions that skip validation of all parameters provided by the caller.
- Do not use preprocessor or metaprogramming facilities beyond file inclusion and simple constant definitions: no token pasting, no variadic macro arguments, no recursive macro expansion, no conditional compilation beyond a single top-level feature-detection block. All macros or code-generation constructs must expand to complete syntactic units.
- Do not dereference pointers, references, or indirect accessors more than one level deep per expression without an intermediate named binding. Do not hide dereference operations inside macros, templates, or type aliases. Do not use function pointers or callable-as-data patterns without explicit documented justification.
- Do not commit code with compiler warnings, linter warnings, or static analyzer warnings. Zero warnings is the only acceptable state. Static analysis tooling must be configured and enforced from the first day of development, not retrofitted.

---
*Source: NASA Power of Ten — Rules for Developing Safety Critical Code, Gerard Holzmann, JPL.*


## How to run

```bash
uv sync
uv run python app.py
```

## Architecture

- **Single file**: all logic lives in `app.py` — no templates directory, no static files
- **Framework**: Flask (migrated from Streamlit — do NOT use Streamlit)
- **Rendering pipeline**: Markdown → extract mermaid blocks → protect math → Python-Markdown → restore math → full HTML page
- **Client-side rendering**: KaTeX (LaTeX) and Mermaid (diagrams) load from CDN — no server-side installs needed
- **Search**: in-page JavaScript search with keyword and regex support, runs entirely in the browser with no server round-trips

## Key files

- `app.py` — the entire application
- `example.md` — demo document loaded by default
- `.recent_files.json` — persisted list of recently opened file paths (gitignored)
- `.uploaded_files/` — cached copies of uploaded files for recent-file reopening (gitignored)
- `backup/` — previous Streamlit version of the app (archived)

## Rendering rules

- Math protection (`_protect_math` / `_restore_math`) must run BEFORE the markdown parser to prevent `$...$` from being mangled
- Mermaid blocks must be extracted as ordered segments to preserve document position — do NOT strip them all out and append at the bottom
- Mermaid CDN script must load AFTER the body content, AFTER KaTeX
- Do NOT use `mdx_math` with MathJax 3 — it silently drops all equations
- Use KaTeX auto-render with `defer` + `onload` pattern

## Dependencies

- `flask` — web framework
- `markdown` — Python-Markdown for HTML conversion
- `markupsafe` — HTML escaping (installed with Flask)
- `werkzeug` — secure filename handling (installed with Flask)
- KaTeX and Mermaid load from CDN at runtime

## Do NOT

- Use Streamlit — it reruns the entire script on every interaction, breaking search, state, and UX
- Use `st.iframe()`, `st.components.v1.html()`, or any Streamlit API
- Use `mdx_math` or MathJax — use KaTeX
- Add a templates directory — keep HTML generation inline in `app.py`
- Expose the app to the public internet without adding authentication
