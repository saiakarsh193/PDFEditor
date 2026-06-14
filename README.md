# PDF Editor

A browser-based PDF editor with a Python backend. Upload PDFs, images, and Word documents — then visually rearrange, rotate, and remove pages before downloading the final merged PDF.

## Features

- **Upload** PDF, PNG, JPG, and DOCX files (DOCX and images are auto-converted to PDF)
- **Upload more** files at any point during editing
- **Drag & drop** to reorder entire file groups or individual pages
- **Move pages** between different file groups by dragging
- **Rotate** individual pages 90° clockwise
- **Delete** individual pages or entire file groups
- **Download** the result as a single merged PDF

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10+ · Flask 3 |
| PDF processing | [PyMuPDF](https://pymupdf.readthedocs.io/) (fitz) |
| DOCX conversion | LibreOffice headless (preferred) · [docx2pdf](https://github.com/AlJohri/docx2pdf) fallback (requires Microsoft Word) |
| Frontend | Vanilla JS · [SortableJS](https://sortablejs.github.io/Sortable/) |

## Getting Started

### Prerequisites
- Python 3.10+
- **DOCX conversion** requires one of:
  - [LibreOffice](https://www.libreoffice.org/download/) (free, recommended — install to the default path)
  - Microsoft Word (used as a fallback via COM automation)

### Installation

```bash
# 1. Clone the repo
git clone https://github.com/your-username/pdf-editor.git
cd pdf-editor

# 2. Create and activate a virtual environment
python -m venv env
# Windows:
env\Scripts\activate
# macOS/Linux:
source env/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the server
python app.py
```

Open http://localhost:5000 in your browser.

## Usage

1. **Upload files** — click **Upload Files** in the header or drop files anywhere on the page.
2. **Rearrange files** — drag the ⠿ handle on a file group header to reorder entire files.
3. **Rearrange pages** — drag individual page thumbnails within or between file groups.
4. **Rotate a page** — click the **↻** button on a page card.
5. **Delete a page** — click the **✕** button on a page card.
6. **Remove a file group** — click **✕ Remove** in the file group header.
7. **Download** — click **⬇ Download PDF** to get the final merged PDF.

> Sessions are stored in memory and cleaned up automatically after 2 hours of inactivity.

## Project Structure

```
pdf-editor/
├── app.py            # Flask routes and session cleanup thread
├── pdf_engine.py     # PyMuPDF: thumbnail rendering, conversion, PDF assembly
├── session_store.py  # In-memory session state management
├── templates/
│   └── index.html    # Single-file frontend (HTML + CSS + JS)
├── uploads/          # Temporary per-session upload directories
├── requirements.txt
├── CLAUDE.md         # Developer guide for AI-assisted development
└── README.md
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Serves the editor UI |
| `POST` | `/api/upload` | Upload one or more files |
| `GET` | `/api/state` | Get current page arrangement |
| `PUT` | `/api/state` | Update page arrangement |
| `GET` | `/api/thumbnail/<page_id>` | Get PNG thumbnail for a page |
| `POST` | `/api/rotate/<page_id>` | Rotate a page 90° CW/CCW |
| `GET` | `/api/download` | Download the assembled PDF |

Session identity is passed via the `X-Session-ID` request header (or `?sid=` query param for image tags).

## License

MIT
