from sqlalchemy.orm import Session
from api import models, schemas
from fastapi import HTTPException, status


def create(request: schemas.CreateDatasetRequest, db: Session):
    new_project = models.Dataset(name=request.name)
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project


def get_dataset(log_id: str) -> models.Dataset:
    dataset = models.Dataset.query().filter(models.Dataset.id == log_id).first()
