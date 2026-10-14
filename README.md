# Project 07 v1.6 — Privacy + Gemini

Bản này thêm màn hình Bảo vệ dữ liệu, file AES-256-GCM, CSV mã giả đã review và retry Gemini 5xx có giới hạn. Đọc **HUONG_DAN_BAO_VE_DU_LIEU.md** trước khi cấu hình vault.

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

## Cấu hình Gemini API từ Google AI Studio

1. Vào https://aistudio.google.com/apikey để tạo API key của project bạn có quyền sử dụng.
2. Trên Streamlit Cloud, mở Settings → Secrets và nhập:

```toml
GEMINI_API_KEY = "DAN_KEY_THAT_VAO_SECRETS"
PROJECT07_GEMINI_MODEL = "gemini-3.8-flash"
PROJECT07_GEMINI_TIMEOUT = "180"
PROJECT07_APPROVED_BASELINE_SHA256 = ""
PROJECT07_APPROVED_AUTHORITY_SHA256 = ""
PROJECT07_AUTHORITY_APPROVAL_REFERENCE = ""
```

Key chỉ nhập trong Secrets, không đưa vào GitHub hoặc chat. Mẫu ở `.streamlit/secrets.example.toml`. Model mặc định là Gemini 3.8 Flash; nếu project không truy cập được, chọn model có quyền sử dụng và hỗ trợ generateContent + structured JSON rồi sửa `PROJECT07_GEMINI_MODEL`. Không tự chuyển model khi quota hoặc model lỗi. Model IDs/lifecycle và quota có thể thay đổi: kiểm tra AI Studio khi triển khai.

Cả 4 tác vụ dùng Gemini Developer API `generateContent`, gửi JSON schema tương ứng và vẫn kiểm tra policy quote, test coverage, evidence linkage và human gates tại backend. Không cần Ollama, server trên laptop hoặc Google SDK mới. REST adapter dùng thư viện Python chuẩn; requirements đã có đủ dependencies. Chưa kiểm tra bằng key thật của nhóm.

**Phê duyệt baseline:** con người vẫn cần đối chiếu policy và authority trước khi điền hash/mã phê duyệt. Màn hình Vai trò & cấu hình hiển thị hash file demo để đối chiếu. Tính hash không phải phê duyệt. Các biến phê duyệt rỗng sẽ làm Python tests bị chặn; không tự điền hash chỉ để vượt chốt. Streamlit luôn bật human gates.

## PyCharm / local Windows

Dùng Python 3.12. Trong Terminal tại thư mục gốc, cài `python -m pip install -r requirements.txt`. Tạo `.streamlit/secrets.toml` bằng mẫu rồi chạy `python -m streamlit run streamlit_app.py`. PyCharm Run Configuration cũng có thể đặt biến môi trường `GEMINI_API_KEY`, `PROJECT07_GEMINI_MODEL`, `PROJECT07_GEMINI_TIMEOUT`. App không tự đọc `.env`; `.env.example` chỉ là mẫu tên biến. Không dùng Run Python thông thường để thay cho lệnh Streamlit.

## NotebookLM / Gemini Notebook Enterprise

Gemini API của AI Studio không phải API notebook. Người dùng chưa xác định cụ thể dịch vụ notebook nào, nên bản này chỉ tích hợp Gemini API. Không tự tạo hoặc đọc notebook của tài khoản Google.

Nếu ý là NotebookLM tại https://notebooklm.google.com, có thể dùng như công cụ để con người đọc/đối chiếu policy riêng. Output NotebookLM chưa review không tự trở thành policy nguồn hoặc approval của app.

Google công bố API quản lý notebook/sources của Gemini Notebook Enterprise. Cần Google Cloud project, service/API được bật, IAM và license theo tài liệu; không thể dùng API key AI Studio để mặc định nối dịch vụ này. Tài liệu API được kiểm tra: https://docs.cloud.google.com/gemini/enterprise/notebooklm-enterprise/docs/api-notebooks . Chưa triển khai adapter enterprise hoặc giả định có endpoint chat phù hợp 4 tác vụ. Cần xác định đúng dịch vụ và thao tác muốn thực hiện trước khi viết phần này.

## Lỗi Gemini thường gặp

- `MODEL_CONFIGURATION_ERROR`: thiếu API key hoặc model/timeout cấu hình sai.
- `MODEL_AUTH_ERROR`: key không hợp lệ hoặc project chưa có quyền.
- `MODEL_NOT_FOUND`: model không khả dụng cho project.
- `MODEL_RATE_LIMIT`: quota/rate limit; kiểm tra AI Studio trước khi thử lại. Không tự retry hàng loạt.
- `MODEL_BLOCKED`, `MODEL_TRUNCATED`, `MODEL_SCHEMA_ERROR`: model chưa tạo JSON phù hợp; bước đó dừng, con người cần kiểm tra phạm vi/nguồn.

Không ghi key vào URL hoặc log. App vẫn dùng chung database và chưa có xác thực người dùng. Khi công khai app, người truy cập có thể kích hoạt lời gọi dùng quota/key của chủ app; kiểm soát quyền truy cập của deployment và quota/billing trong AI Studio phù hợp nhu cầu demo. Chỉ đưa dữ liệu giả lập vào app; policy/data liên quan từng tác vụ được gửi tới Google khi gọi Gemini.

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

GitHub Actions chạy `python -m pytest backend/tests -q` và `python scripts/check_streamlit.py`. AppTest không gọi model thật. Tests transport Gemini dùng HTTP mô phỏng. Xem `STREAMLIT_TEST_REPORT.txt` để biết phần đã kiểm tra.

Demo dùng chung SQLite, chưa xác thực người duyệt hoặc tách dữ liệu theo người dùng. Người truy cập có thể xem/thao tác các run trong cùng instance; chỉ dùng dữ liệu giả lập. Không dựa vào SQLite local để lưu bền vững trên cloud: tải JSON giữ kết quả demo; nếu cần lưu lâu dài, cần database ngoài và adapter phù hợp.

Chưa có link công khai được tạo chỉ từ gói mã này; phải deploy qua tài khoản GitHub và Streamlit của nhóm. Tài liệu nghiệp vụ/nhật ký AI viết code nằm trong `docs`. `README_GITHUB_RENDER_REFERENCE.md (lịch sử phương án Ollama)` và launcher React/FastAPI là phương án trước, không dùng khi deploy Streamlit.

## Tài liệu chính thức

- Deploy: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
- Dependencies: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies
- Secrets: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management
- Chia sẻ: https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app

Gemini API docs: https://ai.google.dev/api/generate-content
Gemini keys: https://ai.google.dev/gemini-api/docs/api-key
Model lifecycle: https://ai.google.dev/gemini-api/docs/deprecations

## Kiểm tra lỗi 403

Mở Vai trò & cấu hình → Kiểm tra key và danh sách model. Nút chỉ gọi API đọc metadata, không sinh nội dung và không gửi policy. Nếu Google có reason phù hợp, app dịch thành thông báo cụ thể về key, service, referrer hoặc IP; nếu không có reason thì vẫn ghi HTTP 403 chung, không suy đoán. Danh sách model đọc thành công chưa chứng minh generateContent được phép hoặc có quota.
