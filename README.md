# German Company Crawler

Công cụ scraping dữ liệu công ty Đức từ nhiều nguồn khác nhau.

## 📋 Mô tả

Dự án này thu thập 23 trường dữ liệu về công ty Đức từ các nguồn:
- Handelsregister.de (Sổ đăng ký thương mại)
- Northdata.de (Dữ liệu kinh doanh)
- Unternehmensregister.de (Đăng ký doanh nghiệp)
- LinkedIn (Thông tin công ty)
- Creditreform.de (Đánh giá tín dụng)

## 🚀 Cài đặt

### 1. Clone repository
```bash
git clone https://github.com/Datapix-organization/Company-crawler.git
cd Company-crawler
```

### 2. Tạo virtual environment
```bash
python -m venv venv
```

### 3. Activate virtual environment
**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 4. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

## 📁 Cấu trúc dự án

```
german-company-crawler/
├── models/              # Data models
│   ├── __init__.py
│   └── company_model.py
├── scrapers/            # Scraping modules
├── utils/               # Helper functions
├── data/                # Output data
├── requirements.txt     # Dependencies
├── .gitignore
└── README.md
```

## 💾 Data Model

Dự án thu thập 23+ trường dữ liệu:
- Registernummer (Số đăng ký)
- Handelsregister (Sổ thương mại)
- Mitarbeiter (Nhân viên)
- USt-IdNr (Mã số thuế)
- Insolvenz (Phá sản)
- Unternehmenszweck (Mục đích KD)
- Umsatz (Doanh thu)
- Gewinn (Lợi nhuận)
- ... và nhiều hơn nữa

## 🔧 Sử dụng

```python
from models import CompanyData
from scrapers import HandelsregisterScraper

# Khởi tạo scraper
scraper = HandelsregisterScraper()

# Scrape dữ liệu công ty
company_data = scraper.scrape("HRB182742")

# Export to JSON
company_data.model_dump_json()
```

## 📊 Test Case

**Công ty mẫu:** MAGNA Real Estate GmbH
- Registernummer: HRB182742
- USt-IdNr: DE305962143

## 🛠️ Công nghệ sử dụng

- Python 3.12+
- Selenium / Playwright (Browser automation)
- BeautifulSoup4 (HTML parsing)
- Pydantic (Data validation)
- Pandas (Data processing)

## 📝 License

Private project for Hai Pham

## 👥 Contributors

- Thanh Nguyen Thai (@thanh2004nguyen)
- Hai Pham (Client)

## 📮 Contact

Email: nguyenthaithanh101104@gmail.com
