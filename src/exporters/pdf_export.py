"""Render an email draft to PDF using reportlab."""
from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def draft_to_pdf_bytes(draft: dict[str, Any]) -> bytes:
    """Render a structured email draft to PDF and return the bytes."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )
    styles = getSampleStyleSheet()
    flowables: list = []

    subject = (draft.get("subject") or "").strip() or "(no subject)"
    flowables.append(Paragraph(f"<b>Subject:</b> {subject}", styles["Title"]))
    flowables.append(Spacer(1, 18))

    for field in ("greeting", "body", "closing", "signature"):
        chunk = (draft.get(field) or "").strip()
        if not chunk:
            continue
        # Preserve paragraph breaks within the body.
        for para in chunk.split("\n\n"):
            flowables.append(
                Paragraph(para.replace("\n", "<br/>"), styles["BodyText"])
            )
            flowables.append(Spacer(1, 8))
        flowables.append(Spacer(1, 4))

    doc.build(flowables)
    return buffer.getvalue()
