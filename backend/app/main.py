from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.db.session import engine
from app.models import Base
from app.providers.comms import MapsConfig
from app.seed import seed_if_needed

settings = get_settings()
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit_default])

app = FastAPI(
    title="CivicLink API",
    version="1.0.0",
    description="Unified Smart Municipal & Citizen Governance Platform",
    docs_url="/docs",
    redoc_url="/redoc",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

upload_dir = Path(settings.local_storage_path)
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(upload_dir)), name="media")

app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    seed_if_needed()


@app.get("/health")
def health():
    db_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "app": settings.app_name, "mode": settings.app_mode, "database": db_ok}


@app.get("/api/v1/system/public-config")
def public_config():
    return {
        "app": settings.app_name,
        "mode": settings.app_mode,
        "maps": MapsConfig().as_public(),
        "demoBanner": settings.is_demo,
    }
