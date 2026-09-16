"""FastAPI Application Entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Graph-Based EV Charging Station Optimization API",
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register API routes
from app.api.routes import router as api_router

app.include_router(api_router)


@app.get("/")
def root():
    """Root health check endpoint."""
    return {
        "message": "EV Charging Network Optimization API",
        "status": "running",
        "version": settings.VERSION,
    }
