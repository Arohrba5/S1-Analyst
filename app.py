from flask import Flask, render_template, request, jsonify
import os  # Import the 'os' module to access environment variables
import psycopg2  # To connect to PostgreSQL
import requests

app = Flask(__name__)

def get_latest_s1_filing(cik):
    # Ensure 10-digit entry with padding
    cik = cik.zfill(10)
    url = f"https://data.sec.gov/submissions/cik{cik}.json"
    headers = {"User-Agent": "S1 Analyst (alex.s.rohrbach@gmail.com)"}

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return {"error": "Unable to fetch data from SEC Edgar."}
    
    filings = response.json().get('filings', {}).get('recent',{})

    # Extract necessary data for query
    form_types = filings.get('form', [])
    accession_numbers = filings.get('accessionNumber', [])
    filing_dates = filings.get('filingDate', [])

    # Find latest S-1
    s1_filings = [
        (form, accession, data)
        for form, accession, data in zip(form_types, accession_numbers, filing_dates)
        if form in ["S-1", "S-1/A"]
    ]

    if not s1_filings:
        return {"error": "No filings found for this CIK."}
    
    # Sort by filing data
    s1_filings.sort(key=lambda x: x[2], reverse=True)

    latest_filing = s1_filings[0]
    filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{latest_filing[1].replace('-', '')}/index.htm"

    return {"formType": latest_filing[0], "filingDate": latest_filing[2], "url": filing_url}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search',methods=['POST'])
def search():
    cik = request.form.get('cik')
    if not cik:
        return render_template('index.html', error="Please enter valid CIK.")
    # NTD: Add more cik checks before proceding to helper function
    
    result = get_latest_s1_filing(cik)
    if "error" in result:
        return render_template('index.html', error=result["error"])
    
    # Pass result to new page
    return render_template('result.html', filing=result)

@app.route('/about')
def cik_lookup():
    return render_template('about.html')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Use PORT if provided, otherwise default to 5000
    app.run(host="0.0.0.0", port=port, debug=True)        # Use 0.0.0.0 to accept connections from any IP