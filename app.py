from flask import Flask, render_template, request, jsonify
import os
import psycopg2
import requests
import zipfile
import json
import logging
import psutil

app = Flask(__name__)

SEC_BULK_DATA_URL = "https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip"
DB_CONNECTION = os.environ.get("DATABASE_URL")  # Heroku Postgres connection string
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def process_file(file_name, zip_ref, cursor, conn):
    """Processes a single JSON file from the ZIP and filters for S-1 filings."""
    try:
        with zip_ref.open(file_name) as f:
            record = json.load(f)  # Load the entire JSON file
            cik = record.get("cik", "Unknown")
            company_name = record.get("name", "Unknown")
            filings = record.get("filings", {}).get("recent", {})
            
            # Extract S-1 and S-1/A filings
            for i, form in enumerate(filings.get("form", [])):
                if form in ["S-1", "S-1/A"]:
                    filing_date = filings.get("filingDate", [])[i]
                    accession_number = filings.get("accessionNumber", [])[i]
                    raw_data = json.dumps({
                        "form": form,
                        "filingDate": filing_date,
                        "accessionNumber": accession_number
                    })

                    # Insert only relevant filings
                    cursor.execute(
                        """
                        INSERT INTO submissions (cik, company_name, filing_date, form_type, accession_number, raw_data)
                        VALUES (%s, %s, %s, %s, %s, %s);
                        """,
                        (cik, company_name, filing_date, form, accession_number, raw_data)
                    )
                    conn.commit()
    except Exception as e:
        logging.error(f"Error processing file {file_name}: {e}")


def update_submissions_data():
    """Download, extract, and update the database with the latest submissions data."""
    try:
        # Paths
        zip_path = "submissions.zip"

        # Download ZIP file
        logging.info("Downloading ZIP file from SEC...")
        headers = {"User-Agent": "S1 Analyst (alex.s.rohrbach@gmail.com)"}
        response = requests.get(SEC_BULK_DATA_URL, headers=headers, stream=True)
        if response.status_code == 200:
            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logging.info("ZIP file downloaded successfully.")
        else:
            logging.error(f"Failed to download ZIP file. Status code: {response.status_code}")
            raise Exception("Failed to download ZIP file.")

        # Process the ZIP file incrementally
        logging.info("Processing ZIP file incrementally...")
        conn = psycopg2.connect(DB_CONNECTION)
        cursor = conn.cursor()

        # Truncate the submissions table
        logging.info("Truncating the submissions table...")
        cursor.execute("TRUNCATE TABLE submissions;")
        conn.commit()

        batch_size = 50  # Log every 50 files
        file_count = 0
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            for file_name in zip_ref.namelist():
                if file_name.endswith(".json"):
                    process_file(file_name, zip_ref, cursor, conn)
                    file_count += 1

                    # Log every `batch_size` files
                    if file_count % batch_size == 0:
                        logging.info(f"Processed {file_count} files so far.")

        # Final log for any remaining files
        logging.info(f"Total files processed: {file_count}")

        cursor.close()
        conn.close()
        logging.info("Database updated successfully.")

    except Exception as e:
        logging.error(f"An error occurred: {e}")

def get_latest_s1_filing(cik):
    """Extract cik from user. Find latest s-1 for company. Return dictionary of necessary info for lookup. """
    # Ensure 10-digit entry with padding
    cik = cik.zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    headers = {"User-Agent": "S1 Analyst (alex.s.rohrbach@gmail.com)"}

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return {"error": "Unable to fetch data from SEC Edgar."}
    
    filings = response.json().get('filings', {}).get('recent',{})

    # Extract necessary data for query
    form_types = filings.get('form', [])
    accession_numbers = filings.get('accessionNumber', [])
    filing_dates = filings.get('filingDate', [])
    primary_documents = filings.get('primaryDocument', [])

    # Ensure all lists are of the same length
    if not (len(form_types) == len(accession_numbers) == len(filing_dates) == len(primary_documents)):
        return {"error": "Malformed data received from SEC Edgar."}

    # Find latest S-1
    s1_filings = [
        (form, accession, date, document)
        for form, accession, date, document in zip(form_types, accession_numbers, filing_dates, primary_documents)
        if form in ["S-1", "S-1/A"]
    ]

    if not s1_filings:
        return {"error": "No S-1 filing found for this CIK."}
    
    # Sort by filing data
    s1_filings.sort(key=lambda x: x[2], reverse=True)

    latest_filing = s1_filings[0]
    formatted_accession = latest_filing[1].replace("-", "")  # Remove hyphens from accession number
    document_name = latest_filing[3]  # Get the primary document name
    filing_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{formatted_accession}/{document_name}"
    
    return {"formType": latest_filing[0], "filingDate": latest_filing[2], "url": filing_url}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search',methods=['POST'])
def search():
    cik = request.form.get('cik','').strip()

    if not cik:
        return render_template('index.html', error="Please enter a CIK.")
    if not cik.isdigit():
        return render_template('index.html', error="CIK must be a numeric value.")
    if len(cik) != 10:
        return render_template('index.html', error="CIK must be 10 digits in length.")
    
    result = get_latest_s1_filing(cik)
    if "error" in result:
        # Fallback for old filings
        return render_template(
            'index.html', 
            error=f"{result['error']} Filings older than one year may not appear. Search Edgar for older filings: https://www.sec.gov/edgar/searchedgar/companysearch.html"
        )
    
    # Pass result to new page
    return render_template('result.html', filing=result)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/update-submissions', methods=['POST'])
def trigger_update():
    """Trigger submissions update manually"""
    try:
        update_submissions_data()
        return jsonify({"status": "success", "message": "Submissions data updated successfully!"}), 200
    except Exception as e:
        logging.error(f"Error during update: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)