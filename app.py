from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
import psycopg2
import csv
import logging
import requests

app = Flask(__name__)

DB_CONNECTION = os.environ.get("DATABASE_URL")  # Heroku Postgres connection string
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Helper Functions
def load_recent_filings():
    """Helper function to load the 5 most recent S-1 filings."""
    conn = psycopg2.connect(DB_CONNECTION)
    cursor = conn.cursor()

    # Query for the 5 most recent S-1 filings
    cursor.execute("""
        SELECT cik, company_name, filing_date, form_type, accession_number, primary_document
        FROM submissions
        ORDER BY filing_date DESC
        LIMIT 5;
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    # Format the data for the table
    filings = [
        {
            "cik": row[0],
            "company_name": row[1],
            "filing_date": row[2],
            "form_type": row[3],
            "accession_number": row[4],
            "primary_document": row[5],
        }
        for row in rows
    ]
    return filings

# Home Route
@app.route('/')
def home():
    filings = load_recent_filings()
    return render_template('index.html', filings=filings)

# Search Route
@app.route('/search', methods=['POST'])
def search():
    cik = request.form.get('cik', '').strip()
    filings = load_recent_filings()

    if not cik:
        return render_template('index.html', filing=filings, error="Please enter a CIK.")
    if not cik.isdigit():
        return render_template('index.html', filing=filings, error="CIK must be a numeric value.")
    if len(cik) != 10:
        return render_template('index.html', filing=filings, error="CIK must be 10 digits in length.")

    result = get_latest_s1_filing(cik)
    if "error" in result:
        # Fallback for old filings
        return render_template(
            'index.html', 
            error=f"{result['error']} Filings older than one year may not appear. Search Edgar for older filings: https://www.sec.gov/edgar/searchedgar/companysearch.html"
        )
    
    # Pass result to new page
    return render_template('result.html', filing=result)

# Upload Route
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        # Check if the file is part of the request
        if 'file' not in request.files:
            return jsonify({"error": "No file part in the request."}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected."}), 400

        # Save the uploaded file temporarily
        temp_path = os.path.join("uploads", file.filename)
        os.makedirs("uploads", exist_ok=True)  # Ensure the uploads directory exists
        file.save(temp_path)

        # Process the CSV and insert data into the database
        try:
            conn = psycopg2.connect(DB_CONNECTION)
            cursor = conn.cursor()

            with open(temp_path, "r", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    cursor.execute("""
                        INSERT INTO submissions (cik, company_name, filing_date, form_type, accession_number, primary_document)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING;
                    """, (row['cik'], row['company_name'], row['filing_date'], row['form_type'], row['accession_number'], row['primary_document']))
            conn.commit()
            cursor.close()
            conn.close()

            # Clean up the temporary file
            os.remove(temp_path)

            logging.info("Data uploaded and stored successfully.")
            return redirect(url_for('home'))

        except Exception as e:
            logging.error(f"An error occurred: {e}")
            return jsonify({"error": "Failed to process the file."}), 500

    return render_template('upload.html')

# Get Latest S-1 Filing Function
def get_latest_s1_filing(cik):
    """Extract cik from user. Find latest S-1 filing for a company. Return necessary info."""
    cik = cik.zfill(10)  # Ensure 10-digit entry with padding
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    headers = {"User-Agent": "S1 Analyst (alex.s.rohrbach@gmail.com)"}

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return {"error": "Unable to fetch data from SEC Edgar."}

    filings = response.json().get('filings', {}).get('recent', {})

    # Extract necessary data for query
    form_types = filings.get('form', [])
    accession_numbers = filings.get('accessionNumber', [])
    filing_dates = filings.get('filingDate', [])
    primary_documents = filings.get('primaryDocument', [])

    # Ensure all lists are of the same length
    if not (len(form_types) == len(accession_numbers) == len(filing_dates) == len(primary_documents)):
        return {"error": "Malformed data received from SEC Edgar."}

    # Find latest S-1 filing
    s1_filings = [
        (form, accession, date, document)
        for form, accession, date, document in zip(form_types, accession_numbers, filing_dates, primary_documents)
        if form in ["S-1", "S-1/A"]
    ]

    if not s1_filings:
        return {"error": "No S-1 filing found for this CIK."}

    # Sort by filing date
    s1_filings.sort(key=lambda x: x[2], reverse=True)

    latest_filing = s1_filings[0]
    formatted_accession = latest_filing[1].replace("-", "")  # Remove hyphens from accession number
    document_name = latest_filing[3]  # Get the primary document name
    filing_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{formatted_accession}/{document_name}"

    return {"formType": latest_filing[0], "filingDate": latest_filing[2], "url": filing_url}

# About Page
@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)