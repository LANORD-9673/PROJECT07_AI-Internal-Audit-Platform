CHỈ THAY MỘT FILE — BẢN GEMINI ĐÃ CÓ TRÊN GITHUB

1. Giải nén ZIP.
2. Thay file backend/services/gemini.py trên GitHub bằng file cùng đường dẫn trong ZIP.
   Có thể vào repo > backend > services > gemini.py > Edit, dán toàn bộ nội dung mới và Commit changes.
3. Reboot app Streamlit.
4. Nhấn RCM > Tạo bản nháp bằng LLM.
5. Nếu Google vẫn trả 403, thông báo sẽ có HTTP 403 — Google: <thông điệp gốc đã che key>.
   Gửi thông báo đó để xác định nguyên nhân. Không gửi API key hoặc ảnh Secrets.

Bản này giữ nút kiểm tra metadata của bản vá trước, không đổi key, model hay gates.
Bản vá trước chỉ hiển thị reason đã biết, làm mất thông điệp chi tiết khi reason không khớp.
Bản này giữ thông điệp Google sau khi che key cấu hình, chuỗi key chuẩn, query key/token và bearer token.
30 kiểm thử Gemini transport/config/error/redaction đã đạt, dùng HTTP mô phỏng; chưa kiểm chứng key live của nhóm.
