import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import get_settings
from backend.db import init_db
from backend.errors import AppError
from backend.routers import approval, employees, health, metrics, partner, schedule

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("shift-scheduler")


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    if settings.dev_mode:
        await init_db()
        logger.info("Database tables initialized in dev mode.")
    yield


app = FastAPI(title="Shift Scheduler Agent", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(schedule.router)
app.include_router(partner.router)
app.include_router(approval.router)
app.include_router(employees.router)
app.include_router(metrics.router)
app.include_router(health.router)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    correlation_id = request.headers.get("x-correlation-id", str(uuid.uuid4()))
    request.state.request_id = request_id
    request.state.correlation_id = correlation_id
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    response.headers["x-request-id"] = request_id
    response.headers["x-correlation-id"] = correlation_id
    logger.info(
        "request_complete",
        extra={
            "request_id": request_id,
            "correlation_id": correlation_id,
            "path": request.url.path,
            "method": request.method,
            "status_code": response.status_code,
            "elapsed_ms": elapsed_ms,
        },
    )
    return response


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "errorCode": exc.error_code.value,
            "userMessage": exc.user_message,
            "developerMessage": exc.developer_message,
            "correlationId": correlation_id,
        },
    )

