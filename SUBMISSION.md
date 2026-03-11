# Homework Submission

**Họ tên:** Nguyễn Trường Giang

## Các bài đã hoàn thành

- [x] Bài 1: Statistics APIs
- [x] Bài 2: Batch Create
- [x] Bài 3: Batch Delete
- [x] Bài 4: Connection Retry
- [x] Bài 5: Health Check
- [x] Bài 6: Pagination (Bonus)
- [x] Bài 7: Search (Bonus)

---

## Bài 1: Statistics APIs (20 điểm)

### 1.1 GET /assets/stats

![GET /assets/stats](image/image-1.1.png)

### 1.2 GET /assets/count

![GET /assets/count](image/image-1.2.png)

---

## Bài 2: Batch Create Assets (25 điểm)

### 2.1 Success Case — Tạo batch 2 assets thành công (201)

![Batch create success](image/image-2.1.png)

### 2.2 Error Case — Empty name bị reject (400)

![Empty name error](image/image-2.2.png)

### 2.3 Error Case — Empty list bị reject (400)

![Empty list error](image/image-2.3.png)

### 2.4 Error Case — Invalid type bị reject (422)

![Invalid type error](image/image-2.4.png)

---

## Bài 3: Batch Delete Assets (20 điểm)

### 3.1 Batch Delete — Xóa 2 asset thật + 1 fake ID (200)

![Batch delete](image/image-3.1.png)

### 3.2 Verify Deletion — Asset đã xóa trả về 404

![Verify deletion](image/image-3.2.png)

---

## Bài 4: Database Connection Retry (25 điểm)

![Connection retry](image/image-4.1.png)

Cái này phải mở thêm 1 terminal để chờ tầm 3 giây rồi mới docker compose up
![Connection retry with docker](image/image-4.2.png)

---

## Bài 5: Database Health Check (15 điểm)

![Health check 1](image/image-5.1.png)

![Health check 2](image/image-5.2.png)

![Health check 3](image/image-5.3.png)

---

## Bài 6: Pagination & Filtering (15 điểm) - BONUS 🌟

![Pagination 1](image/image-6.1.png)

![Pagination 2](image/image-6.2.png)

![Pagination 3](image/image-6.3.png)

---

## Bài 7: Search by Name (10 điểm) - BONUS 🌟

![Search 1](image/image-7.1.png)

![Search 2](image/image-7.2.png)

![Search 3](image/image-7.3.png)
