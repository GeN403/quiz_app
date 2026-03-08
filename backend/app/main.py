"""FastAPI application entrypoint."""

import io
import logging
import os
import sys
from contextlib import asynccontextmanager
from uuid import uuid4

import aiosqlite
import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import create_agent_router, create_api_router
from app.core.logging import configure_logging, reset_correlation_id, set_correlation_id
from app.db.database import init_db

configure_logging()
logger = logging.getLogger(__name__)

# Force UTF-8 stream on Windows terminals when needed.
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    logger.warning("GEMINI_API_KEY is not set.")
    logger.warning("Backend starts, but quiz generation will fail.")
    logger.warning("Set GEMINI_API_KEY in backend/.env.")
else:
    logger.info("GEMINI_API_KEY is configured.")

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.0-flash-lite")

_NEW_FIELDS = frozenset({"difficulty", "length", "genre", "topic"})
_SEED_FIELD = "resolve_seed"

_DB_PATH = os.getenv("SQLITE_DB_PATH", "quiz_app.db")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーション起動時に SQLite DB を初期化し、終了時に接続を閉じる。"""
    async with aiosqlite.connect(_DB_PATH) as db:
        await init_db(db)
        app.state.db = db
        logger.info("SQLite DB initialized: %s", _DB_PATH)
        yield
    logger.info("SQLite DB connection closed.")


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    correlation_id = request.headers.get("x-correlation-id", "").strip() or f"corr_{uuid4().hex[:12]}"
    request.state.correlation_id = correlation_id
    token = set_correlation_id(correlation_id)
    try:
        response = await call_next(request)
    finally:
        reset_correlation_id(token)
    response.headers["x-correlation-id"] = correlation_id
    return response


@app.exception_handler(RequestValidationError)
async def custom_validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    if any(_SEED_FIELD in tuple(err.get("loc", ())) for err in errors):
        return JSONResponse(status_code=422, content={"detail": "INVALID_SEED"})

    for err in errors:
        field = err.get("loc", (None,))[-1]
        if field in _NEW_FIELDS and err.get("type") == "value_error":
            raw = (err.get("ctx") or {}).get("error")
            code = str(raw) if raw is not None else "VALIDATION_ERROR"
            return JSONResponse(status_code=422, content={"detail": code})

    return await request_validation_exception_handler(request, exc)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(create_api_router(model))
app.include_router(create_agent_router(api_key))
