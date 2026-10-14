# NEXUS giao diện 1.8

## Cập nhật GitHub và Streamlit
1. Giải nén ZIP trên máy. Mở thư mục chứa streamlit_app.py.
2. Trên GitHub, mở đúng repository và nhánh mà Streamlit đang chạy.
3. Upload nội dung thư mục, giữ nguyên cấu trúc. Không upload riêng file ZIP.
4. Các file giao diện mới bắt buộc: nexus_ui.py và assets/nexus-logo.png. Thay streamlit_app.py bằng bản mới. Các file backend tiếp tục đi cùng gói đầy đủ.
5. Commit thay đổi. Trong Streamlit, giữ Main file path là streamlit_app.py. Chờ tự triển khai hoặc dùng Reboot app.
6. Giữ Secrets hiện có. Không đưa API key, khóa vault hoặc secrets.toml vào GitHub.

## Sử dụng
- Trang chủ có nút bảo vệ dữ liệu, tạo cuộc kiểm toán, đánh giá và các bước workflow.
- Menu bên trái chứa toàn bộ tác vụ; Audit Run chọn cuộc kiểm toán đang làm.
- Công tắc Chế độ tối đổi Dark/Light, được giữ trong phiên hiện tại. Phiên mới mặc định Dark.
- Logo chính chủ dùng nguyên ảnh đính kèm, đặt trên nền trắng để đọc được ở cả hai chế độ.
- Logo xoay trong thông báo chờ gọi API, mã hóa file và tạo bảng đối chiếu. Máy bật Reduce motion sẽ ngừng hiệu ứng để hỗ trợ khả năng tiếp cận.

## Phạm vi
Bản này thay lớp trình bày, không mở khóa FINAL, không thay quy tắc kiểm toán, review hay lưu trữ dữ liệu. Lấy cảm hứng từ bố cục nổi bật và sắc xanh/vàng của ảnh tham khảo; không sao chép hình nhân vật hoặc tài sản của trò chơi.
Hiệu ứng tải tùy chỉnh hoạt động sau khi giao diện được dựng; giai đoạn trình duyệt kết nối lần đầu do Streamlit quản lý. Các bảng dữ liệu dùng bộ dựng gốc của Streamlit; màu bảng có thể khác lớp giao diện tùy phiên bản trình duyệt.
