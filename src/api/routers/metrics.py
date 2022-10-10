from fastapi import APIRouter
from api import database, schemas, schemas
from api.repository import event_log as eventlog_repository
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, status, File, UploadFile, Form, HTTPException
from session import get_session, SessionInfo
from api.routers.globals import session_manager, clean_expired_sessions, check_session_validity, do_login, \
    get_user_from_session

router = APIRouter(
    prefix="/v1/metrics",
    tags=['Metrics']
)


@router.post('/GetCaseCount')
def get_case_count(session: SessionInfo = Depends(get_session),
                   project_id: str = Form(...)):
    df = session_manager.get_handler_for_process_and_session(project_id, session.session_id).dataframe
    case_count = len(df['case:concept:name'].unique())

    return case_count


@router.post('/GetEventCount')
def get_event_count(session: SessionInfo = Depends(get_session),
                    project_id: str = Form(...)):

    df = session_manager.get_handler_for_process_and_session(project_id, session.session_id).dataframe
    event_count = len(df)

    return event_count


    return {}
