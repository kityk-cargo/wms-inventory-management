from typing import List
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import StockOperation, StockResponse
from app.services.notification import send_low_stock_alert
import app.repository.stock_repository as stock_repo
import app.repository.product_repository as product_repo
import app.repository.location_repository as location_repo
from app.utils import create_error_response

router = APIRouter()


@router.post("/inbound", response_model=StockResponse)
def add_stock(operation: StockOperation, db: Session = Depends(get_db)):
    if operation.quantity <= 0:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=create_error_response(
                detail="Quantity must be positive",
                criticality="critical",
                recovery_suggestion="Please provide a positive quantity for inbound operations",
            ),
        )
    product_id = operation.product_id  # renamed for clarity
    location_id = operation.location_id  # renamed for clarity
    product = product_repo.get_by_id(db, product_id)
    if not product:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=create_error_response(
                detail="Product not found",
                criticality="critical",
                recovery_suggestion="Check if the product ID exists or create a new product",
            ),
        )
    location = location_repo.get_by_id(db, location_id)
    if not location:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=create_error_response(
                detail="Location not found",
                criticality="critical",
                recovery_suggestion="Check if the location ID exists or create a new location",
            ),
        )
    stock = stock_repo.get_stock(db, product_id, location_id)
    if stock:
        stock = stock_repo.update_stock_quantity(db, stock, operation.quantity)
    else:
        stock_data = {
            "product_id": product_id,
            "location_id": location_id,
            "quantity": operation.quantity,
        }
        stock = stock_repo.create_stock(db, stock_data)
    if stock.quantity < 20:
        send_low_stock_alert(stock)
    return stock


@router.post("/outbound", response_model=StockResponse)
def remove_stock(operation: StockOperation, db: Session = Depends(get_db)):
    if operation.quantity <= 0:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=create_error_response(
                detail="Quantity must be positive",
                criticality="critical",
                recovery_suggestion="Please provide a positive quantity for outbound operations",
            ),
        )
    product_id = operation.product_id  # renamed for clarity
    location_id = operation.location_id  # renamed for clarity
    stock = stock_repo.get_stock(db, product_id, location_id)
    if not stock:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=create_error_response(
                detail="No stock found for this product at the specified location",
                criticality="critical",
                recovery_suggestion="Check if the product exists at this location, or add stock via an inbound operation",
            ),
        )
    if stock.quantity < operation.quantity:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=create_error_response(
                detail="Insufficient stock",
                criticality="critical",
                recovery_suggestion="Reduce the outbound quantity or add more stock via an inbound operation",
            ),
        )
    stock = stock_repo.update_stock_quantity(db, stock, -operation.quantity)
    if stock.quantity < 20:
        send_low_stock_alert(stock)
    return stock


@router.get("/", response_model=List[StockResponse])
def list_stock_endpoint(db: Session = Depends(get_db)):
    return stock_repo.list_stock(db)
