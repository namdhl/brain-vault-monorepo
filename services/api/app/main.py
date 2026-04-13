import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import ensure_dirs
from .logging_config import setup_logging
from .middleware import RequestLoggingMiddleware
from .routes.assets import router as assets_router
from .routes.health import router as health_router
from .routes.items import router as items_router
from .routes.jobs import router as jobs_router
from .routes.metrics import router as metrics_router
from .routes.search import router as search_router
from .routes.uploads import router as uploads_router

setup_logging(os.getenv("LOG_LEVEL", "INFO"))
ensure_dirs()

app = FastAPI(title="Brain Vault API", version="0.1.0")

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(items_router)
app.include_router(uploads_router)
app.include_router(assets_router)
app.include_router(jobs_router)
app.include_router(search_router)
app.include_router(metrics_router)
