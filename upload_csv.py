import psycopg2
import csv
import os

DB_CONNECTION = os.environ.get("DATABASE_URL")  # Ensure this is set in your environment
CSV_FILE = "filtered_s1_filings.csv"
BATCH_SIZE = 1000  # Adjust batch size for optimal performance

try:
    conn = psycopg2.connect(DB_CONNECTION, connect_timeout=10)
    cursor = conn.cursor()

    # Step 1: Truncate the table
    cursor.execute("TRUNCATE TABLE submissions;")
    conn.commit()
    print("Database truncated successfully.")

    # Step 2: Insert new data from CSV in batches
    with open(CSV_FILE, "r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        batch = []
        for i, row in enumerate(reader, start=1):
            batch.append((
                row['cik'], row['company_name'], row['filing_date'], 
                row['form_type'], row['accession_number'], row['primary_document']
            ))

            if len(batch) >= BATCH_SIZE:
                cursor.executemany("""
                    INSERT INTO submissions (cik, company_name, filing_date, form_type, accession_number, primary_document)
                    VALUES (%s, %s, %s, %s, %s, %s);
                """, batch)
                conn.commit()
                print(f"Inserted batch of {BATCH_SIZE} rows (up to row {i}).")
                batch = []

        # Insert remaining rows in the batch
        if batch:
            cursor.executemany("""
                INSERT INTO submissions (cik, company_name, filing_date, form_type, accession_number, primary_document)
                VALUES (%s, %s, %s, %s, %s, %s);
            """, batch)
            conn.commit()
            print(f"Inserted remaining {len(batch)} rows.")

    print("Data uploaded successfully.")

except Exception as e:
    print(f"Error: {e}")

finally:
    if 'cursor' in locals() and cursor:
        cursor.close()
    if 'conn' in locals() and conn:
        conn.close()