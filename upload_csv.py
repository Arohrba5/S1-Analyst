import psycopg2
import os

DB_CONNECTION = os.environ.get("DATABASE_URL")
CSV_FILE = "filtered_s1_filings.csv"

try:
    conn = psycopg2.connect(DB_CONNECTION, connect_timeout=10)
    cursor = conn.cursor()

    # Truncate the table
    cursor.execute("TRUNCATE TABLE submissions;")
    conn.commit()
    print("Database truncated successfully.")

    # Use COPY for faster bulk insert
    with open(CSV_FILE, "r", encoding="utf-8") as csvfile:
        next(csvfile)  # Skip the header row
        cursor.copy_expert("""
            COPY submissions (cik, company_name, filing_date, form_type, accession_number, primary_document)
            FROM STDIN WITH CSV HEADER;
        """, csvfile)
    conn.commit()
    print("Data uploaded successfully.")

except Exception as e:
    print(f"Error: {e}")

finally:
    if 'cursor' in locals() and cursor:
        cursor.close()
    if 'conn' in locals() and conn:
        conn.close()