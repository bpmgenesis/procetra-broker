from fastapi import APIRouter, Depends, status, File, UploadFile, Form, Response
from api import database, schemas
from sqlalchemy.orm import Session

router = APIRouter(
    prefix="/dataset",
    tags=['Dataset']
)

get_db = database.get_db

@router.post('/CreateDataset', response_model=schemas.CreateDatasetResponse)
def create_project(request: schemas.CreateDatasetRequest, db: Session = Depends(get_db)):
    return project.create(request, db)

