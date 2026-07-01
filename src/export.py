"""export.py — conversion d'une note markdown en Word (.docx) via pandoc."""
from __future__ import annotations
import os
import tempfile


def memo_to_docx_bytes(markdown_text: str) -> bytes | None:
    """Convertit une note markdown en .docx. Renvoie les octets, ou None si échec."""
    try:
        import pypandoc
    except Exception as e:
        print(f"[export] pypandoc indisponible : {e}")
        return None
    try:
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "note.docx")
            pypandoc.convert_text(markdown_text, "docx", format="markdown", outputfile=out)
            with open(out, "rb") as f:
                return f.read()
    except Exception as e:
        print(f"[export] conversion échouée : {e}")
        return None