# 📝 Bài Tập Về Nhà - Sessions 1-3

**Deadline:** Trước ngày thứ 3  
**Cách nộp:** Push lên Git repository cá nhân tại branch homework. Mời dinhmanhtan (dmtangtnd@mail.com) vào project. Tạo pull request từ branch homework vào main. Set reviewer là dinhmanhtan  
**Note**: Project có thể viết bằng ngôn ngữ khác không bắt buộc phải dùng Go. Nếu sử dụng ngôn ngữ khác cần mô tả cách cài đặt và chạy project

---

## 📑 Mục Lục

- [Yêu Cầu Chung](#yêu-cầu-chung)
- [📤 Nộp Bài](#-nộp-bài)
- [Bài 1: Statistics APIs (20 điểm)](#bài-1-statistics-apis-20-điểm)
  - [1.1 Get Assets Statistics](#11-get-assets-statistics)
  - [1.2 Count Assets by Filter](#12-count-assets-by-filter)
- [Bài 2: Batch Create Assets (25 điểm)](#bài-2-batch-create-assets-25-điểm)
- [Bài 3: Batch Delete Assets (20 điểm)](#bài-3-batch-delete-assets-20-điểm)
- [Bài 4: Database Connection Retry (25 điểm) ⭐](#bài-4-database-connection-retry-25-điểm-)
- [Bài 5: Database Health Check (15 điểm)](#bài-5-database-health-check-15-điểm)
- [Bài 6: Pagination & Filtering (15 điểm) - BONUS 🌟](#bài-6-pagination--filtering-15-điểm---bonus-)
- [Bài 7: Search by Name (10 điểm) - BONUS 🌟](#bài-7-search-by-name-10-điểm---bonus-)
- [📊 Chấm Điểm](#-chấm-điểm)
- [💡 Gợi Ý & Tips](#-gợi-ý--tips)
- [📚 Tài Liệu Tham Khảo](#-tài-liệu-tham-khảo)
- [🚀 Bonus Challenges](#-bonus-challenges)

---

## Yêu Cầu Chung

- ✅ Code phải chạy được không có lỗi
- ✅ Follow Clean Architecture như đã học
- ✅ Có error handling đầy đủ
- ✅ Test được bằng curl hoặc Postman

---

## 📤 Nộp Bài

### Cần nộp:

**File `SUBMISSION.md`** hoặc **`SUBMISSION.pdf`** gồm:

```markdown
# Homework Submission

**Họ tên:** [Tên của bạn]

## Các bài đã hoàn thành

- [x] Bài 1: Statistics APIs
- [x] Bài 2: Batch Create
- [x] Bài 3: Batch Delete
- [x] Bài 4: Connection Retry
- [x] Bài 5: Health Check
- [x] Bài 6: Pagination (Bonus)
- [x] Bài 7: Search (Bonus)
```

Mỗi bài cần 1 file Test screenshots hoặc command outputs chứng minh
File này đặt trong thư mục [homeworks/submissions](../submissions/)

---

## Bài 1: Statistics APIs (20 điểm)

**Yêu cầu:** Implement API để lấy thống kê về assets

### 1.1 Get Assets Statistics

- **Endpoint:** `GET /assets/stats`
- **Response:** 200 OK
  ```json
  {
    "total": 150,
    "by_type": {
      "domain": 100,
      "ip": 40,
      "service": 10
    },
    "by_status": {
      "active": 120,
      "inactive": 30
    }
  }
  ```

### 1.2 Count Assets by Filter

- **Endpoint:** `GET /assets/count`
- **Query params:** `type`, `status` (optional)
- **Response:** 200 OK
  ```json
  {
    "count": 85,
    "filters": {
      "type": "domain",
      "status": "active"
    }
  }
  ```

**Test:**

```bash
# Get statistics
curl http://localhost:8080/assets/stats

# Count all
curl http://localhost:8080/assets/count

# Count by type
curl "http://localhost:8080/assets/count?type=domain"

# Count by type and status
curl "http://localhost:8080/assets/count?type=domain&status=active"
```

---

## Bài 2: Batch Create Assets (25 điểm)

**Yêu cầu:** Tạo nhiều assets cùng lúc trong 1 transaction

### API Specification

- **Endpoint:** `POST /assets/batch`
- **Request body:**
  ```json
  {
    "assets": [
      { "name": "domain1.com", "type": "domain" },
      { "name": "domain2.com", "type": "domain" },
      { "name": "192.168.1.1", "type": "ip" }
    ]
  }
  ```
- **Response:** 201 Created
  ```json
  {
    "created": 3,
    "ids": ["uuid-1", "uuid-2", "uuid-3"]
  }
  ```

### Yêu cầu kỹ thuật:

- Sử dụng **database transaction** (all or nothing)
- Nếu 1 asset validation fail → rollback tất cả
- Limit tối đa 100 assets/request
- Validate từng asset trước khi insert

**Test:**

```bash
# Success case
curl -X POST http://localhost:8080/assets/batch \
  -H "Content-Type: application/json" \
  -d '{
    "assets": [
      {"name":"test1.com","type":"domain"},
      {"name":"test2.com","type":"domain"}
    ]
  }'

# Error case (invalid type) - should rollback all
curl -X POST http://localhost:8080/assets/batch \
  -H "Content-Type: application/json" \
  -d '{
    "assets": [
      {"name":"test1.com","type":"domain"},
      {"name":"test2.com","type":"invalid_type"}
    ]
  }'
# Expected: 400 Bad Request, none created
```

---

## Bài 3: Batch Delete Assets (20 điểm)

**Yêu cầu:** Xóa nhiều assets cùng lúc

### API Specification

- **Endpoint:** `DELETE /assets/batch`
- **Query params:** `?ids=uuid1,uuid2,uuid3`
- **Response:** 200 OK
  ```json
  {
    "deleted": 3,
    "not_found": 0
  }
  ```

### Behavior:

- Xóa tất cả IDs hợp lệ
- Bỏ qua IDs không tồn tại (không trả lỗi)
- Return số lượng đã xóa và không tìm thấy

**Test:**

```bash
# Create test assets first
ID1=$(curl -s -X POST http://localhost:8080/assets \
  -H "Content-Type: application/json" \
  -d '{"name":"test1.com","type":"domain"}' | jq -r '.id')

ID2=$(curl -s -X POST http://localhost:8080/assets \
  -H "Content-Type: application/json" \
  -d '{"name":"test2.com","type":"domain"}' | jq -r '.id')

# Batch delete (include 1 fake ID)
curl -X DELETE "http://localhost:8080/assets/batch?ids=$ID1,$ID2,fake-uuid-123"

# Expected response:
# {"deleted": 2, "not_found": 1}

# Verify deletion
curl http://localhost:8080/assets/$ID1
# Expected: 404 Not Found
```

---

## Bài 4: Database Connection Retry (25 điểm) ⭐

**Yêu cầu:** Server phải tự động retry khi connect DB thất bại

### Specification:

- Retry tối đa **5 lần**
- Exponential backoff: **1s → 2s → 4s → 8s → 16s**
- Log rõ ràng từng attempt
- Nếu hết 5 lần vẫn fail → exit với error message

### Expected Logs:

```
🔄 Database connection attempt 1/5...
⚠️  Connection failed: connection refused. Retrying in 1s...
🔄 Database connection attempt 2/5...
⚠️  Connection failed: connection refused. Retrying in 2s...
🔄 Database connection attempt 3/5...
✅ Database connected successfully!
```

### Hints:

- Tạo file `internal/database/retry.go`
- Function: `ConnectWithRetry(dsn string, maxRetries int) (*sql.DB, error)`
- Exponential backoff: `time.Sleep(time.Duration(1<<uint(attempt-1)) * time.Second)`

---

## Bài 5: Database Health Check (15 điểm)

**Yêu cầu:** Nâng cấp `/health` endpoint với thông tin database

### API Specification

- **Endpoint:** `GET /health`
- **Response:**
  - 200 OK (nếu DB connected)
  - 503 Service Unavailable (nếu DB down)

  ```json
  {
    "status": "ok",
    "database": {
      "status": "connected",
      "open_connections": 2,
      "in_use": 0,
      "idle": 2,
      "max_open": 25
    },
    "timestamp": "2026-03-06T10:00:00Z"
  }
  ```

### Implementation hints:

- Update `HealthHandler` để nhận `*sql.DB`
- Dùng `db.Ping()` để check connection
- Dùng `db.Stats()` để lấy connection pool info

**Test:**

```bash
# Normal operation
curl http://localhost:8080/health | jq

# Stop database
docker-compose stop db
sleep 2
curl http://localhost:8080/health
# Expected: 503, status="degraded", database.status="disconnected"

# Restart database
docker-compose start db
sleep 2
curl http://localhost:8080/health
# Expected: 200, status="ok", database.status="connected"
```

---

## Bài 6: Pagination & Filtering (15 điểm) - BONUS 🌟

**Yêu cầu:** Thêm phân trang và filter cho list assets

### API Specification

- **Endpoint:** `GET /assets`
- **Query params:**
  - `page` (default: 1)
  - `limit` (default: 20, max: 100)
  - `type` (optional: domain, ip, service)
  - `status` (optional: active, inactive)

- **Response:**
  ```json
  {
    "data": [...],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 150,
      "total_pages": 8
    }
  }
  ```

### SQL hints:

```sql
SELECT * FROM assets
WHERE type = $1 AND status = $2
ORDER BY created_at DESC
LIMIT $3 OFFSET $4
```

**Test:**

```bash
# Page 1, 10 items
curl "http://localhost:8080/assets?page=1&limit=10"

# Filter by type
curl "http://localhost:8080/assets?type=domain"

# Combine filters
curl "http://localhost:8080/assets?page=2&limit=20&type=domain&status=active"
```

---

## Bài 7: Search by Name (10 điểm) - BONUS 🌟

**Yêu cầu:** Tìm kiếm assets theo tên (partial match)

### API Specification

- **Endpoint:** `GET /assets/search`
- **Query params:** `q` (search query, required)
- **Response:** Array of matching assets (max 100)
- **Behavior:** Case-insensitive, partial match

### SQL hints:

```sql
SELECT * FROM assets
WHERE name ILIKE $1
LIMIT 100
```

**Test:**

```bash
# Search for "example"
curl "http://localhost:8080/assets/search?q=example"

# Search for ".com"
curl "http://localhost:8080/assets/search?q=.com"

# Case insensitive
curl "http://localhost:8080/assets/search?q=DOMAIN"
```

---

## 📊 Chấm Điểm

| Bài Tập                 | Điểm    | Bắt Buộc    |
| ----------------------- | ------- | ----------- |
| Bài 1: Statistics       | 20      | ✅ Bắt buộc |
| Bài 2: Batch Create     | 25      | ✅ Bắt buộc |
| Bài 3: Batch Delete     | 20      | ✅ Bắt buộc |
| Bài 4: Connection Retry | 25      | ✅ Bắt buộc |
| Bài 5: Health Check     | 15      | ✅ Bắt buộc |
| Bài 6: Pagination       | 15      | 🌟 Bonus    |
| Bài 7: Search           | 10      | 🌟 Bonus    |
| **Tổng bắt buộc**       | **105** |             |
| **Tổng có bonus**       | **130** |             |

---

## 💡 Gợi Ý & Tips

### Transaction trong Go:

```go
tx, err := db.Begin()
if err != nil {
    return err
}
defer tx.Rollback() // Auto rollback if not committed

// Do operations with tx...
_, err = tx.Exec(query, args...)
if err != nil {
    return err // Rollback via defer
}

return tx.Commit() // Success
```

### Dynamic SQL với filters:

```go
conditions := []string{}
args := []interface{}{}
argIndex := 1

if typeFilter != "" {
    conditions = append(conditions, fmt.Sprintf("type = $%d", argIndex))
    args = append(args, typeFilter)
    argIndex++
}

whereClause := ""
if len(conditions) > 0 {
    whereClause = "WHERE " + strings.Join(conditions, " AND ")
}

query := fmt.Sprintf("SELECT * FROM assets %s", whereClause)
rows, err := db.Query(query, args...)
```

### Parse query string IDs:

```go
idsParam := r.URL.Query().Get("ids")
if idsParam == "" {
    return nil, errors.New("ids parameter required")
}

ids := strings.Split(idsParam, ",")
// ids = ["uuid1", "uuid2", "uuid3"]
```

### Count query:

```go
var count int
query := "SELECT COUNT(*) FROM assets WHERE type = $1"
err := db.QueryRow(query, assetType).Scan(&count)
```

---

## 📚 Tài Liệu Tham Khảo

- [PostgreSQL Transactions](https://www.postgresql.org/docs/current/tutorial-transactions.html)
- [Connection Pooling Best Practices](https://www.alexedwards.net/blog/configuring-sqldb)
- [SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
- [RESTful API Design](https://restfulapi.net/)

## 🚀 Bonus Challenges

1. **Rate Limiting:** Giới hạn số request/phút từ mỗi IP
2. **Caching:** Cache list assets trong memory (5 phút)
3. **Audit Log:** Log mọi CREATE/UPDATE/DELETE vào bảng audit
4. **Soft Delete:** Thêm `deleted_at` timestamp thay vì xóa hẳn
5. **Import CSV:** Upload file CSV để tạo nhiều assets
6. **Export CSV:** Download assets dưới dạng CSV
7. **Webhooks:** Gọi webhook khi có asset mới được tạo

---

**Chúc các bạn làm bài tốt! Có thắc mắc hỏi trên group nhé! 🚀**

---