Bài 4: CI/CD với GitHub Actions

**Nhiệm vụ:** Thiết lập CI/CD pipeline với các job bảo mật (Gitleaks, Trivy, TruffleHog, và Bandit) thay thế cho Gosec vì project viết bằng Python.

## 1. Cấu hình Workflow
File `.github/workflows/ci.yml` đã được tạo và thiết lập các job tự động chạy khi có sự kiện Push hoặc Pull Request vào tất cả các nhánh.
Các job bao gồm:
- **Backend Unit Tests:** Chạy bằng Pytest.
- **Gitleaks Secret Scan:** Quét phát hiện mã nhúng bí mật dạng Hardcoded.
- **Trivy Vulnerability Scan:** Quét vulnerabilities (CVEs) trên filesystem.
- **TruffleHog Deep Secret Scan:** Quét mã bí mật sâu vào lịch sử commit.
- **Bandit Python SAST Scan:** Quét lổ hổng bảo mật SAST thay thế chuyên dụng cho Python.

## 2. GitHub Actions Workflow Execution

### 2.1 Workflow đang chạy (In Progress)
Các job tự động xuất kích ngay khi có commit được đẩy lên repository.
![Workflow Running](image4-1.png)

### 2.2 Tất cả các Job hoàn tất thành công (Success)
Các quy trình kiểm tra mã nguồn, test và quét bảo mật đều vượt qua (Pass) không xuất hiện lỗi (Green Checks).
![Workflow Success](image4-2.png)

## 3. Kết quả các Scan Tools Bảo Mật (Security Scan Results)

### 3.1 Gitleaks - Không tìm thấy lỗ hổng bí mật
![Gitleaks Result](image4-3.png)

### 3.2 Trivy - Phân tích lỗ hổng thư viện / Filesystem
Danh sách lỗ hổng (Ví dụ ở đây gói `aiohttp` đã được cập nhật bản vá tránh CVE) đã được phân tích.
![Trivy Result](image4-4.png)

### 3.3 TruffleHog - Quét sâu lịch sử
Dò tìm lịch sử commit để phòng chống bí mật lưu trữ giấu mặt thành công.
![TruffleHog Result](image4-5.png)



### 3.4 Bandit - Python SAST Scan
Quét mã nguồn tĩnh (SAST) chuyên dụng cho Python. Job hoàn thành (Pass) do ta thiết lập tùy chọn `-ll` chỉ báo lỗi và Fail CI/CD nếu phát hiện lỗ hổng ở mức độ **Medium** hoặc **High**. Trong kết quả log, các lỗi được phát hiện đều ở mức độ **Low**, do đó pipeline vẫn pass.
![alt text](image4-6.png)

## Kết luận
CI/CD Pipeline chạy ổn định và đáp ứng 100% yêu cầu bảo mật. Đã xử lý các cảnh báo bảo mật trên code và cài đặt thành công cờ trạng thái Exit-code trong workflow để CI tự đánh giá Fail nếu phát hiện rủi ro.