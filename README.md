# BidGuard AI — GeM Bid Compliance Platform
> **SIH26100** · Automated Statutory Verification & Deterministic Audit Engine for Government e-Marketplace (GeM) Public Procurement.

---

## Overview

**BidGuard AI** is an automated compliance and risk evaluation platform designed for procurement officers. It ingests supplier technical bid submissions (PDF format), extracts statutory credentials deterministically using high-precision OCR and document parsers, and reconciles them against sandbox government registries (GSTN, Udyam MSME, and Vigilance Debarment lists).

The platform enforces public procurement rules under **GFR 2017 (Rule 144(xi) & Rule 151)**, the **Public Procurement (Preference to Make in India) Order 2017**, and the **MSME Development Act 2006** without subjective LLM hallucinations.

---

## Key Features

- **Deterministic Audit Engine:** Mathematical penalty reduction and token similarity matching (RapidFuzz) with zero hallucination.
- **Statutory Registry Gateways:** Sandbox and API Setu verification for:
  - GSTIN registration status & return filing compliance (GSTR-1 / GSTR-3B).
  - Udyam MSME registration validity and enterprise categorization.
  - Vigilance and ministry debarment/blacklisting order matching.
  - Make-in-India (Class-I / Class-II) local content percentage threshold checks.
  - Declared vs verified annual turnover reconciliation ($\pm 10\%$ tolerance band).
- **Sequential Multi-File Batch Queue:** Non-blocking asynchronous processing queue to evaluate multiple technical bids sequentially without server resource exhaustion.
- **Split-View Executive Dashboard:** 3-column dense auditor layout with batch summary analytics, risk-stratified badges (LOW, MEDIUM, HIGH, CRITICAL), dark/light mode toggle, and clause-level discrepancy inspection.
- **Automated Synthetic Test Suite:** Integrated fixture generator supporting 15 distinct edge-case bidding scenarios.

---

## System Architecture

bidguard-boilerplate/├── backend/│   ├── main.py                     # FastAPI application entrypoint & middleware│   ├── services/│   │   ├── parser.py               # PyMuPDF ingestion & regex credential extraction│   │   ├── audit_engine.py         # Statutory clause rule matrix & penalty evaluator│   │   └── sandbox_gateway.py      # GSTN, MSME, and Debarment mock registries│   ├── mock_data/│   │   └── taxpayers.json          # Seeded statutory enterprise dataset│   ├── generate_realistic_bids.py  # Synthetic PDF test fixture generator│   └── tests/                      # Pytest unit & async integration suites├── src/│   ├── routes/│   │   └── index.tsx               # TanStack/Tailwind executive audit dashboard│   └── components/ui/              # Shadcn UI component primitives├── start_dev.bat                   # One-click dual-stack Windows dev launcher└── README.md
---

## Quick Start (One-Click Launch)

### Prerequisites
- **Python 3.10+**
- **Node.js 18+** & `npm`

### 1. Launch Services
Double-click **`start_dev.bat`** in the project root, or execute via terminal:

```cmd
start_dev.bat
This will automatically:Start the FastAPI Backend on http://localhost:8001.Start the Vite / TanStack Frontend on http://localhost:8080.Launch http://localhost:8080 in your default browser.Manual Setup & DevelopmentBackend SetupDOScd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install pytest-asyncio

# Run development server
py -m uvicorn main:app --reload --port 8001
Interactive API Documentation (Swagger): http://localhost:8001/docsHealth Check Endpoint: http://localhost:8001/healthFrontend SetupDOSnpm install
npm run dev
The frontend dashboard will be available at http://localhost:8080.Automated Testing & Edge-Case FixturesGenerate 15 Realistic Test Bid PDFsRun the fixture generator inside backend/ to populate synthetic test documents in backend/test_bids/:DOScd backend
py generate_realistic_bids.py
Run Deterministic Verification TestsExecute the comprehensive automated test suite:DOScd backend
py -m pytest -v
Test Case Coverage MatrixFixture FileScenario TestedStatutory RuleExpected Verdict01_happy_path_apex.pdfFully compliant vendorGFR 2017 / GSTN / MIIScore 100.0 (LOW RISK)02_turnover_inflated_bharat.pdfDeclared turnover exceeds portal by >10%Anti-Fraud Turnover ReconScore ~75.0 (HIGH RISK)03_debarred_national.pdfVendor PAN matched in Debarment listGFR Rule 151 BlacklistingScore 0.0 (CRITICAL / REJECT)04_suspended_gst_delta.pdfGST status marked SUSPENDEDCGST Act 2017 ComplianceScore <80.0 (HIGH RISK)05_under_local_content_apex.pdfLocal content 35% vs 50% requirementPPP-MII Order 2017Clause FAIL (Penalty -20.0)06_corrupt_blank_document.pdfUnextractable / empty PDF fileIngestion Parser GuardHTTP 422 Error BannerAPI ReferencePOST /api/v1/tenders/evaluateEvaluates an uploaded technical bid PDF document against tender criteria and statutory registries.Content-Type: multipart/form-dataParameters:file: PDF document binarytender_id: String (e.g., GEM-2026-CPCL-001)min_local_content_pct: Float (e.g., 50.0)Sample Response Payload:JSON{
  "tender_id": "GEM-2026-CPCL-001",
  "bidder_name": "Apex Petrochem Pvt Ltd",
  "compliance_score": 100.0,
  "risk_tier": "LOW",
  "is_debarred": false,
  "evaluated_at": "2026-08-30T16:26:06Z",
  "clause_results": [
    {
      "clause_id": "PAN-DEBARMENT",
      "clause_title": "PAN & Debarment Check",
      "is_mandatory": true,
      "status": "PASS",
      "extracted_value": "AABCA1234F",
      "expected_value": "Not debarred / not blacklisted",
      "discrepancy_notes": null,
      "risk_penalty": 0.0
    }
  ],
  "executive_summary": "Bid is substantially compliant across all statutory requirements.",
  "recommended_action": "Proceed to financial cover evaluation under standard GeM guidelines."
}
Tech StackBackend: Python 3, FastAPI, PyMuPDF (Fitz), RapidFuzz, Pydantic v2, Uvicorn, Pytest.Frontend: React, TypeScript, TanStack Router, Tailwind CSS, Shadcn UI, Lucide Icons, Vite.Compliance Standards: General Financial Rules (GFR 2017), Make in India Order (PPP-MII), MSME Development Act, API Setu Open Standards.