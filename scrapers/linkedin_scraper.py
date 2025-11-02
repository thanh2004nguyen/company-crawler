"""
LinkedIn Scraper
Scrapes company data from LinkedIn using Playwright with session/cookie management
"""

import sys
from pathlib import Path
import os
import json
import time
import logging
from typing import Dict, Optional, List, Tuple

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LinkedInScraper:
    """Scraper for LinkedIn using Playwright with session management"""
    
    def __init__(self, headless: bool = True):
        self.base_url = "https://www.linkedin.com"
        self.headless = headless
        
        # Session storage path
        session_dir = Path("data/linkedin_session")
        session_dir.mkdir(parents=True, exist_ok=True)
        self.session_storage_path = session_dir / "context_storage.json"
        
        logger.info(f"🔧 LinkedIn Scraper initialized (headless={headless})")
        logger.info(f"📁 Session storage: {self.session_storage_path}")
    
    def _save_context_storage(self, context: BrowserContext):
        """Lưu context storage state (cookies, localStorage) vào file"""
        try:
            storage_state = context.storage_state()
            with open(self.session_storage_path, 'w', encoding='utf-8') as f:
                json.dump(storage_state, f, indent=2)
            logger.info(f"✅ Đã lưu session/cookies vào {self.session_storage_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Lỗi khi lưu session: {e}")
            return False
    
    def _load_context_storage(self) -> Optional[Dict]:
        """Load context storage state từ file nếu có"""
        if not self.session_storage_path.exists():
            logger.info("ℹ️ Chưa có session được lưu, cần đăng nhập mới")
            return None
        
        try:
            with open(self.session_storage_path, 'r', encoding='utf-8') as f:
                storage_state = json.load(f)
            logger.info(f"✅ Đã load session từ {self.session_storage_path}")
            return storage_state
        except Exception as e:
            logger.warning(f"⚠️ Không thể load session: {e}")
            return None
    
    def _setup_browser_context(self, playwright, load_session: bool = True) -> Tuple[Browser, BrowserContext]:
        """Setup browser và context với session nếu có"""
        browser = playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
            ]
        )
        
        # Load session nếu có
        storage_state = None
        if load_session:
            storage_state = self._load_context_storage()
        
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='Europe/Berlin',
            storage_state=storage_state,
            ignore_https_errors=False,
        )
        
        # Thêm stealth script
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        return browser, context
    
    def wait_for_manual_login(self, page: Page, first_time: bool = True) -> bool:
        """
        Mở trang đăng nhập và chờ user đăng nhập thủ công
        User sẽ đăng nhập và nhấn Enter để báo hiệu đã xong
        """
        # Chỉ navigate đến login page nếu là lần đầu hoặc đang ở trang khác
        if first_time:
            logger.info("🔐 Đang mở trang đăng nhập LinkedIn...")
            logger.info("📋 Vui lòng đăng nhập thủ công trong browser")
            logger.info("⏳ Sau khi đăng nhập thành công, nhấn ENTER trong terminal này...")
            
            try:
                page.goto(f"{self.base_url}/login", wait_until='networkidle', timeout=30000)
            except Exception as e:
                # Nếu có lỗi navigation (có thể đang redirect), đợi một chút
                logger.info("⏳ Đang chờ page load...")
                page.wait_for_timeout(2000)
        
        # Chờ user đăng nhập và nhấn Enter
        input("\n✅ Nhấn ENTER sau khi đã đăng nhập thành công...\n")
        
        # Đợi một chút để đảm bảo page đã load xong
        page.wait_for_timeout(2000)
        
        # Kiểm tra xem đã đăng nhập chưa bằng cách check URL và elements
        current_url = page.url
        logger.info(f"📍 Current URL: {current_url}")
        
        # Check xem có đăng nhập thành công không
        # LinkedIn sẽ redirect về /feed/ hoặc homepage sau khi đăng nhập
        is_logged_in_by_url = (
            '/feed' in current_url or 
            '/in/' in current_url or
            (self.base_url in current_url and '/login' not in current_url and current_url != f"{self.base_url}/")
        )
        
        # Kiểm tra thêm bằng cách tìm elements chỉ xuất hiện khi đã đăng nhập
        is_logged_in_by_elements = False
        try:
            # Tìm search box (chỉ có khi đã đăng nhập)
            search_box = page.locator("input[placeholder='Search']")
            if search_box.is_visible(timeout=3000):
                is_logged_in_by_elements = True
                logger.info("✅ Tìm thấy search box - đã đăng nhập")
        except:
            pass
        
        is_logged_in = is_logged_in_by_url or is_logged_in_by_elements
        
        # Nếu vẫn ở trang login, có thể user chưa đăng nhập xong
        if '/login' in current_url and not is_logged_in:
            logger.warning("⚠️ Có vẻ bạn vẫn ở trang login.")
            logger.info("💡 Hãy đảm bảo bạn đã đăng nhập thành công trong browser.")
            logger.info("❓ Bạn có muốn thử lại? (y/n)")
            retry = input().strip().lower()
            if retry == 'y':
                # Không navigate lại, chỉ đợi user nhấn Enter
                return self.wait_for_manual_login(page, first_time=False)
            return False
        
        logger.info("✅ Đã đăng nhập thành công!")
        return True
    
    def test_session_incognito(self, headless: bool = False) -> bool:
        """
        Test session bằng cách mở tab ẩn danh (incognito) - KHÔNG dùng browser cache/cookies
        Chỉ dùng cookies từ session file đã lưu
        Nếu session hoạt động, sẽ tự động đăng nhập
        """
        logger.info("🧪 Testing session với incognito mode (tab ẩn danh)...")
        logger.info("💡 Browser sẽ mở để bạn có thể xem - KHÔNG dùng cache/cookies của browser")
        
        # Temporarily set headless để user có thể xem
        original_headless = self.headless
        self.headless = headless
        
        with sync_playwright() as playwright:
            # Tạo browser MỚI - không load session vào context chính
            browser = playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                ]
            )
            
            # Load session từ file
            storage_state = self._load_context_storage()
            if not storage_state:
                logger.error("❌ Không tìm thấy session file. Cần đăng nhập trước!")
                self.headless = original_headless
                return False
            
            logger.info("📁 Đã load cookies từ session file")
            logger.info(f"🍪 Số lượng cookies: {len(storage_state.get('cookies', []))}")
            
            # Tạo INCOGNITO context - KHÔNG dùng browser cache/localStorage
            # Chỉ dùng cookies từ session file
            incognito_context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='Europe/Berlin',
                # KHÔNG load storage_state ở đây - chỉ add cookies thủ công
                ignore_https_errors=False,
            )
            
            # Thêm stealth script
            incognito_context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            # Load CHỈ cookies từ session file (không dùng localStorage/cache)
            cookies = storage_state.get('cookies', [])
            if cookies:
                # Set cookies vào incognito context
                incognito_context.add_cookies(cookies)
                logger.info(f"✅ Đã thêm {len(cookies)} cookies vào incognito context")
            
            page = incognito_context.new_page()
            
            try:
                logger.info("🔍 Đang truy cập LinkedIn (incognito mode)...")
                logger.info("⏳ Vui lòng quan sát browser - nếu thấy đã đăng nhập thì session hoạt động!")
                
                # Dùng domcontentloaded thay vì networkidle để tránh timeout
                page.goto(self.base_url, wait_until='domcontentloaded', timeout=60000)
                page.wait_for_timeout(3000)  # Đợi thêm một chút để LinkedIn redirect nếu cần
                
                current_url = page.url
                logger.info(f"📍 Current URL: {current_url}")
                
                # Kiểm tra xem có đăng nhập thành công không
                is_logged_in = False
                
                # Check URL
                if '/login' not in current_url:
                    is_logged_in = True
                
                # Check thêm bằng cách tìm search box
                try:
                    search_box = page.locator("input[placeholder='Search']")
                    if search_box.is_visible(timeout=3000):
                        is_logged_in = True
                        logger.info("✅ Tìm thấy search box - đã đăng nhập!")
                except:
                    pass
                
                if is_logged_in:
                    logger.info("=" * 60)
                    logger.info("✅ SUCCESS! Session hoạt động trong incognito mode!")
                    logger.info("✅ Điều này chứng tỏ cookies từ session file hoạt động")
                    logger.info("✅ KHÔNG dùng cache/cookies từ browser")
                    logger.info("=" * 60)
                    logger.info("💡 Browser sẽ mở thêm 5 giây để bạn xác nhận...")
                    page.wait_for_timeout(5000)
                    return True
                else:
                    logger.warning("=" * 60)
                    logger.warning("❌ Session không hoạt động - vẫn ở trang login")
                    logger.warning("⚠️ Có thể cookies đã hết hạn hoặc không hợp lệ")
                    logger.warning("=" * 60)
                    logger.info("💡 Browser sẽ mở thêm 3 giây để bạn xác nhận...")
                    page.wait_for_timeout(3000)
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Lỗi khi test session: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return False
            finally:
                browser.close()
                self.headless = original_headless
    
    def setup_login_session(self, headless: bool = False) -> bool:
        """
        Setup login session: mở browser không headless để user đăng nhập
        Sau đó lưu session/cookies để dùng lại
        """
        logger.info("🔧 Setting up LinkedIn login session...")
        
        # Temporarily set headless to False để user có thể đăng nhập
        original_headless = self.headless
        self.headless = headless
        
        should_test = False
        
        with sync_playwright() as playwright:
            browser, context = self._setup_browser_context(playwright, load_session=False)
            page = context.new_page()
            
            try:
                # Chờ user đăng nhập
                if self.wait_for_manual_login(page):
                    # Lưu session sau khi đăng nhập
                    if self._save_context_storage(context):
                        logger.info("✅ Đã lưu session thành công!")
                        
                        # Hỏi user có muốn test không (trước khi đóng context)
                        logger.info("\n🧪 Bạn có muốn test session với incognito mode không? (y/n)")
                        test_choice = input().strip().lower()
                        should_test = (test_choice == 'y')
                        
                        # Đóng browser trước khi ra khỏi context
                        browser.close()
                        # Context sẽ được đóng khi ra khỏi 'with' block
                    else:
                        logger.error("❌ Không thể lưu session")
                        self.headless = original_headless
                        return False
                else:
                    logger.error("❌ Đăng nhập không thành công")
                    self.headless = original_headless
                    return False
                    
            except KeyboardInterrupt:
                logger.info("⚠️ Đã hủy bởi user")
                self.headless = original_headless
                return False
            finally:
                # Đảm bảo browser được đóng
                try:
                    browser.close()
                except:
                    pass
        
        # Sau khi đã ra khỏi playwright context hoàn toàn, mới test
        if should_test:
            self.test_session_incognito(headless=headless)  # Dùng cùng headless mode
        
        self.headless = original_headless
        return True
    
    def scrape_with_playwright(self, company_name: str, registernummer: str) -> Dict:
        """
        Scrape company data using Playwright với session đã lưu
        
        Args:
            company_name: Company name
            registernummer: HRB number
            
        Returns:
            Dict with scraped data
        """
        try:
            logger.info(f"🔍 Scraping LinkedIn with Playwright for {company_name}")
            
            data = {
                'registernummer': registernummer,
                'mitarbeiter': None,
                'website': None,
                'email': None,
                'telefonnummer': None,
                'about_html': None
            }
            
            with sync_playwright() as playwright:
                browser, context = self._setup_browser_context(playwright, load_session=True)
                page = context.new_page()
                
                try:
                    # Kiểm tra xem có session không, nếu không cần đăng nhập
                    logger.info("🔍 Đang kiểm tra session...")
                    page.goto(self.base_url, wait_until='domcontentloaded', timeout=60000)
                    page.wait_for_timeout(2000)  # Đợi redirect nếu có
                    current_url = page.url
                    logger.info(f"📍 Current URL: {current_url}")
                    
                    # Kiểm tra đăng nhập bằng URL và search box
                    is_logged_in = '/login' not in current_url
                    if not is_logged_in:
                        # Check thêm bằng search box
                        try:
                            search_box = page.locator("input[placeholder='Search']")
                            if search_box.is_visible(timeout=3000):
                                is_logged_in = True
                                logger.info("✅ Tìm thấy search box - đã đăng nhập")
                        except:
                            pass
                    
                    if not is_logged_in:
                        logger.warning("⚠️ Chưa có session hoặc session đã hết hạn. Cần đăng nhập.")
                        logger.info("💡 Chạy: python scrapers/linkedin_scraper.py -> chọn option 1 để đăng nhập")
                        logger.info("💡 Hoặc chạy: scraper.setup_login_session(headless=False)")
                        return data
                    
                    logger.info("✅ Session hoạt động, bắt đầu scrape...")
                    
                    # Bước 1: Tìm kiếm công ty
                    logger.info(f"🔍 Searching for company: {company_name}")
                    try:
                        search_input = page.locator("input[placeholder='Search']")
                        if not search_input.is_visible(timeout=5000):
                            logger.warning("⚠️ Không tìm thấy search box, có thể cần đợi thêm...")
                            page.wait_for_timeout(2000)
                            search_input = page.locator("input[placeholder='Search']")
                        
                        search_input.fill(company_name)
                        search_input.press('Enter')
                        logger.info("✅ Đã gửi search query")
                        page.wait_for_timeout(3000)
                    except Exception as e:
                        logger.error(f"❌ Lỗi khi search: {e}")
                        return data
                    
                    # Xử lý modal
                    self._dismiss_all_modals(page)
                    
                    # Bước 2: Click "Companies" filter
                    logger.info("🏢 Clicking 'Companies' filter...")
                    try:
                        companies_btn = page.locator("//*[@id='search-reusables__filters-bar']/ul/li[3]/button")
                        if companies_btn.is_visible(timeout=5000):
                            companies_btn.click()
                            page.wait_for_timeout(2000)
                            logger.info("✅ Companies filter clicked")
                    except Exception as e:
                        logger.warning(f"⚠️ Could not find Companies filter: {e}")
                        # Fallback selectors
                        fallback_selectors = [
                            "button:has-text('Companies')",
                            "button.artdeco-pill:has-text('Companies')",
                        ]
                        for selector in fallback_selectors:
                            try:
                                btn = page.locator(selector).first
                                if btn.is_visible(timeout=2000):
                                    btn.click()
                                    page.wait_for_timeout(2000)
                                    logger.info(f"✅ Found Companies button with fallback: {selector}")
                                    break
                            except:
                                continue
                    
                    # Bước 3: Click vào công ty đầu tiên
                    logger.info("🏢 Looking for company with matching name...")
                    company_links = page.locator("a[href*='/company/']")
                    
                    if company_links.count() > 0:
                        first_link = company_links.first
                        company_text = first_link.inner_text().strip()
                        logger.info(f"📋 Found company: {company_text}")
                        
                        # Kiểm tra tên có khớp không
                        if company_name.lower() in company_text.lower() or company_text.lower() in company_name.lower():
                            logger.info(f"✅ Company name matches! Clicking on: {company_text}")
                        else:
                            logger.warning(f"⚠️ Company name doesn't match. Expected: {company_name}, Found: {company_text}")
                        
                        first_link.click()
                        page.wait_for_timeout(3000)
                        self._dismiss_all_modals(page)
                    else:
                        logger.error("❌ No company links found")
                        return data
                    
                    # Bước 4: Click "About" tab
                    logger.info("📄 Clicking 'About' tab...")
                    # Có 2 About links, dùng selector cụ thể hơn hoặc .first
                    try:
                        # Thử tìm link trong navigation menu trước (tab chính)
                        about_link = page.locator("a[href*='/about/'][class*='org-page-navigation']").first
                        if about_link.is_visible(timeout=5000):
                            about_link.click()
                            logger.info("✅ Clicked About tab (navigation)")
                            page.wait_for_timeout(3000)
                            self._dismiss_all_modals(page)
                        else:
                            # Fallback: dùng link đầu tiên
                            about_link = page.locator("a[href*='/about/']").first
                            if about_link.is_visible(timeout=3000):
                                about_link.click()
                                logger.info("✅ Clicked About tab (fallback)")
                                page.wait_for_timeout(3000)
                                self._dismiss_all_modals(page)
                            else:
                                logger.warning("⚠️ Could not find About tab")
                    except Exception as e:
                        logger.warning(f"⚠️ Error clicking About tab: {e}")
                        # Fallback: thử dùng .first
                        try:
                            about_link = page.locator("a[href*='/about/']").first
                            about_link.click()
                            logger.info("✅ Clicked About tab (fallback 2)")
                            page.wait_for_timeout(3000)
                            self._dismiss_all_modals(page)
                        except Exception as e2:
                            logger.error(f"❌ Could not click About tab: {e2}")
                    
                    # Bước 5: Extract About section HTML
                    logger.info("📄 Extracting full About section HTML...")
                    about_section = page.locator("section.artdeco-card.org-page-details-module__card-spacing")
                    
                    if about_section.is_visible(timeout=5000):
                        about_html = about_section.inner_html()
                        data['about_html'] = about_html
                        logger.info(f"📄 Retrieved About section HTML ({len(about_html)} characters)")
                        
                        # Extract specific data từ About section
                        about_data = self._extract_about_data_playwright(about_section)
                        data.update(about_data)
                    else:
                        logger.warning("⚠️ Could not find About section")
                    
                    logger.info(f"✅ Successfully scraped {company_name}")
                    return data
                    
                except Exception as e:
                    logger.error(f"❌ Error during scraping: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    return data
                finally:
                    browser.close()
                    
        except Exception as e:
            logger.error(f"❌ Error scraping {company_name} with Playwright: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {}
    
    def _extract_about_data_playwright(self, about_section) -> Dict:
        """Extract specific data from About section using Playwright"""
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
                website_locator = about_section.locator("//dt[contains(., 'Website')]/following-sibling::dd//a")
                if website_locator.is_visible(timeout=2000):
                    data['website'] = website_locator.get_attribute('href')
                    logger.info(f"✅ Found website: {data['website']}")
            except:
                logger.info("ℹ️ No website found")
            
            # Extract Phone
            try:
                phone_locator = about_section.locator("//dt[contains(., 'Phone')]/following-sibling::dd//a")
                if phone_locator.is_visible(timeout=2000):
                    phone_href = phone_locator.get_attribute('href')
                    if phone_href:
                        data['telefonnummer'] = phone_href.replace('tel:', '')
                        logger.info(f"✅ Found phone: {data['telefonnummer']}")
            except:
                logger.info("ℹ️ No phone found")
            
            # Extract Company size (số nhân viên)
            try:
                size_locator = about_section.locator("//dt[contains(., 'Company size')]/following-sibling::dd")
                if size_locator.is_visible(timeout=2000):
                    size_text = size_locator.inner_text()
                    import re
                    numbers = re.findall(r'\d+', size_text)
                    if numbers:
                        data['mitarbeiter'] = int(max(numbers))
                        logger.info(f"✅ Found company size: {data['mitarbeiter']} employees")
            except:
                logger.info("ℹ️ No company size found")
            
            # Extract Industry
            try:
                industry_locator = about_section.locator("//dt[contains(., 'Industry')]/following-sibling::dd")
                if industry_locator.is_visible(timeout=2000):
                    data['industry'] = industry_locator.inner_text().strip()
                    logger.info(f"✅ Found industry: {data['industry']}")
            except:
                logger.info("ℹ️ No industry found")
            
            # Extract Founded year
            try:
                founded_locator = about_section.locator("//dt[contains(., 'Founded')]/following-sibling::dd")
                if founded_locator.is_visible(timeout=2000):
                    data['founded'] = founded_locator.inner_text().strip()
                    logger.info(f"✅ Found founded: {data['founded']}")
            except:
                logger.info("ℹ️ No founded year found")
                
        except Exception as e:
            logger.error(f"Error extracting about data: {e}")
        
        return data
    
    def _dismiss_all_modals(self, page: Page):
        """Dismiss all possible modals, overlays, and popups on LinkedIn"""
        logger.info("🚫 Dismissing all modals and overlays...")
        
        modal_selectors = [
            "button[aria-label='Dismiss']",
            "button[data-test-modal-close-btn]",
            ".artdeco-modal__dismiss",
            "button[aria-label='Close']",
            "button[data-control-name='modal.dismiss']",
            ".premium-upsell-modal button[aria-label='Dismiss']",
            ".network-growth-modal button[aria-label='Dismiss']",
            "button[data-test-id='modal-close']",
            ".artdeco-toast-item__dismiss",
        ]
        
        dismissed_count = 0
        
        for selector in modal_selectors:
            try:
                elements = page.locator(selector)
                count = elements.count()
                for i in range(count):
                    element = elements.nth(i)
                    if element.is_visible(timeout=500):
                        try:
                            element.click()
                            dismissed_count += 1
                            logger.info(f"✅ Dismissed modal: {selector}")
                            page.wait_for_timeout(500)
                        except:
                            continue
            except:
                continue
        
        # JavaScript để đóng modal
        try:
            page.evaluate("""
                () => {
                    const overlays = document.querySelectorAll('.artdeco-modal__overlay, .modal-overlay');
                    overlays.forEach(overlay => {
                        if (overlay.style.display !== 'none') {
                            overlay.click();
                        }
                    });
                    
                    const modals = document.querySelectorAll('.artdeco-modal, .modal, [role="dialog"]');
                    modals.forEach(modal => {
                        if (modal.style.display !== 'none') {
                            modal.style.display = 'none';
                        }
                    });
                    
                    const toasts = document.querySelectorAll('.artdeco-toast-item, .toast');
                    toasts.forEach(toast => toast.remove());
                }
            """)
            logger.info("✅ Executed JavaScript to dismiss modals")
        except Exception as e:
            logger.warning(f"⚠️ JavaScript modal dismissal failed: {e}")
        
        if dismissed_count > 0:
            logger.info(f"✅ Total modals dismissed: {dismissed_count}")
        else:
            logger.info("ℹ️ No modals found to dismiss")
        
        page.wait_for_timeout(1000)
    
    # Compatibility method - giữ lại tên cũ để server.py không bị lỗi
    def scrape_with_selenium(self, company_name: str, registernummer: str) -> Dict:
        """Alias for scrape_with_playwright - để tương thích với code cũ"""
        return self.scrape_with_playwright(company_name, registernummer)
    
    def scrape_company(self, company_name: str, registernummer: str) -> Dict:
        """Placeholder method"""
        return self.scrape_with_playwright(company_name, registernummer)


if __name__ == "__main__":
    import sys
    
    # Nếu có arguments từ command line, dùng để scrape
    if len(sys.argv) > 1:
        # Mode: scrape với arguments
        # Usage: python scrapers/linkedin_scraper.py "Company Name" "HRB123456"
        company_name = sys.argv[1] if len(sys.argv) > 1 else "MAGNA Real Estate GmbH"
        registernummer = sys.argv[2] if len(sys.argv) > 2 else "HRB182742"
        # Mặc định headless=False để user có thể xem browser
        headless = sys.argv[3].lower() == 'true' if len(sys.argv) > 3 else False
        
        scraper = LinkedInScraper(headless=headless)
        
        print("\n" + "="*80)
        print(f"LINKEDIN SCRAPER - SCRAPING: {company_name}")
        print("="*80 + "\n")
        
        result = scraper.scrape_with_playwright(company_name, registernummer)
        
        print("\n" + "="*80)
        print("SCRAPED DATA:")
        print("="*80)
        for key, value in result.items():
            if key == 'about_html':
                if value:
                    print(f"\n{key}:")
                    print(f"  Length: {len(str(value))} characters")
                    print(f"  Preview: {str(value)[:200]}...")
                else:
                    print(f"{key}: None")
            else:
                print(f"{key}: {value}")
        print("="*80 + "\n")
    else:
        # Mode: Interactive menu (cho setup/test)
        scraper = LinkedInScraper(headless=False)  # Non-headless để test
        
        print("\n" + "="*80)
        print("LINKEDIN SCRAPER - SETUP & TEST")
        print("="*80 + "\n")
        
        print("Chọn chức năng:")
        print("1. Setup login session (đăng nhập và lưu session)")
        print("2. Test session với incognito mode")
        print("3. Scrape company (MAGNA Real Estate)")
        print("4. Tất cả (setup -> test -> scrape)")
        
        choice = input("\nNhập lựa chọn (1/2/3/4): ").strip()
        
        if choice == "1":
            scraper.setup_login_session(headless=False)
        elif choice == "2":
            scraper.test_session_incognito(headless=False)  # Non-headless để user xem
        elif choice == "3":
            result = scraper.scrape_with_playwright("MAGNA Real Estate GmbH", "HRB182742")
            print("\n" + "="*80)
            print("SCRAPED DATA:")
            print("="*80)
            for key, value in result.items():
                if key == 'about_html':
                    print(f"  {key}: {len(str(value))} characters")
                else:
                    print(f"  {key}: {value}")
            print("="*80 + "\n")
        elif choice == "4":
            # Setup
            if scraper.setup_login_session(headless=False):
                # Test
                scraper.test_session_incognito(headless=False)
                # Scrape
                result = scraper.scrape_with_playwright("MAGNA Real Estate GmbH", "HRB182742")
                print("\n" + "="*80)
                print("SCRAPED DATA:")
                print("="*80)
                for key, value in result.items():
                    if key == 'about_html':
                        print(f"  {key}: {len(str(value))} characters")
                    else:
                        print(f"  {key}: {value}")
                print("="*80 + "\n")
