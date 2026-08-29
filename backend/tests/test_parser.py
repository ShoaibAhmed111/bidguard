from __future__ import annotations

import asyncio
from pathlib import Path

import fitz
import pytest

from models.schemas import BoundingBox, ExtractedBidData
from services.parser import BidDocumentParser

APEX_NAME = "Apex Petrochem Pvt Ltd"
APEX_PAN = "AABCA1234F"
APEX_GSTIN = "33AABCA1234F1Z5"
APEX_UDYAM = "UDYAM-TN-01-0012345"


def _build_apex_pdf() -> bytes:
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((72, 80), APEX_NAME, fontsize=24)
    page.insert_text((72, 130), f"PAN: {APEX_PAN}", fontsize=11)
    page.insert_text((72, 155), f"GSTIN: {APEX_GSTIN}", fontsize=11)
    page.insert_text((72, 180), f"Udyam No: {APEX_UDYAM}", fontsize=11)
    page.insert_text((72, 205), "Annual turnover: Rs. 25.00 Crore", fontsize=11)
    page.insert_text((72, 230), "Make in India local content: 65%", fontsize=11)
    payload = document.tobytes()
    document.close()
    return payload


def _parse(file_bytes: bytes) -> ExtractedBidData:
    return asyncio.run(BidDocumentParser().parse_pdf(file_bytes))


def _assert_box(box: BoundingBox, *, page: int = 1) -> None:
    assert isinstance(box, BoundingBox)
    assert box.page == page
    assert box.xmin < box.xmax
    assert box.ymin < box.ymax


def test_parse_apex_extracts_all_fields_and_bounding_boxes() -> None:
    extracted = _parse(_build_apex_pdf())

    assert extracted.legal_name == APEX_NAME
    assert extracted.pan == APEX_PAN
    assert extracted.gstin == APEX_GSTIN
    assert extracted.udyam_no == APEX_UDYAM
    assert extracted.declared_turnover_inr_cr == pytest.approx(25.0)
    assert extracted.make_in_india_local_content_pct == pytest.approx(65.0)

    expected_keys = {
        "legal_name",
        "pan",
        "gstin",
        "udyam_no",
        "declared_turnover_inr_cr",
        "make_in_india_local_content_pct",
    }
    assert expected_keys <= set(extracted.bounding_boxes)

    for key in expected_keys:
        _assert_box(extracted.bounding_boxes[key])

    document = fitz.open(stream=_build_apex_pdf(), filetype="pdf")
    page = document[0]
    name_hits = page.search_for(APEX_NAME)
    gstin_hits = page.search_for(APEX_GSTIN)
    document.close()
    assert name_hits
    assert gstin_hits
    name_box = extracted.bounding_boxes["legal_name"]
    gstin_box = extracted.bounding_boxes["gstin"]
    name_rect = name_hits[0]
    gstin_rect = gstin_hits[0]
    assert abs(name_box.xmin - name_rect.x0) < 1.0
    assert abs(name_box.ymin - name_rect.y0) < 1.0
    assert abs(gstin_box.xmin - gstin_rect.x0) < 1.0
    assert abs(gstin_box.ymin - gstin_rect.y0) < 1.0


def test_parse_indian_rupee_amount_converts_to_crores() -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 80), "Delta Fluid Tech Pvt Ltd", fontsize=20)
    page.insert_text((72, 140), "Gross sales 25,00,00,000", fontsize=11)
    payload = document.tobytes()
    document.close()

    extracted = _parse(payload)
    assert extracted.declared_turnover_inr_cr == pytest.approx(25.0)
    assert "declared_turnover_inr_cr" in extracted.bounding_boxes


def test_parse_path_reads_file(tmp_path: Path) -> None:
    pdf_path = tmp_path / "apex.pdf"
    pdf_path.write_bytes(_build_apex_pdf())
    extracted = asyncio.run(BidDocumentParser().parse_path(pdf_path))
    assert extracted.gstin == APEX_GSTIN
    assert extracted.legal_name == APEX_NAME


def test_empty_bytes_returns_empty_extraction() -> None:
    extracted = _parse(b"")
    assert extracted.legal_name == ""
    assert extracted.pan is None
    assert extracted.gstin is None
    assert extracted.bounding_boxes == {}


def test_malformed_bytes_returns_empty_extraction() -> None:
    extracted = _parse(b"this is not a pdf")
    assert isinstance(extracted, ExtractedBidData)
    assert extracted.legal_name == ""
    assert extracted.gstin is None


def test_blank_pdf_returns_empty_extraction() -> None:
    document = fitz.open()
    document.new_page()
    payload = document.tobytes()
    document.close()
    extracted = _parse(payload)
    assert extracted.pan is None
    assert extracted.gstin is None
    assert extracted.declared_turnover_inr_cr is None
