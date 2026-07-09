from fastapi import FastAPI
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

app.include_router(health_router)
app.include_router(review_router, prefix="/api/v1")
app.include_router(estimate_router, prefix="/api/v1")
app.include_router(recommend_router, prefix="/api/v1")


@app.on_event("startup")
def startup_event():
    logger.info("ArchitectIQ API starting up...")
    logger.info("Application initialized successfully")
