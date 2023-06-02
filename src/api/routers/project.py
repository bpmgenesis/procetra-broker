from fastapi import APIRouter
from api import database, schemas
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, status, File, UploadFile, Form, HTTPException
from fastapi.encoders import jsonable_encoder

from api.fastapi_crudrouter import SQLAlchemyCRUDRouter
from api.models import ProjectDBModel
from api.repository import project
from api import oauth2
from typing import List
from uuid import UUID, uuid4

import pandas as pd
from pm4py.objects.log.util import dataframe_utils
from pm4py.objects.conversion.log import converter as log_converter
from pm4py import format_dataframe
from sqlalchemy.types import Integer, Text, String, DateTime
from pydantic import BaseModel
from api.session import verifier, cookie, backend
from api.schemas import SessionData
from api.routers import globals
import os
import json
from session import get_session, SessionInfo

import sys
from io import StringIO

from api.routers.globals import session_manager, clean_expired_sessions, check_session_validity, do_login, \
    get_user_from_session
from typing import Union

router = APIRouter(
    prefix="/v1",
    tags=['Project']
)

get_db = database.get_db
engine = database.engine


class ProjectCreate(BaseModel):
    realm_id: str
    tenant_id: str
    project_id: str
    project_name: str


class Project(ProjectCreate):
    id: str

    class Config:
        orm_mode = True


ProjectRouter = SQLAlchemyCRUDRouter(
    schema=Project,
    create_schema=ProjectCreate,
    db_model=ProjectDBModel,
    db=database.get_db,
    prefix='v1/projects',
    tags=['Projects']
)


class CsvLog(BaseModel):
    name: str


table_name = 'evet_logs'


@router.post('/CreateProject')
def create_project(
        session: SessionInfo = Depends(get_session),
        project_id: Union[str , None] = Form(...),
        project_name: str = Form(...),
        admin: str = Form(...),
        is_public: bool = Form(...),
        disable_cache: bool = Form(...),
        db: Session = Depends(database.get_org_event_db)):
    try:

        if project_id is None or project_id == 'unique.id':
            project_id = str(uuid4())

        projectObject = {
            'project_id': project_id,
            'project_name': project_name,
            'creator': session.account_name,
            'admin': admin,
            'is_public': is_public,
            'disable_cache': disable_cache
        }
        project.create(session.realm_id, session.tenant_id, project_id, project_name, admin, is_public, disable_cache,
                       projectObject, 0,
                       0, db)
        return projectObject;
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post('/GetProjectById')
def get_project_by_id(
        session=Depends(get_session),
        project_id: str = Form(...),
        db: Session = Depends(database.get_org_event_db)):
    try:

        result = project.get(session.realm_id, session.tenant_id, project_id, db)

        obj = {
            'project_id': result.project_id,
            'project_name': result.project_name,
            'admin': result.admin,
            'is_public': result.is_public,
            'disable_cache': result.disable_cache,
            'is_data_loaded': result.is_data_loaded
        }

        return obj
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/GetProjects')
def get_projects(
        session=Depends(get_session),
        db: Session = Depends(database.get_org_event_db)):
    try:
        result = project.get_all_projects(session.realm_id, session.tenant_id, db)
        projects = [];
        for x in result:
            projects.append({
                'project_id': x.project_id,
                'project_name': x.project_name,
                'admin': x.admin,
                'is_public': x.is_public,
                'disable_cache': x.disable_cache,
                'is_data_loaded': x.is_data_loaded,
                'case_count': x.case_count,
                'event_count': x.event_count
            })

        return {'projects': projects}

    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/uploadfile/", dependencies=[Depends(cookie)])
async def create_upload_file(name: str = Form(...), file: UploadFile = File(...),
                             session_data: SessionData = Depends(verifier)):
    try:
        os.mkdir("logs")
        print(os.getcwd())
    except Exception as e:
        print(e)
    file_name = os.getcwd() + "/logs/" + file.filename.replace(" ", "-")
    with open(file_name, 'wb+') as f:
        f.write(file.file.read())
        f.close()

    # file = jsonable_encoder({"imagePath": file_name})
    # new_image = await add_image(file)
    # return {"filename": new_image}

    # csv = await file.read()  # async read
    # stream = StringIO(str(csv))
    #
    log_csv = pd.read_csv(file_name, sep=',')
    log_csv = format_dataframe(log_csv, case_id='Case ID', activity_key='Activity', timestamp_key='End Date')
    log_csv = dataframe_utils.convert_timestamp_columns_in_df(log_csv)
    #
    log_csv = log_csv.sort_values('time:timestamp')

    log_csv.to_sql(
        name,
        engine,
        if_exists='append',
        index=False,
        chunksize=500,
        dtype={
            "case:concept:name": String(),
            "concept:name": String()
        }
    )

    session_data.Logs[name] = log_csv;
    print(session_data.Logs)
    # print(csv)
    return {"filename": file.filename}


@router.get('/Load/{log_name}', dependencies=[Depends(cookie)])
async def load_log(log_name: str, db: Session = Depends(get_db), session_id: UUID = Depends(cookie)):
    session_data = await backend.read(session_id)
    if log_name in session_data.Logs:
        print('found in session')
        table_df = session_data.Logs[log_name]
    else:
        print('found in db')
        table_df = pd.read_sql_table(
            table_name,
            con=engine
        )
        session_data.Logs[log_name] = table_df;
        await backend.update(session_id, session_data)
    return {'log': 'test'}


@router.post('/GetTraceCount', dependencies=[Depends(cookie)])
async def get_trace_count(log_name: str = Form(...), db: Session = Depends(get_db), session_id: UUID = Depends(cookie)):
    session_data = await backend.read(session_id)
    table_df = None
    if log_name in session_data.Logs:
        print('found in session')
        table_df = session_data.Logs[log_name]
    else:
        print('found in db')
        table_df = pd.read_sql_table(
            table_name,
            con=engine
        )
        session_data.Logs[log_name] = table_df;
        await backend.update(session_id, session_data)

    return {'TraceCount': len(table_df['case:concept:name'].unique())}


@router.post('/CreateProjectItem')
def create_project_item(
        session=Depends(get_session),
        project_id: str = Form(...),
        model_id: str = Form(...),
        item_id: str = Form(...),
        db: Session = Depends(database.get_org_event_db)):
    try:

        result = project.create_project_item(realm_id=session.realm_id, tenant_id=session.tenant_id,
                                             project_id=project_id, model_id=model_id,
                                             item_id=item_id,
                                             item_info={}, db=db)
        return {"status": "OK"}


    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post('/GetProjectItems')
def get_project_items(
        session=Depends(get_session),
        project_id: str = Form(...),
        model_id: str = Form(...),
        db: Session = Depends(database.get_org_event_db)):
    try:
        result = project.get_all_project_items(session.realm_id, session.tenant_id, project_id, model_id, db)
        project_items = [];
        for x in result:
            project_items.append({
                "item_id": x.item_id
            })

        return project_items

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
