from fastapi import FastAPI, Request, status
from app.routers import products, stock, locations, health
from datetime import datetime
import json
from fastapi.responses import JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from app.utils import format_datetime, create_error_response


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return format_datetime(obj)
        return super().default(obj)


app = FastAPI(
    title="WMS Inventory Management Service",
    description="Service for managing inventory in a warehouse management system",
    version="1.0.0",
    redirect_slashes=True,  # Disable automatic redirects for trailing slashes
)

# Add GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def custom_json_middleware(request, call_next):
    response = await call_next(request)
    if isinstance(response, JSONResponse):
        response_content = response.body.decode()
        try:
            data = json.loads(response_content)
            response.body = json.dumps(data, cls=CustomJSONEncoder).encode()
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
    return response


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with common error format"""
    # Skip health routes
    if request.url.path.startswith("/health"):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": str(exc)},
        )

    error_detail = str(exc)
    recovery = "Please check the request format and ensure all required fields are provided correctly."

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=create_error_response(
            detail=error_detail, criticality="critical", recovery_suggestion=recovery
        ),
    )


@app.exception_handler(SQLAlchemyError)
async def sql_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle database errors with common error format"""
    # Skip health routes
    if request.url.path.startswith("/health"):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Database error occurred"},
        )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=create_error_response(
            detail="Database operation failed", criticality="critical"
        ),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions with common error format"""
    # Skip health routes
    if request.url.path.startswith("/health"):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(exc)},
        )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=create_error_response(
            detail="Internal server error", criticality="critical"
        ),
    )


# Include routers
app.include_router(products.router, prefix="/api/v1/products", tags=["Products"])
app.include_router(stock.router, prefix="/api/v1/stock", tags=["Stock"])
app.include_router(locations.router, prefix="/api/v1/locations", tags=["Locations"])
app.include_router(health.router, prefix="/health")


@app.get("/")
async def root():
    return {"message": "WMS Inventory Management System"}
