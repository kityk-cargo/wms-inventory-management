from fastapi import FastAPI
from app.routers import products, stock, locations

app = FastAPI(title="WMS Inventory Management")

app.include_router(products.router, prefix="/products", tags=["products"])
app.include_router(stock.router, prefix="/stock", tags=["stock"])
app.include_router(locations.router, prefix="/locations", tags=["locations"])


@app.get("/")
async def root():
    return {"message": "WMS Inventory Management System"}
