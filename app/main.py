import os
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse
from curl_cffi.requests import AsyncSession, RequestsError
from typing import Optional

# Ghi lại thời gian khởi động của server
start_time = datetime.now(timezone.utc)

# Đọc cấu hình từ biến môi trường
SECRET_KEY = os.getenv("API_KEY")
IP_SOCKS = os.getenv("IPSOCKS")
USER_SOCKS = os.getenv("USERSOCKS")
PASS_SOCKS = os.getenv("PASSSOCKS")

# Xây dựng chuỗi proxy URL một lần duy nhất khi khởi động
final_proxy_url = None
if IP_SOCKS:
    proxy_scheme = "socks5h" 
    auth_part = ""
    if USER_SOCKS and PASS_SOCKS:
        auth_part = f"{USER_SOCKS}:{PASS_SOCKS}@"
    final_proxy_url = f"{proxy_scheme}://{auth_part}{IP_SOCKS}"
    print(f"Proxy đã được cấu hình để sử dụng: {proxy_scheme}://...@{IP_SOCKS}")
else:
    print("Không có cấu hình proxy nào được tìm thấy. API sẽ chạy ở chế độ trực tiếp.")

if not SECRET_KEY:
    raise ValueError("Biến môi trường API_KEY chưa được thiết lập.")

app = FastAPI(
    title="Server-Configured Fetcher API",
    description="API được cấu hình proxy hoàn toàn ở phía máy chủ qua biến môi trường."
)

@app.get("/status", tags=["Server Status"])
async def get_server_status():
    """
    Cung cấp thông tin trạng thái và cấu hình hiện tại của server.
    """
    uptime = datetime.now(timezone.utc) - start_time
    proxy_status = {
        "configured": False,
        "details": "API is running in direct mode."
    }
    if final_proxy_url:
        proxy_status["configured"] = True
        proxy_status["details"] = f"Using proxy configured at {IP_SOCKS}"
    return {
        "status": "active",
        "server_time_utc": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": uptime.total_seconds(),
        "proxy": proxy_status
    }

@app.get("/", tags=["Main API"])
async def fetch_url(
    key: str = Query(..., description="API Key để xác thực."),
    url: str = Query(..., description="URL của trang web bạn muốn lấy nội dung."),
    referer: Optional[str] = Query(None, description="URL referer để gửi trong request header.")
):
    if key != SECRET_KEY:
        raise HTTPException(status_code=403, detail="API Key không hợp lệ hoặc bị thiếu.")
    if not url.startswith("http://") and not url.startswith("https://"):
        raise HTTPException(status_code=400, detail="URL không hợp lệ.")
    headers = {}
    if referer:
        headers["Referer"] = referer
    request_kwargs = {"headers": headers}
    if final_proxy_url:
        request_kwargs["proxies"] = {"http": final_proxy_url, "https": final_proxy_url}
    try:
        response = await session.get(url, **request_kwargs)
        response.raise_for_status()
        return response.text
    except RequestsError as exc:
        raise HTTPException(status_code=502, detail=f"Lỗi khi yêu cầu đến URL mục tiêu: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lỗi máy chủ không xác định: {exc}")

@app.on_event("shutdown")
async def shutdown_event():
    await session.close()
