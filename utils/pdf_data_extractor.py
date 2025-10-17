#!/usr/bin/env python3
"""
PDF Data Extractor cho Handelsregister PDF files
Trích xuất thông tin bổ sung từ PDF mà XML không có
"""

import pdfplumber
import re
import logging
from typing import Dict, Optional, List, Any
import os

logger = logging.getLogger(__name__)

class PDFDataExtractor:
    """Extractor cho PDF files từ Handelsregister"""
    
    def __init__(self):
        # Patterns để extract từ Handelsregister PDF
        # Theo format của PDF German
        self.patterns = {
            # 1. Stammkapital (Vốn điều lệ)
            'stammkapital': [
                r'Grund- oder Stammkapital:\s*\n(\d+[\d\.,]+)\s*EUR',
                r'Stammkapital:\s*\n?(\d+[\d\.,]+)\s*EUR',
            ],
            
            # 2. Geschäftsadresse
            'geschaeftsadresse': [
                r'Geschäftsanschrift:\s*(.+?)(?=\n[a-z]\)|\n\d+\.)',
            ],
            
            # 3. Gegenstand (Unternehmenszweck)
            'unternehmenszweck': [
                r'Gegenstand\s+des\s+Unternehmens:\s*(.+?)(?=\n\d+\.)',
            ],
            
            # 4. Geschäftsführer
            'geschaeftsfuehrer': [
                r'Geschäftsführer:\s*([^\n]+)',
            ],
            
            # 5. Tag der letzten Eintragung
            'letzte_eintragung': [
                r'Tag\s+der\s+letzten\s+Eintragung:\s*(\d{2}\.\d{2}\.\d{4})',
            ],
            
            # 6. Gesellschaftsvertrag vom - KHÔNG extract vì có thể là ngày sửa điều lệ
            # Ưu tiên lấy từ Northdata JSON-LD (chuẩn xác hơn)
            # 'gruendungsdatum': [
            #     r'Gesellschaftsvertrag\s+vom\s+(\d{2}\.\d{2}\.\d{4})',
            #     r'Satzung\s+vom\s+(\d{2}\.\d{2}\.\d{4})',
            # ],
            
            # 7. Handelsregister
            'handelsregister': [
                r'Handelsregister\s+([A-Z])\s+des\s+Amtsgerichts\s+(\w+)',
            ],
            
            # 8. Registernummer
            'registernummer': [
                r'Nummer\s+der\s+Firma:\s*(HRB\s*\d+)',
                r'(HRB\s*\d+)',
            ],
            
            # 9. Anzahl Eintragungen
            'anzahl_eintragungen': [
                r'Anzahl\s+der\s+bisherigen\s+Eintragungen:\s*(\d+)',
            ],
        }
    
    def extract_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Extract data từ PDF file"""
        try:
            if not os.path.exists(pdf_path):
                logger.warning(f"⚠️  PDF file không tồn tại: {pdf_path}")
                return {}
            
            logger.info(f"📊 Extracting data từ PDF: {pdf_path}")
            
            extracted_data = {}
            
            with pdfplumber.open(pdf_path) as pdf:
                # Extract text từ tất cả pages
                full_text = ""
                for page_num, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        full_text += f"\n--- PAGE {page_num + 1} ---\n"
                        full_text += page_text
                
                # Extract data using patterns
                extracted_data = self._extract_with_patterns(full_text)
                
                # Extract tables
                tables_data = self._extract_tables(pdf)
                if tables_data:
                    extracted_data.update(tables_data)
                
                logger.info(f"✅ Đã extract {len(extracted_data)} trường từ PDF")
                return extracted_data
                
        except Exception as e:
            logger.error(f"❌ Lỗi extract PDF data: {str(e)}")
            return {}
    
    def _extract_with_patterns(self, text: str) -> Dict[str, Any]:
        """Extract data using regex patterns"""
        extracted = {}
        
        for field_name, patterns in self.patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                if matches:
                    # Lấy match đầu tiên
                    value = matches[0]
                    
                    # Handle tuple results (for multi-group patterns)
                    if isinstance(value, tuple):
                        value = ' '.join(value).strip()
                    else:
                        value = value.strip()
                    
                    # Clean up value
                    if field_name == 'stammkapital':
                        value = self._clean_number(value)
                    elif field_name in ['anzahl_eintragungen']:
                        try:
                            value = int(value)
                        except:
                            value = None
                    elif field_name == 'registernummer':
                        # Clean up spaces
                        value = value.replace(' ', '')
                    elif field_name in ['geschaeftsadresse', 'unternehmenszweck']:
                        # Remove extra whitespaces and newlines
                        value = ' '.join(value.split())
                    
                    extracted[field_name] = value
                    break  # Chỉ lấy pattern đầu tiên match
        
        return extracted
    
    def _extract_tables(self, pdf) -> Dict[str, Any]:
        """Extract data từ tables trong PDF"""
        table_data = {}
        
        try:
            for page_num, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                
                for table_num, table in enumerate(tables):
                    if not table:
                        continue
                    
                    # Analyze table structure
                    table_text = "\n".join([" | ".join([str(cell) if cell else "" for cell in row]) for row in table if row])
                    
                    # Tìm patterns trong table
                    for field_name, patterns in self.patterns.items():
                        for pattern in patterns:
                            matches = re.findall(pattern, table_text, re.IGNORECASE | re.DOTALL)
                            if matches and field_name not in table_data:
                                value = matches[0]
                                
                                # Handle tuple results
                                if isinstance(value, tuple):
                                    value = ' '.join([str(v) for v in value if v]).strip()
                                else:
                                    value = str(value).strip()
                                
                                # Clean value
                                if field_name == 'stammkapital':
                                    value = self._clean_number(value)
                                elif field_name in ['anzahl_eintragungen']:
                                    try:
                                        value = int(value)
                                    except:
                                        value = None
                                
                                table_data[field_name] = value
                                break
                                
        except Exception as e:
            logger.error(f"❌ Lỗi extract tables: {str(e)}")
        
        return table_data
    
    def _clean_number(self, value: str) -> Optional[float]:
        """Clean và convert số (German format: 11.100.000,00)"""
        try:
            # Remove EUR, spaces, etc. - keep only digits, dots and commas
            cleaned = re.sub(r'[^\d,.]', '', value)
            
            # German number format: 11.100.000,00
            # Remove dots (thousands separator)
            cleaned = cleaned.replace('.', '')
            # Replace comma with dot (decimal separator)
            cleaned = cleaned.replace(',', '.')
            
            return float(cleaned)
        except:
            return None


def test_pdf_extractor():
    """Test PDF extractor với sample file"""
    extractor = PDFDataExtractor()
    
    # Test với file thực tế
    pdf_path = "data/MAGNA_Real_Estate_GmbH/HRB182742_AD.pdf"
    
    print("🧪 Testing PDF Data Extractor...")
    result = extractor.extract_from_pdf(pdf_path)
    
    print("\n📊 KẾT QUẢ EXTRACT:")
    for key, value in result.items():
        print(f"  {key}: {value}")
    
    return result


if __name__ == "__main__":
    test_pdf_extractor()
