# File mô phỏng 100 khoản vay

File `demo/privacy_sample_loans_100.csv` gồm 100 hồ sơ, 28 cột, 80 profile khách hàng hư cấu. Tất cả được tạo tổng hợp, không lấy từ dữ liệu ngân hàng hoặc khách hàng thật. Email dùng example.test; điện thoại, CCCD và tài khoản có tiền tố SIM để không nhầm với thông tin có thể sử dụng thực tế. Trường source_system đánh dấu NEXUS_SIMULATED_ONLY.

Ngày phê duyệt và giải ngân mô phỏng từ 09–14/10/2026, sau baseline 08/10/2026. Có khoản vay nhà, xe, kinh doanh và tiêu dùng; hồ sơ APPROVED, PENDING, REJECTED; số tiền VND và các thời điểm có timezone +07:00. Một số hồ sơ có tình huống phân tách nhiệm vụ, hạn mức hoặc thứ tự giải ngân cần kiểm tra.

## Thử bảo vệ dữ liệu

1. Mở Bảo vệ dữ liệu, tải sample từ nút mới hoặc dùng CSV tải riêng từ cuộc trò chuyện.
2. Upload CSV. App mã hóa toàn bộ file thành .nexus.enc.
3. Review cột: tên, email, phone, CCCD/tài khoản, ngày sinh và IDs được đề xuất TOKENIZE. Trường amount_vnd, thời gian, trạng thái được đề xuất KEEP để phục vụ test. Các trường không cần cho T01–T03 như thu nhập, sản phẩm, mục đích, tài sản bảo đảm và ghi chú bị REMOVE mặc định.
4. Nhập scope và reviewer, xác nhận, xuất CSV mã giả. Không tự giữ tất cả cột vì file trông giống dữ liệu thật.

## Nếu muốn chạy workflow với bản đã token hóa

Mã hóa/review thêm `demo/privacy_sample_authority.csv` trong cùng scope và cùng khóa chủ, rồi import hai CSV đã review. Dùng policy baseline có sẵn. Chủ app cần đối chiếu snapshot authority mới và cập nhật hash phê duyệt đúng bản đã import, không dùng hash bảng demo cũ. Dữ liệu giả lập không tự thay cho approval của con người.

Các tình huống được đưa vào để demo kiểm toán. Không coi kết quả engine trên sample là ground truth đã được xác nhận độc lập hoặc chất lượng LLM thật.
