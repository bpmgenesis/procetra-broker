from fastapi import APIRouter, Depends, status, File, UploadFile, Form, HTTPException
from api import database, schemas
from sqlalchemy.orm import Session
from uuid import UUID, uuid4
from api.repository import analyse_model
from api.util import orm_utils
from api.routers import globals
import json
from session import get_session, SessionInfo

router = APIRouter(
    prefix="/v1",
    tags=['AnalyseModels']
)

get_db = database.get_db
engine = database.engine


@router.post('/CreateAnalyseModel')
def create_analyse_model(
        session: SessionInfo = Depends(get_session),
        project_id: str = Form(...),
        analyse_model_name: str = Form(...),
        db: Session = Depends(database.get_org_event_db)):
    try:
        id = str(uuid4())
        analyse_model_object = {
            'project_id': project_id,
            'model_id': id,
            'model_name': analyse_model_name,
            'creator': session.account_name
        }
        analyse_model.create(session.realm_id, session.tenant_id, project_id, id, analyse_model_name, db)
        return analyse_model_object;
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post('/GetAnalyseModels')
def get_analyse_models(
        session: SessionInfo = Depends(get_session),
        project_id: str = Form(...),
        db: Session = Depends(database.get_org_event_db)):
    try:
        result = analyse_model.get_analyse_models(session.realm_id, session.tenant_id, project_id, db)
        analyse_models = [];
        for x in result:
            analyse_models.append({
                'project_id': x.project_id,
                'model_id': x.id,
                'model_name': x.name
            })

        return analyse_models

    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post('/GetAnalyseModelById')
def get_analyse_model_by_id(
        session: SessionInfo = Depends(get_session),
        project_id: str = Form(...),
        model_id: str = Form(...),
        db: Session = Depends(database.get_org_event_db)):
    try:
        analysis_model = analyse_model.get_analyse_model_by_id(session.realm_id, session.tenant_id, project_id,
                                                               model_id, db)
        if analysis_model is not None:
            return {
                "project_id": analysis_model.project_id,
                "model_id": analysis_model.id,
                "model_name": analysis_model.name
            }

        raise HTTPException(status_code=404, detail=str("Model Not Found."))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/DeleteAnalyseModelById')
def delete_analyse_model_by_id(
        session: SessionInfo = Depends(get_session),
        project_id: str = Form(...),
        model_id: str = Form(...),
        db: Session = Depends(database.get_org_event_db)):
    try:
        is_deleted = analyse_model.delete_analyse_model_by_id(session.realm_id, session.tenant_id, project_id,
                                                              model_id, db)
        return is_deleted

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
