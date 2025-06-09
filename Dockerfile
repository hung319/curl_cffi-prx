# Bước 1: Chọn một image nền Python gọn nhẹ và hiệu quả.
FROM python:3.11-slim

# Bước 2: Đặt thư mục làm việc bên trong container.
WORKDIR /code

# Bước 3: Sao chép file requirements.txt vào trước để tận dụng caching.
COPY requirements.txt .

# Bước 4: Cài đặt các thư viện Python.
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Bước 5: Sao chép mã nguồn ứng dụng vào thư mục làm việc trong container.
COPY ./app /code/app

# Bước 6: Mở cổng mặc định là 8000.
EXPOSE 8000

# Bước 7: Lệnh để chạy ứng dụng khi container khởi động.
# Sử dụng biến môi trường ${PORT} hoặc mặc định là 8000.
CMD sh -c 'uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}'
