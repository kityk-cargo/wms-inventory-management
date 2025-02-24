from typing import Optional
from sqlalchemy.orm import Session
from app.models import Location


def get_by_id(db: Session, location_id: int) -> Optional[Location]:
    return db.query(Location).filter(Location.id == location_id).first()


def get_by_identifiers(db: Session, aisle: str, bin: str) -> Optional[Location]:
    return (
        db.query(Location).filter(Location.aisle == aisle, Location.bin == bin).first()
    )


def create_location(db: Session, location_data: dict) -> Location:
    location = Location(**location_data)
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


def update_location(
    db: Session, existing_location: Location, update_data: dict
) -> Location:
    for key, value in update_data.items():
        setattr(existing_location, key, value)
    db.commit()
    db.refresh(existing_location)
    return existing_location


def list_locations(db: Session):
    return db.query(Location).all()


def exists(db: Session, aisle: str, bin: str) -> bool:
    return bool(
        db.query(Location).filter(Location.aisle == aisle, Location.bin == bin).first()
    )
