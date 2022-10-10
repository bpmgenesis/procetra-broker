from sqlalchemy.orm import Session
from api import models, schemas
from fastapi import HTTPException, status
import json
from typing import List, Dict


def get_by_service_name(service_name: str, db: Session) -> List[models.ServisRegistration]:
    servis_registrations = db.query(models.ServisRegistration).filter_by(service_name=service_name).all();
    return servis_registrations
