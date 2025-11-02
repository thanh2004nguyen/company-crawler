# LinkedIn Session Storage

Thư mục này chứa session/cookies của LinkedIn để scraper có thể đăng nhập tự động.

## File

- `context_storage.json`: Chứa cookies và session state của LinkedIn

## Cách sử dụng

1. **Setup session lần đầu:**
   ```bash
   python scrapers/linkedin_scraper.py
   # Chọn option 1
   ```

2. **Session sẽ tự động được load** khi scraper chạy

3. **Nếu session hết hạn:** Chạy lại setup (option 1) để đăng nhập lại

## Lưu ý

- Session file này được commit lên git để team có thể dùng chung
- Nếu session hết hạn, cần đăng nhập lại và update file này

