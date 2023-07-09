from fastapi import APIRouter
from api import database, schemas, schemas
from api.repository import event_log as eventlog_repository
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, status, File, UploadFile, Form, HTTPException, Request, Response
from session import get_session, SessionInfo
from api.routers.globals import session_manager, clean_expired_sessions, check_session_validity, do_login, \
    get_user_from_session
from bson.json_util import dumps

router = APIRouter(
    prefix="/v1/metrics",
    tags=['Metrics']
)


@router.post('')
async def create_metric(
        request: Request,
        db: Session = Depends(database.get_db),
        mongo_db=Depends(database.get_mongo_db)):
    try:

        body = await request.json()
        notes = mongo_db.metrics
        metric_names = {
            "COUNT_OF_TIMELINES": "Count of timelines",
            "COUNT_OF_EVENTS": "Count of events per timeline",
            "COUNT_OF_UNIQUE_EVENTS": "Count of unique events per timeline",
            "COUNT_OF_EVENTS_SINGLE": "Count of events",
            "DURATION": "Duration",
            "BUSINESS_DURATION": "Business duration",
            "TIME_INTERVAL": "Time interval measurement",
            "ATTRIBUTE_VALUE": "Attribute value",
            "COUNT_OF_UNIQUE_ATTRIBUTE": "Attribute distinct count",
            "COST_OF_EVENTS": "Cost of events",
            "DERIVED_METRIC": "Derived metric"
        }
        body['metric_name'] = metric_names[body['metric_type']]
        new_metric = notes.insert_one(body)
        return {'id': str(new_metric.inserted_id)}




    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('')
async def get_metrics(
        request: Request,
        response: Response,
        db: Session = Depends(database.get_db),
        mongo_db=Depends(database.get_mongo_db)):
    try:

        metrics = mongo_db.metrics
        cursor = metrics.find()
        list_cur = list(cursor)
        for metric in list_cur:
            metric['id'] = str(metric['_id'])
            del metric['_id']

        response.headers["Access-Control-Expose-Headers"] = "X-Total-Count"
        response.headers["X-Total-Count"] = str(len(list_cur))
        return list_cur



    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
