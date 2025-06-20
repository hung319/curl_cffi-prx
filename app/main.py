# app/main.py

import os
import json
from datetime import datetime, timezone
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict
from fastapi.responses import Response
from curl_cffi.requests import AsyncSession, RequestsError


# Các phần code phía trên không thay đổi
# ...
start_time = datetime.now(timezone.utc)
SECRET_KEY = os.getenv("API_KEY")
IP_SOCKS = os.getenv("IPSOCKS")
USER_SOCKS = os.getenv("USERSOCKS")
PASS_SOCKS = os.getenv("PASSSOCKS")
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
    title="Fetcher API with Docs",
    description="API để fetch URL, hỗ trợ health check và có tài liệu tự động.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)
session = AsyncSession(impersonate="chrome120", timeout=45)

class PostRequest(BaseModel):
    url: str
    key: str
    data: Optional[str] = None
    custom_headers: Optional[Dict[str, str]] = None
    referer: Optional[str] = None

@app.get("/", tags=["Health Check"])
async def get_root_health_check():
    uptime = datetime.now(timezone.utc) - start_time
    proxy_status = { "configured": bool(final_proxy_url), "details": f"Using proxy configured at {IP_SOCKS}" if final_proxy_url else "API is running in direct mode." }
    return { "status": "active", "server_time_utc": datetime.now(timezone.utc).isoformat(), "uptime_seconds": uptime.total_seconds(), "proxy": proxy_status }

def create_passthrough_response(response, url):
    """Hàm trợ giúp để tạo response 'trong suốt'."""
    response.raise_for_status()
    original_headers = response.headers
    proxy_response_headers = {
        "Content-Type": original_headers.get("Content-Type", "application/octet-stream")
    }
    original_content_disposition = original_headers.get("Content-Disposition")
    if original_content_disposition:
        proxy_response_headers["Content-Disposition"] = original_content_disposition
    if "Content-Length" in original_headers:
        proxy_response_headers["Content-Length"] = original_headers["Content-Length"]
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=proxy_response_headers
    )

@app.get("/api", tags=["GET Method"])
async def fetch_url_get_api(
    key: str = Query(...,),
    url: str = Query(...,),
    referer: Optional[str] = Query(None),
    custom_headers: Optional[str] = Query(None)
):
    if key != SECRET_KEY: raise HTTPException(status_code=403, detail="API Key không hợp lệ hoặc bị thiếu.")
    if not url.startswith("http://") and not url.startswith("https://"): raise HTTPException(status_code=400, detail="URL không hợp lệ.")
    headers = {}
    if custom_headers:
        try:
            parsed_headers = json.loads(custom_headers)
            if isinstance(parsed_headers, dict): headers.update(parsed_headers)
            else: raise HTTPException(status_code=400, detail="custom_headers phải là một đối tượng JSON.")
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Giá trị của custom_headers không phải là một chuỗi JSON hợp lệ.")
    if referer: headers["Referer"] = referer
    request_kwargs = {"headers": headers}
    if final_proxy_url: request_kwargs["proxies"] = {"http": final_proxy_url, "https": final_proxy_url}
    try:
        response = await session.get(url, **request_kwargs)
        return create_passthrough_response(response, url)
    except RequestsError as exc:
        raise HTTPException(status_code=502, detail=f"Lỗi khi yêu cầu đến URL mục tiêu: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lỗi máy chủ không xác định: {exc}")

@app.post("/api", tags=["POST Method"])
async def fetch_url_post_api(request: PostRequest):
    if request.key != SECRET_KEY: raise HTTPException(status_code=403, detail="API Key không hợp lệ hoặc bị thiếu.")
    headers = request.custom_headers or {}
    if request.referer: headers["Referer"] = request.referer
    request_kwargs = {"headers": headers, "data": request.data}
    
    # --- SỬA LỖI: Sửa lại tên biến bị gõ sai ---
    if final_proxy_url: 
        request_kwargs["proxies"] = {"http": final_proxy_url, "https": final_proxy_url}
    
    try:
        response = await session.post(request.url, **request_kwargs)
        return create_passthrough_response(response, request.url)
    except RequestsError as exc:
        raise HTTPException(status_code=502, detail=f"Lỗi khi yêu cầu đến URL mục tiêu: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lỗi máy chủ không xác định: {exc}")

@app.on_event("shutdown")
async def shutdown_event():
    await session.close()
