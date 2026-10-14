# Nhật ký LLM hỗ trợ lập trình và review của nhóm

## Những thay đổi trong lượt chỉnh sửa này

AI hỗ trợ đọc đề bài và mã, đề xuất giải pháp, sửa backend/frontend, viết regression cases và chạy kiểm thử tự động. Không có sub-agent tham gia. Mã gốc không có lịch sử đủ để quy tác giả từng dòng.

| Vấn đề phát hiện | Thay đổi mã | Kiểm tra đã thực hiện | Việc con người còn phải xác nhận |
|---|---|---|---|
| Gate chạy test mặc định tắt | Bật gate mặc định; pin authority SHA256 | Gate default + integration test | Policy, authority và phạm vi demo |
| Plan thiếu mapping/coverage | Kiểm control_id, support, duplicate và đủ T01–T03 | 5 negative plan cases | Chất lượng mục tiêu/thủ tục |
| Finding thiếu policy/actual values | Truyền RCM, observed_values; kiểm quote/control/evidence | Workflow + 4 negative finding cases | Diễn giải criteria/condition và kiến nghị |
| Exceptions chưa review vẫn viết findings | Yêu cầu resolved review cho mọi exception | Workflow chặn trước review | Xác minh mỗi exception |
| Review thay đổi nhưng report cũ còn tồn tại | Invalidate artifacts phụ thuộc; khóa Run khi report đã review | Test đổi review và khóa | Quy trình làm lại Run |
| Evaluation chưa có bộ đo cụ thể | 18 ca viết tay, baseline và structural metrics | 18 regression cases | Nhãn độc lập, chất lượng LLM live |
| Vai trò AI chưa rõ trên giao diện | Trang phân vai runtime và phát triển mã | Frontend build | Kiểm UI trên máy nhóm |
| Hướng dẫn startup không khớp code | .env.example đúng tên biến; PowerShell đọc .env | Review mã tĩnh | Chạy Windows + Ollama |

## Mẫu nhóm bổ sung sau khi chạy live

| Ngày | Thành viên | Công đoạn | Prompt/yêu cầu thực tế | File/output | Lỗi hoặc sửa tay | Ai review, lý do |
|---|---|---|---|---|---|---|
| Điền sau | Điền sau | Điền sau | Dán prompt thực tế hoặc đường dẫn log | Điền sau | Điền sau | Điền sau |

Không ghi một thành viên đã review nếu họ chưa thực hiện. Không gán output test stub là output model live. Chuẩn bị mỗi thành viên giải thích một phần mã, một failure case và một quyết định con người đã thực hiện.
