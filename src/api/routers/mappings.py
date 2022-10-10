from fastapi import APIRouter, Depends, status, File, UploadFile, Form, HTTPException
from api import database, schemas
from sqlalchemy.orm import Session
from uuid import UUID, uuid4
from api.repository import mapping
from api.routers import globals
import json

from session import get_session, SessionInfo

router = APIRouter(
    prefix="/v1",
    tags=['Mappings']
)

get_db = database.get_db
engine = database.engine


@router.post('/CreateMapping')
def create_mapping(
        session: SessionInfo = Depends(get_session),
        project_id: str = Form(...),
        mapping_name: str = Form(...),
        mapping_file_name: str = Form(...),
        mapping_data: str = Form(...),
        db: Session = Depends(database.get_org_event_db)):
    try:
        id = str(uuid4())

        mapping.create(session.realm_id, session.tenant_id, project_id, id, mapping_name, mapping_file_name,
                       mapping_data, db)
        return id;
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post('/GetProjectMappings')
def get_project_mappings(
        session_id: str = Form(...),
        tenant_id: str = Form(...),
        project_id: str = Form(...),
        user: str = Depends(globals.get_user),
        db: Session = Depends(database.get_org_event_db)):
    try:
        result = mapping.get_mapping_models(tenant_id, project_id, db)
        mappings = [];
        for x in result:
            mappings.append({
                'project_id': x.project_id,
                'mapping_id': x.mapping_id,
                'mapping_name': x.mapping_name,
                'mapping_file_name': x.mapping_file_name,
                'mapping_data': json.loads(x.mapping_data)
            })

        return mappings

    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
