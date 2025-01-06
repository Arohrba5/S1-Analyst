import psycopg2
import csv
import os

DB_CONNECTION = os.environ.get("DATABASE_URL")  # Ensure this is set in your environment
CSV_FILE = "filtered_s1_filings.csv"

try:
    conn = psycopg2.connect(DB_CONNECTION)
    cursor = conn.cursor()

    # Step 1: Truncate the table
    cursor.execute("TRUNCATE TABLE submissions;")
    conn.commit()
    print("Database truncated successfully.")

    # Step 2: Insert new data from CSV
    with open(CSV_FILE, "r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            cursor.execute("""
                INSERT INTO submissions (cik, company_name, filing_date, form_type, accession_number, primary_document)
                VALUES (%s, %s, %s, %s, %s, %s);
            """, (row['cik'], row['company_name'], row['filing_date'], row['form_type'], row['accession_number'], row['primary_document']))
    conn.commit()
    print("Data uploaded successfully.")

except Exception as e:
    print(f"Error: {e}")

finally:
    cursor.close()
    conn.close()