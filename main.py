from fastapi import FastAPI, Security, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from contextlib import asynccontextmanager
from src.infrastructure.database.mongodb import MongoDB
from src.presentation.api.user_routes import router as user_router
from src.presentation.api.job_routes import router as job_router
from src.presentation.websocket.websocket_routes import router as websocket_router
from src.infrastructure.events.redis_notification_subscriber import RedisNotificationSubscriber
from src.config.settings import settings
import logging
from src.config.auth import security
from fastapi.responses import JSONResponse
import traceback


# Global notification subscriber
notification_subscriber = RedisNotificationSubscriber()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if settings.debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        )
        logging.getLogger("uvicorn").setLevel(logging.INFO)
        logging.debug("[main.lifespan] Debug logging configured")
    await MongoDB.connect_to_mongo(settings.mongodb_url, settings.database_name)
    await notification_subscriber.start()
    yield
    # Shutdown
    await notification_subscriber.stop()
    await MongoDB.close_mongo_connection()


app = FastAPI(
    title="AI Backend API",
    description="AI Backend with FastAPI, MongoDB, WebSockets, and queue processing",
    version="1.0.0",
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True},
)

# Log requests and unhandled exceptions to help diagnose 500 errors
@app.middleware("http")
async def exception_logging_middleware(request: Request, call_next):
    logging.debug("[middleware] START | %s %s", request.method, request.url.path)
    try:
        response = await call_next(request)
        logging.debug("[middleware] END | %s %s -> %s", request.method, request.url.path, response.status_code)
        return response
    except Exception:
        logging.exception("[middleware] EXCEPTION | method=%s path=%s", request.method, request.url.path)
        raise

# Global catch-all exception handler to ensure we always see error details in DEBUG
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.exception("[exception_handler] Unhandled exception | method=%s path=%s", request.method, request.url.path)
    if settings.debug:
        tb = traceback.format_exc()
        return JSONResponse(
            status_code=500,
            content={
                "error": type(exc).__name__,
                "message": str(exc),
                "path": request.url.path,
                "traceback": tb.splitlines()[-30:],
            },
        )
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (auth enforced within routes via get_current_user)
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


@app.get("/api/v1/ping")
async def ping():
    logging.debug("[ping] received ping")
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        log_level="debug",
        access_log=True
    )
