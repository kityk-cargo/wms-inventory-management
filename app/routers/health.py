from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from pydantic import BaseModel
from typing import Dict, Any, Optional, Tuple
import logging
from datetime import datetime

from app.database import get_db

router = APIRouter(tags=["Health"])
logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    components: Optional[Dict[str, Any]] = None


def check_database_connectivity(db: Session) -> Dict[str, Any]:
    """Check if the database is available and return its status"""
    try:
        # Simple query to check database connectivity
        start_time = datetime.now()
        db.execute(text("SELECT 1"))
        query_time = (
            datetime.now() - start_time
        ).total_seconds() * 1000  # Time in milliseconds

        return {"status": "UP", "details": {"responseTime": f"{query_time:.2f}ms"}}
    except SQLAlchemyError as e:
        logger.error(f"Database connectivity check failed: {str(e)}")
        return {
            "status": "DOWN",
            "details": {"error": str(e), "errorType": e.__class__.__name__},
        }
    except Exception as e:
        logger.error(f"Unexpected error during database check: {str(e)}")
        return {
            "status": "DOWN",
            "details": {"error": str(e), "errorType": e.__class__.__name__},
        }


def create_health_response(
    components: Optional[Dict[str, Dict[str, Any]]] = None
) -> Tuple[Dict[str, Any], bool]:
    """
    Create a standardized health response with the given components.
    Returns a tuple of (response_dict, is_healthy)
    """
    if components is None:
        components = {"application": {"status": "UP"}}

    # Determine overall status
    overall_status = "UP"
    for component, status_info in components.items():
        if status_info["status"] != "UP":
            overall_status = "DOWN"
            break

    response = {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "components": components,
    }

    return response, overall_status == "UP"


@router.get("/liveness", response_model=HealthResponse)
async def liveness_check():
    """
    Liveness probe endpoint.
    Determines if the application is running.
    Used by Kubernetes to know when to restart the container.
    """
    # Liveness only needs basic status without components
    return {
        "status": "UP",
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/readiness", response_model=HealthResponse)
async def readiness_check(db: Session = Depends(get_db)):
    """
    Readiness probe endpoint.
    Determines if the service is ready to receive traffic, including database availability.
    Used by Kubernetes to know when to stop sending traffic to the container.
    """
    components = {
        "application": {"status": "UP"},
        "database": check_database_connectivity(db),
    }

    response, is_healthy = create_health_response(components)

    if not is_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=response
        )

    return response


@router.get("/startup", response_model=HealthResponse)
async def startup_check(db: Session = Depends(get_db)):
    """
    Startup probe endpoint.
    Determines if the application has started correctly, including database initialization.
    Used by Kubernetes to know when the application has started.
    """
    components = {
        "application": {"status": "UP"},
        "database": check_database_connectivity(db),
    }

    response, is_healthy = create_health_response(components)

    if not is_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=response
        )

    return response


@router.get("", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """
    Overall health check endpoint.
    Returns comprehensive health status of the service, including all components.
    """
    components = {
        "application": {"status": "UP"},
        "database": check_database_connectivity(db),
    }

    response, is_healthy = create_health_response(components)

    if not is_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=response
        )

    return response
