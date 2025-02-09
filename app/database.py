from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_SCHEMA = os.getenv("DATABASE_SCHEMA", "wms_schema")
DATABASE_USER = os.getenv("DATABASE_USER")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")

# Construct the full database URL
full_database_url = f"postgresql://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_URL}?options=-c search_path={DATABASE_SCHEMA}"

engine = create_engine(full_database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
