import io
import os
import subprocess

import fitz  # PyMuPDF


ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".docx"}


def _find_libreoffice() -> str | None:
    candidates = [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def _convert_docx_libreoffice(soffice: str, docx_path: str, out_dir: str) -> str:
    subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf", "--outdir", out_dir, docx_path],
        check=True,
        capture_output=True,
        timeout=60,
    )
    base = os.path.splitext(os.path.basename(docx_path))[0]
    return os.path.join(out_dir, base + ".pdf")


def to_pdf(source_path: str, original_name: str) -> str:
    """
    Convert image or docx to PDF in-place next to source_path.
    Returns the path to the final .pdf file (may be source_path itself for PDFs).
    """
    ext = os.path.splitext(original_name)[1].lower()

    if ext == ".pdf":
        return source_path

    pdf_path = os.path.splitext(source_path)[0] + ".pdf"

    if ext in (".png", ".jpg", ".jpeg"):
        img_doc = fitz.open(source_path)
        pdf_bytes = img_doc.convert_to_pdf()
        img_doc.close()
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)
        os.remove(source_path)
        return pdf_path

    if ext == ".docx":
        out_dir = os.path.dirname(source_path)
        soffice = _find_libreoffice()
        if soffice:
            generated = _convert_docx_libreoffice(soffice, source_path, out_dir)
            # LibreOffice names the output after the input basename
            if generated != pdf_path:
                os.replace(generated, pdf_path)
        else:
            try:
                from docx2pdf import convert as docx_convert
                docx_convert(source_path, pdf_path)
            except Exception as e:
                raise RuntimeError(
                    "DOCX conversion failed. Install LibreOffice (recommended) or "
                    "ensure Microsoft Word is installed and registered. "
                    f"Detail: {e}"
                )
        os.remove(source_path)
        return pdf_path

    raise ValueError(f"Unsupported file type: {ext}")


def page_count(pdf_path: str) -> int:
    doc = fitz.open(pdf_path)
    n = doc.page_count
    doc.close()
    return n


def render_thumbnail(source_path: str, page_idx: int, rotation: int, width_px: int = 220) -> bytes:
    """Render a single PDF page as PNG bytes, applying rotation non-destructively."""
    doc = fitz.open(source_path)
    page = doc[page_idx]

    # Determine scale to hit target width
    rect = page.rect
    scale = width_px / rect.width

    # Build rotation matrix on top of scale matrix
    mat = fitz.Matrix(scale, scale).prerotate(rotation)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    png_bytes = pix.tobytes("png")
    doc.close()
    return png_bytes


def assemble_pdf(page_specs: list[dict]) -> bytes:
    """
    Build a new PDF from an ordered list of page specs.

    Each spec: {"source_path": str, "page_idx": int, "rotation": int}
    Returns PDF bytes.
    """
    output = fitz.open()

    # Group consecutive pages from the same source to use insert_pdf efficiently
    for spec in page_specs:
        src_path = spec["source_path"]
        idx = spec["page_idx"]
        rotation = spec["rotation"]

        src_doc = fitz.open(src_path)
        output.insert_pdf(src_doc, from_page=idx, to_page=idx)
        src_doc.close()

        # Apply rotation to the newly inserted page
        inserted_page = output[-1]
        current_rotation = inserted_page.rotation
        # Set absolute rotation (PyMuPDF stores it as the page's /Rotate value)
        inserted_page.set_rotation((current_rotation + rotation) % 360)

    buf = io.BytesIO()
    output.save(buf)
    output.close()
    return buf.getvalue()
