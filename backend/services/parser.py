from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import fitz

from models.schemas import BoundingBox, ExtractedBidData

PAN_RE = re.compile(r"[A-Z]{5}[0-9]{4}[A-Z]")
GSTIN_RE = re.compile(
    r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]",
)
UDYAM_RE = re.compile(r"UDYAM-[A-Z]{2}-[0-9]{2}-[0-9]{7}", re.IGNORECASE)

TURNOVER_KEYWORD_RE = re.compile(
    r"(?:annual\s+)?(?:turnover|annual\s+revenue|gross\s+sales)",
    re.IGNORECASE,
)
TURNOVER_AMOUNT_RE = re.compile(
    r"(?:(?:Rs\.?|INR|₹)\s*)?"
    r"(?P<amount>[\d,]+(?:\.\d+)?)"
    r"(?:\s*(?P<unit>crores?|cr\.?|lakhs?|lakh))?",
    re.IGNORECASE,
)

LOCAL_CONTENT_KEYWORD_RE = re.compile(
    r"(?:local\s+content|make\s+in\s+india|class[- ]i\s+local)",
    re.IGNORECASE,
)
PERCENT_RE = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*(?:%|percent(?:age)?)",
    re.IGNORECASE,
)

PAN_LABELED_RE = re.compile(
    r"\bPAN\b\s*[:#.\-]?\s*([A-Z]{5}[0-9]{4}[A-Z])",
    re.IGNORECASE,
)

COMPANY_SUFFIX_RE = re.compile(
    r"\b(?:pvt\.?\s*ltd\.?|private\s+limited|limited|ltd\.?|llp|inc\.?|corp\.?|corporation)\b",
    re.IGNORECASE,
)
NAME_NOISE = {
    "tender",
    "bid",
    "bid document",
    "confidential",
    "annexure",
    "page",
    "gem",
    "government",
    "e-procurement",
}

_CONTEXT_CHARS = 180


def _empty_extraction() -> ExtractedBidData:
    return ExtractedBidData(legal_name="")


def _rect_to_box(rect: fitz.Rect, page_num: int) -> BoundingBox:
    return BoundingBox(
        ymin=float(rect.y0),
        xmin=float(rect.x0),
        ymax=float(rect.y1),
        xmax=float(rect.x1),
        page=page_num,
    )


def _union_rects(rects: list[fitz.Rect]) -> fitz.Rect:
    merged = fitz.Rect(rects[0])
    for rect in rects[1:]:
        merged |= rect
    return merged


def _bbox_for_text(page: fitz.Page, needle: str, page_num: int) -> BoundingBox | None:
    if not needle:
        return None
    hits = page.search_for(needle)
    if not hits:
        hits = page.search_for(needle.strip())
    if not hits:
        return None
    return _rect_to_box(_union_rects(hits[:4]), page_num)


def _parse_indian_number(raw: str) -> float | None:
    cleaned = raw.replace(",", "").strip()
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _to_crores(amount: float, unit: str | None, raw_amount: str) -> float:
    normalized_unit = re.sub(r"[^a-z]", "", (unit or "").lower())
    if normalized_unit.startswith("cr"):
        return amount
    if normalized_unit.startswith("lakh"):
        return amount / 100.0
    if "," in raw_amount or amount >= 100_000:
        return amount / 10_000_000.0
    return amount


def _first_regex_hit(
    pages: list[tuple[int, fitz.Page, str]],
    pattern: re.Pattern[str],
) -> tuple[str, int, fitz.Page] | None:
    for page_num, page, text in pages:
        match = pattern.search(text)
        if match:
            return match.group(0).upper(), page_num, page
        compact = re.sub(r"\s+", "", text)
        compact_match = pattern.search(compact)
        if compact_match:
            return compact_match.group(0).upper(), page_num, page
    return None


def _extract_turnover(
    pages: list[tuple[int, fitz.Page, str]],
) -> tuple[float | None, BoundingBox | None]:
    for page_num, page, text in pages:
        for keyword in TURNOVER_KEYWORD_RE.finditer(text):
            window = text[keyword.start() : keyword.end() + _CONTEXT_CHARS]
            amount_match = TURNOVER_AMOUNT_RE.search(window)
            if not amount_match:
                continue
            raw_amount = amount_match.group("amount")
            parsed = _parse_indian_number(raw_amount)
            if parsed is None:
                continue
            crores = _to_crores(parsed, amount_match.group("unit"), raw_amount)
            snippet = amount_match.group(0)
            box = _bbox_for_text(page, snippet, page_num) or _bbox_for_text(
                page, raw_amount, page_num
            )
            return round(crores, 4), box
    return None, None


def _extract_local_content(
    pages: list[tuple[int, fitz.Page, str]],
) -> tuple[float | None, BoundingBox | None]:
    for page_num, page, text in pages:
        for keyword in LOCAL_CONTENT_KEYWORD_RE.finditer(text):
            window = text[keyword.start() : keyword.end() + _CONTEXT_CHARS]
            percent_match = PERCENT_RE.search(window)
            if not percent_match:
                continue
            value = float(percent_match.group("value"))
            if value > 100:
                continue
            snippet = percent_match.group(0)
            box = _bbox_for_text(page, snippet, page_num)
            return value, box
    return None, None


def _score_name_span(text: str, size: float, y0: float) -> float:
    stripped = " ".join(text.split())
    if len(stripped) < 5:
        return -1.0
    lowered = stripped.lower()
    if lowered in NAME_NOISE or any(token == lowered for token in NAME_NOISE):
        return -1.0
    if PAN_RE.fullmatch(stripped.replace(" ", "")) or GSTIN_RE.search(stripped.replace(" ", "")):
        return -1.0
    score = size
    if COMPANY_SUFFIX_RE.search(stripped):
        score += 12.0
    if y0 < 200:
        score += 4.0
    if stripped.isupper() and len(stripped) > 12:
        score += 2.0
    return score


def _extract_legal_name(
    page: fitz.Page,
    page_num: int,
) -> tuple[str, BoundingBox | None]:
    payload: dict[str, Any] = page.get_text("dict")
    best_text = ""
    best_score = -1.0
    best_rect: fitz.Rect | None = None

    for block in payload.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            line_text = " ".join(span.get("text", "") for span in spans).strip()
            size = max(float(span.get("size", 0)) for span in spans)
            bbox = line.get("bbox") or spans[0].get("bbox")
            if not bbox:
                continue
            rect = fitz.Rect(bbox)
            score = _score_name_span(line_text, size, rect.y0)
            if score > best_score:
                best_score = score
                best_text = " ".join(line_text.split())
                best_rect = rect

    if best_score < 0 or not best_text:
        return "", None
    box = _rect_to_box(best_rect, page_num) if best_rect is not None else None
    return best_text, box


def _open_pdf(file_bytes: bytes) -> fitz.Document:
    return fitz.open(stream=file_bytes, filetype="pdf")


class BidDocumentParser:
    """Extract bid identifiers, financials, and visual evidence boxes from PDFs."""

    async def parse_pdf(self, file_bytes: bytes) -> ExtractedBidData:
        if not file_bytes:
            return _empty_extraction()

        try:
            document = _open_pdf(file_bytes)
        except Exception:
            return _empty_extraction()

        try:
            if document.page_count == 0:
                return _empty_extraction()
            return self._extract_from_document(document)
        except Exception:
            return _empty_extraction()
        finally:
            document.close()

    async def parse_path(self, path: str | Path) -> ExtractedBidData:
        try:
            payload = Path(path).read_bytes()
        except OSError:
            return _empty_extraction()
        return await self.parse_pdf(payload)

    def _extract_from_document(self, document: fitz.Document) -> ExtractedBidData:
        pages: list[tuple[int, fitz.Page, str]] = []
        for index in range(document.page_count):
            page = document[index]
            pages.append((index + 1, page, page.get_text() or ""))

        boxes: dict[str, BoundingBox] = {}

        legal_name, name_box = _extract_legal_name(pages[0][1], pages[0][0])
        if name_box is not None:
            boxes["legal_name"] = name_box

        gstin: str | None = None
        gstin_hit = _first_regex_hit(pages, GSTIN_RE)
        if gstin_hit:
            gstin, page_num, page = gstin_hit
            box = _bbox_for_text(page, gstin, page_num)
            if box is not None:
                boxes["gstin"] = box

        pan: str | None = None
        for page_num, page, text in pages:
            labeled = PAN_LABELED_RE.search(text)
            if labeled:
                pan = labeled.group(1).upper()
                box = _bbox_for_text(page, pan, page_num)
                if box is not None:
                    boxes["pan"] = box
                break
        if pan is None and gstin and len(gstin) >= 12:
            pan = gstin[2:12]
            for page_num, page, _text in pages:
                box = _bbox_for_text(page, pan, page_num)
                if box is not None:
                    boxes["pan"] = box
                    break
        if pan is None:
            pan_hit = _first_regex_hit(pages, PAN_RE)
            if pan_hit:
                pan, page_num, page = pan_hit
                box = _bbox_for_text(page, pan, page_num)
                if box is not None:
                    boxes["pan"] = box

        udyam_no: str | None = None
        udyam_hit = _first_regex_hit(pages, UDYAM_RE)
        if udyam_hit:
            udyam_no, page_num, page = udyam_hit
            box = _bbox_for_text(page, udyam_no, page_num)
            if box is not None:
                boxes["udyam_no"] = box

        turnover, turnover_box = _extract_turnover(pages)
        if turnover_box is not None:
            boxes["declared_turnover_inr_cr"] = turnover_box

        local_pct, local_box = _extract_local_content(pages)
        if local_box is not None:
            boxes["make_in_india_local_content_pct"] = local_box

        return ExtractedBidData(
            legal_name=legal_name,
            pan=pan,
            gstin=gstin,
            udyam_no=udyam_no,
            declared_turnover_inr_cr=turnover,
            make_in_india_local_content_pct=local_pct,
            bounding_boxes=boxes,
        )
