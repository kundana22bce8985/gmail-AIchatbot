from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.routes import router
from app.api.chat import router as chat_router
from app.api.reader import router as reader_router


BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Gmail AI Agent started")
    yield
    print("👋 Gmail AI Agent stopped")


app = FastAPI(
    title="Gmail AI Agent",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)


# Allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# API routes
app.include_router(
    router,
    prefix="/api/v1"
)

app.include_router(
    chat_router,
    prefix="/api/v1"
)

app.include_router(
    reader_router,
    prefix="/api/v1"
)


# Serve static files
if STATIC_DIR.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(STATIC_DIR)),
        name="static"
    )


@app.get("/", include_in_schema=False)
def root():
    index_path = STATIC_DIR / "index.html"

    if index_path.exists():
        return FileResponse(str(index_path))

    return {
        "message": "Gmail AI Agent is running"
    }