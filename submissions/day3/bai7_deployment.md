# Bài 7: Deploy ứng dụng lên Cloud AWS (Free Tier)

Trong bài tập này, ứng dụng đã được deploy thành công lên một máy ảo Ubuntu (EC2 instance) trên AWS (gói Free Tier). Dưới đây là các bước đã thực hiện:

## 1. Khởi tạo và Truy cập EC2 Instance
- **Khởi tạo EC2:** Đã tạo một máy ảo Ubuntu 22.04 LTS trên AWS.
- **Tạo cặp khoá SSH:** Đã tạo và tải xuống file `.pem` để kết nối an toàn với máy chủ.
- **Cấu hình Security Group (Firewall):** Mở các cổng cần thiết cho ứng dụng: 
  - `22` (SSH)
  - `80` (HTTP)
  - `443` (HTTPS)
  - Cổng của các service backend/frontend.

**Kết nối SSH vào máy ảo Ubuntu:**
![Kết nối SSH thành công](images/image7-1.png)
*(Minh hoạ quá trình đăng nhập qua SSH vào máy chủ).*

## 2. Cài đặt Môi trường (Docker & Docker Compose)
- Đã cài đặt Docker engine và Docker Compose trên máy chủ Ubuntu.
- Clone repository chứa mã nguồn (hoặc upload qua SCP) lên máy chủ.
- Chạy lệnh `./deploy.sh` để khởi tạo các container cho Backend, Frontend và Database.

**Danh sách các container đang chạy:**
![Danh sách Docker containers](images/image7-2.png)
*(Minh hoạ các dịch vụ như frontend, backend, nginx, postgres,... đang ở trạng thái "Up" và hoạt động).*

## 3. Truy cập Ứng dụng qua Public IP
- Sau khi quá trình khởi tạo container hoàn tất, ứng dụng đã có thể truy cập qua trình duyệt.

**Trình duyệt truy cập trực tiếp bằng Public IP:**
![Truy cập qua Public IP](images/image7-3.png)
*(Ứng dụng hiển thị giao diện Frontend đầy đủ khi truy cập qua địa chỉ IP của EC2).*