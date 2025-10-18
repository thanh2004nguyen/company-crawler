"""
German Company Crawler API Server
Clean, fast, and reliable API for crawling German company data
"""

import os
import sys
import json
import logging
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from concurrent.futures import ThreadPoolExecutor

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scrapers.handelsregister_scraper import HandelsregisterScraper
from scrapers.northdata_scraper import NorthdataScraper
from scrapers.linkedin_scraper import LinkedInScraper
from scrapers.unternehmensregister_scraper import UnternehmensregisterScraper

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="German Company Crawler API",
    description="Professional API for crawling and extracting German company data from multiple sources",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Pydantic models
class CompanyRequest(BaseModel):
    company_name: str
    registernummer: str
    ust_idnr: Optional[str] = ""

class CompanyResponse(BaseModel):
    company_name: str
    registernummer: str
    files: Dict[str, Dict[str, Optional[str]]]  # {"handelsregister": {"pdf": "content", "xml": "content"}, "northdata": {"html": "content"}, "linkedin": {"about_html": "content"}, "unternehmensregister": {"jahresabschluss_html": "content"}}
    success: bool
    error: Optional[str] = None

# Initialize scrapers
handelsregister_scraper = HandelsregisterScraper(headless=False, language='FR')  # Show browser
northdata_scraper = NorthdataScraper(headless=False)  # Show browser
linkedin_scraper = LinkedInScraper()  # Selenium scraper
unternehmensregister_scraper = UnternehmensregisterScraper()  # Playwright scraper

def load_companies_data():
    """Load companies data from companies.json"""
    try:
        with open('data/companies.json', 'r', encoding='utf-8') as f:
            companies = json.load(f)
        logger.info(f"📋 Loaded {len(companies)} companies from companies.json")
        return companies
    except Exception as e:
        logger.warning(f"⚠️ Could not load companies.json: {e}")
        return []

def get_company_ust_idnr(company_name: str, registernummer: str) -> Optional[str]:
    """Get USt-IdNr from companies.json if available"""
    companies = load_companies_data()
    
    for company in companies:
        # Match by company name and register number
        if (company.get('company_name', '').lower() == company_name.lower() and 
            company.get('registernummer', '').replace('HRB', '').replace(' ', '') == registernummer.replace('HRB', '').replace(' ', '')):
            
            ust_idnr = company.get('ust_idnr', '')
            if ust_idnr and ust_idnr.strip():
                logger.info(f"✅ Found USt-IdNr in companies.json: {ust_idnr}")
                return ust_idnr.strip()
    
    logger.info(f"ℹ️ No USt-IdNr found in companies.json for {company_name}")
    return None

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "German Company Crawler API",
        "version": "2.0.0",
        "status": "active",
        "endpoints": {
            "company_crawler": "/api/company",
            "docs": "/docs",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "german-company-crawler"}

@app.post("/api/company", response_model=CompanyResponse)
async def crawl_company(request: CompanyRequest):
    """
    Crawl company data from all sources
    
    Args:
        request: Company info (name, registernummer, ust_idnr)
        
    Returns:
        Dict with file contents from each source
    """
    try:
        logger.info(f"🚀 Crawling company: {request.company_name} (HRB: {request.registernummer})")
        
        # 1. Get USt-IdNr from companies.json first
        ust_idnr_from_file = get_company_ust_idnr(request.company_name, request.registernummer)
        
        # 2. Use USt-IdNr from request if provided, otherwise use from companies.json
        final_ust_idnr = request.ust_idnr if request.ust_idnr and request.ust_idnr.strip() else ust_idnr_from_file
        
        if final_ust_idnr:
            logger.info(f"🔢 Using USt-IdNr: {final_ust_idnr}")
        else:
            logger.info(f"ℹ️ No USt-IdNr available, will try to extract from scrapers")
        
        # Run scrapers in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor() as executor:
            # 1. Start Handelsregister scraper
            handelsregister_future = executor.submit(
                handelsregister_scraper.scrape_company,
                request.company_name,
                request.registernummer,
                final_ust_idnr
            )
            
            # 2. Start Northdata scraper
            northdata_future = executor.submit(
                northdata_scraper.scrape_company,
                request.company_name,
                request.registernummer
            )
            
            # 3. Start LinkedIn scraper
            linkedin_future = executor.submit(
                linkedin_scraper.scrape_with_selenium,
                request.company_name,
                request.registernummer
            )
            
            # 4. Start Unternehmensregister scraper
            unternehmensregister_future = executor.submit(
                unternehmensregister_scraper.scrape_company,
                request.company_name,
                request.registernummer
            )
            
            # 5. Wait for results
            handelsregister_data = handelsregister_future.result()
            northdata_data = northdata_future.result()
            linkedin_data = linkedin_future.result()
            unternehmensregister_data = unternehmensregister_future.result()
        
        # 4. Process Handelsregister results
        handelsregister_files = {}
        try:
            # Lấy file paths và đọc content
            if 'download_directory' in handelsregister_data:
                download_dir = handelsregister_data['download_directory']
                logger.info(f"📁 Download directory: {download_dir}")
                
                # PDF file
                pdf_path = os.path.join(download_dir, f"{request.registernummer}_AD.pdf")
                logger.info(f"📄 Checking PDF: {pdf_path}")
                if os.path.exists(pdf_path):
                    logger.info(f"✅ PDF exists, reading content...")
                    with open(pdf_path, 'rb') as f:
                        pdf_content = f.read()
                    # Dùng pdfplumber để extract text từ PDF
                    import pdfplumber
                    with pdfplumber.open(pdf_path) as pdf:
                        text = ""
                        for page in pdf.pages:
                            text += page.extract_text() + "\n"
                    handelsregister_files["pdf"] = text
                    logger.info(f"✅ PDF content length: {len(text)} chars")
                else:
                    logger.warning(f"⚠️ PDF not found: {pdf_path}")
                    handelsregister_files["pdf"] = None
                
                # XML file
                xml_path = os.path.join(download_dir, f"{request.registernummer}_SI.xml")
                logger.info(f"📄 Checking XML: {xml_path}")
                if os.path.exists(xml_path):
                    logger.info(f"✅ XML exists, reading content...")
                    with open(xml_path, 'r', encoding='utf-8') as f:
                        xml_content = f.read()
                    handelsregister_files["xml"] = xml_content
                    logger.info(f"✅ XML content length: {len(xml_content)} chars")
                else:
                    logger.warning(f"⚠️ XML not found: {xml_path}")
                    handelsregister_files["xml"] = None
            else:
                logger.warning("⚠️ No download_directory in handelsregister_data")
                handelsregister_files["pdf"] = None
                handelsregister_files["xml"] = None
                        
            logger.info(f"✅ Handelsregister: {len([f for f in handelsregister_files.values() if f])} files")
            
        except Exception as e:
            import traceback
            logger.error(f"❌ Lỗi Handelsregister: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            handelsregister_files = {"pdf": None, "xml": None}
        
        # 5. Process Northdata results
        northdata_files = {}
        try:
            # Lấy HTML filepath từ northdata_data và đọc content
            if 'html_filepath' in northdata_data and northdata_data['html_filepath']:
                html_filepath = northdata_data['html_filepath']
                logger.info(f"📄 Checking HTML: {html_filepath}")
                
                if os.path.exists(html_filepath):
                    logger.info(f"✅ HTML exists, reading content...")
                    with open(html_filepath, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    northdata_files = {"html": html_content}
                    logger.info(f"✅ HTML content length: {len(html_content)} chars")
                else:
                    logger.warning(f"⚠️ HTML file không tồn tại: {html_filepath}")
                    northdata_files = {"html": None}
            else:
                logger.warning("⚠️ No html_filepath in northdata_data")
                northdata_files = {"html": None}
                
            logger.info(f"✅ Northdata: {len([f for f in northdata_files.values() if f])} files")
            
        except Exception as e:
            import traceback
            logger.error(f"❌ Lỗi Northdata: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            northdata_files = {"html": None}
        
        # 6. Process LinkedIn results
        linkedin_files = {}
        try:
            if 'about_html' in linkedin_data and linkedin_data['about_html']:
                linkedin_files["about_html"] = linkedin_data['about_html']
                logger.info(f"✅ LinkedIn about_html content length: {len(linkedin_data['about_html'])} chars")
            else:
                logger.warning("⚠️ No about_html in linkedin_data")
                linkedin_files["about_html"] = None
                
            logger.info(f"✅ LinkedIn: {len([f for f in linkedin_files.values() if f])} files")
            
        except Exception as e:
            import traceback
            logger.error(f"❌ Lỗi LinkedIn: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            linkedin_files = {"about_html": None}
        
        # 7. Process Unternehmensregister results
        unternehmensregister_files = {}
        try:
            if 'jahresabschluss_html' in unternehmensregister_data and unternehmensregister_data['jahresabschluss_html']:
                unternehmensregister_files["jahresabschluss_html"] = unternehmensregister_data['jahresabschluss_html']
                logger.info(f"✅ Unternehmensregister jahresabschluss_html content length: {len(unternehmensregister_data['jahresabschluss_html'])} chars")
            else:
                logger.warning("⚠️ No jahresabschluss_html in unternehmensregister_data")
                unternehmensregister_files["jahresabschluss_html"] = None
                
            logger.info(f"✅ Unternehmensregister: {len([f for f in unternehmensregister_files.values() if f])} files")
            
        except Exception as e:
            import traceback
            logger.error(f"❌ Lỗi Unternehmensregister: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            unternehmensregister_files = {"jahresabschluss_html": None}
        
        # 8. Extract USt-IdNr from scrapers if not available
        extracted_ust_idnr = None
        if not final_ust_idnr:
            logger.info("🔍 Trying to extract USt-IdNr from scrapers...")
            
            # Try to extract from Handelsregister XML
            if handelsregister_files.get("xml"):
                import re
                xml_content = handelsregister_files["xml"]
                ust_match = re.search(r'DE\d{9}', xml_content)
                if ust_match:
                    extracted_ust_idnr = ust_match.group()
                    logger.info(f"✅ Found USt-IdNr in Handelsregister XML: {extracted_ust_idnr}")
            
            # Try to extract from Northdata HTML
            if not extracted_ust_idnr and northdata_files.get("html"):
                import re
                html_content = northdata_files["html"]
                ust_match = re.search(r'DE\d{9}', html_content)
                if ust_match:
                    extracted_ust_idnr = ust_match.group()
                    logger.info(f"✅ Found USt-IdNr in Northdata HTML: {extracted_ust_idnr}")
            
            # Try to extract from Unternehmensregister HTML
            if not extracted_ust_idnr and unternehmensregister_files.get("jahresabschluss_html"):
                import re
                html_content = unternehmensregister_files["jahresabschluss_html"]
                ust_match = re.search(r'DE\d{9}', html_content)
                if ust_match:
                    extracted_ust_idnr = ust_match.group()
                    logger.info(f"✅ Found USt-IdNr in Unternehmensregister HTML: {extracted_ust_idnr}")
        
        # 9. Combine all files by source
        all_files = {
            "handelsregister": handelsregister_files,
            "northdata": northdata_files,
            "linkedin": linkedin_files,
            "unternehmensregister": unternehmensregister_files
        }
        
        # Add extracted USt-IdNr to response if found
        if extracted_ust_idnr:
            all_files["extracted_ust_idnr"] = extracted_ust_idnr
        
        # 4. Create response
        response = CompanyResponse(
            company_name=request.company_name,
            registernummer=request.registernummer,
            files=all_files,
            success=True
        )
        
        logger.info(f"✅ Hoàn thành crawl: {request.company_name}")
        return response
        
    except Exception as e:
        error_response = CompanyResponse(
            company_name=request.company_name,
            registernummer=request.registernummer,
            files={
                "handelsregister": {"pdf": None, "xml": None},
                "northdata": {"html": None},
                "linkedin": {"about_html": None},
                "unternehmensregister": {"jahresabschluss_html": None}
            },
            success=False,
            error=str(e)
        )
        return error_response

if __name__ == "__main__":
    # Run server with increased timeout
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        timeout_keep_alive=3600,  # 60 minutes keep-alive timeout
        timeout_graceful_shutdown=60  # 60 seconds graceful shutdown
    )
