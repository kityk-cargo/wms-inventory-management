from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.models import Location
from app.schemas import LocationCreate, LocationResponse

router = APIRouter()

# Define Pydantic example instances for locations
example_location_obj = LocationResponse(
    id=200, aisle="C12", bin="D34", created_at=datetime(2023, 6, 1, 8, 0, 0)
)

example_location_obj_alt = LocationResponse(
    id=201, aisle="C13", bin="D35", created_at=datetime(2023, 6, 2, 9, 0, 0)
)


@router.post("/", response_model=LocationResponse)
def create_location(location: LocationCreate, db: Session = Depends(get_db)):
    if not location.aisle or len(location.aisle.strip()) == 0:
        raise HTTPException(status_code=400, detail="Aisle identifier cannot be empty")

    if not location.bin or len(location.bin.strip()) == 0:
        raise HTTPException(status_code=400, detail="Bin identifier cannot be empty")

    location.aisle = location.aisle.strip()
    location.bin = location.bin.strip()

    existing = (
        db.query(Location)
        .filter(Location.aisle == location.aisle, Location.bin == location.bin)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Location already exists")

    new_location = Location(aisle=location.aisle, bin=location.bin)
    db.add(new_location)
    try:
        db.commit()
        db.refresh(new_location)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    return new_location


@router.put("/{location_id}", response_model=LocationResponse)
def update_location(
    location_id: int, location: LocationCreate, db: Session = Depends(get_db)
):
    existing_location = db.query(Location).filter(Location.id == location_id).first()
    if not existing_location:
        raise HTTPException(status_code=404, detail="Location not found")

    setattr(existing_location, "aisle", location.aisle)
    setattr(existing_location, "bin", location.bin)
    db.commit()
    db.refresh(existing_location)
    return existing_location


@router.get("/{location_id}", response_model=LocationResponse)
def get_location(location_id: int, db: Session = Depends(get_db)):
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location


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
                                    # A third extra example using a literal dict generated by the model for clarity:
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
def list_locations(db: Session = Depends(get_db)):
    return db.query(Location).all()
