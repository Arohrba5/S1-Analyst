import zipfile
import json
import csv
import requests
import logging

# Constants
SEC_BULK_DATA_URL = "https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip"
OUTPUT_FILE = "filtered_s1_filings.csv"  # Smaller filtered output file
HEADERS = {
    "User-Agent": "S1 Analyst (alex.s.rohrbach@gmail.com)",
    "Accept-Encoding": "gzip, deflate",
    "Host": "www.sec.gov"
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def download_zip_file(url, output_path):
    """Download the ZIP file from the SEC."""
    logging.info("Downloading ZIP file from SEC...")
    try:
        response = requests.get(url, headers=HEADERS, stream=True)
        response.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logging.info("ZIP file downloaded successfully.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to download ZIP file: {e}")
        raise


def extract_s1_filings(zip_path, output_path):
    """Extract and filter S-1 filings from the ZIP file."""
    logging.info("Processing ZIP file...")
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["cik", "company_name", "filing_date", "form_type", "accession_number", "primary_document"])

                for file_name in zip_ref.namelist():
                    if file_name.endswith(".json"):
                        with zip_ref.open(file_name) as f:
                            try:
                                record = json.load(f)
                                cik = str(record.get("cik", "Unknown")).zfill(10)
                                company_name = record.get("name", "Unknown")
                                filings = record.get("filings", {}).get("recent", {})
                                
                                for i, form in enumerate(filings.get("form", [])):
                                    if form in ["S-1", "S-1/A"]:
                                        filing_date = filings.get("filingDate", [])[i]
                                        accession_number = filings.get("accessionNumber", [])[i]
                                        primary_document = filings.get("primaryDocument", [])[i]

                                        writer.writerow([cik, company_name, filing_date, form, accession_number, primary_document])
                            except Exception as e:
                                logging.error(f"Error processing file {file_name}: {e}")
        logging.info(f"Filtered data saved to {output_path}")
    except zipfile.BadZipFile as e:
        logging.error(f"Failed to process ZIP file: {e}")
        raise


def main():
    ZIP_FILE = "submissions.zip"  # Local path to store the downloaded ZIP file

    # Step 1: Download ZIP file from SEC
    download_zip_file(SEC_BULK_DATA_URL, ZIP_FILE)

    # Step 2: Extract and filter S-1 filings
    extract_s1_filings(ZIP_FILE, OUTPUT_FILE)


if __name__ == "__main__":
    main()