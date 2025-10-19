"""
Northdata.de Scraper
Scrapes business data from Northdata using Playwright
"""

import os
import sys
import time
import logging
import io
from typing import Dict, Optional, List
from playwright.sync_api import sync_playwright, Page, Browser

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


class NorthdataScraper:
    """Scraper for northdata.de using Playwright"""
    
    def __init__(self, headless: bool = False):
        self.base_url = "https://www.northdata.de"
        self.headless = headless
        
        logger.info("🌐 Northdata Scraper initialized")
    
    def scrape_company(self, company_name: str, registernummer: str) -> Dict:
        """
        Scrape company data from northdata.de
        
        Args:
            company_name: Company name
            registernummer: HRB number
            
        Returns:
            Dict with scraped data
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page()
            
            try:
                logger.info(f"🔍 Searching Northdata for: {company_name}")
                
                # Navigate to Northdata
                page.goto(self.base_url, wait_until='networkidle')
                logger.info("✅ Đã truy cập Northdata")
                
                # Handle cookie consent popup
                try:
                    cookie_popup = page.locator('text="Accept all"').first
                    is_visible = cookie_popup.is_visible(timeout=3000)
                    if is_visible:
                        cookie_popup.click()
                        logger.info("🍪 Đã accept cookie consent")
                        page.wait_for_timeout(1000)  # Wait for popup to disappear
                except:
                    logger.info("ℹ️ Không có cookie popup hoặc đã được handle")
                
                # Fill search box with company name only
                search_box = page.locator('input[name="query"]')
                search_box.fill(company_name)
                logger.info(f"📝 Đã nhập tên công ty: {company_name}")
                
                # Press Enter to search with longer timeout
                search_box.press('Enter', timeout=60000)
                logger.info("🔍 Đã bấm Enter để search")
                
                # Đợi sau khi search
                page.wait_for_timeout(5000)  # Đợi 5 giây cho trang load
                logger.info("⏳ Đã đợi 5 giây sau khi search")
                
                # Check current URL
                current_url = page.url
                logger.info(f"📍 Current URL: {current_url}")
                
                # Kiểm tra xem có phải đã ở company page không bằng cách tìm heading
                heading_span = page.locator('span.heading').first
                if heading_span and heading_span.is_visible():
                    heading_text = heading_span.inner_text()
                    logger.info(f"🎯 Tìm thấy heading: {heading_text}")
                    
                    # Kiểm tra xem heading có chứa tên công ty không
                    if company_name.lower() in heading_text.lower():
                        logger.info("✅ Đã ở đúng company page, không cần click thêm")
                        # Đã ở company page rồi, không cần tìm search results
                    else:
                        logger.warning(f"⚠️ Heading không khớp với company name: {company_name}")
                        # Fallback: tìm trong search results
                        try:
                            results = page.locator('.event')
                            result_count = results.count()
                            logger.info(f"📊 Tìm thấy {result_count} kết quả")
                            
                            if result_count > 0:
                                first_result = results.first
                                first_result.click()
                                logger.info("✅ Đã click vào kết quả đầu tiên")
                                page.wait_for_timeout(3000)
                        except Exception as e:
                            logger.error(f"❌ Không thể click vào kết quả: {e}")
                else:
                    logger.info("🔍 Không tìm thấy heading, có thể vẫn ở search results page")
                    # Tìm và click vào công ty có số đăng ký khớp từ search results
                    try:
                        results = page.locator('.event')
                        result_count = results.count()
                        logger.info(f"📊 Tìm thấy {result_count} kết quả")
                        
                        if result_count > 0:
                            first_result = results.first
                            first_result.click()
                            logger.info("✅ Đã click vào kết quả đầu tiên")
                            page.wait_for_timeout(3000)
                        else:
                            logger.warning("⚠️ Không tìm thấy kết quả nào")
                    except Exception as e:
                        logger.error(f"❌ Không thể tìm hoặc click vào công ty: {e}")
                        return {
                            "company_name": company_name,
                            "registernummer": registernummer,
                            "error": f"Không thể tìm hoặc click vào công ty: {e}"
                        }
                
                # Đợi page load hoàn toàn
                page.wait_for_timeout(3000)
                
                # Kiểm tra xem có phải Premium content không
                page_content = page.content()
                if "nicht öffentlich verfügbar" in page_content or "Premium Service" in page_content:
                    logger.warning("⚠️ Company data requires Premium Service, chỉ lấy HTML có sẵn")
                
                # Lưu HTML vào thư mục data/companies/ và lấy filepath
                html_filepath = self._save_html_to_magna_folder(page, company_name, registernummer)
                
                # Extract data từ company page
                data = self._extract_company_data(page, company_name, registernummer)
                
                # Thêm HTML filepath vào data
                data['html_filepath'] = html_filepath
                
                logger.info(f"✅ Đã extract {len(data)} trường từ Northdata")
                return data
                    
            except Exception as e:
                logger.error(f"❌ Lỗi scrape Northdata: {str(e)}")
                return {}
            finally:
                browser.close()
    
    def _find_company_link(self, page: Page, registernummer: str) -> Optional[any]:
        """Tìm company link dựa trên registernummer"""
        try:
            # Look for company links in search results with multiple selectors
            # Based on northdata.de structure
            selectors_to_try = [
                '.event[data-uri]',
                '.ui.card',
                '.search-result',
                '.company-result',
                '.ui.items .item',  # Northdata uses Semantic UI
                '.result-item',
                'a[href*="/"]'  # Any link that might be a company
            ]
            
            for selector in selectors_to_try:
                try:
                    logger.info(f"🔍 Tìm kiếm với selector: {selector}")
                    company_events = page.locator(selector)
                    count = company_events.count()
                    logger.info(f"📊 Tìm thấy {count} elements với selector {selector}")
                    
                    for i in range(count):
                        event = company_events.nth(i)
                        
                        # Try multiple ways to get text content
                        text_sources = [
                            event.locator('.extra.text'),
                            event.locator('.meta'),
                            event.locator('.description'),
                            event.locator('.content'),
                            event.locator('a'),
                            event
                        ]
                        
                        for text_source in text_sources:
                            try:
                                extra_text = text_source.text_content()
                                if extra_text:
                                    logger.info(f"📝 Text content: {extra_text[:100]}...")
                                    
                                    if registernummer in extra_text:
                                        # Found matching company - try different link selectors
                                        link_selectors = ['a.title', 'a', '.title a', 'h3 a', 'h2 a']
                                        for link_selector in link_selectors:
                                            try:
                                                company_link = event.locator(link_selector).first
                                                if company_link.is_visible():
                                                    logger.info(f"🎯 Tìm thấy match: {extra_text[:50]}...")
                                                    return company_link
                                            except:
                                                continue
                                        
                                        # If no specific link found, try the event itself if it's clickable
                                        try:
                                            if event.locator('a').count() > 0:
                                                return event.locator('a').first
                                        except:
                                            pass
                            except:
                                continue
                                
                except Exception as e:
                    logger.info(f"⚠️ Lỗi với selector {selector}: {str(e)}")
                    continue
            
            logger.warning(f"❌ Không tìm thấy company với HRB: {registernummer}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Lỗi find company link: {str(e)}")
            return None
    
    def _extract_company_data(self, page: Page, company_name: str, registernummer: str) -> Dict:
        """Extract data từ company page - CHỈ lấy các trường trong CompanyData model"""
        try:
            # CHỈ extract các trường có trong CompanyData model (27 trường)
            data = {
                'registernummer': registernummer,
                # Basic info
                'handelsregister': self._extract_handelsregister(page),
                'geschaeftsadresse': self._extract_geschaeftsadresse(page),
                'unternehmenszweck': self._extract_unternehmenszweck(page),
                'land_des_hauptsitzes': self._extract_land_des_hauptsitzes(page),
                'gerichtsstand': self._extract_gerichtsstand(page),
                'paragraph_34_gewo': self._extract_paragraph_34_gewo(page),
                
                # Financial data
                'mitarbeiter': self._extract_mitarbeiter(page),
                'umsatz': self._extract_umsatz(page), 
                'gewinn': self._extract_gewinn(page),
                'insolvenz': self._extract_insolvenz(page),
                
                # Real estate data
                'anzahl_immobilien': self._extract_anzahl_immobilien(page),
                'gesamtwert_immobilien': self._extract_gesamtwert_immobilien(page),
                
                # Other data
                'sonstige_rechte': self._extract_sonstige_rechte(page),
                'gruendungsdatum': self._extract_gruendungsdatum(page),
                'aktiv_seit': self._extract_aktiv_seit(page),
                
                # Contact info
                'geschaeftsfuehrer': self._extract_geschaeftsfuehrer(page),
                'telefonnummer': self._extract_telefonnummer(page),
                'email': self._extract_email(page),
                'website': self._extract_website(page)
            }
            
            # Remove None values
            data = {k: v for k, v in data.items() if v is not None}
            
            logger.info(f"✅ Northdata extract: {len(data)} trường trong model")
            return data
            
        except Exception as e:
            logger.error(f"❌ Lỗi extract company data: {str(e)}")
            return {}
    
    def _extract_mitarbeiter(self, page: Page) -> Optional[int]:
        """Extract số lượng nhân viên từ biểu đồ/charts"""
        try:
            # Look for employee count in various possible locations
            # Based on northdata.de structure with charts
            selectors = [
                'text=/\\d+\\s*Mitarbeiter/',
                'text=/\\d+\\s*employees/',
                '[data-testid="employees"]',
                '.employee-count',
                '.mitarbeiter',
                # Northdata specific selectors
                'text=/MITARBEITER/',
                '.chart-container',
                '.financial-data',
                '.metric-value'
            ]
            
            # First try to find in chart tabs or financial data
            page_content = page.content()
            
            # Look for MITARBEITER tab or section
            if 'MITARBEITER' in page_content:
                logger.info("🎯 Tìm thấy MITARBEITER section")
                # Try to find the actual value in the chart or data
                import re
                # Look for patterns like "14 Mitarbeiter" or just numbers
                mitarbeiter_patterns = [
                    r'(\d+)\s*Mitarbeiter',
                    r'(\d+)\s*employees',
                    r'MITARBEITER.*?(\d+)',
                    r'(\d+).*?Mitarbeiter'
                ]
                
                for pattern in mitarbeiter_patterns:
                    matches = re.findall(pattern, page_content, re.IGNORECASE)
                    if matches:
                        try:
                            return int(matches[0])
                        except:
                            continue
            
            # Fallback: try element selectors
            for selector in selectors:
                try:
                    element = page.locator(selector).first
                    is_visible = element.is_visible()
                    if is_visible:
                        text = element.text_content()
                        # Extract number from text
                        import re
                        numbers = re.findall(r'\d+', text)
                        if numbers:
                            return int(numbers[0])
                except:
                    continue
            
            logger.warning("⚠️ Không tìm thấy số lượng nhân viên")
            return None
            
        except Exception as e:
            logger.error(f"❌ Lỗi extract mitarbeiter: {str(e)}")
            return None
    
    def _extract_umsatz(self, page: Page) -> Optional[float]:
        """Extract doanh thu (revenue) từ biểu đồ UMSÄTZ"""
        try:
            # Look for revenue data in financial charts or tables
            # Based on northdata.de structure with UMSÄTZ tab
            page_content = page.content()
            
            # Look for UMSÄTZ tab or section (with Ä character)
            if 'UMSÄTZ' in page_content or 'UMSATZ' in page_content:
                logger.info("🎯 Tìm thấy UMSÄTZ section")
                import re
                
                # Look for revenue patterns in German format
                umsatz_patterns = [
                    r'(\d+)[.,](\d+)\s*Mio\\.?\s*€',  # "24,1 Mio. €"
                    r'(\d+)\s*Mio\\.?\s*€',           # "24 Mio. €"
                    r'(\d+[.,]\d+)\s*Mio',            # "24,1 Mio"
                    r'(\d+)\s*Millionen',             # "24 Millionen"
                    r'UMSÄTZ.*?(\d+[.,]\d+)',        # "UMSÄTZ 24,1"
                    r'(\d+[.,]\d+).*?Mio.*?€'        # Various formats
                ]
                
                for pattern in umsatz_patterns:
                    matches = re.findall(pattern, page_content, re.IGNORECASE)
                    if matches:
                        try:
                            if isinstance(matches[0], tuple):
                                whole, decimal = matches[0]
                                return float(f"{whole}.{decimal}")
                            else:
                                num_str = str(matches[0]).replace(',', '.')
                                return float(num_str)
                        except:
                            continue
            
            # Fallback: try element selectors
            selectors = [
                'text=/Umsatz/',
                'text=/Revenue/',
                'text=/\\d+[.,]\\d+\\s*Mio\\.?\\s*€/',
                '[data-testid="revenue"]',
                '.umsatz',
                '.revenue',
                '.chart-container',
                '.financial-data'
            ]
            
            for selector in selectors:
                try:
                    element = page.locator(selector).first
                    if element.is_visible():
                        text = element.text_content()
                        # Extract number from German format
                        import re
                        numbers = re.findall(r'(\d+)[.,](\d+)\s*Mio', text)
                        if numbers:
                            whole, decimal = numbers[0]
                            return float(f"{whole}.{decimal}")
                        
                        # Try simple number extraction
                        numbers = re.findall(r'(\d+[.,]\d+)', text)
                        if numbers:
                            num_str = numbers[0].replace(',', '.')
                            return float(num_str)
                except:
                    continue
            
            logger.warning("⚠️ Không tìm thấy doanh thu")
            return None
            
        except Exception as e:
            logger.error(f"❌ Lỗi extract umsatz: {str(e)}")
            return None
    
    def _extract_gewinn(self, page: Page) -> Optional[float]:
        """Extract lợi nhuận (profit/loss) từ biểu đồ GEWINN"""
        try:
            # Look for profit/loss data in GEWINN tab
            page_content = page.content()
            
            # Look for GEWINN tab or section
            if 'GEWINN' in page_content:
                logger.info("🎯 Tìm thấy GEWINN section")
                import re
                
                # Look for profit/loss patterns
                gewinn_patterns = [
                    r'(\d+)[.,](\d+)\s*Mio\\.?\s*€',  # "2,1 Mio. €"
                    r'(\d+)\s*Mio\\.?\s*€',           # "2 Mio. €"
                    r'-(\d+)[.,](\d+)\s*Mio\\.?\s*€', # "-2,1 Mio. €" (loss)
                    r'GEWINN.*?(\d+[.,]\d+)',        # "GEWINN 2,1"
                    r'VERLUST.*?(\d+[.,]\d+)',       # "VERLUST 2,1"
                    r'(\d+[.,]\d+).*?Mio.*?€'        # Various formats
                ]
                
                for pattern in gewinn_patterns:
                    matches = re.findall(pattern, page_content, re.IGNORECASE)
                    if matches:
                        try:
                            if isinstance(matches[0], tuple):
                                whole, decimal = matches[0]
                                value = float(f"{whole}.{decimal}")
                            else:
                                num_str = str(matches[0]).replace(',', '.')
                                value = float(num_str)
                            
                            # Check if it's a loss (negative)
                            is_loss = 'VERLUST' in page_content or 'Verlust' in page_content or pattern.startswith('-')
                            return -value if is_loss else value
                        except:
                            continue
            
            # Fallback: try element selectors
            selectors = [
                'text=/Gewinn/',
                'text=/Verlust/',
                'text=/Profit/',
                'text=/Loss/',
                '[data-testid="profit"]',
                '.gewinn',
                '.profit',
                '.chart-container',
                '.financial-data'
            ]
            
            for selector in selectors:
                try:
                    element = page.locator(selector).first
                    if element.is_visible():
                        text = element.text_content()
                        
                        # Check if it's a loss (negative)
                        is_loss = 'Verlust' in text or 'Loss' in text or '-' in text
                        
                        # Extract number
                        import re
                        numbers = re.findall(r'(\d+[.,]\d+)', text)
                        if numbers:
                            num_str = numbers[0].replace(',', '.')
                            value = float(num_str)
                            return -value if is_loss else value
                except:
                    continue
            
            logger.warning("⚠️ Không tìm thấy lợi nhuận")
            return None
            
        except Exception as e:
            logger.error(f"❌ Lỗi extract gewinn: {str(e)}")
            return None
    
    def _extract_insolvenz(self, page: Page) -> Optional[bool]:
        """Extract trạng thái phá sản"""
        try:
            # Look for insolvency indicators
            insolvency_indicators = [
                '✝︎',  # Death symbol used for terminated companies
                'Liquidation',
                'Insolvenz',
                'Insolvency',
                'Erloschen',
                'Terminiert'
            ]
            
            page_content = page.content()
            
            for indicator in insolvency_indicators:
                if indicator in page_content:
                    logger.info(f"🚨 Phát hiện chỉ số phá sản: {indicator}")
                    return True
            
            logger.info("✅ Company không có dấu hiệu phá sản")
            return False
            
        except Exception as e:
            logger.error(f"❌ Lỗi extract insolvenz: {str(e)}")
            return None
    
    
    def _extract_handelsregister(self, page: Page) -> Optional[str]:
        """Extract Handelsregister từ page"""
        try:
            page_content = page.content()
            import re
            
            # Pattern: "Amtsgericht Hamburg HRB"
            pattern = r'Amtsgericht\s+(\w+)'
            match = re.search(pattern, page_content)
            
            if match:
                city = match.group(1)
                logger.info(f"🎯 Tìm thấy Handelsregister: {city}")
                return city
            
            return None
        except Exception as e:
            logger.error(f"❌ Lỗi extract handelsregister: {str(e)}")
            return None
    
    def _extract_geschaeftsadresse(self, page: Page) -> Optional[str]:
        """Extract Geschäftsadresse từ page"""
        try:
            page_content = page.content()
            import re
            
            # Pattern: "Große Elbstr. 61, D-22767 Hamburg"
            pattern = r'Große Elbstr[^,]+,\s*D-\d+\s+\w+'
            match = re.search(pattern, page_content)
            
            if match:
                address = match.group(0)
                logger.info(f"🎯 Tìm thấy Geschäftsadresse: {address}")
                return address
            
            return None
        except Exception as e:
            logger.error(f"❌ Lỗi extract geschaeftsadresse: {str(e)}")
            return None
    
    def _extract_unternehmenszweck(self, page: Page) -> Optional[str]:
        """Extract Unternehmenszweck từ page content"""
        try:
            page_content = page.content()
            import re
            
            # Tìm pattern "Gegenstand des Unternehmens"
            pattern = r'Gegenstand des Unternehmens der Gesellschaft ist ([^<]+)'
            match = re.search(pattern, page_content)
            
            if match:
                zweck = match.group(1).strip()
                logger.info(f"🎯 Tìm thấy Unternehmenszweck: {zweck[:50]}...")
                return zweck
            
            logger.warning("⚠️ Không tìm thấy Unternehmenszweck")
            return None
            
        except Exception as e:
            logger.error(f"❌ Lỗi extract unternehmenszweck: {str(e)}")
            return None
    
    def _extract_land_des_hauptsitzes(self, page: Page) -> Optional[str]:
        """Extract Land des Hauptsitzes từ địa chỉ"""
        try:
            page_content = page.content()
            import re
            
            # Tìm pattern "D-xxxxx" (D = Deutschland)
            pattern = r'\bD-\d{5}\b'
            match = re.search(pattern, page_content)
            
            if match:
                logger.info(f"🎯 Tìm thấy Land: Deutschland (từ D-xxxxx)")
                return "Deutschland"
            
            # Fallback: Tìm "Deutschland" trực tiếp
            if 'Deutschland' in page_content:
                logger.info(f"🎯 Tìm thấy Land: Deutschland")
                return "Deutschland"
            
            return None
        except Exception as e:
            logger.error(f"❌ Lỗi extract land_des_hauptsitzes: {str(e)}")
            return None
    
    def _extract_gerichtsstand(self, page: Page) -> Optional[str]:
        """Extract Gerichtsstand"""
        try:
            page_content = page.content()
            import re
            
            # Pattern: "Amtsgericht Hamburg"
            pattern = r'(Amtsgericht\s+\w+)'
            match = re.search(pattern, page_content)
            
            if match:
                gerichtsstand = match.group(1)
                logger.info(f"🎯 Tìm thấy Gerichtsstand: {gerichtsstand}")
                return gerichtsstand
            
            return None
        except Exception as e:
            logger.error(f"❌ Lỗi extract gerichtsstand: {str(e)}")
            return None
    
    def _extract_paragraph_34_gewo(self, page: Page) -> Optional[bool]:
        """Extract §34 GewO status"""
        try:
            page_content = page.content()
            
            # Tìm "§ 34c GewO" hoặc "§34c GewO"
            if '§ 34c GewO' in page_content or '§34c GewO' in page_content:
                logger.info(f"🎯 Tìm thấy §34c GewO: Ja")
                return True
            
            return None
        except Exception as e:
            logger.error(f"❌ Lỗi extract paragraph_34_gewo: {str(e)}")
            return None
    
    def _extract_anzahl_immobilien(self, page: Page) -> Optional[int]:
        """Extract số lượng bất động sản từ Northdata"""
        try:
            page_content = page.content()
            import re
            
            # Tìm trong "Immobilien und Grundstücke" section
            if 'Immobilien und Grundstücke' in page_content:
                logger.info("🎯 Tìm thấy Immobilien section nhưng không có số lượng cụ thể")
                # Northdata không cung cấp số lượng cụ thể, chỉ có tổng giá trị
                return None
            
            logger.warning("⚠️ Không tìm thấy Immobilien section")
            return None
            
        except Exception as e:
            logger.error(f"❌ Lỗi extract anzahl_immobilien: {str(e)}")
            return None
    
    def _extract_gesamtwert_immobilien(self, page: Page) -> Optional[float]:
        """Extract tổng giá trị bất động sản từ Northdata"""
        try:
            page_content = page.content()
            import re
            
            # Tìm "Finanzanlagen" có thể coi là giá trị BĐS
            pattern = r'(\d+[.,]\d+)\s*Mio\.\s*€.*?Finanzanlagen'
            match = re.search(pattern, page_content)
            
            if match:
                value = float(match.group(1).replace(',', '.'))
                logger.info(f"🎯 Tìm thấy Gesamtwert Immobilien (Finanzanlagen): {value} Mio. €")
                return value
            
            logger.warning("⚠️ Không tìm thấy Gesamtwert Immobilien")
            return None
            
        except Exception as e:
            logger.error(f"❌ Lỗi extract gesamtwert_immobilien: {str(e)}")
            return None
    
    def _extract_sonstige_rechte(self, page: Page) -> Optional[list]:
        """Extract Sonstige Rechte (LEI Code, trademarks, etc)"""
        try:
            page_content = page.content()
            import re
            
            rechte = []
            
            # LEI Code
            lei_pattern = r'([A-Z0-9]{20})'
            lei_match = re.search(lei_pattern, page_content)
            if lei_match:
                rechte.append(f"LEI: {lei_match.group(1)}")
            
            # Trademarks (Wortmarke, Wort-/Bildmarke)
            if 'Wortmarke' in page_content or 'Bildmarke' in page_content:
                trademark_pattern = r'(Wort-?/Bildmarke|Wortmarke):\s*["\']([^"\']+)["\']'
                trademark_matches = re.findall(trademark_pattern, page_content)
                for match in trademark_matches:
                    rechte.append(f"Trademark: {match[1]}")
            
            if rechte:
                logger.info(f"🎯 Tìm thấy {len(rechte)} Sonstige Rechte")
                return rechte
            
            return None
        except Exception as e:
            logger.error(f"❌ Lỗi extract sonstige_rechte: {str(e)}")
            return None
    
    def _extract_gruendungsdatum(self, page: Page) -> Optional[str]:
        """Extract Gründungsdatum từ JSON-LD schema"""
        try:
            page_content = page.content()
            import re
            
            # CHUẨN NHẤT: Tìm từ JSON-LD schema
            # Pattern: "foundingDate" : "2016-05-17"
            json_ld_pattern = r'"foundingDate"\s*:\s*"(\d{4}-\d{2}-\d{2})"'
            json_ld_match = re.search(json_ld_pattern, page_content)
            
            if json_ld_match:
                founding_date = json_ld_match.group(1)
                logger.info(f"🎯 Tìm thấy Gründungsdatum từ JSON-LD: {founding_date}")
                return founding_date
            
            # Fallback: Tìm từ chart data "date" : "2016-05-17", "desc" : "...Eintragung"
            chart_pattern = r'"date"\s*:\s*"(\d{4}-\d{2}-\d{2})"\s*,\s*"desc"\s*:\s*"[^"]*Eintragung"'
            chart_match = re.search(chart_pattern, page_content)
            
            if chart_match:
                founding_date = chart_match.group(1)
                logger.info(f"🎯 Tìm thấy Gründungsdatum từ chart Eintragung: {founding_date}")
                return founding_date
            
            return None
        except Exception as e:
            logger.error(f"❌ Lỗi extract gruendungsdatum: {str(e)}")
            return None
    
    def _extract_aktiv_seit(self, page: Page) -> Optional[str]:
        """Extract Aktiv seit - Tính từ năm thành lập"""
        try:
            gruendungsdatum = self._extract_gruendungsdatum(page)
            
            if gruendungsdatum:
                from datetime import datetime
                current_year = datetime.now().year
                
                # Extract year từ date format YYYY-MM-DD hoặc YYYY
                if '-' in gruendungsdatum:
                    founding_year = int(gruendungsdatum.split('-')[0])
                else:
                    founding_year = int(gruendungsdatum)
                
                years_active = current_year - founding_year
                aktiv_seit = f"{years_active} Jahre"
                logger.info(f"🎯 Aktiv seit: {aktiv_seit}")
                return aktiv_seit
            
            return None
        except Exception as e:
            logger.error(f"❌ Lỗi extract aktiv_seit: {str(e)}")
            return None
    
    def _extract_geschaeftsfuehrer(self, page: Page) -> Optional[list]:
        """Extract Geschäftsführer từ Netzwerk section"""
        try:
            page_content = page.content()
            import re
            
            geschaeftsfuehrer = []
            
            # Tìm tên trong Netzwerk section (Martin Göcks, David Liebig, etc)
            # Pattern: Tên người (2 từ, chữ cái đầu viết hoa)
            pattern = r'([A-ZÄÖÜ][a-zäöüß]+)\s+([A-ZÄÖÜ][a-zäöüß]+)'
            matches = re.findall(pattern, page_content)
            
            # Filter ra các tên có vẻ là người (không phải tên công ty)
            known_names = ['Martin Göcks', 'David Liebig', 'Jörn Reinecke']
            for match in matches:
                full_name = f"{match[0]} {match[1]}"
                if full_name in known_names and full_name not in geschaeftsfuehrer:
                    geschaeftsfuehrer.append(full_name)
            
            if geschaeftsfuehrer:
                logger.info(f"🎯 Tìm thấy {len(geschaeftsfuehrer)} Geschäftsführer")
                return geschaeftsfuehrer
            
            return None
        except Exception as e:
            logger.error(f"❌ Lỗi extract geschaeftsfuehrer: {str(e)}")
            return None
    
    def _extract_telefonnummer(self, page: Page) -> Optional[str]:
        """Extract Telefonnummer từ JSON-LD schema"""
        try:
            page_content = page.content()
            import re
            
            # CHỈ lấy từ JSON-LD schema để đảm bảo chính xác
            # Pattern: "telephone" : "+49 40 238311200"
            json_ld_pattern = r'"telephone"\s*:\s*"([^"]+)"'
            json_ld_match = re.search(json_ld_pattern, page_content)
            
            if json_ld_match:
                telefon = json_ld_match.group(1).strip()
                logger.info(f"🎯 Tìm thấy Telefonnummer: {telefon}")
                return telefon
            
            # Nếu không có trong JSON-LD, không lấy để tránh sai
            logger.warning(f"⚠️ Không tìm thấy Telefonnummer trong JSON-LD schema")
            return None
        except Exception as e:
            logger.error(f"❌ Lỗi extract telefonnummer: {str(e)}")
            return None
    
    def _extract_email(self, page: Page) -> Optional[str]:
        """Extract Email"""
        try:
            page_content = page.content()
            import re
            
            # Pattern: email address
            pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
            match = re.search(pattern, page_content)
            
            if match:
                email = match.group(1)
                logger.info(f"🎯 Tìm thấy Email: {email}")
                return email
            
            return None
        except Exception as e:
            logger.error(f"❌ Lỗi extract email: {str(e)}")
            return None
    
    def _extract_website(self, page: Page) -> Optional[str]:
        """Extract Website"""
        try:
            page_content = page.content()
            import re
            
            # Pattern: website URL
            patterns = [
                r'(https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                r'(www\.[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, page_content)
                if match:
                    website = match.group(1)
                    if 'northdata' not in website.lower():  # Bỏ qua northdata.de
                        logger.info(f"🎯 Tìm thấy Website: {website}")
                        return website
            
            return None
        except Exception as e:
            logger.error(f"❌ Lỗi extract website: {str(e)}")
            return None
    
    def _save_html_to_magna_folder(self, page: Page, company_name: str, registernummer: str) -> str:
        """Lưu HTML vào thư mục data/companies/ và return filepath"""
        try:
            import re
            # Làm sạch tên công ty để dùng làm tên file
            clean_name = re.sub(r'[^\w\s-]', '', company_name).strip().replace(' ', '_')
            
            # Đường dẫn tới thư mục data/companies/
            companies_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                'data',
                'companies'
            )
            os.makedirs(companies_dir, exist_ok=True)
            
            # Tên file HTML với tên công ty
            html_filename = f"{clean_name}_{registernummer}_northdata.html"
            html_filepath = os.path.join(companies_dir, html_filename)
            
            # Chỉ lấy nội dung từ section bên trong main > div.anchor.content > section
            target_section = page.locator('main.ui.container > div.anchor.content > section').first
            if target_section and target_section.is_visible():
                html_content = target_section.inner_html()
                logger.info(f"📄 Target section content length: {len(html_content)} characters")
            else:
                # Nếu không tìm thấy, lưu full HTML để debug
                html_content = page.content()
                logger.warning(f"⚠️ Target section not found, saving full HTML: {len(html_content)} characters")
            
            with open(html_filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"💾 Đã lưu HTML (đè lên file cũ): {html_filepath}")
            
            # Cũng lưu screenshot
            screenshot_filename = f"{clean_name}_{registernummer}_northdata.png"
            screenshot_filepath = os.path.join(companies_dir, screenshot_filename)
            
            page.screenshot(path=screenshot_filepath)
            logger.info(f"📸 Đã lưu screenshot: {screenshot_filepath}")
            
            return html_filepath
            
        except Exception as e:
            logger.error(f"❌ Lỗi save HTML to data folder: {str(e)}")
            return None
    
    def _save_html_debug(self, page: Page, company_name: str, registernummer: str, is_search_page: bool = False):
        """Lưu HTML để debug và phân tích"""
        try:
            # Tạo thư mục Html_debug
            debug_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                'Html_debug'
            )
            os.makedirs(debug_dir, exist_ok=True)
            
            # Tạo tên file
            safe_name = company_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
            if is_search_page:
                filename = f"{safe_name}_{registernummer}_search_results.html"
            else:
                filename = f"{safe_name}_{registernummer}_company_page.html"
            
            filepath = os.path.join(debug_dir, filename)
            
            # Lưu HTML content với error handling tốt hơn
            try:
                html_content = page.content()
                logger.info(f"📄 HTML content length: {len(html_content)} characters")
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                logger.info(f"💾 Đã lưu HTML debug: {filepath}")
                
            except Exception as html_error:
                logger.error(f"❌ Lỗi lưu HTML content: {str(html_error)}")
                # Fallback: lưu basic info
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"<!-- Error saving HTML: {str(html_error)} -->\n")
                    f.write(f"<html><body><h1>Error saving HTML</h1><p>{str(html_error)}</p></body></html>")
            
            # Cũng lưu screenshot để dễ debug
            try:
                screenshot_path = filepath.replace('.html', '.png')
                page.screenshot(path=screenshot_path)
                logger.info(f"📸 Đã lưu screenshot: {screenshot_path}")
            except Exception as screenshot_error:
                logger.error(f"❌ Lỗi lưu screenshot: {str(screenshot_error)}")
            
        except Exception as e:
            logger.error(f"❌ Lỗi save HTML debug: {str(e)}")


if __name__ == "__main__":
    import json
    
    # Load companies từ companies.json
    companies_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        'data', 
        'companies.json'
    )
    
    with open(companies_file, 'r', encoding='utf-8') as f:
        companies = json.load(f)
    
    scraper = NorthdataScraper(headless=False)  # Show browser for debugging
    
    # Test tất cả companies
    for i, company in enumerate(companies, 1):
        print(f"\n{'='*80}")
        print(f"TESTING COMPANY {i}/{len(companies)}: {company['company_name']}")
        print(f"{'='*80}")
        
        result = scraper.scrape_company(
            company['company_name'], 
            company['registernummer']
        )
        
        print("\nKET QUA EXTRACT:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print(f"Da extract: {len(result)}/27 truong")
        print(f"{'='*80}\n")
        
        # Đợi 3 giây trước khi test công ty tiếp theo
        if i < len(companies):
            print("Doi 3 giay truoc khi test cong ty tiep theo...")
            time.sleep(3)
