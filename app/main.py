"""FastAPI app: security headers, size limit, gzip, locked-down CORS, static UI."""
import json
import logging
import sys
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routes import router

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(message)s")
CSP = ("default-src 'self'; style-src 'self' https://fonts.googleapis.com; "
       "font-src https://fonts.gstatic.com; img-src 'self' data:; frame-ancestors 'none'")

app = FastAPI(title="The Blind Spot", docs_url=None, redoc_url=None)
app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(CORSMiddleware, allow_origins=[], allow_methods=["GET", "POST"])


@app.middleware("http")
async def guard(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Reject oversized payloads and add security headers."""
    if int(request.headers.get("content-length") or 0) > settings.max_payload_bytes:
        resp = JSONResponse({"detail": "Payload too large"}, status_code=413)
    else:
        resp = await call_next(request)
    resp.headers.update({
        "Content-Security-Policy": CSP, "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer",
    })
    return resp


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception) -> JSONResponse:
    """Never expose stack traces."""
    entry = {"severity": "ERROR", "event": "unhandled", "err": type(exc).__name__}
    logging.error(json.dumps(entry))
    return JSONResponse({"detail": "Internal error"}, status_code=500)


app.include_router(router)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
