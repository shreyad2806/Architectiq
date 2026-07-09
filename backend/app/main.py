import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.health import router as health_router
from app.api.review import router as review_router
from app.api.estimate import router as estimate_router
from app.api.recommend import router as recommend_router
from app.utils.logger import logger

app = FastAPI(
    title="ArchitectIQ API",
    version="1.0.0",
    description="""
ArchitectIQ is an AI Architecture Review and Cost Optimization API.

It analyzes AI system architectures, estimates production costs,
identifies latency bottlenecks, evaluates production readiness,
and generates optimization recommendations.
""",
    contact={
        "name": "ArchitectIQ",
        "url": "https://github.com/shreyad2806"
    },
    license_info={
        "name": "MIT"
    },
    openapi_tags=[
        {
            "name": "Architecture Review",
            "description": "Analyze AI architectures and generate production readiness reports."
        },
        {
            "name": "Cost Estimation",
            "description": "Estimate AI token usage, latency and infrastructure costs."
        },
        {
            "name": "Optimization",
            "description": "Generate optimization recommendations for AI systems."
        },
        {
            "name": "Health",
            "description": "Service health monitoring endpoints."
        }
    ]
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

_ALLOWED_ORIGINS = [
    "http://localhost:5173",   # Vite / React dev server
    "http://localhost:3000",   # CRA / alternative dev server
    # "https://architectiq.example.com",  # TODO: replace with deployed frontend URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(review_router, prefix="/api/v1")
app.include_router(estimate_router, prefix="/api/v1")
app.include_router(recommend_router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}: "
        f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "Unexpected error occurred.",
        },
    )


@app.on_event("startup")
def startup_event():
    logger.info("ArchitectIQ API starting up...")
    logger.info("Application initialized successfully")
