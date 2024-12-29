# S1 Analyst App

## Overview
This MVP version of the S-1 Analyst App is designed for users to quickly find and access SEC S-1 filings. As a venture capitalist, I find it helpful to study S-1 filings to see how late-stage companies position their products and analyze their financial growth.

In future iterations, the app will include parsing and analysis of S-1 documents to:
 - Summarize key sections (e.g., company overview, business riks) 
 - Identify and visualize financial trends
 - Identify key noteworthy quotes

## What is an S-1 Filing?
SEC Form S-1 is the initial registration form required by the SEC for new securities offered by public companies in the US. S-1 filings are typically submitted by private companies as they prepare to go public. These documents can be updated multiple times, so this app focuses on retrieving the most recent version of a company's S-1 filing.

## Features
 - **Quick Access**: Fetch and display the latest S-1 filing for a given company using its CIK (Central Index Key).
 - **Streamlined Workflow**: Automatically generate the URL to view the document directly from the SEC's EDGAR system.
 - **Future Enhancements**: Planned features include automated analysis and summaries of S-1 filings, such as key risks, company highlights, and financial insights.

## Technical Details
 - **Framework**: Flask (Python)
 - **Hosting**: Heroku (via: https://www.s1analyst.app/)
 - **Backend**: PostgreSQL database
 - **Templating Engine**: Jinja2 for dynamically rendering HTML pages
 - **Data Source**: SEC's EDGAR RESTful APIs (API Documentation: https://www.sec.gov/search-filings/edgar-application-programming-interfaces)

## Current Implementation
The app uses the Submissions API to:
 - Look up the latest S-1 filing for a company.
 - Extract the required document code.
 - Generate a standardized URL to load the S-1 document.

## Known Limitations
 - **Request Limitations**: The SEC API limits requests to 10 per second, which means the app cannot handle high-scale usage without additional caching or queuing mechanisms.
 - **Submission Data**: The Submissions API provides up to one year of data or 1,000 filings per company, which can result in incomplete access to older S-1 filings for high-volume filers like Meta (formerly Facebook).
 - **Workarounds**: While the PostgreSQL database is set up, the app currently relies on the EDGAR API for direct access. The database will become essential for advanced features planned for future releases.

## Contributing
Contributions are welcome! If you would like to improve this project:
 - Fork the repository.
 - Create a feature branch.
 - Submit a pull request with detailed explanations of your changes.

## License
This project is licensed under the MIT License. See the LICENSE file for details.

## CS50 Final Project
I created this app as a final project for CS50 and recorded a demo video here: https://youtu.be/uZrXA0qyCVc