# Project 07 — NEXUS trên Streamlit

Giao diện Streamlit cho toàn bộ workflow v1.4: import policy và data → RCM → test plan → Python tests → human review → findings → reviewed draft report. Bản này không cần deploy Render, build React hoặc chạy backend riêng. React cũ còn trong `frontend` để tham khảo.

## Lấy link web công khai

1. Giải nén gói. Đưa **nội dung bên trong thư mục `project07-streamlit`** lên repository GitHub. Thư mục gốc repo cần có `streamlit_app.py`, `streamlit_runtime.py`, `requirements.txt`, `backend`, `demo` và `.streamlit`.
2. Đăng nhập https://share.streamlit.io bằng GitHub, cho phép Streamlit truy cập repo.
3. Chọn **Create app → Yup, I have an app**, chọn Repository, Branch `main`, Main file path **`streamlit_app.py`**.
4. Trong **Advanced settings**, chọn Python **3.12**, nhập Secrets nếu đã có endpoint LLM/hồ sơ phê duyệt. Có thể deploy chưa có Secrets để xem giao diện/import; các tác vụ cần model hoặc phê duyệt sẽ bị chặn.
5. Chọn tên App URL còn trống và nhấn **Deploy**. Streamlit cấp link thực tế dạng `https://<ten-da-chon>.streamlit.app`. Đây là mẫu, không phải URL đã được tạo.
6. Nếu repo private, app có thể mặc định private; vào cài đặt chia sẻ của app và chuyển public để giảng viên mở tự do. App từ repo public thường public mặc định.

Phải giải nén mã nguồn trước khi đưa lên repo; không upload nguyên ZIP rồi deploy. Nếu giữ thêm thư mục ngoài trong repo, Main file path phải khớp vị trí thực tế; nên dùng cấu trúc gốc ở bước 1.

## Đưa code lên GitHub từ Windows

Truy cập https://github.com/new, tạo repo `project07-streamlit`; có thể private nếu chỉ cần công khai web. Không thêm README/gitignore lúc tạo. Cài Git nếu cần; mở PowerShell tại thư mục có `streamlit_app.py`, thay `TEN_GITHUB` bằng tài khoản thực tế:

```powershell
git init
git add .
git commit -m "Add Project 07 Streamlit demo"
git branch -M main
git remote add origin https://github.com/TEN_GITHUB/project07-streamlit.git
git push -u origin main
```

Repo đã có code thì dùng clone + branch + PR; không force-push. Đưa cả thư mục ẩn `.github`, `.devcontainer`, `.streamlit` lên Git. File `.streamlit/secrets.toml` giữ riêng, gitignore đã chặn.

## Cấu hình Secrets

Mẫu ở `.streamlit/secrets.example.toml`. Cloud: nhập Advanced settings → Secrets. Local: tạo `.streamlit/secrets.toml` tại thư mục gốc và điền giá trị thật.

```toml
PROJECT07_OLLAMA_URL = "https://YOUR-OLLAMA-SERVER"
PROJECT07_OLLAMA_MODEL = "qwen3:4b"
PROJECT07_OLLAMA_TIMEOUT = "180"
PROJECT07_OLLAMA_TOKEN = ""
PROJECT07_APPROVED_BASELINE_SHA256 = ""
PROJECT07_APPROVED_AUTHORITY_SHA256 = ""
PROJECT07_AUTHORITY_APPROVAL_REFERENCE = ""
```

- **Ollama:** URL phải là base URL mà Streamlit Cloud truy cập được, không thêm `/api/chat`. API phải đúng định dạng Ollama và có model đúng tên; endpoint OpenAI-compatible không dùng trực tiếp với adapter này. `localhost` trên cloud không trỏ về laptop. Máy nhóm, model và kết nối cần hoạt động nếu dùng Ollama trên máy nhóm. Token tùy chọn là bearer token mà reverse proxy của nhóm chấp nhận. Không mở Ollama không xác thực ra Internet. Gói không tự cài model hoặc tạo server Ollama.
- **Phê duyệt baseline:** con người đối chiếu policy và authority trước khi điền hash/mã phê duyệt. Màn hình “Vai trò & cấu hình” hiển thị hash file demo để đối chiếu. Tính hash không phải phê duyệt; backend vẫn yêu cầu khớp snapshot của run. Mẫu rỗng chưa đủ chạy tests. Không điền hash của file chưa review chỉ để vượt chốt. Mã phê duyệt giả lập nằm trong policy demo; nhóm vẫn cần hoàn tất kiểm tra dữ liệu/phạm vi theo tài liệu.
- Streamlit luôn bật human gates. Mọi bước duyệt RCM/Plan, xác minh exceptions và review findings vẫn được kiểm tra ở backend.

Chưa cấu hình model thì UI/import chạy được, bốn tác vụ LLM không chạy được. Không tự thay thế kết quả AI bằng dữ liệu giả. Muốn dùng nhà cung cấp LLM API khác cần thêm adapter theo API được nhóm chọn.

## Demo với giảng viên

1. **Vai trò & cấu hình:** phân biệt LLM hỗ trợ viết code với 4 tác vụ LLM trong app.
2. **Dữ liệu & Audit Run:** import bộ demo 60 khoản vay; tạo run từ đúng 3 snapshots.
3. **RCM:** LLM1 tạo bản nháp; đối chiếu policy gốc; con người nhập tên/căn cứ và duyệt.
4. **Test Plan:** LLM2 tạo kế hoạch; con người kiểm tra và duyệt.
5. **Tests & Exceptions:** Python chạy T01–T03. Đọc bằng chứng, xác nhận/bác bỏ từng exception; không tự duyệt hàng loạt.
6. **Findings:** LLM3 tạo finding có quote/control/evidence. Con người review từng finding. Report chỉ tạo khi mọi finding được CONFIRMED.
7. **Report:** LLM4 soạn báo cáo; con người review và tải JSON/phụ lục. Phát hành vẫn **DRAFT**, backend chặn FINAL vì chưa có xác thực/phân quyền người duyệt.
8. **Evaluation:** xem benchmark Python, chỉ số cấu trúc, log LLM và audit trail. Benchmark/mocking không chứng minh chất lượng LLM live.

## Chạy local / Codespaces

Windows: chạy `START_STREAMLIT.bat` tại thư mục gốc nếu máy đã có Python. Hoặc:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

Codespaces: Code → Codespaces → Create codespace on main; chờ dependencies, chạy `bash scripts/start_cloud.sh`, mở port `8501`. Link Codespaces chỉ xem thử khi môi trường hoạt động. Link nộp bài nên là Community Cloud.

## Kiểm tra và giới hạn

GitHub Actions chạy `python -m pytest backend/tests -q` và `python scripts/check_streamlit.py`. AppTest không gọi model thật. Xem `STREAMLIT_TEST_REPORT.txt` để biết phần đã kiểm tra.

Demo dùng chung SQLite, chưa xác thực người duyệt hoặc tách dữ liệu theo người dùng. Người truy cập có thể xem/thao tác các run trong cùng instance; chỉ dùng dữ liệu giả lập. Không dựa vào SQLite local để lưu bền vững trên cloud: tải JSON giữ kết quả demo; nếu cần lưu lâu dài, cần database ngoài và adapter phù hợp.

Chưa có link công khai được tạo chỉ từ gói mã này; phải deploy qua tài khoản GitHub và Streamlit của nhóm. Tài liệu nghiệp vụ/nhật ký AI viết code nằm trong `docs`. `README_GITHUB_RENDER_REFERENCE.md` và launcher React/FastAPI là phương án trước, không dùng khi deploy Streamlit.

## Tài liệu chính thức

- Deploy: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
- Dependencies: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies
- Secrets: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management
- Chia sẻ: https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app
