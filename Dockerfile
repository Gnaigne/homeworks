# Multi-stage build (Diet mode) cho FastAPI
# Bước 1: Build dependency (Giống như việc compile)
FROM python:3.13-slim AS builder

WORKDIR /app
COPY requirements.txt .

# Tạo Virtual Environment và cài đặt package
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt \
    # Xoá bớt cache của pip để giảm dung lượng
    && rm -rf /root/.cache/pip

# Bước 2: Production Stage (Bản build hoàn chỉnh)
FROM python:3.13-slim

# Tạo non-root user an toàn
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy Virtual Environment từ Builder sang
COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv
# Đưa biến môi trường vào PATH để khỏi gọi /opt/venv/bin/python mỗi lần
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY --chown=appuser:appuser . .

# Chuyển sang non-root user
USER appuser

# Mặc định kết nối Database nằm ở Network nội bộ có hostname 'db'
ENV DB_HOST=db
ENV DB_PORT=5432
ENV DB_USER=postgres
ENV DB_PASSWORD=postgres
ENV DB_NAME=mini_asm

EXPOSE 8080

# Chạy server FastAPI bằng Uvicorn
CMD ["python", "-m", "app.server.main"]
