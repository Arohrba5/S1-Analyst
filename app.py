import csv
import logging
import os

from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify, redirect, url_for
from openai import OpenAI
import psycopg2
import requests

app = Flask(__name__)

DB_CONNECTION = os.environ.get("DATABASE_URL")  # Heroku Postgres connection string
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

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


def extract_text_from_url(url):
    """Fetch and extract plain text from an S-1 filing URL, with debugging and cleaning."""
    try:
        # Fetch the URL
        response = requests.get(url)
        if response.status_code != 200:
            logging.error(f"Error: Received status code {response.status_code} from URL.")
            return f"Error: Received status code {response.status_code} from URL."
        
        # Log the status and the first 250 characters of raw HTML
        logging.info(f"Received status code: {response.status_code}")
        logging.info(f"Raw HTML content (first 250 chars): {response.text[:250]}")

        # Parse the HTML content
        soup = BeautifulSoup(response.content, "html.parser")

        # Remove non-text elements like scripts and styles
        for element in soup(["script", "style"]):
            element.decompose()

        # Extract and clean the text
        text = soup.get_text(separator="\n").strip()

        # Log the first 250 characters of extracted text
        logging.info(f"Extracted text (first 250 chars): {text[:250]}")

        # Return the cleaned text or an error message
        return text if text else "Error: No meaningful text found in the HTML content."

    except Exception as e:
        logging.error(f"Exception occurred while fetching or extracting text: {e}")
        return f"Error: An exception occurred while fetching or extracting text: {str(e)}"
    
def chunk_text(text, max_chars=3000):
    """Chunk text into smaller pieces to fit within token limits."""
    return [text[i:i+max_chars] for i in range(0, len(text), max_chars)]

def summarize_chunk(chunk):
    """Summarize a single chunk of text using OpenAI API."""
    prompt = f"Summarize the following SEC S-1 filing text:\n\n{chunk}"
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a financial analyst that summarizes financial filings that we provide you."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.7
        )
        # Access the response content
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error summarizing chunk: {str(e)}"

def summarize_filing_from_url(url):
    """Fetch, chunk, and summarize an S-1 filing from a URL."""
    # Extract the text from the URL
    text = extract_text_from_url(url)
    if not text:
        return "Error: Could not fetch or extract text from the URL."

    # Chunk the text to stay within token limits
    chunks = chunk_text(text)

    # Summarize each chunk
    summaries = [summarize_chunk(chunk) for chunk in chunks]

    # Generate a cohesive summary of all chunks
    final_summary = generate_final_summary(summaries)
    return final_summary

def generate_final_summary(chunk_summaries):
    """Generate a cohesive summary of the entire filing from chunk summaries."""
    combined_summaries = "\n".join(chunk_summaries)
    prompt = f"Summarize the following summaries of an SEC S-1 filing into a single cohesive summary:\n\n{combined_summaries}"
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a financial analyst that writes concise, high-level summaries of SEC filings."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,  # Adjust this as needed for your desired summary length
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating final summary: {str(e)}"

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
        return render_template('index.html', filings=filings, error="Please enter a CIK.")
    if not cik.isdigit():
        return render_template('index.html', filings=filings, error="CIK must be a numeric value.")
    if len(cik) != 10:
        return render_template('index.html', filings=filings, error="CIK must be 10 digits in length.")

    result = get_latest_s1_filing(cik)
    if "error" in result:
        # Fallback for old filings
        return render_template(
            'index.html', 
            error=f"{result['error']} Filings older than one year may not appear. Search Edgar for older filings: https://www.sec.gov/edgar/searchedgar/companysearch.html"
        )
    
    # Extract and summarize the filing
    filing_url = result.get("url")
    filing_summary = None
    try:
        # Use the updated `summarize_filing_from_url` function
        filing_summary = summarize_filing_from_url(filing_url)
    except Exception as e:
        filing_summary = f"An error occurred while summarizing the filing: {str(e)}"

    # Pass the result and summary to the result page
    return render_template('result.html', filing=result, summary=filing_summary)

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