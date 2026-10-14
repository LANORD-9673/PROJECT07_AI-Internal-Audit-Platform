# Cập nhật Project 07 v1.6.1

## GitHub bằng trình duyệt

1. Tải ZIP v1.6.1 và Extract All vào một thư mục mới. Thư mục giải nén phải có streamlit_app.py và backend trực tiếp.
2. Mở repository https://github.com/LANORD-9673/PROJECT07_AI-Internal-Audit-Platform .
3. Ở trang Code, branch main, chọn Add file → Upload files.
4. Chọn toàn bộ nội dung bên trong thư mục đã giải nén, gồm file và folder backend, demo, docs, scripts, .streamlit, .github. Kéo vào khung upload, giữ đúng folder con. Không upload ZIP, không kéo thêm thư mục ngoài bọc toàn bộ mã.
5. Cuộn xuống: commit message Update Project 07 v1.6.1 privacy sample. Commit changes vào main nếu bạn là owner và dùng repo demo cá nhân; repo nhóm nên dùng branch + PR và review.
6. Trên GitHub, kiểm tra backend/services/privacy.py và demo/privacy_sample_loans_100.csv đúng đường dẫn.
7. Streamlit Manage app → Settings → Secrets: giữ nguyên GEMINI_API_KEY, PROJECT07_VAULT_MASTER_KEY và các biến phê duyệt. Không sinh lại khóa chủ đã dùng để mã hóa file cũ.
8. Chờ deploy cập nhật. Nếu còn giao diện cũ, Manage app → Reboot app. Main file vẫn streamlit_app.py; Python 3.12 đã được kiểm tra.

Nếu GitHub báo quá nhiều file khi upload bằng web, upload lần lượt các folder backend, demo, docs, scripts rồi các file gốc. Giữ đúng cấu trúc path. Tổng gói chưa đến 100 file.

## Thử mã hóa

Bảo vệ dữ liệu → Tải CSV giả lập 100 khoản vay → upload lại CSV đó. Có thể dùng file CSV tải riêng từ cuộc trò chuyện. Sau khi tải file mã hóa gốc, review phương án cột, nhập scope và tên auditor, xác nhận rồi xuất bản mã giả.

File dùng thông tin hoàn toàn hư cấu; điện thoại, CCCD và tài khoản có tiền tố SIM, email example.test. Không gửi key qua chat/GitHub. Vault local và app demo chưa đủ để xử lý dữ liệu khách hàng thật lâu dài; xem HUONG_DAN_BAO_VE_DU_LIEU.md.
