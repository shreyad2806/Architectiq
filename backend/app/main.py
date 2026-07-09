from fastapi import FastAPI
from app.api.health import router as health_router
from app.utils.logger import logger

app = FastAPI(
    title="ArchitectIQ API",
    version="1.0.0"
)

app.include_router(health_router)


@app.on_event("startup")
def startup_event():
    logger.info("ArchitectIQ API starting up...")
    logger.info("Application initialized successfully")
