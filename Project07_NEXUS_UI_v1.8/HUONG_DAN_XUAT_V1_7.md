# Project 07 v1.7 — Giữ cấu trúc nguồn và đối chiếu riêng cho auditor

## Sửa theo phản hồi

File protected cũ từ sample có 20 cột thay vì 28 vì REMOVE đã xóa cột. Bản mới dùng MASK che giá trị tại chỗ bằng [REDACTED], không xóa cột. Mọi cột giữ thứ tự và số dòng. Mã giả thay đổi nội dung nhận dạng, không thể giữ đồng thời giá trị gốc và bảo mật giá trị đó.

CSV xuất cùng extension .csv, giữ delimiter comma/semicolon/tab/pipe nhận diện được, UTF-8/BOM hoặc UTF-16 có BOM, newline và có/không newline cuối. Quote có thể được chuẩn hóa theo CSV chuẩn; không cam kết giống byte-for-byte sau khi thay nội dung. Giá trị KEEP được giữ nguyên, trừ text có dấu hiệu formula được escape để không thực thi khi mở spreadsheet. Số âm/dương dạng numeric không bị escape.

XLSX xuất .xlsx cho workbook một sheet dạng bảng chữ nhật, header dòng 1, không có formulas/images/charts. Giữ tên sheet, styles, number formats, widths, freeze panes, filter và kiểu numeric ở ô KEEP đã được kiểm thử. Comments/hyperlinks bị bỏ khỏi bản bảo vệ vì có thể chứa dữ liệu gốc. Không cam kết giữ mọi feature OOXML của mọi workbook. Workbook nhiều sheet hoặc cấu trúc ngoài phạm vi bị chặn xuất mã giả, thay vì để nguyên dữ liệu nhạy cảm ở sheet chưa review. Mã hóa toàn bộ file gốc vẫn hoạt động với những file này.

## Sau khi auditor duyệt

1. **Dữ liệu đã bảo vệ**: cùng định dạng nguồn và đầy đủ cột.
2. **Bảng đối chiếu CSV**: một dòng cho từng ô của bảng, gồm data_row, column, original_row_id/protected_row_id, action, method, original_value và protected_value. KEEP cũng được ghi là unchanged.
3. **Hồ sơ JSON**: scope, người review tự khai, timestamp, tên file, checksum nguồn và bản bảo vệ, số dòng/cột, thứ tự cột, phương án và cell_details đầy đủ. JSON giữ nguyên chuỗi gốc để đối chiếu chính xác, kể cả trường hợp CSV cần escape công thức.

CSV mapping và JSON đều chứa dữ liệu gốc. Auditor tải và lưu riêng vào vị trí private có quyền phù hợp; không đưa vào workflow/LLM hoặc GitHub.

## Không lưu bảng đối chiếu mới vào hệ thống

Pseudonymize không ghi mapping xuống folder, DB hoặc log. Giá trị chỉ được giữ tạm trong RAM/session để phục vụ xử lý và download. Streamlit download buffer tồn tại trong process/phiên cho tới khi được giải phóng; không tuyên bố không bao giờ chạm bộ nhớ server. Tải CSV/JSON trước khi đóng/reboot app; app không có tính năng tìm lại mapping mới sau khi phiên mất.

File gốc AES-GCM và wrapped keys của chức năng archive vẫn được giữ trong private vault theo thiết kế trước; thay đổi này chỉ bỏ **lưu bảng đối chiếu**. Khi auditor import bản đã bảo vệ, normal SQLite còn dữ liệu KEEP và mã giả. Dữ liệu chưa có đăng nhập/phân quyền production nên vẫn chỉ dùng mẫu giả lập.

Các file .map.enc đã sinh bằng bản cũ không bị xóa tự động, để không phá khả năng truy vết/khôi phục dữ liệu trước. Chủ hệ thống cần xử lý các bản lưu cũ theo quy trình quản trị riêng nếu muốn xóa/di chuyển. Hàm restore_mapping giữ để đọc các bản legacy, không tạo bản mới.

## Cập nhật GitHub và thử lại

1. Giải nén ZIP v1.7 mới, upload toàn bộ nội dung vào thư mục gốc repo, giữ folder con; Commit changes.
2. Giữ Secrets và khóa chủ cũ. Reboot app.
3. Vào Bảo vệ dữ liệu, **upload lại file gốc**. Không upload CSV NX cũ để kỳ vọng khôi phục giá trị gốc: mã giả không tự chứa dữ liệu gốc.
4. Review TOKENIZE/MASK/KEEP, nhập scope và người review, xác nhận.
5. Tải dữ liệu đã bảo vệ, tải mapping CSV và hồ sơ JSON, lưu hai loại file riêng.

Sample gốc là demo/privacy_sample_loans_100.csv (100 dòng, 28 cột). Nút tải sample vẫn có trên web.

## Phạm vi và giới hạn

Đề xuất cột bằng heuristic không chứng minh ẩn danh. Bảng bị giới hạn 10 MB, 200 cột, 100.000 dòng và 200.000 ô để xuất mapping chi tiết. Giữ scope/khóa chủ ổn định cho các file loans/authority cần liên kết; tokens ở cột ID vẫn giữ phép so sánh bằng nhau cho T01–T03. Các human gates, approval hashes và schema baseline vẫn giữ nguyên.

Bảng đối chiếu là hồ sơ của auditor, không phải khóa AES giải mã .nexus.enc. Giải mã archive vẫn cần khóa chủ và wrapped key đã lưu ở vault. Nếu muốn auditor tự giữ cả key file archive và không lưu nguồn/keys trên server, đó là thay đổi khác cần xác định riêng.
