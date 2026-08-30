import fitz
from pathlib import Path

OUTPUT_DIR = Path("test_bids")
OUTPUT_DIR.mkdir(exist_ok=True)

def generate_bid(filename, name, pan="", gstin="", udyam="", turnover="", local_pct=""):
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    
    # Official Header
    page.draw_rect(fitz.Rect(54, 40, 541, 42), color=(0.1, 0.25, 0.5), fill=(0.1, 0.25, 0.5))
    page.insert_text((54, 65), name.upper(), fontsize=13, fontname="helv", color=(0.08, 0.2, 0.4))
    page.insert_text((54, 78), "GeM Statutory Bid Document | Tender Ref: GEM-2026-CPCL-001", fontsize=8, fontname="helv", color=(0.4, 0.4, 0.4))
    page.draw_line(fitz.Point(54, 88), fitz.Point(541, 88), color=(0.8, 0.8, 0.8))
    
    # Statutory Values
    y = 120
    if pan:
        page.insert_text((54, y), f"Permanent Account Number: PAN: {pan}", fontsize=9, fontname="helv")
        y += 24
    if gstin:
        page.insert_text((54, y), f"Goods and Services Tax: GSTIN: {gstin}", fontsize=9, fontname="helv")
        y += 24
    if udyam:
        page.insert_text((54, y), f"Udyam Registration: Udyam No: {udyam}", fontsize=9, fontname="helv")
        y += 24
    if turnover:
        page.insert_text((54, y), f"Annual turnover: {turnover}", fontsize=9, fontname="helv")
        y += 24
    if local_pct:
        page.insert_text((54, y), f"Make in India local content: {local_pct}", fontsize=9, fontname="helv")
        y += 24

    doc.save(OUTPUT_DIR / filename)
    doc.close()
    print(f"Created: {filename}")

# 07. Fuzzy Name Match Pass (Abbreviations vs Full Form)
generate_bid("07_fuzzy_name_pass.pdf", "Apex Petrochemical Private Limited", "AABCA1234F", "33AABCA1234F1Z5", "UDYAM-TN-01-0012345", "Rs. 25.00 Crore", "65%")

# 08. Severe Name Mismatch (Shell Entity Penalty)
generate_bid("08_severe_name_mismatch.pdf", "Global Oil & Gas Engineering Ltd", "AABCA1234F", "33AABCA1234F1Z5", "UDYAM-TN-01-0012345", "Rs. 25.00 Crore", "65%")

# 09. Indian Numbering with Raw Lakhs Formatting
generate_bid("09_turnover_in_lakhs.pdf", "Apex Petrochem Pvt Ltd", "AABCA1234F", "33AABCA1234F1Z5", "UDYAM-TN-01-0012345", "Rs. 2,500 Lakhs", "65%")

# 10. Optional Udyam Omitted (Valid Non-MSME)
generate_bid("10_optional_udyam_omitted.pdf", "Apex Petrochem Pvt Ltd", "AABCA1234F", "33AABCA1234F1Z5", "", "Rs. 25.00 Crore", "65%")

# 11. GST Active but Non-Filing Defaulter
generate_bid("11_gst_non_filing_defaulter.pdf", "Delta Fluid Tech", "DDDDE3456N", "29DDDDE3456N1Z9", "UDYAM-KA-04-0022222", "Rs. 8.50 Crore", "52%")

# 12. Unknown PAN (Unverified 404 Warning)
generate_bid("12_unknown_pan_unverified.pdf", "Unregistered Supplier Ltd", "ZZZZZ9999Z", "99ZZZZZ9999Z1Z9", "", "Rs. 10.00 Crore", "50%")

# 13. Compound Multiple Failures (Turnover + MII + Debarred)
generate_bid("13_compound_critical_fail.pdf", "National Industrial Supplies", "CCCDC9012M", "07CCCDC9012M1Z8", "UDYAM-DL-03-0054321", "Rs. 45.00 Crore", "20%")

# 14. Exact Boundary Local Content (50.0% threshold)
generate_bid("14_exact_boundary_local_content.pdf", "Bharat Valves & Pipes Ltd", "BBBCB5678K", "27BBBCB5678K1Z2", "UDYAM-MH-02-0098765", "Rs. 12.00 Crore", "50.0%")

# 15. Turnaround Tolerance Pass (Within 10% Margin)
generate_bid("15_turnover_tolerance_pass.pdf", "Bharat Valves & Pipes Ltd", "BBBCB5678K", "27BBBCB5678K1Z2", "UDYAM-MH-02-0098765", "Rs. 13.00 Crore", "60%")