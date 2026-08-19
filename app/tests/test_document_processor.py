"""Runs the adapted Week 2 parsers against real files under Datasets/ — no
mocking, no API key required."""
from pathlib import Path

import pytest

from backend.documents.processor import DocumentProcessor

DATASETS_DIR = Path(__file__).resolve().parent.parent.parent / "Datasets"


@pytest.mark.skipif(not DATASETS_DIR.exists(), reason="Datasets/ folder not present")
def test_load_real_cbc_pdf_is_scanned_image_with_no_text_layer():
    """This sample PDF is a scanned image (no text layer, 13 pages of images,
    verified via pdfplumber directly) — an example of the PDF spec's own listed
    constraint "Data quality issues & OCR limitations". The parser must not
    crash on it; it should return an empty (not None) result so Agent 1's
    low-confidence/needs_review path can flag it downstream."""
    pdf_path = DATASETS_DIR / "Clinician , Doctor" / "CBC Report - Patient Anal.pdf"
    assert pdf_path.exists(), f"expected sample file at {pdf_path}"

    processor = DocumentProcessor()
    result = processor.process_file(pdf_path)

    assert result is not None
    assert result["format"] == "pdf"
    assert result["full_text"] == ""


@pytest.mark.skipif(not DATASETS_DIR.exists(), reason="Datasets/ folder not present")
def test_load_real_docx_sample():
    docx_path = DATASETS_DIR / "Clinician , Doctor" / "CBC report.zz.docx"
    assert docx_path.exists(), f"expected sample file at {docx_path}"

    processor = DocumentProcessor()
    result = processor.process_file(docx_path)

    assert result is not None
    assert result["format"] == "docx"
    assert len(result["full_text"]) > 0


def test_unsupported_format_returns_none(tmp_path):
    xlsx_path = tmp_path / "sample.xlsx"
    xlsx_path.write_text("not a real xlsx")
    processor = DocumentProcessor()
    assert processor.process_file(xlsx_path) is None
