import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import require_api_key
from .config import ensure_dirs
from .jwt_auth import router as auth_router
from .logging_config import setup_logging
from .middleware import RequestLoggingMiddleware
from .rate_limit import setup_rate_limit
from .routes.assets import router as assets_router
from .routes.backup import router as backup_router
from .routes.health import router as health_router
from .routes.items import router as items_router
from .routes.jobs import router as jobs_router
from .routes.metrics import router as metrics_router
from .routes.profile import router as profile_router
from .routes.query import router as query_router
from .routes.search import router as search_router
from .routes.sync import router as sync_router
from .routes.uploads import router as uploads_router

setup_logging(os.getenv("LOG_LEVEL", "INFO"))
ensure_dirs()

app = FastAPI(
    title="Brain Vault API",
    version="0.1.0",
    # Apply API key auth to all routes by default; open routes override with dependencies=[]
    dependencies=[Depends(require_api_key)],
)

setup_rate_limit(app)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public routes (no auth)
app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(auth_router)  # /v1/auth/token is public (issues tokens)

# Protected routes
app.include_router(items_router)
app.include_router(uploads_router)
app.include_router(assets_router)
app.include_router(jobs_router)
app.include_router(search_router)
app.include_router(backup_router)
app.include_router(profile_router)
app.include_router(query_router)
app.include_router(sync_router)
