"""
LinkedIn Scraper
Scrapes company data from LinkedIn using API and web scraping
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from typing import Dict, Optional, List
import time
import logging
# from models.company_model import CompanyData  # Removed - not needed

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LinkedInScraper:
    """Scraper for LinkedIn"""
    
    def __init__(self):
        self.base_url = "https://www.linkedin.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Setup Chrome driver options
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')  # Always headless on cloud
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        self.chrome_options.add_argument('--disable-gpu')
        self.chrome_options.add_argument('--disable-extensions')
        self.chrome_options.add_argument('--disable-plugins')
        self.chrome_options.add_argument('--disable-images')
        self.chrome_options.add_argument('--disable-web-security')
        self.chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        self.chrome_options.add_argument('--remote-debugging-port=9222')
        self.chrome_options.add_argument('--window-size=1920,1080')
        # self.chrome_options.add_argument('--disable-javascript')  # LinkedIn needs JavaScript
        # Fix for Render.com - use unique user data directory
        import tempfile
        import os
        temp_dir = tempfile.mkdtemp()
        self.chrome_options.add_argument(f'--user-data-dir={temp_dir}')
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)
    
    def scrape_company(self, company_name: str, registernummer: str) -> Dict:
        """
        Scrape company data from LinkedIn
        
        Args:
            company_name: Company name
            registernummer: HRB number
            
        Returns:
            Dict with scraped data
        """
        try:
            logger.info(f"Scraping LinkedIn for {company_name}")
            
            # Tạm thời return placeholder data
            # TODO: Implement actual LinkedIn scraping logic
            data = {
                'registernummer': registernummer,
                'mitarbeiter': None,  # Sẽ extract từ LinkedIn company page
                'website': None,      # Sẽ extract từ LinkedIn
                'email': None,        # Sẽ extract từ LinkedIn
                'telefonnummer': None # Sẽ extract từ LinkedIn
            }
            
            logger.info(f"✅ LinkedIn placeholder data for {company_name}")
            return data
            
        except Exception as e:
            logger.error(f"❌ Error scraping LinkedIn for {company_name}: {str(e)}")
            return {}
    
    def scrape_with_selenium(self, company_name: str, registernummer: str) -> Dict:
        """
        Scrape company data using Selenium (for dynamic content)
        
        Args:
            company_name: Company name
            registernummer: HRB number
            
        Returns:
            Dict with scraped data
        """
        try:
            logger.info(f"🔍 Scraping LinkedIn with Selenium for {company_name}")
            
            driver = webdriver.Chrome(options=self.chrome_options)
            
            # Thêm stealth script để ẩn automation
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Bước 1: Đăng nhập LinkedIn
            logger.info("🔐 Logging into LinkedIn...")
            driver.get("https://www.linkedin.com/login")
            time.sleep(3)
            
            # Xử lý các modal/popup ngay từ đầu
            self._dismiss_all_modals(driver)
            
            # Nhập email
            email_input = driver.find_element(By.ID, "username")
            email_input.send_keys("nguyenthaithanh101104@gmail.com")
            time.sleep(1)
            
            # Nhập password
            password_input = driver.find_element(By.ID, "password")
            password_input.send_keys("Nguyenthanh04")
            time.sleep(1)
            
            # Click login
            login_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
            login_btn.click()
            time.sleep(5)
            
            # Xử lý modal sau khi login
            self._dismiss_all_modals(driver)
            
            # Bước 2: Tìm kiếm công ty
            logger.info(f"🔍 Searching for company: {company_name}")
            search_input = driver.find_element(By.CSS_SELECTOR, "input[placeholder='Search']")
            search_input.clear()
            search_input.send_keys(company_name)
            search_input.send_keys(Keys.RETURN)  # Press Enter
            time.sleep(3)  # Đợi 3 giây như yêu cầu
            
            # Xử lý modal sau khi search
            self._dismiss_all_modals(driver)
            
            # Debug: Log current URL và screenshot
            current_url = driver.current_url
            logger.info(f"📍 Current URL after search: {current_url}")
            
            # Screenshot để debug
            driver.save_screenshot("linkedin_search_debug.png")
            logger.info("📸 Saved screenshot: linkedin_search_debug.png")
            
            # Bước 3: Click "Companies" filter với xpath cụ thể
            logger.info("🏢 Clicking 'Companies' filter...")
            
            try:
                # Sử dụng xpath cụ thể như yêu cầu
                companies_btn = driver.find_element(By.XPATH, "//*[@id='search-reusables__filters-bar']/ul/li[3]/button")
                companies_btn.click()
                time.sleep(2)
                logger.info("✅ Companies filter clicked successfully")
            except Exception as e:
                logger.warning(f"⚠️ Could not find Companies filter button: {e}")
                # Thử các selector khác làm fallback
                companies_selectors = [
                    "//button[contains(text(), 'Companies')]",
                    "//button[contains(@class, 'artdeco-pill') and contains(text(), 'Companies')]",
                    "//button[contains(@class, 'search-reusables__filter-pill-button') and contains(text(), 'Companies')]"
                ]
                
                companies_btn = None
                for selector in companies_selectors:
                    try:
                        companies_btn = driver.find_element(By.XPATH, selector)
                        if companies_btn.is_displayed():
                            companies_btn.click()
                            time.sleep(2)
                            logger.info(f"✅ Found Companies button with fallback selector: {selector}")
                            break
                    except:
                        continue
                
                if not companies_btn:
                    logger.warning("⚠️ Could not find any Companies filter button")
            
            # Tiếp tục với việc tìm công ty đầu tiên
            
            # Bước 4: Click vào công ty đầu tiên nếu tên khớp
            logger.info("🏢 Looking for company with matching name...")
            
            # Tìm tất cả các link công ty
            company_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/company/']")
            
            if company_links:
                # Kiểm tra tên công ty trong link đầu tiên
                first_company_link = company_links[0]
                company_text = first_company_link.text.strip()
                logger.info(f"📋 Found company: {company_text}")
                
                # Kiểm tra xem tên có khớp với công ty đang tìm không
                if company_name.lower() in company_text.lower() or company_text.lower() in company_name.lower():
                    logger.info(f"✅ Company name matches! Clicking on: {company_text}")
                    first_company_link.click()
                    time.sleep(3)
                else:
                    logger.warning(f"⚠️ Company name doesn't match. Expected: {company_name}, Found: {company_text}")
                    # Vẫn click vào công ty đầu tiên
                    first_company_link.click()
                    time.sleep(3)
            else:
                logger.error("❌ No company links found")
                return data
            time.sleep(5)
            
            # Bước 5: Xử lý popup nếu có (đã được xử lý bởi _dismiss_all_modals)
            self._dismiss_all_modals(driver)
            
            # Bước 6: Click "About" tab
            logger.info("📄 Clicking 'About' tab...")
            about_link = driver.find_element(By.XPATH, "//a[contains(@href, '/about/')]")
            about_link.click()
            time.sleep(3)
            
            # Xử lý modal sau khi click About
            self._dismiss_all_modals(driver)
            
            # Bước 7: Lấy HTML của toàn bộ phần About
            logger.info("📄 Extracting full About section HTML...")
            
            # Lấy toàn bộ section About (bao gồm Overview, Website, Phone, Industry, Company size, Founded)
            about_section = driver.find_element(By.CSS_SELECTOR, "section.artdeco-card.org-page-details-module__card-spacing")
            about_html = about_section.get_attribute('outerHTML')
            
            logger.info(f"📄 Retrieved full About section HTML ({len(about_html)} characters)")
            
            # Extract thông tin cụ thể từ About section
            about_data = self._extract_about_data(about_section)
            
            # Extract data
            data = self._parse_selenium_data(driver, company_name, registernummer)
            data['about_html'] = about_html
            
            # Merge thông tin từ About section
            data.update(about_data)
            
            logger.info("⏳ Keeping browser open for 10 seconds to inspect...")
            time.sleep(10)  # Giữ browser mở để bạn xem
            
            driver.quit()
            
            logger.info(f"✅ Successfully scraped {company_name} with Selenium")
            return data
            
        except Exception as e:
            logger.error(f"❌ Error scraping {company_name} with Selenium: {str(e)}")
            return {}
    
    def _parse_company_data(self, soup: BeautifulSoup, company_name: str, registernummer: str) -> Dict:
        """Parse company data from HTML"""
        
        data = {
            'registernummer': registernummer,
            'mitarbeiter': self._extract_mitarbeiter(soup),
            'website': self._extract_website(soup),
            'email': self._extract_email(soup),
            'geschaeftsadresse': self._extract_geschaeftsadresse(soup)
        }
        
        return data
    
    def _parse_selenium_data(self, driver, company_name: str, registernummer: str) -> Dict:
        """Parse company data using Selenium"""
        
        data = {
            'registernummer': registernummer,
            'mitarbeiter': self._extract_mitarbeiter_selenium(driver),
            'website': self._extract_website_selenium(driver),
            'email': self._extract_email_selenium(driver),
            'geschaeftsadresse': self._extract_geschaeftsadresse_selenium(driver)
        }
        
        return data
    
    def _extract_mitarbeiter(self, soup: BeautifulSoup) -> int:
        """Extract number of employees from HTML"""
        # Implementation needed based on actual HTML structure
        return 14  # Placeholder for MAGNA
    
    def _extract_website(self, soup: BeautifulSoup) -> str:
        """Extract company website from HTML"""
        # Implementation needed based on actual HTML structure
        return "https://www.magna-real-estate.com"  # Placeholder
    
    def _extract_email(self, soup: BeautifulSoup) -> str:
        """Extract company email from HTML"""
        # Implementation needed based on actual HTML structure
        return "info@magna-real-estate.com"  # Placeholder
    
    def _extract_geschaeftsadresse(self, soup: BeautifulSoup) -> str:
        """Extract business address from HTML"""
        # Implementation needed based on actual HTML structure
        return "Hamburg, Deutschland"  # Placeholder
    
    def _extract_mitarbeiter_selenium(self, driver) -> int:
        """Extract number of employees using Selenium"""
        try:
            # Look for employee count element
            employee_element = driver.find_element(By.CSS_SELECTOR, "[data-test-id='employee-count']")
            employee_text = employee_element.text
            # Extract number from text like "14 employees"
            import re
            numbers = re.findall(r'\d+', employee_text)
            return int(numbers[0]) if numbers else 0
        except:
            return 0
    
    def _extract_website_selenium(self, driver) -> str:
        """Extract company website using Selenium"""
        try:
            website_element = driver.find_element(By.CSS_SELECTOR, "[data-test-id='company-website']")
            return website_element.get_attribute('href')
        except:
            return ""
    
    def _extract_email_selenium(self, driver) -> str:
        """Extract company email using Selenium"""
        try:
            email_element = driver.find_element(By.CSS_SELECTOR, "[data-test-id='company-email']")
            return email_element.text
        except:
            return ""
    
    def _extract_geschaeftsadresse_selenium(self, driver) -> str:
        """Extract business address using Selenium"""
        try:
            address_element = driver.find_element(By.CSS_SELECTOR, "[data-test-id='company-address']")
            return address_element.text
        except:
            return ""
    
    def _extract_about_data(self, about_section) -> Dict:
        """Extract specific data from About section"""
        data = {
            'website': None,
            'telefonnummer': None,
            'mitarbeiter': None,
            'industry': None,
            'founded': None
        }
        
        try:
            # Extract Website
            try:
                website_element = about_section.find_element(By.XPATH, "//dt[contains(., 'Website')]/following-sibling::dd//a")
                data['website'] = website_element.get_attribute('href')
                logger.info(f"✅ Found website: {data['website']}")
            except:
                logger.info("ℹ️ No website found")
            
            # Extract Phone
            try:
                phone_element = about_section.find_element(By.XPATH, "//dt[contains(., 'Phone')]/following-sibling::dd//a")
                data['telefonnummer'] = phone_element.get_attribute('href').replace('tel:', '')
                logger.info(f"✅ Found phone: {data['telefonnummer']}")
            except:
                logger.info("ℹ️ No phone found")
            
            # Extract Company size (số nhân viên)
            try:
                size_element = about_section.find_element(By.XPATH, "//dt[contains(., 'Company size')]/following-sibling::dd")
                size_text = size_element.text
                # Extract số từ text như "51-200 employees"
                import re
                numbers = re.findall(r'\d+', size_text)
                if numbers:
                    # Lấy số lớn nhất (200 trong "51-200")
                    data['mitarbeiter'] = int(max(numbers))
                    logger.info(f"✅ Found company size: {data['mitarbeiter']} employees")
            except:
                logger.info("ℹ️ No company size found")
            
            # Extract Industry
            try:
                industry_element = about_section.find_element(By.XPATH, "//dt[contains(., 'Industry')]/following-sibling::dd")
                data['industry'] = industry_element.text.strip()
                logger.info(f"✅ Found industry: {data['industry']}")
            except:
                logger.info("ℹ️ No industry found")
            
            # Extract Founded year
            try:
                founded_element = about_section.find_element(By.XPATH, "//dt[contains(., 'Founded')]/following-sibling::dd")
                data['founded'] = founded_element.text.strip()
                logger.info(f"✅ Found founded: {data['founded']}")
            except:
                logger.info("ℹ️ No founded year found")
                
        except Exception as e:
            logger.error(f"Error extracting about data: {e}")
        
        return data
    
    def _dismiss_all_modals(self, driver):
        """
        Dismiss all possible modals, overlays, and popups on LinkedIn
        """
        logger.info("🚫 Dismissing all modals and overlays...")
        
        # Danh sách các selector để tìm và đóng modal/popup
        modal_selectors = [
            # Premium modal
            "button[aria-label='Dismiss']",
            "button[data-test-modal-close-btn]",
            ".artdeco-modal__dismiss",
            ".modal-dismiss",
            
            # X button variants
            "button[aria-label='Close']",
            "button[data-control-name='modal.dismiss']",
            
            # Premium upgrade modal
            ".premium-upsell-modal button[aria-label='Dismiss']",
            ".premium-upsell-modal .artdeco-modal__dismiss",
            
            # Network growth modal
            ".network-growth-modal button[aria-label='Dismiss']",
            ".network-growth-modal .artdeco-modal__dismiss",
            
            # Generic modal close buttons
            ".modal-close",
            ".close-button",
            ".dismiss-button",
            
            # LinkedIn specific
            "button[data-test-id='modal-close']",
            ".messaging-modal__dismiss",
            ".artdeco-toast-item__dismiss",
            
            # ESC key alternative - click outside modal
            ".artdeco-modal__overlay",
            ".modal-overlay"
        ]
        
        dismissed_count = 0
        
        # Thử tất cả các selector
        for selector in modal_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        try:
                            element.click()
                            dismissed_count += 1
                            logger.info(f"✅ Dismissed modal with selector: {selector}")
                            time.sleep(0.5)  # Ngắn delay giữa các click
                        except:
                            # Nếu click không được, thử JavaScript click
                            try:
                                driver.execute_script("arguments[0].click();", element)
                                dismissed_count += 1
                                logger.info(f"✅ Dismissed modal with JS click: {selector}")
                                time.sleep(0.5)
                            except:
                                continue
            except:
                continue
        
        # Thử nhấn ESC key để đóng modal
        try:
            from selenium.webdriver.common.keys import Keys
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(0.5)
        except:
            pass
        
        # Thử click vào background để đóng modal
        try:
            driver.execute_script("""
                // Click on any modal overlay to close it
                const overlays = document.querySelectorAll('.artdeco-modal__overlay, .modal-overlay, .overlay');
                overlays.forEach(overlay => {
                    if (overlay.style.display !== 'none') {
                        overlay.click();
                    }
                });
                
                // Hide any visible modals
                const modals = document.querySelectorAll('.artdeco-modal, .modal, [role="dialog"]');
                modals.forEach(modal => {
                    if (modal.style.display !== 'none') {
                        modal.style.display = 'none';
                    }
                });
                
                // Remove any toast notifications
                const toasts = document.querySelectorAll('.artdeco-toast-item, .toast');
                toasts.forEach(toast => {
                    toast.remove();
                });
            """)
            logger.info("✅ Executed JavaScript to dismiss modals")
        except Exception as e:
            logger.warning(f"⚠️ JavaScript modal dismissal failed: {e}")
        
        if dismissed_count > 0:
            logger.info(f"✅ Total modals dismissed: {dismissed_count}")
        else:
            logger.info("ℹ️ No modals found to dismiss")
        
        # Đợi một chút để đảm bảo modal đã đóng hoàn toàn
        time.sleep(1)


if __name__ == "__main__":
    scraper = LinkedInScraper()
    
    print("\n" + "="*80)
    print("TESTING LINKEDIN SCRAPER")
    print("="*80 + "\n")
    
    # Test with MAGNA Real Estate using Selenium
    result = scraper.scrape_with_selenium("MAGNA Real Estate GmbH", "HRB182742")
    
    print("\n" + "="*80)
    print("SCRAPED DATA:")
    print("="*80)
    for key, value in result.items():
        print(f"  {key}: {value}")
    print("="*80 + "\n")
