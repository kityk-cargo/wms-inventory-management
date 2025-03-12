from fastapi import FastAPI
from app.routers import products, stock, locations, health

app = FastAPI(
    title="WMS Inventory Management Service",
    description="Service for managing inventory in a warehouse management system",
    version="1.0.0",
)

# Include routers
app.include_router(products.router, prefix="/api/v1/products", tags=["Products"])
app.include_router(stock.router, prefix="/api/v1/stock", tags=["Stock"])
app.include_router(locations.router, prefix="/api/v1/locations", tags=["Locations"])
app.include_router(health.router, prefix="/health")


@app.get("/")
async def root():
    return {"message": "WMS Inventory Management System"}
