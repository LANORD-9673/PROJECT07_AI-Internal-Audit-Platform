BẢN VÁ CHẨN ĐOÁN GEMINI 403 — PROJECT 07

Dùng cho bản Project07_Streamlit_Gemini_FULL đã có trên GitHub.
Giải nén và upload các file/thư mục trong ZIP này vào đúng thư mục gốc repo.
Giữ đường dẫn backend/services/gemini.py, backend/services/workflow.py.
File streamlit_app.py ở gốc. Đây là bản vá, không phải bộ mã nguồn đầy đủ cho repo mới.

Commit changes → chờ app cập nhật/reboot → Vai trò & cấu hình → Kiểm tra key và danh sách model.
Nút đọc models metadata, không gửi policy hoặc tạo nội dung. Metadata OK không chứng minh generateContent có quyền/quota.
Nếu có error reason phù hợp, app chỉ hiện bản dịch cố định, không hiện key hoặc nguyên văn payload Google.
Nếu chưa có reason cụ thể, vẫn hiện HTTP 403 chung; cần kiểm tra AI Studio/project.

API_KEY_INVALID / expired: cập nhật key hợp lệ từ https://aistudio.google.com/apikey.
SERVICE_DISABLED: kiểm tra Gemini/Generative Language API của đúng project chứa key.
Referrer/IP blocked: cấu hình giới hạn phù hợp lời gọi server Streamlit, không phải JavaScript trình duyệt.
Key bị lộ: tạo key mới, cập nhật Secrets, thu hồi key bị lộ.

Nhập key trong Streamlit Settings → Secrets, giữ các biến phê duyệt khác:
GEMINI_API_KEY = "KEY_THAT"
PROJECT07_GEMINI_MODEL = "MODEL_CO_QUYEN_SU_DUNG"
PROJECT07_GEMINI_TIMEOUT = "180"
Không upload key lên GitHub, không gửi key qua chat.

76 backend tests passed. Streamlit AppTest passed. Tests dùng HTTP mô phỏng.
Chưa thử live bằng key của nhóm; bản vá không tự cấp quyền Google hoặc sửa cấu hình tài khoản.
