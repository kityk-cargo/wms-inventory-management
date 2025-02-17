from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.models import Location
from app.schemas import LocationCreate, LocationResponse
import app.repository.location_repository as location_repo

router = APIRouter()

# Define Pydantic example instances for locations
example_location_obj = LocationResponse(
    id=200, aisle="C12", bin="D34", created_at=datetime(2023, 6, 1, 8, 0, 0)
)

example_location_obj_alt = LocationResponse(
    id=201, aisle="C13", bin="D35", created_at=datetime(2023, 6, 2, 9, 0, 0)
)


@router.post("/", response_model=LocationResponse)
def create_location_endpoint(location: LocationCreate, db: Session = Depends(get_db)):
    if not location.aisle or len(location.aisle.strip()) == 0:
        raise HTTPException(status_code=400, detail="Aisle identifier cannot be empty")
    if not location.bin or len(location.bin.strip()) == 0:
        raise HTTPException(status_code=400, detail="Bin identifier cannot be empty")
    location.aisle = location.aisle.strip()
    location.bin = location.bin.strip()
    if location_repo.exists(db, location.aisle, location.bin):  
        raise HTTPException(status_code=400, detail="Location already exists")
    return location_repo.create_location(db, location.dict())

@router.put("/{location_id}", response_model=LocationResponse)
def update_location_endpoint(location_id: int, location: LocationCreate, db: Session = Depends(get_db)):
    existing_location = location_repo.get_by_id(db, location_id)
    if not existing_location:
        raise HTTPException(status_code=404, detail="Location not found")
    update_data = location.dict()
    return location_repo.update_location(db, existing_location, update_data)

@router.get("/{location_id}", response_model=LocationResponse)
def get_location_endpoint(location_id: int, db: Session = Depends(get_db)):
    location_obj = location_repo.get_by_id(db, location_id)
    if not location_obj:
        raise HTTPException(status_code=404, detail="Location not found")
    return location_obj

@router.get(
    "/",
    response_model=List[LocationResponse],
    responses={
        200: {
            "content": {
                "application/json": {
                    "examples": {
                        "multiple_locations": {
                            "value": [
                                example_location_obj.dict(),
                                example_location_obj_alt.dict(),
                                {
                                    **LocationResponse(
                                        id=202,
                                        aisle="D05",
                                        bin="B08",
                                        created_at=datetime(2023, 6, 3, 10, 30, 0),
                                    ).dict()
                                },
                                {
                                    **LocationResponse(
                                        id=203,
                                        aisle="D07",
                                        bin="A02",
                                        created_at=datetime(2023, 6, 4, 11, 15, 0),
                                    ).dict()
                                },
                            ]
                        }
                    }
                }
            }
        }
    },
)
def list_locations_endpoint(db: Session = Depends(get_db)):
    return location_repo.list_locations(db)
