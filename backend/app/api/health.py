from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "ArchitectIQ",
        "version": "1.0.0",
        "environment": "development"
    }
