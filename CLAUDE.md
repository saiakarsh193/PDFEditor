# PDF Editor — CLAUDE.md

## Project Overview
Browser-based PDF editor with a Python/Flask backend. Users can upload PDFs, images (PNG/JPG), and DOCX files; rearrange pages across files; rotate and delete pages; then download a merged PDF.

## Dev Setup
Virtual environment is at `env/`. Always use it:
```
env\Scripts\python.exe app.py        # run server
env\Scripts\pip.exe install <pkg>    # install new packages
```
Server runs at http://localhost:5000 in debug mode.

## File Structure
```
app.py            — Flask routes, session creation, cleanup thread
pdf_engine.py     — PyMuPDF: thumbnail rendering, file conversion, PDF assembly
session_store.py  — In-memory session dict; all state mutation helpers
templates/
  index.html      — Entire frontend: HTML + CSS + vanilla JS + SortableJS (CDN)
uploads/          — Per-session temp dirs (auto-cleaned after 2 hours)
requirements.txt
```

## Architecture Notes
- **Session state** lives server-side in `session_store.SESSIONS` (in-memory dict). Sessions are keyed by a UUID the client generates and stores in `localStorage`, sent as `X-Session-ID` header on every API call.
- **Thumbnails** are rendered on-demand by PyMuPDF; never cached to disk. `<img>` tags use `?sid=…&t=…` query params (no custom headers possible on `<img>`).
- **Page source tracking**: each `page` entry carries its own `source_path` so pages can be freely dragged between file groups without losing their origin.
- **File conversion**: all uploads (image/docx) are converted to PDF before entering the editor pipeline. `pdf_engine.to_pdf()` handles this. DOCX conversion tries LibreOffice headless first (`_find_libreoffice` checks two fixed Windows paths), then falls back to `docx2pdf` (Word COM). If both fail a clear error is returned.
- **Download**: `pdf_engine.assemble_pdf()` builds the final PDF in memory (`BytesIO`) — no temp output file.

## Key APIs
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/upload` | Upload files (multipart), returns page metadata |
| GET | `/api/state` | Get current session arrangement |
| PUT | `/api/state` | Replace full arrangement (called after every drag/rotate/delete) |
| GET | `/api/thumbnail/<page_id>` | Stream PNG thumbnail |
| POST | `/api/rotate/<page_id>` | Rotate page 90° CW/CCW |
| GET | `/api/download` | Stream assembled PDF |

## Supported File Types
`.pdf`, `.png`, `.jpg`, `.jpeg`, `.docx`

## Common Tasks
**Add a new API route**: add it to `app.py`. Session helpers are in `session_store.py`.  
**Change thumbnail size**: default is 220px wide; pass `?size=N` query param.  
**Extend file type support**: add extension to `pdf_engine.ALLOWED_EXTENSIONS` and handle conversion in `pdf_engine.to_pdf()`.  
**Session cleanup interval**: controlled by `max_age_seconds` in `session_store.stale_sessions()`, called from the daemon thread in `app.py`.
