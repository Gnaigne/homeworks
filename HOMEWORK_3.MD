# 📝 Bài Tập Về Nhà - Sessions 5-7 (Day 3)

**Deadline:** Trước ngày thứ 7  
**Cách nộp:** Push lên Git repository cá nhân tại branch homework. Mời dinhmanhtan (dmtangtnd@gmail.com) vào project. Tiếp tục code ở nhánh homework. Tạo pull request từ branch homework vào main. Set reviewer là dinhmanhtan  
**Note**: Project có thể viết bằng ngôn ngữ khác không bắt buộc phải dùng Go. Nếu sử dụng ngôn ngữ khác cần mô tả cách cài đặt và chạy project

---

## 📑 Mục Lục

- [Yêu Cầu Chung](#yêu-cầu-chung)
- [📤 Nộp Bài](#-nộp-bài)
- [Bài 1: Mở rộng Scan API (25 điểm)](#bài-1-mở-rộng-scan-api-25-điểm)
- [Bài 2: Viết Unit Tests (25 điểm)](#bài-2-viết-unit-tests-25-điểm)
- [Bài 3: Tích hợp Frontend (20 điểm)](#bài-3-tích-hợp-frontend-20-điểm)
- [Bài 4: CI/CD với GitHub Actions (25 điểm)](#bài-4-cicd-với-github-actions-25-điểm)
- [Bài 5: Deploy với Docker Compose (15 điểm)](#bài-5-deploy-với-docker-compose-15-điểm)
- [Bài 6: Tính năng EASM mới (15 điểm) - BONUS 🌟](#bài-6-tính-năng-easm-mới-15-điểm---bonus-)
- [Bài 7: Deploy lên Cloud VM (20 điểm) - BONUS 🌟](#bài-7-deploy-lên-cloud-vm-20-điểm---bonus-)
- [Bài 8: Domain & TLS/HTTPS (15 điểm) - BONUS 🌟](#bài-8-domain--tlshttps-15-điểm---bonus-)
- [Bài 9: Auto Deploy on Merge (15 điểm) - BONUS 🌟](#bài-9-auto-deploy-on-merge-15-điểm---bonus-)
- [📊 Chấm Điểm](#-chấm-điểm)
- [💡 Gợi Ý & Tips](#-gợi-ý--tips)
- [📚 Tài Liệu Tham Khảo](#-tài-liệu-tham-khảo)

---

## Yêu Cầu Chung

- ✅ Code phải chạy được không có lỗi
- ✅ Follow Clean Architecture như đã học
- ✅ Có error handling đầy đủ
- ✅ Test được bằng curl hoặc Postman
- ✅ Code có comments giải thích logic phức tạp
- ✅ README.md mô tả cách cài đặt và chạy project
- ✅ Cập nhật tài liệu api.yml cho những thay đổi

---

## 📤 Nộp Bài

### Cần nộp:

**File `SUBMISSION.md`** hoặc **`SUBMISSION.pdf`** gồm:

```markdown
# Homework Submission - Day 3

**Họ tên:** [Tên của bạn]

## Các bài đã hoàn thành

- [x] Bài 1: Mở rộng Scan API
- [x] Bài 2: Viết Unit Tests
- [x] Bài 3: Tích hợp Frontend
- [x] Bài 4: CI/CD với GitHub Actions
- [x] Bài 5: Deploy với Docker Compose
- [ ] Bài 6: Tính năng EASM mới (Bonus)
- [ ] Bài 7: Deploy lên Cloud VM (Bonus)
- [ ] Bài 8: Domain & TLS/HTTPS (Bonus)
- [ ] Bài 9: Auto Deploy on Merge (Bonus)

## Link Repository

[Link GitHub repository]

## Link Demo (nếu có)

[Link deployed application]
```

Mỗi bài cần 1 file Test screenshots hoặc command outputs chứng minh.
File này đặt trong thư mục [homeworks/submissions/day3](../submissions/day3)

---

## Bài 1: Mở rộng Scan API (25 điểm)

**Yêu cầu:** Thêm các loại scan mới cho hệ thống EASM

### Existing Scan Types (đã có sẵn)

Hệ thống hiện tại hỗ trợ các scan types sau (passive scans - an toàn):

| Scan Type    | Mô tả                          | Asset Type |
| ------------ | ------------------------------ | ---------- |
| `dns`        | DNS record lookup (A, MX, NS)  | domain     |
| `whois`      | WHOIS registration information | domain     |
| `subdomain`  | Subdomain enumeration          | domain     |
| `cert_trans` | Certificate Transparency logs  | domain     |
| `asn`        | ASN lookup                     | ip         |
| `all`        | Chạy tất cả passive scans      | domain     |

### API Base - Start Scan

- **Endpoint:** `POST /assets/{id}/scan`
- **Request body:**
  ```json
  {
    "scan_type": "dns"
  }
  ```
- **Response:** 202 Accepted
  ```json
  {
    "id": "987e6543-e21b-34c5-d678-426614174999",
    "asset_id": "123e4567-e89b-12d3-a456-426614174000",
    "scan_type": "dns",
    "status": "pending",
    "started_at": "2026-03-09T10:00:00Z",
    "ended_at": null,
    "error": "",
    "results": 0,
    "created_at": "2026-03-09T10:00:00Z"
  }
  ```

### Scan Workflow

```
1. POST /assets/{id}/scan       → Start scan (returns job_id)
2. GET /scan-jobs/{job_id}      → Poll for status
3. GET /scan-jobs/{job_id}/results → Get results when completed
```

### Scan Status Values

| Status      | Mô tả                      |
| ----------- | -------------------------- |
| `pending`   | Job queued but not started |
| `running`   | Job is executing           |
| `completed` | Job finished successfully  |
| `failed`    | Job encountered error      |
| `partial`   | Job completed with errors  |

---

### 1.1 IP Scan (Geolocation & ASN) - MỚI

Mở rộng scan cho IP assets với thông tin geolocation và ASN.

- **Endpoint:** `POST /assets/{id}/scan`
- **Request body:**
  ```json
  {
    "scan_type": "ip"
  }
  ```
- **Response:** 202 Accepted
  ```json
  {
    "id": "987e6543-e21b-34c5-d678-426614174999",
    "asset_id": "123e4567-e89b-12d3-a456-426614174000",
    "scan_type": "ip",
    "status": "pending",
    "started_at": "2026-03-09T10:00:00Z",
    "ended_at": null,
    "error": "",
    "results": 0,
    "created_at": "2026-03-09T10:00:00Z"
  }
  ```

**Scan Result Data (GET /scan-jobs/{id}/results):**

```json
{
  "job_id": "987e6543-e21b-34c5-d678-426614174999",
  "scan_type": "ip",
  "results": [
    {
      "ip_address": "104.21.32.1",
      "geolocation": {
        "country": "US",
        "country_code": "US",
        "city": "San Francisco",
        "region": "California",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "isp": "Cloudflare, Inc.",
        "org": "Cloudflare, Inc."
      },
      "asn": {
        "number": 13335,
        "name": "CLOUDFLARENET",
        "description": "Cloudflare, Inc."
      },
      "reverse_dns": "one.one.one.one",
      "created_at": "2026-03-09T10:00:15Z"
    }
  ]
}
```

### 1.2 Port Scan - MỚI ⚠️

**⚠️ CẢNH BÁO BẢO MẬT:** Port scan là **ACTIVE SCAN** - chỉ được thực hiện trên hệ thống bạn sở hữu hoặc có quyền scan!

- **Endpoint:** `POST /assets/{id}/scan`
- **Request body:**
  ```json
  {
    "scan_type": "port"
  }
  ```
- **Response:** 202 Accepted
  ```json
  {
    "id": "987e6543-e21b-34c5-d678-426614174999",
    "asset_id": "123e4567-e89b-12d3-a456-426614174000",
    "scan_type": "port",
    "status": "pending",
    "started_at": "2026-03-09T10:00:00Z",
    "ended_at": null,
    "error": "",
    "results": 0,
    "created_at": "2026-03-09T10:00:00Z"
  }
  ```

**Scan Result Data (GET /scan-jobs/{id}/results):**

```json
{
  "job_id": "987e6543-e21b-34c5-d678-426614174999",
  "scan_type": "port",
  "results": [
    {
      "ip_address": "127.0.0.1",
      "open_ports": [
        {
          "port": 22,
          "protocol": "tcp",
          "state": "open",
          "service": "ssh",
          "version": "OpenSSH 8.9p1"
        },
        {
          "port": 80,
          "protocol": "tcp",
          "state": "open",
          "service": "http",
          "version": "nginx/1.18.0"
        },
        {
          "port": 443,
          "protocol": "tcp",
          "state": "open",
          "service": "https",
          "version": ""
        },
        {
          "port": 5432,
          "protocol": "tcp",
          "state": "open",
          "service": "postgresql",
          "version": "PostgreSQL 15.0"
        }
      ],
      "closed_ports": 996,
      "total_scanned": 1000,
      "scan_duration_ms": 5432,
      "created_at": "2026-03-09T10:00:15Z"
    }
  ]
}
```

⚠️ **Yêu cầu bảo mật:**

- CHỈ scan: `127.0.0.1` (localhost), `10.x.x.x`, `172.16-31.x.x`, `192.168.x.x`
- KHÔNG scan hệ thống bên ngoài mà không có permission
- Implement safety check trong code để từ chối scan public IPs

### 1.3 SSL/TLS Certificate Scan - (Bonus) ⚠️

- **Endpoint:** `POST /assets/{id}/scan`
- **Request body:**
  ```json
  {
    "scan_type": "ssl"
  }
  ```
- **Response:** 202 Accepted
  ```json
  {
    "id": "987e6543-e21b-34c5-d678-426614174999",
    "asset_id": "123e4567-e89b-12d3-a456-426614174000",
    "scan_type": "ssl",
    "status": "pending",
    "started_at": "2026-03-09T10:00:00Z",
    "ended_at": null,
    "error": "",
    "results": 0,
    "created_at": "2026-03-09T10:00:00Z"
  }
  ```

**Scan Result Data (GET /scan-jobs/{id}/results):**

```json
{
  "job_id": "987e6543-e21b-34c5-d678-426614174999",
  "scan_type": "ssl",
  "results": [
    {
      "domain": "example.com",
      "certificate": {
        "subject": "CN=example.com",
        "issuer": "CN=Let's Encrypt Authority X3, O=Let's Encrypt, C=US",
        "serial_number": "03:ab:cd:ef:12:34:56:78",
        "valid_from": "2026-01-01T00:00:00Z",
        "valid_until": "2026-04-01T00:00:00Z",
        "days_until_expiry": 45,
        "is_expired": false,
        "is_self_signed": false,
        "san": ["example.com", "www.example.com", "api.example.com"]
      },
      "connection": {
        "tls_version": "TLS 1.3",
        "cipher_suite": "TLS_AES_256_GCM_SHA384",
        "key_exchange": "X25519"
      },
      "grade": "A",
      "issues": [],
      "created_at": "2026-03-09T10:00:15Z"
    }
  ]
}
```

### 1.4 Technology Detection Scan - (Bonus)

- **Endpoint:** `POST /assets/{id}/scan`
- **Request body:**
  ```json
  {
    "scan_type": "tech"
  }
  ```
- **Response:** 202 Accepted
  ```json
  {
    "id": "987e6543-e21b-34c5-d678-426614174999",
    "asset_id": "123e4567-e89b-12d3-a456-426614174000",
    "scan_type": "tech",
    "status": "pending",
    "started_at": "2026-03-09T10:00:00Z",
    "ended_at": null,
    "error": "",
    "results": 0,
    "created_at": "2026-03-09T10:00:00Z"
  }
  ```

**Scan Result Data (GET /scan-jobs/{id}/results):**

```json
{
  "job_id": "987e6543-e21b-34c5-d678-426614174999",
  "scan_type": "tech",
  "results": [
    {
      "domain": "example.com",
      "technologies": [
        {
          "name": "nginx",
          "category": "Web Server",
          "version": "1.18.0",
          "confidence": 100
        },
        {
          "name": "React",
          "category": "JavaScript Framework",
          "version": "18.2.0",
          "confidence": 95
        },
        {
          "name": "Cloudflare",
          "category": "CDN",
          "version": null,
          "confidence": 100
        }
      ],
      "headers": {
        "server": "nginx/1.18.0",
        "x-powered-by": "Express",
        "content-type": "text/html; charset=utf-8",
        "x-frame-options": "SAMEORIGIN"
      },
      "meta_tags": {
        "generator": "React 18.2.0",
        "viewport": "width=device-width, initial-scale=1"
      },
      "created_at": "2026-03-09T10:00:15Z"
    }
  ]
}
```

---

### API Endpoints Summary

| Method | Endpoint                  | Mô tả                        |
| ------ | ------------------------- | ---------------------------- |
| POST   | `/assets/{id}/scan`       | Start a scan job             |
| GET    | `/scan-jobs/{id}`         | Get scan job status          |
| GET    | `/scan-jobs/{id}/results` | Get scan job results         |
| GET    | `/assets/{id}/scans`      | List all scans for an asset  |
| GET    | `/assets/{id}/results`    | Get ALL results for an asset |
| GET    | `/assets/{id}/dns`        | Get DNS records for an asset |
| GET    | `/assets/{id}/whois`      | Get WHOIS for an asset       |
| GET    | `/assets/{id}/subdomains` | Get subdomains for an asset  |

### Yêu cầu kỹ thuật:

- Tạo file scanner mới cho mỗi loại: `ip_scanner.go`, `port_scanner.go`, `ssl_scanner.go`, `tech_scanner.go`
- Implement interface Scanner cho tất cả
- Cập nhật `scan_type` enum trong database/model (thêm: `ip`, `port`, `ssl`, `tech`)
- Handle timeout và errors gracefully
- Log scan activities
- Implement safety checks cho active scans (port, ssl)

**Test:**

```bash
# 1. Create assets
# Domain asset
DOMAIN_ASSET=$(curl -s -X POST http://localhost:8080/assets \
  -H "Content-Type: application/json" \
  -d '{"name":"google.com","type":"domain"}' | jq -r '.id')

echo "Domain Asset ID: $DOMAIN_ASSET"

# IP asset
IP_ASSET=$(curl -s -X POST http://localhost:8080/assets \
  -H "Content-Type: application/json" \
  -d '{"name":"127.0.0.1","type":"ip"}' | jq -r '.id')

echo "IP Asset ID: $IP_ASSET"

# 2. Start scans and get job IDs
# DNS Scan (existing)
DNS_JOB=$(curl -s -X POST "http://localhost:8080/assets/$DOMAIN_ASSET/scan" \
  -H "Content-Type: application/json" \
  -d '{"scan_type":"dns"}' | jq -r '.id')

echo "DNS Scan Job: $DNS_JOB"

# IP Scan (new)
IP_JOB=$(curl -s -X POST "http://localhost:8080/assets/$IP_ASSET/scan" \
  -H "Content-Type: application/json" \
  -d '{"scan_type":"ip"}' | jq -r '.id')

echo "IP Scan Job: $IP_JOB"

# Port Scan (new - only localhost!)
PORT_JOB=$(curl -s -X POST "http://localhost:8080/assets/$IP_ASSET/scan" \
  -H "Content-Type: application/json" \
  -d '{"scan_type":"port"}' | jq -r '.id')

echo "Port Scan Job: $PORT_JOB"

# SSL Scan (new)
SSL_JOB=$(curl -s -X POST "http://localhost:8080/assets/$DOMAIN_ASSET/scan" \
  -H "Content-Type: application/json" \
  -d '{"scan_type":"ssl"}' | jq -r '.id')

echo "SSL Scan Job: $SSL_JOB"

# Tech Scan (new)
TECH_JOB=$(curl -s -X POST "http://localhost:8080/assets/$DOMAIN_ASSET/scan" \
  -H "Content-Type: application/json" \
  -d '{"scan_type":"tech"}' | jq -r '.id')

echo "Tech Scan Job: $TECH_JOB"

# 3. Check scan status
sleep 5
curl -s "http://localhost:8080/scan-jobs/$DNS_JOB" | jq

# 4. Get scan results
curl -s "http://localhost:8080/scan-jobs/$DNS_JOB/results" | jq

# 5. Get all results for an asset
curl -s "http://localhost:8080/assets/$DOMAIN_ASSET/results" | jq

# 6. List all scans for an asset
curl -s "http://localhost:8080/assets/$DOMAIN_ASSET/scans" | jq
```

---

## Bài 2: Viết Unit Tests (25 điểm)

**Yêu cầu:** Viết comprehensive unit tests cho application

### 2.1 Model Tests

Tạo file `internal/model/asset_test.go`:

```go
func TestAssetValidation(t *testing.T) {
    tests := []struct {
        name    string
        asset   Asset
        wantErr bool
    }{
        {
            name:    "valid domain asset",
            asset:   Asset{Name: "example.com", Type: "domain"},
            wantErr: false,
        },
        {
            name:    "invalid asset type",
            asset:   Asset{Name: "test", Type: "invalid"},
            wantErr: true,
        },
        // Add more test cases...
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            // Test implementation
        })
    }
}
```

### 2.2 Handler Tests (Bonus)

Tạo file `internal/handler/asset_handler_test.go`:

```go
func TestCreateAssetHandler(t *testing.T) {
    // Setup mock service
    mockService := &MockAssetService{}
    handler := NewAssetHandler(mockService)

    // Create test request
    body := `{"name":"test.com","type":"domain"}`
    req := httptest.NewRequest("POST", "/assets", strings.NewReader(body))
    req.Header.Set("Content-Type", "application/json")

    // Create response recorder
    rr := httptest.NewRecorder()

    // Call handler
    handler.Create(rr, req)

    // Assert response
    assert.Equal(t, http.StatusCreated, rr.Code)
}
```

### 2.3 Service Tests (Bonus)

Tạo file `internal/service/asset_service_test.go`:

```go
func TestAssetService_Create(t *testing.T) {
    // Setup mock storage
    mockStorage := &MockAssetStorage{}
    service := NewAssetService(mockStorage)

    // Test cases...
}
```

### 2.4 Scanner Tests

Tạo tests cho mỗi scanner type:

```go
func TestDNSScanner_Scan(t *testing.T) {
    scanner := NewDNSScanner()

    result, err := scanner.Scan("google.com")

    assert.NoError(t, err)
    assert.NotEmpty(t, result.Records)
}
```

### Yêu cầu kỹ thuật:

- Bắt buộc viết unit test cho 2.1,2.4
- Phần 2.2,2.3 sẽ có điểm bonus nếu thực hiện
- Coverage test lớn sẽ có thêm bonus điểm

**Commands:**

```bash
# Run all tests
go test ./...

# Run with coverage
go test -cover ./...

# Generate HTML coverage report
go test -coverprofile=coverage.out ./...
go tool cover -html=coverage.out -o coverage.html

# Run specific test
go test -v -run TestCreateAssetHandler ./internal/handler/...

# Run benchmarks
go test -bench=. ./...
```

---

## Bài 3: Tích hợp Frontend (20 điểm)

**Yêu cầu:** Kết nối backend API với frontend (có thể sử dụng frontend có sẵn tại session7 hoặc tự build)

### 3.1 Cấu hình CORS

Thêm CORS middleware vào backend:

```go
func CORSMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("Access-Control-Allow-Origin", "*")
        w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")

        if r.Method == "OPTIONS" {
            w.WriteHeader(http.StatusOK)
            return
        }

        next.ServeHTTP(w, r)
    })
}
```

### 3.2 Frontend Features cần hoạt động:

- [ ] Hiển thị danh sách assets
- [ ] Thêm asset mới
- [ ] Xóa asset
- [ ] Khởi tạo scan
- [ ] Xem kết quả scan
- [ ] Dashboard thống kê

### 3.3 Cấu hình Environment

Frontend `.env`:

```env
VITE_API_URL=http://localhost:8080
```

```bash
# 1. Start backend
cd app/session7-deployment/backend
go run ./cmd/server

# 2. Start frontend (new terminal)
cd app/session7-deployment/frontend
npm install
npm run dev

# 3. Open browser at http://localhost:5173

# Test scenarios:
# - Create new asset via UI
# - View asset list
# - Start a scan
# - View scan results
# - Delete an asset
```

**Screenshot requirements:**

- Trang danh sách assets có data
- Form tạo asset hoạt động
- Scan results hiển thị đúng

---

## Bài 4: CI/CD với GitHub Actions (25 điểm)

**Yêu cầu:** Thiết lập CI/CD pipeline với các job bảo mật. Có thể chọn thêm một job bảo mật bất kỳ

### 4.1 Cấu trúc Workflow

Tạo/cập nhật file `.github/workflows/ci.yml`:
Tham khảo [./github/workflows/session7-deployment.yml](./github/workflows/session7-deployment.ym)

### 4.2 Security Scan Tools

**Gosec** - Go Security Scanner:

- Phát hiện SQL injection
- Phát hiện hardcoded credentials
- Phát hiện unsafe operations

**Trivy** - Vulnerability Scanner:

- Scan dependencies for CVEs
- Scan Docker images
- Scan filesystem

**Gitleaks** - Secret Detection:

- Phát hiện API keys
- Phát hiện passwords
- Phát hiện tokens

**TruffleHog** - Secret Scanner:

- Deep commit history scan
- Entropy-based detection
- Regex patterns

### Test:

```bash
# Trigger workflow bằng push commit
**Lưu ý**: Cần set rule bắt buộc pass các cicd job mới được merge request tại phần Setting -> Rules -> Rulesets
Tạo pull request vào main

# Xem results tại:
# https://github.com/<username>/<repo>/actions
```

**Screenshot requirements:**

- GitHub Actions workflow running
- All jobs passed (green checks)
- Security scan results

---

## Bài 5: Deploy với Docker Compose (15 điểm)

**Yêu cầu:** Deploy full application stack bằng Docker Compose

**Screenshot requirements:**

- `docker-compose ps` showing all services running
- Frontend accessible at localhost:3000
- Backend health check passing

---

## Bài 6: Tính năng EASM mới (15 điểm) - BONUS 🌟

**Yêu cầu:** Implement thêm tính năng nâng cao cho EASM

### Gợi ý tính năng:

#### 6.1 Scheduled Scans

Tự động scan assets theo schedule

#### 6.2 Asset Groups/Tags

Nhóm assets theo tags:

#### 6.3 Alerts/Notifications

Cảnh báo khi phát hiện issues:

#### 6.4 Scan Comparison

So sánh kết quả scan theo thời gian:

#### 6.5 Export Reports

Export scan results dạng PDF/CSV:

## Bài 7: Deploy lên Cloud VM (20 điểm) - BONUS 🌟

**Yêu cầu:** Deploy application lên cloud VM thật

### 7.1 Các Cloud Provider Options

| Provider         | Free Tier           | Link                               |
| ---------------- | ------------------- | ---------------------------------- |
| **Oracle Cloud** | Always Free 2 VMs   | https://www.oracle.com/cloud/free/ |
| **Google Cloud** | $300 credit 90 days | https://cloud.google.com/free      |
| **AWS**          | 12 months t2.micro  | https://aws.amazon.com/free/       |
| **Azure**        | $200 credit 30 days | https://azure.microsoft.com/free/  |
| **DigitalOcean** | $200 credit 60 days | https://www.digitalocean.com/      |
| **Vultr**        | $100 credit         | https://www.vultr.com/             |
| **Linode**       | $100 credit 60 days | https://www.linode.com/            |

### 7.2 VM Setup Steps

```bash
# 1. SSH vào VM
ssh -i your-key.pem ubuntu@your-vm-ip

# 2. Update system
sudo apt update && sudo apt upgrade -y

# 3. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 4. Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 5. Clone repository
git clone https://github.com/your-username/your-repo.git
cd your-repo

# 6. Deploy
docker-compose up -d
```

### 7.3 Firewall Configuration

```bash
# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw enable
```

### Test:

```bash
# From local machine
curl http://your-vm-ip:8080/health
```

**Screenshot requirements:**

- SSH connected to VM
- Docker containers running
- Application accessible via public IP

---

## Bài 8: Domain & TLS/HTTPS (15 điểm) - BONUS 🌟

**Yêu cầu:** Gắn domain name và cài đặt SSL certificate. Có thể tự mua domain, hoặc nếu cần subdomain liên hệ dinhmanhtan

### 8.1 Get Free Domain

**Freenom domains (nếu available):**

- .tk, .ml, .ga, .cf domains
- https://www.freenom.com/

**Hoặc sử dụng subdomain services:**

- DuckDNS: https://www.duckdns.org/
- No-IP: https://www.noip.com/
- FreeDNS: https://freedns.afraid.org/

### 8.2 DNS Configuration

```
A Record:    yourdomain.com    →  YOUR_VM_IP
A Record:    www.yourdomain.com → YOUR_VM_IP
```

### 8.3 TLS với Let's Encrypt + Nginx

**Option 1: Certbot (Recommended)**

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal (already set up by certbot)
sudo certbot renew --dry-run
```

**Option 2: Traefik (Docker-native)**

```yaml
# docker-compose.yml with Traefik
services:
  traefik:
    image: traefik:v2.10
    command:
      - "--providers.docker=true"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
      - "--certificatesresolvers.letsencrypt.acme.email=your@email.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - letsencrypt:/letsencrypt

  backend:
    labels:
      - "traefik.http.routers.backend.rule=Host(`api.yourdomain.com`)"
      - "traefik.http.routers.backend.tls.certresolver=letsencrypt"

  frontend:
    labels:
      - "traefik.http.routers.frontend.rule=Host(`yourdomain.com`)"
      - "traefik.http.routers.frontend.tls.certresolver=letsencrypt"
```

**Option 3: Caddy (Automatic HTTPS)**

```
# Caddyfile
yourdomain.com {
    reverse_proxy frontend:80
}

api.yourdomain.com {
    reverse_proxy backend:8080
}
```

### Test:

```bash
# Check HTTPS working
curl -I https://yourdomain.com

# Check certificate
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com
```

**Screenshot requirements:**

- Browser showing HTTPS padlock
- Certificate details in browser
- `curl -I https://yourdomain.com` output

---

## Bài 9: Auto Deploy on Merge (15 điểm) - BONUS 🌟

**Yêu cầu:** CI/CD tự động deploy mỗi lần merge vào main

### 9.1 GitHub Actions Workflow

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    name: Deploy to VM
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to server via SSH
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /path/to/your/app
            git pull origin main
            docker-compose down
            docker-compose up -d --build
            docker-compose ps

      - name: Health check
        run: |
          sleep 30
          curl -f https://yourdomain.com/health || exit 1
```

### 9.2 GitHub Secrets Setup

Vào Repository Settings → Secrets and variables → Actions:

| Secret Name       | Description                   |
| ----------------- | ----------------------------- |
| `SERVER_HOST`     | IP hoặc domain của server     |
| `SERVER_USER`     | SSH username (e.g., ubuntu)   |
| `SSH_PRIVATE_KEY` | Private key để SSH vào server |

### 9.3 Alternative: Self-hosted Runner

```bash
# On your VM
mkdir actions-runner && cd actions-runner
curl -o actions-runner-linux-x64.tar.gz -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz
tar xzf ./actions-runner-linux-x64.tar.gz
./config.sh --url https://github.com/your-username/your-repo --token YOUR_TOKEN
./run.sh
```

Workflow với self-hosted runner:

```yaml
jobs:
  deploy:
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4
      - run: |
          docker-compose down
          docker-compose up -d --build
```

### 9.4 Deployment Strategies

**Rolling Update:**

```yaml
script: |
  docker-compose pull
  docker-compose up -d --no-deps --build backend
  sleep 10
  docker-compose up -d --no-deps --build frontend
```

**Blue-Green Deployment:**

```yaml
script: |
  docker-compose -f docker-compose.blue.yml up -d --build
  # Test new deployment
  curl -f http://localhost:8081/health
  # Switch traffic
  docker-compose -f docker-compose.green.yml down
```

### Test:

```bash
# Make a change and push
git add .
git commit -m "Test auto deploy"
git push origin main

# Watch GitHub Actions
# Check deployment on server
```

**Screenshot requirements:**

- GitHub Actions deploy job successful
- Server updated automatically after merge

---

## 📊 Chấm Điểm

| Bài Tập                     | Điểm    | Bắt Buộc    |
| --------------------------- | ------- | ----------- |
| Bài 1: Mở rộng Scan API     | 25      | ✅ Bắt buộc |
| Bài 2: Viết Unit Tests      | 25      | ✅ Bắt buộc |
| Bài 3: Tích hợp Frontend    | 20      | ✅ Bắt buộc |
| Bài 4: CI/CD GitHub Actions | 25      | ✅ Bắt buộc |
| Bài 5: Deploy Docker        | 15      | ✅ Bắt buộc |
| Bài 6: Tính năng EASM mới   | 15      | 🌟 Bonus    |
| Bài 7: Deploy Cloud VM      | 20      | 🌟 Bonus    |
| Bài 8: Domain & TLS         | 15      | 🌟 Bonus    |
| Bài 9: Auto Deploy          | 15      | 🌟 Bonus    |
| **Tổng bắt buộc**           | **110** |             |
| **Tổng có bonus**           | **175** |             |

---

## 💡 Gợi Ý & Tips

### SSL Certificate Check trong Go:

```go
import (
    "crypto/tls"
    "net"
    "time"
)

func CheckSSL(domain string) (*SSLResult, error) {
    conn, err := tls.Dial("tcp", domain+":443", &tls.Config{
        InsecureSkipVerify: false,
    })
    if err != nil {
        return nil, err
    }
    defer conn.Close()

    cert := conn.ConnectionState().PeerCertificates[0]

    return &SSLResult{
        Subject:      cert.Subject.CommonName,
        Issuer:       cert.Issuer.CommonName,
        ValidFrom:    cert.NotBefore,
        ValidUntil:   cert.NotAfter,
        DaysToExpiry: int(time.Until(cert.NotAfter).Hours() / 24),
    }, nil
}
```

### Port Scanner Safety Check:

```go
func isLocalHost(ip string) bool {
    localPrefixes := []string{
        "127.",
        "10.",
        "172.16.", "172.17.", "172.18.", "172.19.",
        "172.20.", "172.21.", "172.22.", "172.23.",
        "172.24.", "172.25.", "172.26.", "172.27.",
        "172.28.", "172.29.", "172.30.", "172.31.",
        "192.168.",
    }

    for _, prefix := range localPrefixes {
        if strings.HasPrefix(ip, prefix) {
            return true
        }
    }
    return ip == "localhost"
}
```

### Mock for Testing:

```go
// mockgen -source=internal/service/asset_service.go -destination=internal/service/mock_asset_service.go

type MockAssetStorage struct {
    assets map[string]*Asset
}

func (m *MockAssetStorage) Create(asset *Asset) error {
    m.assets[asset.ID] = asset
    return nil
}

func (m *MockAssetStorage) GetByID(id string) (*Asset, error) {
    if asset, ok := m.assets[id]; ok {
        return asset, nil
    }
    return nil, ErrNotFound
}
```

### Docker Health Check Best Practices:

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1
```

---

## 📚 Tài Liệu Tham Khảo

### Testing

- [Go Testing Best Practices](https://blog.golang.org/using-go-modules)
- [Table Driven Tests](https://dave.cheney.net/2019/05/07/prefer-table-driven-tests)
- [Go Test Coverage](https://blog.golang.org/cover)
- [Testify - Go Testing Toolkit](https://github.com/stretchr/testify)

### CI/CD & GitHub Actions

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub Actions for Go](https://docs.github.com/en/actions/automating-builds-and-tests/building-and-testing-go)
- [Gosec Security Scanner](https://github.com/securego/gosec)
- [Trivy Vulnerability Scanner](https://github.com/aquasecurity/trivy)
- [Gitleaks Secret Scanner](https://github.com/gitleaks/gitleaks)

### Docker & Deployment

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Multi-stage Builds](https://docs.docker.com/develop/develop-images/multistage-build/)
- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)

### Domain & TLS/HTTPS 🔐

**Official Documentation:**

- [Let's Encrypt - Getting Started](https://letsencrypt.org/getting-started/)
- [Certbot Instructions](https://certbot.eff.org/instructions)
- [Nginx SSL Configuration](https://nginx.org/en/docs/http/configuring_https_servers.html)
- [Traefik HTTPS & TLS](https://doc.traefik.io/traefik/https/overview/)
- [Caddy Automatic HTTPS](https://caddyserver.com/docs/automatic-https)

**Blog Tutorials:**

- [DigitalOcean - How to Secure Nginx with Let's Encrypt](https://www.digitalocean.com/community/tutorials/how-to-secure-nginx-with-let-s-encrypt-on-ubuntu-22-04)
- [DigitalOcean - How to Use Traefik with Let's Encrypt](https://www.digitalocean.com/community/tutorials/how-to-use-traefik-v2-as-a-reverse-proxy-for-docker-containers-on-ubuntu-20-04)
- [Freecodecamp - SSL Certificate Tutorial](https://www.freecodecamp.org/news/free-https-c051ca570324/)
- [CloudFlare - What is HTTPS?](https://www.cloudflare.com/learning/ssl/what-is-https/)

**YouTube Tutorials:**

- 📹 [TechWorld with Nana - SSL/TLS Explained](https://www.youtube.com/watch?v=T4Df5_cojAs&ab_channel=TechWorldwithNana)
- 📹 [NetworkChuck - Get HTTPS FREE](https://www.youtube.com/watch?v=VCPLmVW8Y3k&ab_channel=NetworkChuck)
- 📹 [Traversy Media - Nginx with Let's Encrypt](https://www.youtube.com/watch?v=kBngB-kVWqc&ab_channel=TraversyMedia)
- 📹 [Christian Lempa - Traefik Tutorial](https://www.youtube.com/watch?v=wLrmmh1eI94&ab_channel=ChristianLempa)
- 📹 [Dreams of Code - Caddy Server](https://www.youtube.com/watch?v=vsMB8KCGqdE&ab_channel=DreamsofCode)

### Auto Deploy / CD 🚀

**Official Documentation:**

- [GitHub Actions - Deploying to a server](https://docs.github.com/en/actions/deployment/about-deployments/deploying-with-github-actions)
- [GitHub Actions - Self-hosted runners](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/about-self-hosted-runners)
- [Docker Hub - Automated Builds](https://docs.docker.com/docker-hub/builds/)

**Blog Tutorials:**

- [DigitalOcean - CI/CD with GitHub Actions](https://www.digitalocean.com/community/tutorials/how-to-set-up-a-continuous-deployment-pipeline-with-github-actions-on-ubuntu-20-04)
- [Dev.to - Auto Deploy with GitHub Actions](https://dev.to/koddr/automate-your-docker-deployments-with-github-actions-and-watchtower-3ld0)
- [Thenewstack - GitHub Actions Deployment Automation](https://thenewstack.io/a-look-at-github-actions-for-deployment-automation/)
- [Medium - Zero Downtime Deployments](https://medium.com/@piergiuseppe.nesci/zero-downtime-deployment-with-docker-docker-compose-and-nginx-49e4e9e1a01c)

**YouTube Tutorials:**

- 📹 [TechWorld with Nana - Complete CI/CD Tutorial](https://www.youtube.com/watch?v=R8_veQiYBjI&ab_channel=TechWorldwithNana)
- 📹 [Fireship - GitHub Actions Tutorial](https://www.youtube.com/watch?v=eB0nUzAI7M8&ab_channel=Fireship)
- 📹 [DevOps Journey - Auto Deploy with GitHub Actions](https://www.youtube.com/watch?v=yfBtjLxn_6k&ab_channel=DevOpsJourney)
- 📹 [Colt Steele - GitHub Actions for Beginners](https://www.youtube.com/watch?v=yLDwAe-FLNI&ab_channel=ColtSteele)
- 📹 [Anton Putra - Self-Hosted GitHub Runner](https://www.youtube.com/watch?v=IdVDR4xr-kk&ab_channel=AntonPutra)
- 📹 [Programming with Mosh - Docker Deployment](https://www.youtube.com/watch?v=3c-iBn73dDE&ab_channel=ProgrammingwithMosh)

### Cloud Providers

- [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/)
- [Google Cloud Free Tier](https://cloud.google.com/free)
- [AWS Free Tier](https://aws.amazon.com/free/)
- [DigitalOcean Tutorials](https://www.digitalocean.com/community/tutorials)

### Security Scanning

- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [Snyk - Security for Developers](https://snyk.io/)
- [GitHub Security Features](https://docs.github.com/en/code-security)

---

## 🚀 Bonus Challenges (Nâng cao)

1. **Kubernetes Deployment:** Deploy lên K8s cluster
2. **Monitoring:** Thêm Prometheus + Grafana
3. **Logging:** Centralized logging với ELK Stack
4. **API Gateway:** Sử dụng Kong hoặc Nginx ingress
5. **Load Balancing:** Cài đặt multiple backend replicas
6. **Database Backup:** Automated backup cho PostgreSQL
7. **Rate Limiting:** Implement rate limiting middleware
8. **API Documentation:** Generate OpenAPI/Swagger docs
9. **WebSocket Support:** Real-time scan status updates
10. **Email Notifications:** Gửi email khi scan complete

---

**Chúc các bạn làm bài tốt! Có thắc mắc hỏi trên group nhé! 🚀**

---
