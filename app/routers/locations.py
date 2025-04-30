from typing import List
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.schemas import LocationCreate, LocationResponse
import app.repository.location_repository as location_repo
from app.utils import create_error_response

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
    aisle = location.aisle.strip()
    bin_code = location.bin.strip()
    if not aisle:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=create_error_response(
                detail="Aisle identifier cannot be empty",
                criticality="critical",
                recovery_suggestion="Please provide a valid aisle identifier",
            ),
        )
    if not bin_code:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=create_error_response(
                detail="Bin identifier cannot be empty",
                criticality="critical",
                recovery_suggestion="Please provide a valid bin identifier",
            ),
        )
    if location_repo.exists(db, aisle, bin_code):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=create_error_response(
                detail="Location already exists",
                criticality="critical",
                recovery_suggestion="Choose a different aisle/bin combination or update the existing location",
            ),
        )
    return location_repo.create_location(db, location.dict())


@router.put("/{location_id}", response_model=LocationResponse)
def update_location_endpoint(
    location_id: int, location: LocationCreate, db: Session = Depends(get_db)
):
    existing_location = location_repo.get_by_id(db, location_id)
    if not existing_location:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=create_error_response(
                detail="Location not found",
                criticality="critical",
                recovery_suggestion="Verify the location ID or create a new location",
            ),
        )
    return location_repo.update_location(db, existing_location, location.dict())


@router.get("/{location_id}", response_model=LocationResponse)
def get_location_endpoint(location_id: int, db: Session = Depends(get_db)):
    location_obj = location_repo.get_by_id(db, location_id)
    if not location_obj:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=create_error_response(
                detail="Location not found",
                criticality="critical",
                recovery_suggestion="Verify the location ID or create a new location",
            ),
        )
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
