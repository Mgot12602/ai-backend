from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from contextlib import asynccontextmanager
from src.infrastructure.database.mongodb import MongoDB
from src.presentation.api.user_routes import router as user_router
from src.presentation.api.job_routes import router as job_router
from src.presentation.websocket.websocket_routes import router as websocket_router
from src.config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await MongoDB.connect_to_mongo(settings.mongodb_url, settings.database_name)
    yield
    # Shutdown
    await MongoDB.close_mongo_connection()


app = FastAPI(
    title="AI Backend API",
    description="AI Backend with FastAPI, MongoDB, WebSockets, and queue processing",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(user_router, prefix="/api/v1")
app.include_router(job_router, prefix="/api/v1")
app.include_router(websocket_router)


@app.get("/")
async def root():
    return {"message": "AI Backend API is running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    # Return 204 No Content to avoid 404 logs when browsers request /favicon.ico
    return Response(status_code=204)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
