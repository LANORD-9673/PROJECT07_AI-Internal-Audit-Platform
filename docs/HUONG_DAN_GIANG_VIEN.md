# Project 07: LLM hỗ trợ kiểm toán, con người kiểm soát quyết định

Ứng dụng giữ phạm vi kiểm toán phê duyệt và giải ngân khoản vay giả lập của Nexus. Điểm cần trình bày: **LLM chuyển văn bản và bằng chứng thành bản nháp có cấu trúc; Python thực hiện kiểm tra chính xác; kiểm toán viên xác minh và duyệt.**

## 1. Đối chiếu yêu cầu trong cd7_llm.pdf

| Yêu cầu | Chức năng và minh chứng trong bản sửa |
|---|---|
| Đọc ít nhất một policy/procedure | Import TXT/PDF/DOCX; lưu snapshot; LLM1 trích xuất RCM; auditor mở policy gốc |
| RCM có cấu trúc | JSON controls gồm control_id, risk, control, clause, source_quote, test_ids; tải JSON ở giao diện |
| Sinh audit test và evidence cần thu thập | LLM2 tạo purpose, evidence_required, applicability, support; kiểm mapping với RCM |
| Ít nhất hai test trên Excel/CSV | Python thực hiện T01, T02, T03 trên dữ liệu import CSV/XLSX |
| Exceptions đối chiếu criteria | LLM3 nhận RCM đã duyệt, exception đã review và observed values; finding gắn criteria_evidence + evidence_details |
| Ít nhất hai findings có evidence linkage | Validator yêu cầu >=2 findings khi exceptions có >=2 loại test; mỗi finding tham chiếu kết quả thuộc đúng Run/control |
| Summary/report cần auditor review | LLM4 sinh DRAFT; auditor duyệt demo; FINAL thật vẫn bị chặn do chưa có xác thực phân quyền |
| Ít nhất ba tác vụ LLM | Bốn tác vụ: RCM, Test Plan, Findings, Report; bốn prompt riêng, inputs/outputs nối tiếp |
| Thành phần ngoài LLM | Rule Python, validators, SQLite, hash/snapshot, audit trail |
| Độ tin cậy | Thiếu thông tin, mâu thuẫn authority, ngoài phạm vi, quote sai, evidence sai, model offline đều có xử lý |
| Human-in-the-loop | Gates duyệt RCM/PLAN; review exceptions; review findings; review report; kiểm tại backend |
| Đánh giá >=3 tiêu chí | 18 ca rule: accuracy, precision, recall + baseline; Run: quote match, test coverage, evidence integrity, latency; đánh giá ngữ nghĩa LLM cần auditor bổ sung |
| Điểm cộng scoring impact/likelihood | Chưa triển khai trong bản này; không phải yêu cầu bắt buộc |

Các yêu cầu chức năng đã có mã triển khai và integration test. Điều kiện “LLM live chạy tốt” vẫn cần chạy model thật; test stub không thay cho bằng chứng demo live.

## 2. Phân vai trong runtime

| Bước | LLM được tự làm | Python / hệ thống | Con người phải làm |
|---|---|---|---|
| Chuẩn bị đầu vào | Không phê duyệt policy | Import, parse, lưu snapshot/hash | Chọn policy, phạm vi; đối chiếu authority và hiệu lực |
| Policy → RCM | Đề xuất risk/control và trích dẫn | Kiểm JSON, ID, quote tồn tại | Kiểm diễn giải, điều khoản và mapping trước duyệt |
| RCM → Plan | Soạn mục tiêu/thủ tục/evidence | Kiểm control, test_id, coverage T01–T03 | Duyệt tính phù hợp của thủ tục |
| Data → Exceptions | Không quyết định PASS/EXCEPTION | Kiểm rule cố định, đếm và gắn evidence | Xác minh exception; xử lý thiếu dữ liệu/xung đột |
| Exceptions → Findings | Viết draft criteria/condition/risk/recommendation | Kiểm refs/mapping/quote và coverage | Xác nhận kết luận, nguyên nhân, kiến nghị và tác động |
| Findings → Report | Tổng hợp nội dung đã review | Đếm Python, gắn evidence appendix | Review toàn báo cáo; người có thẩm quyền mới được phát hành thật |

LLM không được viết lại rule hoặc ngưỡng đang chạy. T01–T03 là Python do nhóm quản lý. Ngưỡng/hạn mức không được suy từ văn bản tùy ý để áp dụng lên policy khác.

T02 chỉ kiểm hạn mức cá nhân, chi nhánh và hiệu lực theo phương án A của baseline. Không chứng minh role-to-tier hoặc toàn bộ tính hợp lệ pháp lý. PASS không đồng nghĩa kiểm toán viên đã phê duyệt khoản vay.

## 3. Phân biệt LLM trong lập trình và LLM trong ứng dụng

**Trong lập trình:** AI có thể gợi ý kiến trúc, soạn React/FastAPI, viết prompt, đề xuất test và hỗ trợ debug. Nhóm chốt nghiệp vụ, review mã, xác nhận expected outcomes và kiểm thử. Một đoạn Python do AI hỗ trợ viết vẫn là thành phần deterministic khi chạy.

**Trong ứng dụng:** Bốn lời gọi Ollama thực sự nhận dữ liệu và sinh nội dung. Backend ghi model, task, thời gian và kết quả lời gọi. Không có LLM đang chạy thì không thể tạo mới RCM/plan/findings/report bằng AI.

Không có căn cứ để xác định ai viết từng dòng mã của bản gốc từ archive. Nhóm phải bổ sung prompt, lịch sử sửa và review thực tế của thành viên; không tuyên bố một tỷ lệ “AI viết X%” thiếu bằng chứng.

## 4. Kiến trúc và các file cần hiểu

| Thành phần | File | Ý nghĩa |
|---|---|---|
| Giao diện | frontend/src/App.jsx, RoleGuide.jsx | Phân vai, nhập nguồn, review và trình bày evidence |
| API/import | backend/main.py, services/importer.py | Nhập tài liệu/dữ liệu và tạo Run |
| Workflow LLM | backend/services/workflow.py | Bốn prompt, validate, review, report, audit events |
| Rule | backend/services/rule_engine/engine.py | T01 SOD, T02 authority limit, T03 thời gian trước giải ngân |
| Gates thực thi | backend/services/rule_engine/api.py | Kiểm hash policy/authority và phê duyệt RCM/PLAN |
| Lưu trữ | backend/models/db.py | Snapshots, nguồn, results, docs, reviews, events |
| Đánh giá | backend/services/evaluation.py | Ca regression viết tay; không đưa nhãn vào runtime |
| Kiểm thử | backend/tests/ | Import, rule, workflow, negative cases |

## 5. Kịch bản demo khoảng 8–10 phút

1. Mở “Vai trò LLM & con người”. Giải thích hai vai trò AI: hỗ trợ phát triển mã và thực hiện tác vụ runtime.
2. Import ba nguồn demo; chọn snapshots và tạo Run. Đọc policy và authority trước khi cấu hình hash trong `.env`.
3. LLM1 sinh RCM. Mở policy gốc; chỉ ra một quote và test_ids. Auditor nhập tên/lý do, duyệt.
4. LLM2 sinh Plan. Nêu evidence_required/applicability. Auditor duyệt. Thử gọi Python trước gate trong ca kiểm thử để chứng minh backend chặn.
5. Chạy T01–T03. Chỉ ra EXCEPTION, INSUFFICIENT_INFORMATION, BLOCKED hoặc OUT_OF_SCOPE khi có. Mở evidence: dòng dữ liệu/snapshot, không lấy câu trả lời AI làm kết quả test.
6. Có thể chuẩn bị review phần lớn trước buổi trình bày rồi mở một hồ sơ minh họa live. Review mọi exception (CONFIRMED hoặc REJECTED). NEEDS_FOLLOWUP khiến việc sinh finding bị chặn. Không xác nhận hàng loạt mà chưa đọc evidence.
7. LLM3 sinh findings; xem ít nhất hai findings và căn cứ policy + observed values. Auditor CONFIRMED từng finding.
8. LLM4 sinh report. Xem số liệu Python, phụ lục evidence, số results chưa review; duyệt report demo. Giải thích APPROVED review vẫn có publication_status DRAFT.
9. Mở Evaluation: phân biệt chỉ số cấu trúc trên Run, bộ rule regression và đánh giá ngữ nghĩa LLM chưa đo. Xem log lời gọi Ollama thực.
10. Nêu failure case: quote bịa hoặc model offline bị từ chối; sửa review sẽ vô hiệu đầu ra phụ thuộc.

Nếu model sai schema/quote/coverage, trình bày đây là failure case có kiểm soát. Đọc nguồn rồi tạo lại bản nháp; không sửa validator để “demo cho đẹp”. Tạo Run mới khi cần thay RCM/PLAN đã duyệt.

## 6. Đánh giá và cách diễn giải

| Tiêu chí | Cách đo | Giới hạn |
|---|---|---|
| Status accuracy | Số status khớp nhãn viết tay / 18 | Chỉ bộ rule cố định; nhãn chưa được auditor độc lập chứng nhận |
| Precision / recall exceptions | TP/(TP+FP), TP/(TP+FN) | Không phải chất lượng toàn bộ LLM |
| Baseline | Luôn trả PASS trên cùng 18 ca | Baseline tối giản, không đại diện KTV thủ công |
| Quote match | Quote có trong policy / controls | Có quote không có nghĩa diễn giải đúng |
| Coverage | Số test hỗ trợ trong T01–T03 / 3 | Không chứng minh test đủ cho toàn bộ policy |
| Evidence integrity | ID hợp lệ trong Run / IDs tham chiếu | Không chứng minh câu văn findings đúng |
| Processing time | Thời gian gọi Ollama, gồm cả failed calls | Phụ thuộc máy/model; chưa benchmark live tại môi trường sửa |
| LLM semantic quality | Auditor chấm worksheet CSV: groundedness, completeness, hallucination | Cần chạy live rồi ghi review độc lập |

Để hoàn thiện phần Evaluation cho giảng viên: chạy ít nhất một Run live; lưu các JSON của RCM/PLAN và nội dung findings/report; dùng `LLM_EVALUATION_REVIEW.csv`; một thành viên khác đối chiếu nguồn và đánh dấu claim đúng/sai/thiếu. Tính groundedness = grounded claims / claims reviewed; hallucination rate = unsupported claims / claims reviewed; completeness = required items covered / required items. Nếu mẫu số bằng 0, ghi “chưa đo”.

## 7. Giới hạn cần nói rõ

- Model live và scripts Windows chưa được chạy trong môi trường Linux sửa mã; cần thử trên máy trình bày.
- Tên người duyệt là tự khai. Có gate và audit trail, chưa có login/RBAC, chữ ký số hay xác thực danh tính. Audit trail SQLite chưa chống chỉnh sửa bởi quản trị máy.
- Validators kiểm cấu trúc, references và trích dẫn; không tự chứng minh ngữ nghĩa hoặc nguyên nhân/thiệt hại. Báo cáo cần người review.
- Policy trên 25.000 ký tự hoặc hơn 60 exceptions xác nhận bị chặn theo giới hạn demo, không âm thầm bỏ bớt nguồn.
- Không có RAG/vector database, chia context theo batches, xử lý ảnh OCR hay sandbox thực thi mã LLM.
- Không tự động kiểm mọi yêu cầu tín dụng và ngày hiệu lực policy trên từng giao dịch. Bộ demo giao dịch sau ngày hiệu lực; dữ liệu khác cần auditor kiểm tính áp dụng trước khi duyệt.
- Chưa kiểm concurrency phê duyệt/generation giữa nhiều người. Demo phù hợp một nhóm chạy tuần tự trên máy local.
- Dữ liệu 60 khoản vay là giả lập. Không đưa dữ liệu khách hàng thật vào khi chưa có bảo mật/phân quyền phù hợp.

## 8. Câu trình bày ngắn bằng tiếng Anh

“Our LLM extracts controls, drafts the audit plan, writes evidence-linked findings, and summarizes reviewed findings. Python executes the tests and calculates the counts. Auditors approve the plan, verify exceptions, review findings, and review the draft report. AI-assisted code generation is separate from these runtime LLM tasks. Our regression results evaluate Python rules; live LLM quality still requires source-based human assessment.”
