import fitz  # PyMuPDF
from pathlib import Path

OUTPUT_DIR = Path("test_bids")
OUTPUT_DIR.mkdir(exist_ok=True)

def create_bid_pdf(filename: str, bidder: str, pan: str = "", gstin: str = "", udyam: str = "", turnover: str = "", local_content: str = "", blank: bool = False):
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    
    if not blank:
        page.insert_text((72, 80), bidder, fontsize=22)
        if pan:
            page.insert_text((72, 120), f"PAN: {pan}", fontsize=11)
        if gstin:
            page.insert_text((72, 145), f"GSTIN: {gstin}", fontsize=11)
        if udyam:
            page.insert_text((72, 170), f"Udyam No: {udyam}", fontsize=11)
        if turnover:
            page.insert_text((72, 195), f"Annual turnover: {turnover}", fontsize=11)
        if local_content:
            page.insert_text((72, 220), f"Make in India local content: {local_content}", fontsize=11)
            
    doc.save(OUTPUT_DIR / filename)
    doc.close()
    print(f"Generated: {OUTPUT_DIR / filename}")

# 1. Compliant Happy Path (Apex Petrochem)
create_bid_pdf(
    "bid_01_compliant_apex.pdf",
    bidder="Apex Petrochem Pvt Ltd",
    pan="AABCA1234F",
    gstin="33AABCA1234F1Z5",
    udyam="UDYAM-TN-01-0012345",
    turnover="Rs. 25.00 Crore",
    local_content="65%"
)

# 2. Turnover Inflation Violation (Bharat Valves)
create_bid_pdf(
    "bid_02_turnover_inflated.pdf",
    bidder="Bharat Valves & Pipes Ltd",
    pan="BBBCB5678K",
    gstin="27BBBCB5678K1Z2",
    udyam="UDYAM-MH-02-0098765",
    turnover="Rs. 22.00 Crore",  # Real is 12.0 Cr
    local_content="60%"
)

# 3. Debarred / Blacklisted Bidder (National Industrial)
create_bid_pdf(
    "bid_03_debarred_national.pdf",
    bidder="National Industrial Supplies",
    pan="CCCDC9012M",
    gstin="07CCCDC9012M1Z8",
    udyam="UDYAM-DL-03-0054321",
    turnover="Rs. 18.00 Crore",
    local_content="55%"
)

# 4. Suspended GST & Non-Filing (Delta Fluid Tech)
create_bid_pdf(
    "bid_04_suspended_gst.pdf",
    bidder="Delta Fluid Tech",
    pan="DDDDE3456N",
    gstin="29DDDDE3456N1Z9",
    udyam="UDYAM-KA-04-0022222",
    turnover="Rs. 8.50 Crore",
    local_content="52%"
)

# 5. Make in India Local Content Deficit
create_bid_pdf(
    "bid_05_under_local_content.pdf",
    bidder="Apex Petrochem Pvt Ltd",
    pan="AABCA1234F",
    gstin="33AABCA1234F1Z5",
    udyam="UDYAM-TN-01-0012345",
    turnover="Rs. 25.00 Crore",
    local_content="35%"  # Tender minimum is 50%
)

# 6. Blank / Unreadable File
create_bid_pdf("bid_06_corrupt_unreadable.pdf", bidder="", blank=True)