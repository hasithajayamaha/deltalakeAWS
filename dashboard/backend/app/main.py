"""FastAPI main application for DataLake Discovery Dashboard."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.api.routes import discovery, deployment, cost, monitoring, config
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="DataLake Discovery API",
    description="API for discovering and managing AWS data lake infrastructure",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(discovery.router, prefix="/api/v1", tags=["Discovery"])
app.include_router(deployment.router, prefix="/api/v1", tags=["Deployment"])
app.include_router(cost.router, prefix="/api/v1", tags=["Cost"])
app.include_router(monitoring.router, prefix="/api/v1", tags=["Monitoring"])
app.include_router(config.router, prefix="/api/v1", tags=["Configuration"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "DataLake Discovery API",
        "version": "1.0.0",
        "docs": "/api/docs"
    }


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0"
    }


@app.get("/api/v1/version")
async def version():
    """Get API and deltalake-aws versions."""
    try:
        import datalake_aws
        datalake_version = getattr(datalake_aws, '__version__', '0.1.0')
    except ImportError:
        datalake_version = "not installed"
    
    return {
        "api_version": "1.0.0",
        "deltalake_aws_version": datalake_version
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
