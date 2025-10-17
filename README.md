# German Company Crawler API

Professional API for crawling and extracting German company data from multiple sources including Northdata, Handelsregister, LinkedIn, and Unternehmensregister.

## Features

- **Multi-source scraping**: Northdata, Handelsregister, LinkedIn, Unternehmensregister
- **27 data fields extraction**: Complete company information including financial, legal, and contact data
- **Parallel processing**: Concurrent scraping for faster results
- **Robust error handling**: Automatic retry and fallback mechanisms
- **Stealth mode**: Advanced bot detection avoidance
- **HTML/PDF/XML data extraction**: Raw data preservation for analysis

## API Endpoints

### POST /api/company
Crawl company data from all sources.

**Request Body:**
```json
{
  "company_name": "MAGNA Real Estate GmbH",
  "registernummer": "HRB182742",
  "ust_idnr": "DE305962143"
}
```

**Response:**
```json
{
  "company_name": "MAGNA Real Estate GmbH",
  "registernummer": "HRB182742",
  "ust_idnr": "DE305962143",
  "northdata": {
    "html": "...",
    "html_filepath": "data/companies/MAGNA_Real_Estate_GmbH_HRB182742_northdata.html"
  },
  "handelsregister": {
    "pdf_filepath": "data/downloads/HRB182742_AD.pdf",
    "xml_filepath": "data/downloads/HRB182742_SI.xml"
  },
  "linkedin": {
    "about_html": "..."
  },
  "unternehmensregister": {
    "search_results_html": "...",
    "jahresabschluss_html": "..."
  }
}
```

### GET /
Root endpoint with API information.

### GET /health
Health check endpoint.

### GET /docs
Interactive API documentation.

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Datapix-organization/Company-crawler.git
cd Company-crawler
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install Playwright browsers:
```bash
playwright install
```

4. Run the server:
```bash
python server.py
```

The API will be available at `http://localhost:8000`

## Data Fields Extracted

The API extracts 27 standardized fields from German company data:

### Basic Information (7 fields)
- registernummer, handelsregister, geschaeftsadresse, unternehmenszweck
- land_des_hauptsitzes, gerichtsstand, paragraph_34_gewo

### Financial Data (4 fields)
- mitarbeiter, umsatz, gewinn, insolvenz

### Real Estate Data (2 fields)
- anzahl_immobilien, gesamtwert_immobilien

### Other Information (3 fields)
- sonstige_rechte, gruendungsdatum, aktiv_seit

### Contact Information (4 fields)
- geschaeftsfuehrer, telefonnummer, email, website

### File Data (5 fields)
- html_filepath, about_html, pdf_filepath, xml_filepath
- search_results_html, jahresabschluss_html

### Additional Information (2 fields)
- ust_idnr

## Project Structure

```
├── server.py                 # FastAPI main application
├── scrapers/                 # Scraper modules
│   ├── northdata_scraper.py
│   ├── handelsregister_scraper.py
│   ├── linkedin_scraper.py
│   └── unternehmensregister_scraper.py
├── utils/                    # Utility modules
│   ├── pdf_data_extractor.py
│   └── xml_parser.py
├── data/                     # Data storage
│   ├── companies.json        # Company list
│   └── companies/            # Scraped data files
└── requirements.txt          # Dependencies
```

## Usage Example

```python
import requests

# API call example
response = requests.post('http://localhost:8000/api/company', json={
    "company_name": "MAGNA Real Estate GmbH",
    "registernummer": "HRB182742",
    "ust_idnr": "DE305962143"
})

data = response.json()
print(f"Company: {data['company_name']}")
print(f"Employees: {data['northdata'].get('mitarbeiter', 'N/A')}")
```

## Technical Details

- **Framework**: FastAPI with Uvicorn
- **Scraping**: Playwright + Selenium with stealth mode
- **Data Processing**: BeautifulSoup, PDFplumber, XML parsing
- **Concurrency**: ThreadPoolExecutor for parallel scraping
- **Error Handling**: Comprehensive try-catch with logging

## Requirements

- Python 3.8+
- Chrome/Chromium browser
- Internet connection for scraping

## License

This project is licensed under the MIT License.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues and questions, please create an issue in the GitHub repository.
