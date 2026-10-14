# NEXUS — Project 07 trên GitHub

Ứng dụng minh họa kiểm toán nội bộ tín dụng: LLM soạn RCM, kế hoạch, findings và báo cáo; Python kiểm tra dữ liệu; con người review và duyệt các bước. Giữ các chốt duyệt và tài liệu của bản v1.4.

## Các tiện ích đã chuẩn bị

| Thành phần | Mục đích |
|---|---|
| GitHub repository | Lưu code, lịch sử thay đổi và cộng tác qua pull request |
| GitHub Actions | Tự chạy test backend, build React và kiểm tra Docker mỗi lần push/PR |
| GitHub Codespaces | Viết code bằng VS Code trong trình duyệt |
| Docker / Render | Chạy React và FastAPI cùng một địa chỉ web |
| docs/NHAT_KY_LLM_LAP_TRINH.md | Ghi nhận AI hỗ trợ viết code và phần con người kiểm chứng |

GitHub Pages chỉ chạy web tĩnh; app này cần FastAPI và SQLite. Link repo là nơi xem code; link Render là nơi giảng viên sử dụng app. Codespaces cung cấp link xem thử khi môi trường đang chạy, không thay thế hosting lâu dài.

## 1. Đưa code lên GitHub bằng Windows

1. Giải nén gói này. Thư mục gốc phải có `README.md`, `Dockerfile`, `backend`, `frontend`, `.github` và `.devcontainer`.
2. Truy cập https://github.com/new, tạo repo tên `project07-nexus`. Chọn Private nếu nhóm chỉ cần công khai web; chọn Public nếu muốn công khai code. Không tạo README/gitignore/license ở bước này vì gói đã có README và gitignore.
3. Cài Git từ https://git-scm.com/downloads/win nếu máy chưa có. Mở PowerShell tại đúng thư mục gốc đã giải nén.
4. Chạy các lệnh sau, thay `TEN_GITHUB` bằng tên tài khoản thực tế:

```powershell
git init
git add .
git commit -m "Prepare Project 07 for GitHub and cloud demo"
git branch -M main
git remote add origin https://github.com/TEN_GITHUB/project07-nexus.git
git push -u origin main
```

Hoàn tất đăng nhập GitHub qua luồng của Git khi được yêu cầu. Không đưa password/token vào code. Dùng Git thay vì kéo toàn bộ ZIP lên repo: ZIP chưa giải nén không phải mã nguồn có thể deploy, và upload thủ công có thể bỏ sót thư mục cấu hình ẩn.

Nếu repo đã có code, hãy dùng một branch/PR và kiểm tra khác biệt; không force-push theo hướng dẫn tạo repo mới này.

## 2. Chạy và sửa code bằng Codespaces

Trên repo: **Code → Codespaces → Create codespace on main**. Chờ setup cài Python dependencies và build React. Trong terminal tại thư mục gốc:

```bash
bash scripts/start_cloud.sh
```

Mở tab **Ports**, chọn port `8000`, mở link. Port mặc định riêng tư; nếu cần chia sẻ demo, đổi Port Visibility sang Public khi tài khoản/chính sách cho phép. Link chỉ hoạt động khi Codespace và server còn chạy; có hạn mức sử dụng.

Sau khi sửa React, chạy lại `cd frontend && npm run build`, rồi khởi động lại server. Sửa Python cũng cần khởi động lại server. Đặt biến LLM bằng Codespaces secrets hoặc export trước khi chạy; `.env.example` là mẫu, app không tự đọc file `.env`.

## 3. Triển khai web công khai bằng Render

1. Đăng nhập https://dashboard.render.com, kết nối repo GitHub.
2. Chọn **New → Web Service**, chọn repo, **Language: Docker**, Dockerfile tại `./Dockerfile`; Root Directory để trống.
3. Chọn Free cho demo có dữ liệu tạm. Health Check Path: `/api/health`. Giữ command từ Dockerfile.
4. Trong Environment, đặt `PROJECT07_OLLAMA_URL`, `PROJECT07_OLLAMA_MODEL`, `PROJECT07_OLLAMA_TIMEOUT` theo phần 4. Đặt `PROJECT07_OLLAMA_TOKEN` nếu dùng proxy có bearer authentication. Không đưa secrets vào frontend hoặc repo.
5. Deploy, mở URL Render cấp. `/` là giao diện; `/api/health` kiểm tra backend; `/docs` là tài liệu API.
6. Bật auto deploy theo nhu cầu. Kiểm tra Actions đã xanh trước khi triển khai thay đổi dùng để thuyết trình.

Cũng có thể dùng **New → Blueprint** với `render.yaml`. Blueprint khai báo Free, không disk, và sẽ hỏi thông số Ollama. Không cần nhập token nếu endpoint không dùng bearer token; có thể tạo Web Service thủ công để bỏ qua biến này.

Free service có thể ngủ và SQLite mất dữ liệu khi restart/redeploy/spin-down. Muốn giữ audit trail lâu dài, chọn cấu hình hỗ trợ persistent disk, mount `/app/storage`, đặt `PROJECT07_DB_PATH=/app/storage/project07.sqlite3`. Tự xem chi phí hiện hành trước khi chọn gói trả phí. Chưa tạo dịch vụ hoặc phát sinh chi phí từ gói code này.

## 4. Điều kiện để các nút LLM chạy thật trên cloud

Code hiện gọi **Ollama `/api/chat`**, không dùng API OpenAI-compatible và không tự tạo kết quả giả.

`http://127.0.0.1:11434` trên Render/Codespaces trỏ vào môi trường đó, không phải laptop của bạn. Docker của app không cài Ollama và không chứa model. Vì vậy, web có thể mở và import dữ liệu trước khi LLM được cấu hình, nhưng bốn tác vụ LLM sẽ báo lỗi nếu không kết nối được model.

Cần máy chủ Ollama riêng có model, cho phép backend truy cập qua endpoint HTTPS hoặc mạng riêng phù hợp. Nếu dùng máy nhóm, máy phải đang bật, Ollama đang chạy và có kết nối được bảo vệ. Không mở trực tiếp port Ollama không xác thực ra Internet. Biến URL chỉ là base URL (không thêm `/api/chat`); token là bearer token mà proxy của nhóm chấp nhận. App không tự thiết lập proxy hoặc máy chủ model.

Nếu muốn bỏ phụ thuộc máy Ollama của nhóm, bước tiếp theo là chọn nhà cung cấp LLM API rồi thêm adapter phù hợp. Không mặc định một dịch vụ trả phí hoặc thay đổi model khi nhóm chưa chọn. Dù thay nhà cung cấp, vẫn giữ JSON validation, trích dẫn policy, review và nhật ký lời gọi.

## 5. Quy trình cộng tác của nhóm

Tạo issue mô tả thay đổi → tạo branch → dùng LLM hỗ trợ viết code → mở PR → Actions kiểm tra → thành viên đọc diff, đối chiếu nghiệp vụ và test → merge → deploy → thử web thực tế. Con người chịu trách nhiệm phê duyệt code và đầu ra nghiệp vụ; Actions kiểm tra kỹ thuật không chứng minh chất lượng LLM.

App vẫn là demo dùng chung database, người duyệt tự khai tên, chưa có đăng nhập/phân quyền hay tách dữ liệu theo tài khoản. Người truy cập có thể xem/thao tác các run trong cùng instance. Chỉ dùng dữ liệu giả lập trong `demo`; không upload dữ liệu tín dụng thật lên bản demo công khai. Các file policy trong gói cần được nhóm rà soát trước khi chọn công khai repo.

## 6. Kiểm tra tại máy

```bash
python -m pip install -r backend/requirements.txt
python -m pytest backend/tests -q
cd frontend
npm ci
npm run build
```

Chạy Docker từ thư mục gốc nếu máy có Docker:

```bash
docker build -t project07 .
docker run --rm -p 8000:8000 project07
```

Sau đó mở http://localhost:8000. Lệnh ví dụ chưa cấu hình LLM; cần truyền biến môi trường và URL model mà container truy cập được để demo đủ workflow.

## Tài liệu chính thức

- GitHub Pages: https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages
- Codespaces ports: https://docs.github.com/en/codespaces/developing-in-a-codespace/forwarding-ports-in-your-codespace
- Render Docker: https://render.com/docs/docker
- Render Free limitations: https://render.com/docs/free
- Render persistent disks: https://render.com/docs/disks

Xem `docs/HUONG_DAN_GIANG_VIEN.md` và `README_START_HERE.txt` để hiểu workflow nghiệp vụ và cách chạy local Windows bản gốc.
