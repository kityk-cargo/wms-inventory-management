from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import Column  # added import to satisfy type annotations in examples
from app.database import get_db
from app.models import Location
from app.schemas import LocationCreate, LocationResponse

router = APIRouter()

@router.post("/", response_model=LocationResponse)
def create_location(location: LocationCreate, db: Session = Depends(get_db)):
    existing = db.query(Location).filter(
        Location.aisle == location.aisle,
        Location.bin == location.bin
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Location already exists")
    
    new_location = Location(
        aisle=location.aisle,
        bin=location.bin
    )
    db.add(new_location)
    db.commit()
    db.refresh(new_location)
    return new_location

@router.put("/{location_id}", response_model=LocationResponse)
def update_location(location_id: int, location: LocationCreate, db: Session = Depends(get_db)):
    existing_location = db.query(Location).filter(Location.id == location_id).first()
    if not existing_location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    setattr(existing_location, 'aisle', location.aisle)
    setattr(existing_location, 'bin', location.bin)
    db.commit()
    db.refresh(existing_location)
    return existing_location

@router.get("/{location_id}", response_model=LocationResponse)
def get_location(location_id: int, db: Session = Depends(get_db)):
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location

@router.get("/", response_model=List[LocationResponse])
def list_locations(db: Session = Depends(get_db)):
    return db.query(Location).all()
