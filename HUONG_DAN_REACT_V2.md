# NEXUS 2.0 — React và FastAPI

## Điều cần biết trước khi cập nhật
Bản này dùng React cho giao diện và FastAPI cho nghiệp vụ Python. Logo nền trong suốt đã tích hợp tại frontend/public/nexus-logo.png. Một server phục vụ cả giao diện và API tại cùng địa chỉ.
Chạy streamlit_app.py vẫn ra giao diện Streamlit cũ. Muốn xem giao diện mới, chạy START_REACT.bat hoặc deploy Dockerfile của gói này. GitHub lưu mã; GitHub Pages không chạy backend Python của ứng dụng.

## Chạy ngay trên Windows
1. Giải nén ZIP ra một thư mục bình thường, không chạy trực tiếp trong cửa sổ ZIP.
2. Cài Python 3.12 có trong PATH. Mở thư mục chứa START_REACT.bat.
3. Sao chép .env.example thành .env. Nhập GEMINI_API_KEY, model đang hoạt động trong project Google của bạn và các biến phê duyệt đang dùng. Các Secrets cũ trên Streamlit không tự chuyển sang server mới.
4. Nếu đã có khóa vault và dữ liệu cũ, giữ nguyên khóa; đừng tạo khóa khác cho kho cũ. Nếu tạo kho demo mới, chạy `python scripts/generate_vault_key.py` rồi đưa kết quả vào PROJECT07_VAULT_MASTER_KEY trong .env. Không đưa .env lên GitHub.
5. Nhấp START_REACT.bat. Lần đầu script tạo môi trường Python và cài dependencies, cần kết nối Internet. Sau khi server chạy, mở http://localhost:8000.
Gói ZIP có frontend/dist đã build, nên chạy bản có sẵn không cần Node.js. Chưa kiểm thử trực tiếp batch trên máy Windows của người dùng.

## Khi muốn sửa giao diện
Cần Node.js và npm. Mở terminal ở thư mục gốc:
```
npm ci --prefix frontend
npm run build --prefix frontend
```
Sau đó khởi động lại server Python. File chính: frontend/src/Experience.jsx (trang chủ), experience.css (theme/hiệu ứng), App.jsx (workflow), Privacy.jsx (bảo vệ dữ liệu).
Bật dev server: chạy backend cổng 8000 và `npm run dev --prefix frontend` ở terminal thứ hai. Vite cổng 5173 chuyển /api sang backend; không đưa API key vào biến VITE hoặc frontend.

## Đưa lên GitHub
Tạo nhánh mới hoặc repo mới để dễ quay lại bản trước. Upload nội dung thư mục Project07_NEXUS_React_v2.0, gồm Dockerfile, backend, frontend, demo, scripts và .github. Không upload riêng file ZIP và không thêm một tầng thư mục ngoài vào repo đang deploy.
Không upload .env, secrets.toml, SQLite, private_vault, node_modules hoặc dữ liệu khách hàng. frontend/dist đã có trong ZIP để chạy tại máy; Git mặc định bỏ qua dist, Docker sẽ build từ source.

## Có link web công khai bằng Render
1. Kết nối repo GitHub vào một Web Service trên Render, chọn runtime Docker. Đây là dịch vụ mới cho bản React, không phải Reboot ứng dụng Streamlit.
2. Root Directory để trống nếu Dockerfile ở gốc repo; Dockerfile path là ./Dockerfile. Dùng lệnh CMD có sẵn. Health check: /api/health.
3. Đưa các giá trị từ cấu hình đang dùng vào Environment: GEMINI_API_KEY, PROJECT07_GEMINI_MODEL, PROJECT07_VAULT_MASTER_KEY, PROJECT07_APPROVED_BASELINE_SHA256, PROJECT07_APPROVED_AUTHORITY_SHA256, PROJECT07_AUTHORITY_APPROVAL_REFERENCE. Không dán dấu ngoặc kép theo cú pháp TOML vào giá trị môi trường.
4. Nếu cần giữ SQLite và vault qua lần triển khai/khởi động lại, cấu hình persistent disk phù hợp, mount /app/storage. Dockerfile đã dùng PROJECT07_DB_PATH=/app/storage/project07.sqlite3 và PROJECT07_VAULT_DIR=/app/storage/private_vault. Đối chiếu quyền ghi của tài khoản nexus với disk thực tế. Không có disk bền vững thì không coi dữ liệu được lưu lâu dài.
5. Triển khai, mở URL của Web Service. Kiểm tra logo, công tắc Light/Dark, /api/health và nút kiểm tra model ở Vai trò LLM & con người.
Chưa tạo tài khoản, dịch vụ hay phát sinh chi phí thay người dùng. Xem lựa chọn gói và điều kiện lưu trữ trên tài khoản của bạn trước khi deploy.
Nguồn hướng dẫn: https://render.com/docs/docker ; https://render.com/docs/web-services ; https://render.com/docs/disks .

## Trình tự demo
- Hồ sơ kiểm toán → Import bộ demo 60 khoản vay → chọn ba snapshot → tạo Audit Run.
- Đối chiếu hiệu lực policy và dữ liệu. Chủ ứng dụng phải cấu hình hash/phê duyệt đúng; bộ demo cũ có tình huống cần kiểm tra tính áp dụng.
- RCM → duyệt → Test Plan → duyệt → Tests & Exceptions → review → Findings & Report.
- Bảo vệ dữ liệu có CSV mô phỏng 100 khoản vay để thử riêng. Cùng mã phạm vi khi thay mã loans và authority để giữ liên kết. Authority sau thay mã có hash mới cần phê duyệt lại đúng nguồn.

## Bảo vệ dữ liệu và giới hạn
Bảng đối chiếu được trả về trình duyệt để auditor tải; không ghi mới vào file/DB/log. Nó có trong RAM của server và bộ nhớ trang trong lúc xử lý. Đổi trang hoặc reload sẽ mất kết quả chưa tải. File gốc mã hóa và khóa đã bọc vẫn lưu tại vault; đọc cấu trúc và xuất tạo các bản lưu gốc riêng.
Chỉ CSV và XLSX đơn giản một sheet được xử lý theo cột; archive mã hóa toàn file hỗ trợ định dạng khác. Không đổi quy tắc review hay mở khóa FINAL. Chưa có đăng nhập/phân quyền theo người dùng; chỉ demo bằng dữ liệu mô phỏng. Chưa xác nhận Gemini live hoặc triển khai Docker/Render thực tế trong lượt này.
Theme được nhớ bằng localStorage trên trình duyệt; hoạt ảnh giảm khi hệ điều hành bật Reduce motion. Loader xoay biểu tượng khi gọi API; không xoay chữ NEXUS.
