from fastapi import APIRouter
from api import database, schemas, schemas
from fastapi import APIRouter, Depends, status, File, UploadFile, Form, HTTPException
from session import get_session, SessionInfo
from procetraconfiguration import configuration as Configuration
from api.routers.globals import session_manager, clean_expired_sessions, check_session_validity, do_login, \
    get_user_from_session
import logging
from threading import Semaphore
import traceback
from pm4py.util import constants

router = APIRouter(
    prefix="/v1",
    tags=['Load Event Data']
)

get_db = database.get_db
engine = database.engine
engine_event_log = database.engine_log


@router.post("/LoadEventData")
def load_log( session: SessionInfo = Depends(get_session),
             project_id: str = Form(...)):
    """
    Service that loads a log from a path
    """


    if Configuration.enable_load_local_path:
        try:
            # reads the session


            logging.info("load_log_from_path start session=" + str(session.session_id))

            # reads the log_name entry from the request JSON
            log_id = project_id
            # reads the log_path entry from the request JSON

            print("log_name = ", log_id, "log_path = ", log_id)
            session_manager.load_log_from_db(session.tenant_id, log_id, parameters={
                constants.PARAMETER_CONSTANT_CASEID_KEY: 'case:concept:name',
                constants.PARAMETER_CONSTANT_ACTIVITY_KEY: 'concept:name'
            })

            logging.info("load_log_from_path complete session=" + str(session.session_id) + " user=" + str(session.account_name))

            return "OK"

        except:
            logging.error(traceback.format_exc())
            return "FAIL"
    return "FAIL"
