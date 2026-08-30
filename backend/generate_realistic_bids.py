import fitz  # PyMuPDF
from pathlib import Path

OUTPUT_DIR = Path("test_bids")
OUTPUT_DIR.mkdir(exist_ok=True)

def draw_table(page, start_y, headers, rows, col_widths):
    x_start = 54
    y = start_y
    row_height = 20
    
    # Draw header background
    header_rect = fitz.Rect(x_start, y, x_start + sum(col_widths), y + row_height)
    page.draw_rect(header_rect, color=(0.7, 0.7, 0.7), fill=(0.92, 0.94, 0.96))
    
    # Write header text
    curr_x = x_start
    for i, h in enumerate(headers):
        page.insert_text((curr_x + 6, y + 14), h, fontsize=9, fontname="helv", color=(0.1, 0.1, 0.1))
        curr_x += col_widths[i]
    y += row_height

    # Write rows
    for row in rows:
        curr_x = x_start
        row_rect = fitz.Rect(x_start, y, x_start + sum(col_widths), y + row_height)
        page.draw_rect(row_rect, color=(0.8, 0.8, 0.8))
        for i, val in enumerate(row):
            page.insert_text((curr_x + 6, y + 14), str(val), fontsize=8.5, fontname="helv", color=(0.15, 0.15, 0.15))
            curr_x += col_widths[i]
        y += row_height
    return y + 10

def generate_formal_bid(filename, bidder_name, cin, pan, gstin, udyam, turnover_str, local_content_str, address, is_debarred=False, blank=False):
    doc = fitz.open()
    page = doc.new_page(width=595, height=842) # Standard A4
    
    if blank:
        doc.save(OUTPUT_DIR / filename)
        doc.close()
        return

    # 1. Letterhead / Header
    page.draw_rect(fitz.Rect(54, 40, 541, 42), color=(0.1, 0.25, 0.5), fill=(0.1, 0.25, 0.5))
    page.insert_text((54, 65), bidder_name.upper(), fontsize=14, fontname="helv", color=(0.08, 0.2, 0.4))
    page.insert_text((54, 78), f"Regd. Office: {address} | CIN: {cin}", fontsize=8, fontname="helv", color=(0.4, 0.4, 0.4))
    page.draw_line(fitz.Point(54, 88), fitz.Point(541, 88), color=(0.8, 0.8, 0.8))

    # 2. Document Title & GeM Reference
    page.insert_text((54, 110), "ANNEXURE - A: STATUTORY COMPLIANCE & ELIGIBILITY UNDERTAKING", fontsize=10, fontname="helv", color=(0.1, 0.1, 0.1))
    page.insert_text((54, 124), "GeM Bid / Tender Ref No: GEM-2026-CPCL-001 | GeM Custom Bid ID: GEM/2026/B/894210", fontsize=8.5, fontname="helv", color=(0.3, 0.3, 0.3))

    # 3. Formal Declaration Intro
    intro_text = (
        "To: The General Manager (Materials & Contracts), Chennai Petroleum Corporation Limited (CPCL).\n"
        "Sub: Submission of Technical & Statutory Credentials in response to Tender No. GEM-2026-CPCL-001.\n\n"
        "Dear Sir/Madam,\n"
        "We hereby declare and certify that all statutory registrations, financial turnover statements, and\n"
        "Make-in-India local value-addition metrics submitted below are true, valid, and compliant with GFR 2017."
    )
    page.insert_text((54, 145), intro_text, fontsize=8.5, fontname="helv", color=(0.2, 0.2, 0.2))

    # 4. Table 1: Statutory Registrations
    table1_headers = ["Statutory Identifier", "Registration / Certificate No.", "Issuing Authority / Status"]
    table1_rows = [
        ["Permanent Account Number (PAN)", pan if pan else "NOT PROVIDED", "Income Tax Department, Govt of India"],
        ["GST Identification Number (GSTIN)", gstin if gstin else "NOT PROVIDED", "GSTN Portal, CBIC"],
        ["Udyam Registration No. (MSME)", udyam if udyam else "NOT APPLICABLE", "Ministry of MSME, Govt of India"],
    ]
    next_y = draw_table(page, 220, table1_headers, table1_rows, [180, 160, 147])

    # 5. Table 2: Financial Turnover & Local Content Declaration
    table2_headers = ["Compliance Parameter", "Declared Value by Bidder", "Mandatory Tender Rule"]
    table2_rows = [
        ["Annual turnover", f"Rs. {turnover_str}" if turnover_str else "N/A", "Must reconcile with GST/CA records"],
        ["Make in India local content", f"{local_content_str}" if local_content_str else "N/A", "Preference to Make in India (Class-I >= 50%)"],
        ["Debarment / Blacklisting Status", "Debarred under Order CPCL/VIG/2025/112" if is_debarred else "Not Debarred / Not Blacklisted", "Rule 151 of GFR 2017 (Integrity Pact)"],
    ]
    next_y = draw_table(page, next_y + 10, table2_headers, table2_rows, [180, 160, 147])

    # 6. Detailed Undertaking Text
    undertaking_text = (
        "Statutory Integrity Undertaking:\n"
        "1. We confirm that our GST registration is currently active and all mandatory GSTR-1 and GSTR-3B\n"
        "   returns up to the preceding financial quarter have been filed without default.\n"
        "2. We have examined the tender terms and confirm that local value addition satisfies Class-I criteria.\n"
        "3. Neither our firm nor our directors have been debarred by GeM, CPCL, or any central ministry."
    )
    page.insert_text((54, next_y + 15), undertaking_text, fontsize=8, fontname="helv", color=(0.25, 0.25, 0.25))

    # 7. Signature / Seal Block
    sig_y = 690
    page.draw_line(fitz.Point(54, sig_y), fitz.Point(541, sig_y), color=(0.85, 0.85, 0.85))
    
    # Authorized Signatory
    page.insert_text((54, sig_y + 20), "For and on behalf of:", fontsize=8, fontname="helv", color=(0.3, 0.3, 0.3))
    page.insert_text((54, sig_y + 35), bidder_name, fontsize=9.5, fontname="helv", color=(0.1, 0.1, 0.1))
    page.insert_text((54, sig_y + 60), "Authorized Signatory & Seal", fontsize=8, fontname="helv", color=(0.4, 0.4, 0.4))
    page.insert_text((54, sig_y + 72), "Designation: Director / Head of Procurement", fontsize=8, fontname="helv", color=(0.4, 0.4, 0.4))
    
    # CA Certification block
    page.insert_text((350, sig_y + 20), "Statutory Auditor / CA Certification:", fontsize=8, fontname="helv", color=(0.3, 0.3, 0.3))
    page.insert_text((350, sig_y + 35), "M/s R. K. Sridhar & Associates, Chartered Accountants", fontsize=8, fontname="helv", color=(0.1, 0.1, 0.1))
    page.insert_text((350, sig_y + 60), "UDIN: 26048192AAAAAE8192", fontsize=8, fontname="helv", color=(0.4, 0.4, 0.4))
    page.insert_text((350, sig_y + 72), "Membership No: 048192 | Date: 30-Aug-2026", fontsize=8, fontname="helv", color=(0.4, 0.4, 0.4))

    doc.save(OUTPUT_DIR / filename)
    doc.close()
    print(f"Generated realistic bid: {filename}")

# Generate Realistic Documents
generate_formal_bid(
    "01_happy_path_apex.pdf",
    bidder_name="Apex Petrochem Pvt Ltd",
    cin="U23209TN2015PTC099812",
    pan="AABCA1234F",
    gstin="33AABCA1234F1Z5",
    udyam="UDYAM-TN-01-0012345",
    turnover_str="25.00 Crore",
    local_content_str="65%",
    address="Plot 42, Manali Industrial Estate, Chennai - 600068, Tamil Nadu"
)

generate_formal_bid(
    "02_turnover_inflated_bharat.pdf",
    bidder_name="Bharat Valves & Pipes Ltd",
    cin="U28991MH2012PLC078123",
    pan="BBBCB5678K",
    gstin="27BBBCB5678K1Z2",
    udyam="UDYAM-MH-02-0098765",
    turnover_str="25.00 Crore",  # Real is 12.0 Cr
    local_content_str="60%",
    address="MIDC Industrial Area, Phase II, Turbhe, Navi Mumbai - 400705, Maharashtra"
)

generate_formal_bid(
    "03_debarred_national.pdf",
    bidder_name="National Industrial Supplies",
    cin="U51909DL2018PTC061245",
    pan="CCCDC9012M",
    gstin="07CCCDC9012M1Z8",
    udyam="UDYAM-DL-03-0054321",
    turnover_str="18.00 Crore",
    local_content_str="55%",
    address="408, Asaf Ali Road, Daryaganj, New Delhi - 110002",
    is_debarred=True
)

generate_formal_bid(
    "04_suspended_gst_delta.pdf",
    bidder_name="Delta Fluid Tech",
    cin="U29100KA2016PTC045892",
    pan="DDDDE3456N",
    gstin="29DDDDE3456N1Z9",
    udyam="UDYAM-KA-04-0022222",
    turnover_str="8.50 Crore",
    local_content_str="52%",
    address="Peenya Industrial Area, 3rd Stage, Bangalore - 560058, Karnataka"
)

generate_formal_bid(
    "05_under_local_content_apex.pdf",
    bidder_name="Apex Petrochem Pvt Ltd",
    cin="U23209TN2015PTC099812",
    pan="AABCA1234F",
    gstin="33AABCA1234F1Z5",
    udyam="UDYAM-TN-01-0012345",
    turnover_str="25.00 Crore",
    local_content_str="35%",  # Below 50% tender threshold
    address="Plot 42, Manali Industrial Estate, Chennai - 600068, Tamil Nadu"
)

generate_formal_bid("06_corrupt_blank_document.pdf", bidder_name="", cin="", pan="", gstin="", udyam="", turnover_str="", local_content_str="", address="", blank=True)