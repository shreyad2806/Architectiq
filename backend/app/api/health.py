from fastapi import APIRouter

router = APIRouter()


@router.get(
    "/health",
    summary="Health Check",
    description="Returns service health, version and readiness status.",
    response_description="Service health status.",
    tags=["Health"],
    responses={
        200: {
            "description": "Service health status.",
            "content": {
                "application/json": {
                    "example": {"status": "healthy"}
                }
            },
        }
    },
)
def health_check():
    return {"status": "healthy"}
