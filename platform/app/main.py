from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.execute import router as execute_router
from app.api.projects import router as projects_router
from app.api.pipeline import router as pipeline_router
from app.config import settings
from app.database import engine, Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (MVP — use Alembic in production)
    import app.models  # noqa: ensure all models registered
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title="Forge Platform",
    description="Meta-prompting engine for AI-driven software development",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(execute_router)
app.include_router(projects_router)
app.include_router(pipeline_router)


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
