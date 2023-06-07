from fastapi import APIRouter
from api import database, schemas, schemas
from api.handlers.parquet.parquet import ParquetHandler
from api.repository import event_log as eventlog_repository
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, status, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse
import html
from fastapi.encoders import jsonable_encoder
from api.repository import project
from api import oauth2
from typing import List, Optional
from uuid import UUID, uuid4
import base64

import pandas as pd
from pm4py.objects.log.util import dataframe_utils
from pm4py.objects.conversion.log import converter as log_converter
from pm4py.algo.filtering.pandas.start_activities import start_activities_filter
from pm4py.algo.filtering.pandas.end_activities import end_activities_filter
from pm4py.statistics.start_activities.pandas import get
from pm4py.statistics.end_activities.pandas import get as get_end
from pm4py import format_dataframe
from sqlalchemy.types import Integer, Text, String, DateTime
from pydantic import BaseModel
from api.session import verifier, cookie, backend
from api.schemas import SessionData
from api.repository import event_log
import os
import pm4py
from pm4py.objects.log.importer.xes import importer as xes_importer

from procetraconfiguration import configuration as Configuration

from api.util import constants
from pm4py.util import constants as pm_constants
import logging
import json

import sys
from io import StringIO
from api.routers.globals import session_manager, clean_expired_sessions, check_session_validity, do_login, \
    get_user_from_session

router = APIRouter(
    prefix="/v1",
    tags=['Log Filtering']
)


@router.post('/GetAllFilters')
def get_all_filters(session_id: str = Form(...), project_id: str = Form(...)):
    handler: ParquetHandler = session_manager.get_handler_for_process_and_session(project_id, session_id)

    # import pm4py
    #
    # from pm4py.objects.conversion.process_tree import converter as tree_converter
    #
    # from pm4py.objects.bpmn.layout import layouter as bpmn_layouter
    # from pm4py.objects.bpmn.exporter import exporter as bpmn_exporter
    #
    # tree = pm4py.discover_process_tree_inductive(handler.dataframe)
    # bpmn_graph = tree_converter.apply(tree, variant=tree_converter.Variants.TO_BPMN)
    # bpmn_graph = bpmn_layouter.apply(bpmn_graph)
    # bpmn_exporter.apply(bpmn_graph, os.path.join(os.getcwd(), "running-example.bpmn"))

    return handler.filters_chain


@router.post('/AddFilter')
def add_filter(session_id: str = Form(...), project_id: str = Form(...), filter: str = Form(...),
               all_filters: str = Form(...)):
    """
    Adds a filter to the process
    Returns
    -------------
    dictio
        Success, or not
    """



    # reads the session
    session = session_id
    # reads the requested process name
    process = project_id

    # reads the specific filter to add
    filter = json.loads(filter)
    # reads all the filters
    all_filters = json.loads(all_filters)

    parameters = {}
    parameters["force_reload"] = True

    new_handler = session_manager.get_handler_for_process_and_session(process, session,
                                                                      parameters=parameters).add_filter(
        filter, all_filters)
    session_manager.set_handler_for_process_and_session(process, session, new_handler)

    return {"status": "OK"}


@router.post('/RemoveFilter')
def remove_filter(session_id: str = Form(...), project_id: str = Form(...), filter: str = Form(...),
                  all_filters: str = Form(...)):
    """
    Removes a filter from the process
    Returns
    -------------
    dictio
        Success, or not
    """


    # reads the specific filter to add
    filter = json.loads(filter)
    # reads all the filters

    all_filters = json.loads(all_filters)

    parameters = {}
    parameters["force_reload"] = True

    new_handler = session_manager.get_handler_for_process_and_session(project_id, session_id,
                                                                      parameters=parameters).remove_filter(
        filter, all_filters)
    session_manager.set_handler_for_process_and_session(project_id, session_id, new_handler)

    return {"status": "OK"}
