from fastapi import APIRouter
from fastapi import Depends, status, File, UploadFile, Form, HTTPException
from api import database, schemas, schemas
from fastapi import APIRouter, Depends, status, File, UploadFile, Form, HTTPException
from typing import Optional
from sqlalchemy.orm import Session
from io import StringIO
import pandas as pd

from pm4py import format_dataframe
from pm4py.objects.log.util import dataframe_utils

from uuid import UUID, uuid4

from sqlalchemy.types import Integer, Text, String, DateTime
from api.repository import event_log
from procetraconfiguration import configuration as Configuration
from api.routers.globals import session_manager, clean_expired_sessions, check_session_validity, do_login, \
    get_user_from_session
import logging
from threading import Semaphore
import traceback
from api.util import constants

router = APIRouter(
    prefix="/v1",
    tags=['Process Schema']
)

get_db = database.get_db
engine = database.engine
engine_event_log = database.engine_log


class Commons:
    semaphore_matplot = Semaphore(1)


@router.post("/GetProcessSchema")
def get_process_schema(session_id: str = Form(...), log_id: str = Form(...), decoration: str = Form('freq'),
                       typeOfModel: str = Form('dfg'),
                       simplicity: float = Form(constants.DEFAULT_DEC_FACTOR)):
    """
    Gets the process schema in the wanted format
    Returns
    ------------
    dictio
        JSONified dictionary that contains in the 'base64' entry the SVG representation
        of the process schema. Moreover, 'model' contains the process model (if the output is meaningful)
        and 'format' contains the format
    :return:
    """
    clean_expired_sessions()

    dictio = {}
    # reads the session
    session = session_id
    # reads the requested process name
    process = log_id

    logging.info(
        "get_process_schema start session=" + str(session) + " process=" + str(process))

    if check_session_validity(session):
        user = get_user_from_session(session)
        if session_manager.check_user_log_visibility(user, process):
            Commons.semaphore_matplot.acquire()
            try:
                # reads the decoration
                decoration = decoration
                # reads the typeOfModel
                type_of_model = typeOfModel
                # reads the simplicity
                simplicity = simplicity
                variant = type_of_model + "_" + decoration
                parameters = {"decreasingFactor": simplicity}
                handler = session_manager.get_handler_for_process_and_session(process, session)
                filters_chain = handler.get_filters_chain_repr()
                ps_repr = process + "@@" + variant + "@@" + str(simplicity) + "@@" + filters_chain
                saved_obj = session_manager.get_object_memory(ps_repr) if Configuration.enable_process_caching else None
                if saved_obj is not None:
                    base64 = saved_obj[0]
                    model = saved_obj[1]
                    format = saved_obj[2]
                    this_handler = saved_obj[3]
                    activities = saved_obj[4]
                    start_activities = saved_obj[5]
                    end_activities = saved_obj[6]
                    gviz_base64 = saved_obj[7]
                    graph_rep = saved_obj[8]
                    type_of_model = saved_obj[9]
                    decoration = saved_obj[10]
                    second_model = saved_obj[11]
                    second_format = saved_obj[12]
                    activity_key = saved_obj[13]
                    log_summary = saved_obj[14]
                else:
                    base64, model, format, this_handler, activities, start_activities, end_activities, gviz_base64, graph_rep, type_of_model, decoration, second_model, second_format, activity_key, log_summary = handler.get_schema(
                        variant=variant,
                        parameters=parameters)
                    session_manager.save_object_memory(ps_repr, [base64, model, format, this_handler, activities,
                                                                 start_activities,
                                                                 end_activities, gviz_base64, graph_rep, type_of_model,
                                                                 decoration,
                                                                 second_model, second_format, activity_key,
                                                                 log_summary])
                if model is not None:
                    if type(model) is not str:
                        model = model.decode('utf-8')

                dictio = {"base64": base64.decode('utf-8'), "model": model, "format": format, "handler": this_handler,
                          "activities": activities,
                          "start_activities": start_activities, "end_activities": end_activities,
                          "gviz_base64": gviz_base64.decode('utf-8'), "graph_rep": graph_rep,
                          "type_of_model": type_of_model, "decoration": decoration,
                          "second_model": second_model, "second_format": second_format, "activity_key": activity_key}
                for key in log_summary:
                    dictio[key] = log_summary[key]
            except:
                logging.error(traceback.format_exc())
            Commons.semaphore_matplot.release()

            logging.info(
                "get_process_schema complete session=" + str(session) + " process=" + str(process) + " user=" + str(
                    user))
    return dictio
