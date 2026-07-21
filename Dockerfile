# Sử dụng Python image mỏng nhẹ
FROM python:3.10-slim

# Cài đặt các thư viện hệ thống cần thiết cho OpenCV/Ultralytics
RUN apt-get update && apt-get install -y libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirement và cài đặt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy mã nguồn
COPY app.py .

# Expose port mặc định của Knative
EXPOSE 8080

# Chạy ứng dụng
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]