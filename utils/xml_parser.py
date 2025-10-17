#!/usr/bin/env python3
"""
XML Parser utilities cho Handelsregister SI files - Version 2
Sử dụng logic đơn giản và hiệu quả hơn
"""

import xml.etree.ElementTree as ET
import logging
from typing import Dict, Optional, List, Any

logger = logging.getLogger(__name__)

class HandelsregisterXMLParser:
    """Parser cho XML files từ Handelsregister - Version 2"""
    
    def __init__(self):
        self.namespaces = {'tns': 'http://www.xjustiz.de'}
    
    def parse_xml_file(self, xml_path: str) -> Dict[str, Any]:
        """Parse XML file và trả về structured data"""
        try:
            with open(xml_path, 'r', encoding='utf-8') as file:
                content = file.read()
                return self.parse_xml_content(content)
        except Exception as e:
            logger.error(f"❌ Lỗi đọc XML file {xml_path}: {str(e)}")
            return {}
    
    def parse_xml_content(self, xml_content: str) -> Dict[str, Any]:
        """Parse XML content và extract company data"""
        try:
            root = ET.fromstring(xml_content)
            company_data = self._extract_company_info(root)
            logger.info(f"✅ Đã parse XML thành công: {len(company_data)} trường")
            return company_data
        except Exception as e:
            logger.error(f"❌ Lỗi parse XML content: {str(e)}")
            return {}
    
    def _get_text(self, root: ET.Element, path: str) -> Optional[str]:
        """Helper function để lấy text từ XPath"""
        try:
            el = root.find(path, self.namespaces)
            return el.text.strip() if el is not None and el.text else None
        except:
            return None
    
    def _extract_company_info(self, root: ET.Element) -> Dict[str, Any]:
        """Extract thông tin công ty từ XML ElementTree"""
        result = {}
        
        try:
            # 1. Registernummer
            register_code = self._get_text(root, './/tns:register/code')
            laufende_nummer = self._get_text(root, './/tns:laufendeNummer')
            if register_code and laufende_nummer:
                result['registernummer'] = f"{register_code}{laufende_nummer}"
            
            # 2. Handelsregister (từ mã K1101R = Amtsgericht Hamburg)
            gericht_code = self._get_text(root, './/tns:gericht/code')
            if gericht_code == 'K1101R':
                result['handelsregister'] = 'Hamburg'
                result['gerichtsstand'] = 'Amtsgericht Hamburg'
            
            # 3. Geschäftsführer - tìm trong beteiligung có code 086
            geschaeftsfuehrer = []
            for beteiligung in root.findall('.//tns:beteiligung', self.namespaces):
                # Kiểm tra có code 086 (Geschäftsführer) không
                code_elements = beteiligung.findall('.//code')
                has_086 = any(code.text == '086' for code in code_elements if code.text)
                
                if has_086:
                    vorname = self._get_text(beteiligung, './/tns:vorname')
                    nachname = self._get_text(beteiligung, './/tns:nachname')
                    if vorname and nachname:
                        geschaeftsfuehrer.append(f"{vorname} {nachname}")
            
            if geschaeftsfuehrer:
                result['geschaeftsfuehrer'] = geschaeftsfuehrer
            
            # 4. Geschäftsadresse
            strasse = self._get_text(root, './/tns:strasse')
            hausnummer = self._get_text(root, './/tns:hausnummer')
            plz = self._get_text(root, './/tns:postleitzahl')
            ort = self._get_text(root, './/tns:ort')
            if strasse and hausnummer and plz and ort:
                result['geschaeftsadresse'] = f"{strasse} {hausnummer}, {plz} {ort}"
            
            # 5. Unternehmenszweck
            gegenstand = self._get_text(root, './/tns:basisdatenRegister/tns:gegenstand')
            if gegenstand and gegenstand != "Strukturierter Registerinhalt":
                result['unternehmenszweck'] = gegenstand
            
            # 6. Gründungsdatum
            # KHÔNG lấy từ aktuellesSatzungsdatum vì có thể là ngày Formwechsel/sửa điều lệ
            # Ưu tiên lấy từ Northdata JSON-LD schema (chuẩn xác hơn)
            # satzungsdatum = self._get_text(root, './/tns:aktuellesSatzungsdatum')
            # if satzungsdatum:
            #     result['gruendungsdatum'] = satzungsdatum
            pass
            
            # 7. Land des Hauptsitzes - Tìm từ <tns:staat>
            # Một số XML có field này, một số không
            staat_code = self._get_text(root, './/tns:anschrift/tns:staat/code')
            if staat_code == '000':  # Code 000 = Deutschland
                result['land_des_hauptsitzes'] = 'Deutschland'
            else:
                # Fallback: Nếu không có staat, search trong comment
                for staat_elem in root.findall('.//tns:staat', self.namespaces):
                    # Tìm comment trước element này
                    comment_text = ET.tostring(staat_elem, encoding='unicode')
                    if 'Deutschland' in comment_text:
                        result['land_des_hauptsitzes'] = 'Deutschland'
                        break
            
            # 8. Gerichtsstand (đã được xử lý ở trên)
            
            # 9. Paragraph 34 GewO
            if gegenstand and '§ 34c GewO' in gegenstand:
                result['paragraph_34_gewo'] = True
            
            # 10. Stammkapital
            stammkapital = self._get_text(root, './/tns:stammkapital/tns:zahl')
            if stammkapital:
                try:
                    result['stammkapital'] = float(stammkapital)
                except:
                    pass
            
            # 11. Letzte Eintragung
            letzte_eintragung = self._get_text(root, './/tns:letzteEintragung')
            if letzte_eintragung:
                result['letzte_eintragung'] = letzte_eintragung
            
            # 12. Letzte Änderung
            letzte_aenderung = self._get_text(root, './/tns:letzteAenderung/tns:aenderungsdatum')
            if letzte_aenderung:
                result['letzte_aenderung'] = letzte_aenderung
            
            # 13. Abrufdatum
            abrufdatum = self._get_text(root, './/tns:abrufdatum')
            if abrufdatum:
                result['abrufdatum'] = abrufdatum
            
            # 14. Geburtsdatum Geschäftsführer
            geburtsdatum = self._get_text(root, './/tns:geburtsdatum')
            if geburtsdatum:
                result['geburtsdatum_geschaeftsfuehrer'] = geburtsdatum
            
            # 15. Unternehmensname
            unternehmensname = self._get_text(root, './/tns:bezeichnung.aktuell')
            if unternehmensname:
                result['unternehmensname'] = unternehmensname
            
            logger.info(f"✅ Đã extract {len(result)} trường từ XML")
            return result
            
        except Exception as e:
            logger.error(f"❌ Lỗi extract company info: {str(e)}")
            return {}


def test_xml_parser():
    """Test XML parser với sample data"""
    parser = HandelsregisterXMLParser()
    
    # Test với file thực tế
    xml_path = "data/MAGNA_Real_Estate_GmbH/HRB182742_SI.xml"
    
    print("🧪 Testing XML Parser V2...")
    
    # Debug register code
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        ns = {'tns': 'http://www.xjustiz.de'}
        
        print("\n🔍 DEBUG:")
        register_code = root.find('.//tns:register/code', ns)
        laufende_nummer = root.find('.//tns:laufendeNummer', ns)
        gericht_code = root.find('.//tns:gericht/code', ns)
        
        print(f"Register code: {register_code.text if register_code is not None else None}")
        print(f"Laufende nummer: {laufende_nummer.text if laufende_nummer is not None else None}")
        print(f"Gericht code: {gericht_code.text if gericht_code is not None else None}")
        
    except Exception as e:
        print(f"Debug error: {e}")
    
    result = parser.parse_xml_file(xml_path)
    
    print("\n📊 KẾT QUẢ PARSE:")
    for key, value in result.items():
        print(f"  {key}: {value}")
    
    return result


if __name__ == "__main__":
    test_xml_parser()
