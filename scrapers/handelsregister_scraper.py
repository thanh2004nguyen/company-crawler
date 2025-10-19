"""
Handelsregister.de Scraper
Sử dụng Playwright để scrape dữ liệu từ handelsregister.de
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
import logging
import hashlib
import io
from typing import Dict
from playwright.sync_api import sync_playwright, Page
from utils import HandelsregisterXMLParser, PDFDataExtractor
# from models.company_model import CompanyData  # Removed - not needed

# Force UTF-8 encoding cho console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HandelsregisterScraper:
    """Scraper cho handelsregister.de sử dụng Playwright"""
    
    def __init__(self, headless: bool = False, language: str = 'FR'):
        self.search_url = "https://www.handelsregister.de/rp_web/normalesuche/welcome.xhtml"
        self.headless = headless
        self.language = language  # FR (French), DE (German), EN (English)
        self.xml_parser = HandelsregisterXMLParser()
        self.pdf_extractor = PDFDataExtractor()
        
    def scrape_company(self, company_name: str, registernummer: str, ust_idnr: str) -> Dict:
        """
        Scrape dữ liệu công ty từ handelsregister.de
        
        Args:
            company_name: Tên công ty
            registernummer: Số đăng ký (vd: "HRB182742")
            ust_idnr: Mã số thuế VAT
            
        Returns:
            Dict chứa dữ liệu đã scrape
        """
        logger.info(f"🚀 Bắt đầu scrape: {company_name}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page()
            
            try:
                # 1. Truy cập trang
                logger.info(f"🔗 Truy cập: {self.search_url}")
                page.goto(self.search_url, wait_until='networkidle')
                page.wait_for_timeout(2000)
                
                # 2. Chọn ngôn ngữ (luôn chọn)
                self._select_language(page)
                
                # 3. Điền form
                self._fill_search_form(page, company_name, registernummer)
                
                # 4. Click search
                self._click_search_button(page)
                
                # 5. Tạo thư mục lưu files
                download_dir = self._create_download_directory(company_name)
                logger.info(f"📁 Download directory: {download_dir}")
                
                # 6. LUÔN LUÔN CRAWL - Đợi và check kết quả tìm kiếm
                logger.info("⏱️  Đang đợi kết quả tìm kiếm...")
                page.wait_for_load_state('networkidle')
                page.wait_for_timeout(5000)
                
                # 7. Kiểm tra có kết quả
                if self._check_results_found(page):
                    logger.info("✅ Đã tìm thấy company - Bắt đầu download files (đè lên files cũ)")
                    
                    # 8. Download AD (PDF) và SI (XML) - Đè lên files cũ nếu có
                    self._download_documents(page, download_dir, registernummer)
                    
                    # 9. Extract data từ PDF (trước)
                    pdf_data = self._extract_pdf_data(download_dir, registernummer)
                    
                    # 10. Extract data từ XML (sau - override PDF)
                    xml_data = self._extract_xml_data(download_dir, registernummer)
                    
                    # 11. Combine data (XML override PDF vì có format tốt hơn)
                    data = {
                        'registernummer': registernummer,
                        'download_directory': download_dir,
                        **pdf_data,  # PDF data trước (backup)
                        **xml_data   # XML data sau (override - priority cao hơn)
                    }
                else:
                    logger.warning("❌ Không tìm thấy kết quả")
                    data = {
                        'registernummer': registernummer,
                        'download_directory': download_dir
                    }
                
                browser.close()
                return data
                
            except Exception as e:
                logger.error(f"❌ Lỗi: {str(e)}")
                browser.close()
                return {}
    
    def _select_language(self, page: Page):
        """Chọn ngôn ngữ từ dropdown menu"""
        try:
            logger.info(f"🌍 Chọn ngôn ngữ: {self.language}")
            
            # Hover để mở dropdown
            page.hover('li#localSubMenu')
            page.wait_for_timeout(1000)
            
            # Đợi menu hiển thị với timeout dài hơn
            try:
                page.wait_for_selector('ul.ui-menu-list[style*="display: block"]', state='visible', timeout=10000)
            except:
                logger.warning("⚠️  Dropdown menu không hiển thị, thử click trực tiếp")
            
            # Click ngôn ngữ
            language_id = self.language.lower()
            page.click(f'a#{language_id}', timeout=5000)
            
            # Đợi reload
            page.wait_for_load_state('networkidle', timeout=30000)
            page.wait_for_timeout(2000)
            
            logger.info(f"✅ Đã chọn ngôn ngữ: {self.language}")
        except Exception as e:
            logger.warning(f"⚠️  Không thể chọn ngôn ngữ: {str(e)}")
            logger.info("ℹ️  Tiếp tục với ngôn ngữ mặc định (German)")
    
    def _fill_search_form(self, page: Page, company_name: str, registernummer: str):
        """Điền form tìm kiếm"""
        try:
            register_type = self._get_register_type(registernummer)
            register_number = self._get_register_number(registernummer)
            
            logger.info(f"📝 Điền form: {company_name} - {register_type}{register_number}")
            
            # Điền tên công ty
            page.fill('textarea#form\\:schlagwoerter', company_name)
            page.wait_for_timeout(500)
            
            # Chọn loại register
            page.click('label#form\\:registerArt_label')
            page.wait_for_timeout(500)
            page.click(f'li[data-label="{register_type}"]')
            page.wait_for_timeout(500)
            
            # Điền số register
            page.fill('input#form\\:registerNummer', register_number)
            page.wait_for_timeout(500)
            
            logger.info("✅ Đã điền form xong")
        except Exception as e:
            logger.error(f"❌ Lỗi điền form: {str(e)}")
    
    def _click_search_button(self, page: Page):
        """Click nút tìm kiếm"""
        try:
            logger.info("🔍 Click nút tìm kiếm")
            
            # Thử nhiều selector khác nhau
            selectors = [
                'button#form\\:btnSuche',  # Button ID
                'span.ui-button-text:has-text("Suchen")',  # German
                'span.ui-button-text:has-text("Rechercher")',  # French
                'span.ui-button-text:has-text("Search")',  # English
                'button[type="submit"]',  # Generic submit
            ]
            
            clicked = False
            for selector in selectors:
                try:
                    locator = page.locator(selector)
                    count = locator.count()
                    if count > 0:
                        page.click(selector, timeout=3000)
                        logger.info(f"✅ Clicked button with selector: {selector}")
                        clicked = True
                        break
                except:
                    continue
            
            if not clicked:
                logger.error("❌ Không tìm thấy search button")
                
        except Exception as e:
            logger.error(f"❌ Lỗi click search: {str(e)}")
    
    def _check_results_found(self, page: Page) -> bool:
        """Kiểm tra có tìm thấy kết quả không"""
        try:
            results_table = page.query_selector('tr.ui-widget-content')
            if results_table:
                page_text = page.inner_text('body')
                if 'Amtsgericht' in page_text or 'HRB' in page_text:
                    return True
            return False
        except:
            return False
    
    def _get_register_type(self, registernummer: str) -> str:
        """Extract loại register"""
        types = ['HRB', 'HRA', 'GnR', 'PR', 'VR', 'GsR']
        for reg_type in types:
            if registernummer.startswith(reg_type):
                return reg_type
        return 'HRB'
    
    def _get_register_number(self, registernummer: str) -> str:
        """Extract số register"""
        for reg_type in ['HRB', 'HRA', 'GnR', 'PR', 'VR', 'GsR']:
            if registernummer.startswith(reg_type):
                return registernummer[len(reg_type):]
        return registernummer
    
    def _create_download_directory(self, company_name: str) -> str:
        """Tạo thư mục lưu files download - Lưu vào data/companies/"""
        import re
        # Tạo đường dẫn: data/companies/
        base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        download_dir = os.path.join(base_dir, 'companies')
        
        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(download_dir, exist_ok=True)
        
        logger.info(f"📁 Sử dụng thư mục: {download_dir}")
        return download_dir
    
    def _check_existing_files(self, download_dir: str, registernummer: str) -> bool:
        """Kiểm tra files đã tồn tại chưa"""
        try:
            pdf_path = os.path.join(download_dir, f"{registernummer}_AD.pdf")
            xml_path = os.path.join(download_dir, f"{registernummer}_SI.xml")
            
            # Kiểm tra PDF và XML
            pdf_exists = os.path.exists(pdf_path)
            xml_exists = os.path.exists(xml_path)
            
            if pdf_exists and xml_exists:
                logger.info(f"✅ Files đã tồn tại:")
                logger.info(f"  📄 PDF: {pdf_exists}")
                logger.info(f"  📄 XML: {xml_exists}")
                return True
            else:
                logger.info(f"❌ Files chưa đầy đủ:")
                logger.info(f"  📄 PDF: {pdf_exists}")
                logger.info(f"  📄 XML: {xml_exists}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Lỗi kiểm tra files: {str(e)}")
            return False
    
    def _check_files_changed(self, page: Page, download_dir: str, registernummer: str) -> bool:
        """Kiểm tra files mới có khác files cũ không bằng cách so sánh hash"""
        try:
            # Tạo temp directory
            temp_dir = os.path.join(download_dir, '.temp')
            os.makedirs(temp_dir, exist_ok=True)
            
            # Download files mới vào temp
            logger.info("📥 Downloading files mới để so sánh...")
            self._download_documents(page, temp_dir, registernummer)
            
            # So sánh hash
            pdf_changed = self._compare_file_hash(
                os.path.join(download_dir, f"{registernummer}_AD.pdf"),
                os.path.join(temp_dir, f"{registernummer}_AD.pdf")
            )
            
            xml_changed = self._compare_file_hash(
                os.path.join(download_dir, f"{registernummer}_SI.xml"),
                os.path.join(temp_dir, f"{registernummer}_SI.xml")
            )
            
            # Nếu có file nào thay đổi → move temp files sang main dir
            if pdf_changed or xml_changed:
                logger.info(f"📝 Files thay đổi: PDF={pdf_changed}, XML={xml_changed}")
                
                # Move files mới sang main directory
                if pdf_changed:
                    os.replace(
                        os.path.join(temp_dir, f"{registernummer}_AD.pdf"),
                        os.path.join(download_dir, f"{registernummer}_AD.pdf")
                    )
                if xml_changed:
                    os.replace(
                        os.path.join(temp_dir, f"{registernummer}_SI.xml"),
                        os.path.join(download_dir, f"{registernummer}_SI.xml")
                    )
                
                # Clean up temp
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
                
                return True
            else:
                # Clean up temp
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
                
                return False
                
        except Exception as e:
            logger.error(f"❌ Lỗi check files changed: {str(e)}")
            return False
    
    def _compare_file_hash(self, file1: str, file2: str) -> bool:
        """So sánh hash của 2 files, return True nếu khác nhau"""
        try:
            if not os.path.exists(file1) or not os.path.exists(file2):
                return True  # Nếu file không tồn tại → coi như khác
            
            hash1 = self._get_file_hash(file1)
            hash2 = self._get_file_hash(file2)
            
            return hash1 != hash2
            
        except:
            return True
    
    def _get_file_hash(self, filepath: str) -> str:
        """Tính MD5 hash của file"""
        try:
            md5_hash = hashlib.md5()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    md5_hash.update(chunk)
            return md5_hash.hexdigest()
        except:
            return ""
    
    def _download_documents(self, page: Page, download_dir: str, registernummer: str):
        """Download AD (PDF) và SI (XML)"""
        try:
            # Download AD (PDF)
            logger.info("📥 Downloading AD (PDF)...")
            pdf_path = self._download_ad_pdf(page, download_dir, registernummer)
            
            # Wait for download to complete
            page.wait_for_timeout(3000)
            
            # Reload trang để có thể download SI
            page.reload(wait_until='networkidle')
            page.wait_for_timeout(2000)
            
            # Download SI (XML)
            logger.info("📥 Downloading SI (XML)...")
            self._download_si_xml(page, download_dir, registernummer)
            
            logger.info("✅ Đã download xong tất cả documents")
            
        except Exception as e:
            logger.error(f"❌ Lỗi download documents: {str(e)}")
    
    def _download_ad_pdf(self, page: Page, download_dir: str, registernummer: str) -> str:
        """Click và download AD (PDF)"""
        try:
            # Setup download handler
            with page.expect_download() as download_info:
                # Click vào link AD với selector chính xác
                page.click('a[onclick*="Global.Dokumentart.AD"]')
                # Wait for form submission và download
                page.wait_for_timeout(5000)
            
            # Lưu file
            download = download_info.value
            pdf_path = os.path.join(download_dir, f"{registernummer}_AD.pdf")
            download.save_as(pdf_path)
            
            logger.info(f"✅ Đã lưu AD PDF: {pdf_path}")
            return pdf_path
            
        except Exception as e:
            logger.error(f"❌ Lỗi download AD: {str(e)}")
            return None
    
    def _download_si_xml(self, page: Page, download_dir: str, registernummer: str):
        """Click và download SI (XML)"""
        try:
            # Setup download handler
            with page.expect_download() as download_info:
                # Click vào link SI với selector chính xác
                page.click('a[onclick*="Global.Dokumentart.SI"]')
                # Wait for form submission và download
                page.wait_for_timeout(5000)
            
            # Lưu file
            download = download_info.value
            xml_path = os.path.join(download_dir, f"{registernummer}_SI.xml")
            download.save_as(xml_path)
            
            logger.info(f"✅ Đã lưu SI XML: {xml_path}")
            
        except Exception as e:
            logger.error(f"❌ Lỗi download SI: {str(e)}")
    
    def _extract_xml_data(self, download_dir: str, registernummer: str) -> Dict:
        """Extract data từ XML file"""
        try:
            xml_path = os.path.join(download_dir, f"{registernummer}_SI.xml")
            
            if not os.path.exists(xml_path):
                logger.warning(f"⚠️  XML file không tồn tại: {xml_path}")
                return {}
            
            logger.info(f"📊 Extracting data từ XML: {xml_path}")
            xml_data = self.xml_parser.parse_xml_file(xml_path)
            
            # Map XML fields sang CompanyData fields
            # CHỈ lấy các trường có trong CompanyData model (27 trường)
            company_data = {}
            
            # Map trực tiếp - CHỈ các trường trong model
            field_mapping = {
                'registernummer': 'registernummer',
                'handelsregister': 'handelsregister', 
                'geschaeftsfuehrer': 'geschaeftsfuehrer',
                'geschaeftsadresse': 'geschaeftsadresse',
                'unternehmenszweck': 'unternehmenszweck',
                'gruendungsdatum': 'gruendungsdatum',
                'land_des_hauptsitzes': 'land_des_hauptsitzes',
                'gerichtsstand': 'gerichtsstand',
                'paragraph_34_gewo': 'paragraph_34_gewo'
                # stammkapital KHÔNG có trong CompanyData model nên không lấy
                # letzte_eintragung, letzte_aenderung, abrufdatum cũng không có trong model
            }
            
            for xml_field, company_field in field_mapping.items():
                if xml_field in xml_data and xml_data[xml_field] is not None:
                    company_data[company_field] = xml_data[xml_field]
            
            logger.info(f"✅ Đã extract {len(company_data)} trường từ XML")
            return company_data
            
        except Exception as e:
            logger.error(f"❌ Lỗi extract XML data: {str(e)}")
            return {}
    
    def _extract_pdf_data(self, download_dir: str, registernummer: str) -> Dict:
        """Extract data từ PDF file"""
        try:
            pdf_path = os.path.join(download_dir, f"{registernummer}_AD.pdf")
            
            if not os.path.exists(pdf_path):
                logger.warning(f"⚠️  PDF file không tồn tại: {pdf_path}")
                return {}
            
            logger.info(f"📊 Extracting data từ PDF: {pdf_path}")
            pdf_data = self.pdf_extractor.extract_from_pdf(pdf_path)
            
            # Map PDF fields sang CompanyData fields
            # CHỈ lấy các trường có trong CompanyData model (27 trường)
            company_data = {}
            
            # Map trực tiếp (không override nếu XML đã có) - CHỈ các trường trong model
            field_mapping = {
                # PDF có thể backup cho các trường này nếu XML không có:
                'geschaeftsadresse': 'geschaeftsadresse',
                'unternehmenszweck': 'unternehmenszweck',
                'geschaeftsfuehrer': 'geschaeftsfuehrer',
                # 'gruendungsdatum': 'gruendungsdatum',  # KHÔNG lấy từ PDF vì không chính xác
                'handelsregister': 'handelsregister',
                'registernummer': 'registernummer'
                # KHÔNG lấy: stammkapital, letzte_eintragung, anzahl_eintragungen, gruendungsdatum
                # Vì không có trong model hoặc không chính xác
            }
            
            for pdf_field, company_field in field_mapping.items():
                if pdf_field in pdf_data and pdf_data[pdf_field] is not None:
                    # Chỉ add nếu chưa có từ XML (XML có priority cao hơn)
                    if company_field not in company_data or company_data.get(company_field) is None:
                        company_data[company_field] = pdf_data[pdf_field]
            
            logger.info(f"✅ Đã extract {len(company_data)} trường từ PDF")
            return company_data
            
        except Exception as e:
            logger.error(f"❌ Lỗi extract PDF data: {str(e)}")
            return {}


def test_from_companies_json(language: str = 'FR'):
    """Test scraper với data từ companies.json"""
    
    companies_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        'data', 
        'companies.json'
    )
    
    with open(companies_file, 'r', encoding='utf-8') as f:
        companies = json.load(f)
    
    if companies:
        company = companies[0]
        
        scraper = HandelsregisterScraper(headless=True, language=language)
        
        result = scraper.scrape_company(
            company['company_name'],
            company['registernummer'],
            company['ust_idnr']
        )
        
        print("\n" + "="*60)
        print("📊 KẾT QUẢ SCRAPE:")
        print("="*60)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("="*60)
    else:
        print("❌ Không có company trong companies.json")


if __name__ == "__main__":
    test_from_companies_json(language='FR')
