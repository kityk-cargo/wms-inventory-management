from fastapi import FastAPI, Depends
from app.routers import products, stock, locations, health
from sqlalchemy.orm import Session
from app.database import get_db
from typing import List
from app.schemas import ProductResponse
import app.repository.product_repository as product_repo

app = FastAPI(
    title="WMS Inventory Management Service",
    description="Service for managing inventory in a warehouse management system",
    version="1.0.0",
    redirect_slashes=False,  # Disable automatic redirects for trailing slashes
)

# Include routers
app.include_router(products.router, prefix="/api/v1/products", tags=["Products"])
app.include_router(stock.router, prefix="/api/v1/stock", tags=["Stock"])
app.include_router(locations.router, prefix="/api/v1/locations", tags=["Locations"])
app.include_router(health.router, prefix="/health")


# Direct route for contract testing - this duplicates the functionality
# in the products router but directly at the path expected by the contract.
# In a production environment, we'd want the contract and implementation to align better.
@app.get(
    "/api/v1/products", response_model=List[ProductResponse], tags=["ContractTesting"]
)
async def get_products_for_contract(db: Session = Depends(get_db)):
    """
    Special route to satisfy the contract testing requirements.

    This route is necessary because the contract expects exactly '/api/v1/products'
    while our normal router is mounted at '/api/v1/products' and has endpoints underneath.

    Contract requirement: Product IDs must be integers.
    """
    # Call the repository function directly to get products
    # The contract requires all product IDs to be integers
    return product_repo.list_products(db)


@app.get("/")
async def root():
    return {"message": "WMS Inventory Management System"}
