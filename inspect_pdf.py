import pdfplumber
import sys

pdf_path = "LCM-Diversos.pdf"

try:
    with pdfplumber.open(pdf_path) as pdf:
        print(f"Total pages: {len(pdf.pages)}")
        
        for i, page in enumerate(pdf.pages[:3]):
            print(f"\n--- Page {i+1} ---")
            
            # Check for tables
            tables = page.extract_tables()
            if tables:
                print(f"Found {len(tables)} table(s)")
                for t_idx, table in enumerate(tables):
                    print(f"Table {t_idx+1} preview:")
                    for row in table[:5]:
                        print(row)
            else:
                print("No tables found. First 500 characters of text:")
                print(page.extract_text()[:500])

except Exception as e:
    print(f"Error reading PDF: {e}")
