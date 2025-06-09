# Dockerfile

# Bước 1-2 không đổi
FROM python:3.11-slim
WORKDIR /code

# Bước 3-4 không đổi
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# --- THAY ĐỔI: Thêm entrypoint script vào image ---
# Sao chép entrypoint script vào container
COPY entrypoint.sh .
# Cấp quyền thực thi cho script
RUN chmod +x /code/entrypoint.sh

# Bước 5 không đổi
COPY ./app /code/app

# Bước 6 không đổi
EXPOSE 8000

# --- THAY ĐỔI: Sử dụng ENTRYPOINT thay vì CMD ---
# Chỉ định entrypoint script làm lệnh khởi động chính của container.
# Lệnh CMD cũ đã được thay thế hoàn toàn.
ENTRYPOINT ["/code/entrypoint.sh"]
