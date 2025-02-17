import pytest
from sqlalchemy.orm import Session
from app.repository import location_repository


@pytest.fixture
def sample_location(db_session: Session):
    # Arrange
    location_data = {"aisle": "A1", "bin": "B1"}
    # Act
    location = location_repository.create_location(db_session, location_data)
    # Assert
    assert isinstance(location.id, int), "Invalid Location ID"
    assert location.aisle == "A1", "Aisle mismatch"
    assert location.bin == "B1", "Bin mismatch"
    return location


def test_create_location(db_session: Session):
    """Should create a location and return its details."""
    # Arrange
    location_data = {"aisle": "A2", "bin": "B2"}
    # Act
    location = location_repository.create_location(db_session, location_data)
    # Assert
    assert isinstance(location.id, int), "Location ID is not an integer"
    assert location.aisle == "A2", "Aisle mismatch"
    assert location.bin == "B2", "Bin mismatch"


def test_get_location(db_session: Session, sample_location):
    """Should retrieve location details by id."""
    # Arrange
    location_id = sample_location.id
    # Act
    fetched_location = location_repository.get_by_id(db_session, location_id)
    # Assert
    assert fetched_location is not None, "Fetched location is None"
    assert fetched_location.id == sample_location.id, "Location ID mismatch"
    assert fetched_location.aisle == sample_location.aisle, "Aisle mismatch"
    assert fetched_location.bin == sample_location.bin, "Bin mismatch"


def test_list_locations(db_session: Session, sample_location):
    """Should list locations including the created one."""
    # Arrange
    # sample_location fixture provides an existing location
    # Act
    locations = location_repository.list_locations(db_session)
    # Assert
    assert any(
        loc.id == sample_location.id for loc in locations
    ), "Created location not found in location list"


def test_create_duplicate_location(db_session: Session, sample_location):
    """Negative: Should not allow creating duplicate location with same aisle and bin."""
    # Arrange
    duplicate_data = {"aisle": sample_location.aisle, "bin": sample_location.bin}
    # Act & Assert: Expect exception or error due to unique constraint.
    with pytest.raises(Exception):
        location_repository.create_location(db_session, duplicate_data)


def test_get_nonexistent_location(db_session: Session):
    """Edge: Retrieving a location with an invalid id should return None."""
    # Arrange
    invalid_id = 999999
    # Act
    location = location_repository.get_by_id(db_session, invalid_id)
    # Assert
    assert location is None, "Expected None for non-existent location"
