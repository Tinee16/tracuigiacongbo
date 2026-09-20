# Hướng B: collector an toàn hơn

Project đã được tổ chức lại thành package `dav_scraper` và bổ sung:

- Chuẩn hóa Unicode NFKC/NFD, bỏ dấu tiếng Việt, xử lý `_`, `-`, dấu câu, viết hoa/thường và khoảng trắng.
- Mở rộng viết tắt phổ biến: `CTCP`, `Cty`, `CP`, `DP`.
- So khớp cả tên pháp lý, thương hiệu và chuỗi không có khoảng trắng.
- Retry có backoff cho lỗi máy chủ 5xx; timeout rõ ràng.
- Delay ngẫu nhiên trong khoảng cấu hình giữa các request, chỉ một session ổn định.
- Dừng an toàn khi nhận 401/403/429 hoặc phát hiện CAPTCHA/Cloudflare/access-denied; không xoay IP, không vượt CAPTCHA, không gửi request dồn dập.
- Phát hiện liên kết phân trang bằng `href`, `rel`, `aria-label`, sau đó mới dùng fallback `?page=`.
- Deduplicate bản ghi và lưu được các cột gốc dạng `column_1`, `column_2`, ... cùng `row_text`.
- Ghi `summary.json` với trạng thái `success`, `no_records_found`, `blocked` hoặc `network_error`.

## Chạy

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python main.py --output output/vinphaco_results.xlsx
```

Điều chỉnh nhịp truy cập:

```bash
python main.py --min-delay 3 --max-delay 8 --retries 3 --max-pages 100
```

Kiểm thử bộ so khớp:

```bash
pytest -q
```

Nếu portal yêu cầu CAPTCHA hoặc đăng nhập, hãy giải quyết thủ công theo quy định của website rồi chạy lại; chương trình cố ý dừng thay vì tìm cách vượt cơ chế bảo vệ.
