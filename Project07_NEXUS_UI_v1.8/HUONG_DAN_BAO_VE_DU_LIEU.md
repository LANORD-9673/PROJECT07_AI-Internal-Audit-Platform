> Lịch sử v1.6. Với v1.7, đọc HUONG_DAN_XUAT_V1_7.md: MASK giữ cột và mapping mới chỉ tải riêng cho auditor, không lưu vault. Phần tạo khóa/giải mã archive vẫn áp dụng.

# Project 07 v1.6 — Bảo vệ dữ liệu đầu vào

## Kết quả của tính năng

Upload ở màn hình **Bảo vệ dữ liệu** tự tạo file `.nexus.enc` mã hóa toàn bộ nội dung gốc bằng AES-256-GCM. Không dùng LLM để quyết định thuật toán hoặc đọc dữ liệu gốc. File loại bất kỳ được hỗ trợ ở lớp mã hóa, tối đa 10 MB.

CSV/XLSX còn được đọc để đề xuất cách xử lý cột. XLSX dùng sheet đầu tiên; file gốc nhiều sheet vẫn được mã hóa nguyên vẹn. Không tuyên bố hệ thống hiểu mọi bộ dữ liệu hoặc phát hiện mọi thông tin cá nhân.

| Xử lý | Áp dụng | Ý nghĩa |
|---|---|---|
| AES-256-GCM | Toàn bộ file gốc và bảng ánh xạ | Mã hóa có kiểm tra toàn vẹn; cần khóa để khôi phục |
| TOKENIZE | Cột có dấu hiệu ID, tên, liên hệ… | HMAC theo phạm vi kiểm toán, thay giá trị bằng mã `NX_…` |
| REMOVE | Cột chưa nhận diện hoặc không cần | Loại khỏi bản CSV dùng phân tích |
| KEEP | Số tiền/thời gian/trạng thái nghiệp vụ được đề xuất hoặc auditor chọn | Giữ giá trị có thể đọc, chỉ xuất sau khi auditor review |

TOKENIZE là **mã giả**, không phải ẩn danh tuyệt đối. Vẫn lộ việc một giá trị xuất hiện nhiều lần, và dữ liệu số/thời gian có thể giúp tái nhận dạng. KEEP không phải mã hóa từng ô trong CSV. File gốc vẫn được mã hóa đầy đủ, gồm mọi cột.

## Khóa và thư mục máy chủ

1. Chủ app tự tạo **khóa chủ** bằng lệnh trên máy riêng:

```powershell
python scripts/generate_vault_key.py
```

2. Sao chép kết quả Base64 vào **Streamlit → Settings → Secrets**:

```toml
PROJECT07_VAULT_MASTER_KEY = "CHUOI_BASE64_VUA_TAO"
PROJECT07_GEMINI_MAX_RETRIES = "2"
```

Giữ các biến Gemini và phê duyệt hiện có. Không đưa khóa chủ vào GitHub, chat, README, log hoặc file CSV. Lệnh trên in một bí mật thật: chạy riêng trên máy chủ app, không ghi màn hình/chia sẻ output. Mẫu Secrets trong gói không chứa khóa thật.

3. Folder mặc định là `backend/private_vault`, có 3 thư mục:

| Thư mục | Nội dung |
|---|---|
| `encrypted` | File gốc mã hóa, đặt tên bằng UUID; tên file gốc nằm bên trong ciphertext |
| `keys` | Khóa AES riêng của mỗi file đã được mã hóa bằng khóa chủ |
| `maps` | Bảng token → giá trị gốc và ghi nhận phương án/người review, được mã hóa bằng khóa riêng từng file |

Khóa từng file tự sinh; không xuất ra web. Khóa chủ nằm trong Secrets/biến môi trường, tách khỏi folder chứa khóa bọc. Linux đặt directory mode `0700`, file mode `0600`; không có endpoint công khai tải khóa, mapping hoặc giải mã. Windows `chmod` không tương đương ACL NTFS: người quản trị phải đặt quyền thư mục riêng phù hợp trước khi dùng thực tế.

Chủ app có thể cấu hình `PROJECT07_VAULT_DIR` thành đường dẫn private persistent storage trên máy chủ. Không đặt vault trong GitHub, web static directory, hoặc shared folder. Bảo vệ cả parent directory và account chạy server.

**Folder + encryption không bảo đảm chống mọi trường hợp đánh cắp.** Kẻ có quyền quản trị server/process hoặc đọc được cả khóa chủ và vault vẫn có thể khôi phục dữ liệu. Dữ liệu gốc được đọc trong RAM khi xử lý. Production cần xác thực, phân quyền theo auditor/tenant, quản lý khóa chuyên dụng, cơ chế sao lưu và kiểm tra vận hành. Bản demo chưa có các lớp này.

## Streamlit Cloud và sao lưu

Không dựa vào folder local của Streamlit Community Cloud để lưu khóa lâu dài. Tính năng được xây dựng cho vault local riêng tư; chưa có adapter Cloud KMS/Secret Manager/object storage. Khi app bị redeploy/recreate, dữ liệu local có thể không còn, dù bạn giữ khóa chủ trong Secrets.

Giữ file mã hóa tải xuống **và** sao lưu riêng thư mục `keys`, `maps` cùng hồ sơ khóa chủ theo quyền quản trị. Chỉ có file `.nexus.enc` và khóa chủ mà thiếu wrapped key trong `keys` vẫn không giải mã được. Mất khóa chủ cũng không khôi phục được. Không thay khóa chủ hiện tại mà chưa di chuyển/rewrap các khóa cũ.

Muốn vận hành với dữ liệu khách hàng thật, triển khai server có private persistent disk và quản lý khóa/đăng nhập phù hợp, hoặc xây adapter lưu trữ/khóa cloud. Bản Community Cloud hiện tại chỉ demo dữ liệu giả lập. Không tự tạo tài khoản, dịch vụ trả phí hoặc giả định có persistent disk trong gói này.

## Auditor sử dụng

1. Mở **Bảo vệ dữ liệu**, upload file. Nếu chưa cấu hình khóa chủ, tính năng chặn mã hóa; không tự tạo khóa chủ tạm.
2. Tải file `.nexus.enc` đã mã hóa. Web tự lưu wrapped key phía máy chủ.
3. Với CSV/XLSX, xem phương án xử lý từng cột. Có thể đổi TOKENIZE/REMOVE/KEEP.
4. Nhập **mã phạm vi kiểm toán** và **người review**, xác nhận đã đối chiếu file gốc, rồi bấm duyệt.
5. Tải CSV mã giả hoặc import trực tiếp bản đã review vào loans/authority.

Dùng cùng phạm vi cho các file cần liên kết. `maker_id`, `approver_id`, `employee_id` có cùng giá trị nguyên văn sẽ nhận cùng token; do đó vẫn kiểm tra phân tách nhiệm vụ/phân quyền được. Giữ cùng khóa chủ trong cả phiên kiểm toán. Giá trị khác nhau hoặc scope khác nhau có token khác nhau. Cơ chế này giữ tính bằng nhau, không giữ thứ tự số; không dùng TOKENIZE cho amount nếu muốn Python tính toán.

ID token hóa còn là dữ liệu cá nhân giả danh nếu có thể liên kết trở lại. Chỉ giữ số tiền, thời gian, trạng thái khi có mục đích kiểm toán và auditor đã review. CSV tải xuống có escape dấu bắt đầu công thức để giảm rủi ro spreadsheet formula injection; vì vậy các ô bắt đầu `=`, `+`, `-`, `@` có thể được thêm dấu nháy đơn trong bản CSV.

Phương án cột chỉ được đề xuất bằng quy tắc tên cột; có thể nhận diện nhầm. Cột lạ mặc định REMOVE. Auditor phải đọc/đối chiếu nguồn và sửa phương án cần thiết. Không có guarantee privacy tự động cho mọi dataset.

## Liên kết workflow cũ

- Màn hình import bộ demo 60 khoản vay vẫn dùng dữ liệu giả lập.
- Upload dữ liệu loans/authority tùy chỉnh qua UI được chuyển sang bước bảo vệ/review; import chỉ dùng bản CSV đã được duyệt.
- Policy import hiện tại vẫn là nguồn policy của workflow; văn bản policy được gửi tới Gemini trong LLM1. Tính năng mới không tự làm sạch nội dung policy/PDF/DOCX thành dữ liệu đọc được bởi LLM.
- Các API backend gốc còn phục vụ kiểm thử/development và không được coi là dịch vụ production xử lý dữ liệu thật đã xác thực. Triển khai Streamlit gọi API nội bộ, không mở một API server riêng.
- Normal SQLite chỉ chứa bản CSV được import, gồm token và các cột KEEP. Không phải mọi trường SQLite đều được mã hóa; KEEP vẫn đọc được bởi người có quyền truy cập app/database.
- T01–T03 vẫn chỉ hiểu schema/baseline Project 07; mã hóa file bất kỳ không làm test engine tự hiểu ngành/schema mới.
- Authority sau token hóa có hash mới. Chủ app cần review đúng snapshot/bảng authority và cập nhật approval hash tương ứng, không tự phê duyệt vì có mã hóa.
- Gemini thấy các dữ liệu đã import theo tác vụ; không thấy wrapped keys/bảng ánh xạ hay file gốc từ module vault. Con người vẫn duyệt RCM/Plan/Exceptions/Findings/Report.

## Khôi phục riêng cho quản trị viên

Chỉ chạy local hoặc terminal quản trị máy chủ, không có nút public decrypt. Cấu hình `PROJECT07_VAULT_MASTER_KEY` và `PROJECT07_VAULT_DIR` trong môi trường của terminal (script không tự đọc Streamlit Secrets). Dùng:

```powershell
python scripts/restore_protected.py downloaded-file.nexus.enc restored-private-file.csv
```

Đích do admin chỉ định, không ghi đè file có sẵn. Module có hàm `restore_mapping(reference)` cho quản trị viên kiểm chứng riêng; không expose qua API/web. File được khôi phục là plaintext và phải được bảo vệ/xóa theo quy trình quản trị riêng.

## Gemini 503

Lỗi 503 báo quá tải model là vấn đề dịch vụ, độc lập với mã hóa. Default `PROJECT07_GEMINI_MAX_RETRIES=2`: tối đa 3 lần gọi, nghỉ khoảng 1 rồi 2 giây cộng jitter. Chỉ retry HTTP 500/502/503/504. 403, 429, network timeout và schema lỗi không tự retry; không tự đổi model. Retry có thể phát sinh thêm lần gọi/quota theo cách Google xử lý; có thể đặt giá trị 0 để tắt.

Log LLM hiện ghi một logical task, latency tính cả các lần thử; không phải log riêng từng HTTP attempt. Khi hết số lần thử mà vẫn 503, bước đó dừng; bản nháp RCM đã duyệt và các bước trước giữ nguyên. Không có guarantee retry sẽ hết quá tải.

## Nguồn kỹ thuật

- AEAD/AES-GCM: https://cryptography.io/en/latest/hazmat/primitives/aead/
- Key separation/storage: https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html
- Gemini retry: https://ai.google.dev/gemini-api/docs/troubleshooting
