from flask import Flask, render_template, request, jsonify
import os
import psycopg2
import requests

app = Flask(__name__)

def get_latest_s1_filing(cik):
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
            error=f"{result['error']} If the company has been public for a long time, its S-1 may no longer appear in recent filings. Visit SEC Edgar to search: https://www.sec.gov/edgar/searchedgar/companysearch.html"
        )
    
    # Pass result to new page
    return render_template('result.html', filing=result)

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)