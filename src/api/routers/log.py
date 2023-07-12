from fastapi import APIRouter
from api import database, schemas, schemas, service
from api.handlers.parquet.parquet import ParquetHandler
from api.repository import event_log as eventlog_repository
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, status, File, UploadFile, Form, HTTPException, Request, Header
from fastapi.responses import FileResponse
import math
import html
import numpy as np
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
from pm4py import format_dataframe, BPMN
from sqlalchemy.types import Integer, Text, String, DateTime
from pydantic import BaseModel

from api.routers.query import query_wrapper
from api.service import Vis
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

import sys
from io import StringIO
from api.routers.globals import session_manager, clean_expired_sessions, check_session_validity, do_login, \
    get_user_from_session

from session import get_session, SessionInfo

import numpy as np

nat = np.datetime64('NaT')


def nat_check(nat):
    return nat == np.datetime64('NaT')


router = APIRouter(
    prefix="/v1",
    tags=['Log Handling']
)

get_db = database.get_db
engine = database.engine
engine_event_log = database.engine_log


def view_bpmn(bpmn_graph: BPMN, format: str = pm_constants.DEFAULT_FORMAT_GVIZ_VIEW, bgcolor: str = "white"):
    pm4py.write.write_bpmn(bpmn_graph, os.getcwd() + '/process.bpmn', False)
    """
    Views a BPMN graph

    :param bpmn_graph: BPMN graph
    :param format: Format of the visualization (if html is provided, GraphvizJS is used to render the visualization in an HTML page)
    :param bgcolor: Background color of the visualization (default: white)

    .. code-block:: python3

        import pm4py

        bpmn_graph = pm4py.discover_bpmn_inductive(dataframe, activity_key='concept:name', case_id_key='case:concept:name', timestamp_key='time:timestamp')
        pm4py.view_bpmn(bpmn_graph)
    """
    format = str(format).lower()
    from pm4py.visualization.bpmn import visualizer as bpmn_visualizer
    parameters = bpmn_visualizer.Variants.CLASSIC.value.Parameters
    gviz = bpmn_visualizer.apply(bpmn_graph, parameters={parameters.FORMAT: format, "bgcolor": bgcolor})
    return str(gviz)


def load_log(process_id: str, log_name: str, parameters=None):
    """
    Loads an event log inside the known handlers
    Parameters
    ------------
    log_name
        Log name
    file_path
        Full path (in the services machine) to the log
    parameters
        Possible parameters
    """
    session_manager.load_log_static(process_id, log_name, parameters=parameters)


import sqlite3


# conn_event_logs = sqlite3.connect(Configuration.event_log_db_path)
# cursor_event_logs = conn_event_logs.cursor()
# cursor_event_logs.execute("SELECT LOG_NAME, LOG_PATH FROM EVENT_LOGS WHERE LOADED_BOOT = 1")
# for result in cursor_event_logs.fetchall():
#     load_log(str(result[0]), str(result[1]))
# conn_event_logs.close()


async def get_df_session_or_database(project_id: str, session_id: UUID):
    session_data = await backend.read(session_id)
    table_df = None
    if project_id in session_data.Logs:
        print('found in session')
        table_df = session_data.Logs[project_id]
    else:
        print('found in db')
        table_df = pd.read_sql_table(
            project_id,
            con=engine
        )
        # event_data_info = eventlog_repository.get(project_id, db)
        # if event_data_info is None:
        # raise HTTPException(status_code=404, detail="Event data info not found")
        # table_df[event_data_info.timestamp_key] = pd.to_datetime(table_df[event_data_info.timestamp_key])
        # table_df[event_data_info.start_timestamp_key] = pd.to_datetime(table_df[event_data_info.start_timestamp_key])

        session_data.Logs[project_id] = table_df;
        await backend.update(session_id, session_data)

    return table_df


def prepare_dataset(source_df, case_column_name: str, activity_column_name: str, timestamp_key: str,
                    start_timestamp_key: str,
                    cost_key: str, resource_key: str):
    case_id = 'case:consept:name';

    case_ids = case_column_name.split(';')

    # case id setting up
    try:
        if len(case_ids) == 1:
            source_df['case:consept:name'] = source_df[case_ids[0]].astype(str)
        elif len(case_ids) == 2:
            source_df['case:consept:name'] = source_df[case_ids[0]].astype(str) + ' - ' + source_df[case_ids[1]].astype(
                str)
    except Exception as e:
        raise Exception("Error occured in setting up case:concept:name")

    # activity key setting up
    try:
        activity_key = 'case:consept';
        activity_keys = activity_column_name.split(';')

        if len(activity_keys) == 1:
            source_df['case:consept'] = source_df[activity_keys[0]].astype(str)
        elif len(activity_keys) == 2:
            source_df['case:consept'] = source_df[activity_keys[0]].astype(str) + ' - ' + source_df[
                activity_keys[1]].astype(str)
    except Exception as e:
        raise Exception("Error occured in setting up case:name")

    # formatting dataset
    source_df = format_dataframe(source_df, case_id=case_id, activity_key=activity_key,
                                 timestamp_key=timestamp_key, start_timestamp_key=start_timestamp_key)

    source_df = dataframe_utils.convert_timestamp_columns_in_df(source_df)

    # rename and convert cost field
    if cost_key is not None:
        if cost_key in source_df.columns:
            source_df = source_df.rename(columns={cost_key: "concept:cost"})
            source_df.to_numeric(source_df['concept:cost'])

    # rename and convert resource field
    if resource_key is not None:
        if resource_key in source_df.columns:
            source_df = source_df.rename(columns={resource_key: "org:resource"})

    #
    return source_df.sort_values('time:timestamp')


def save_log(source_df, case_column_name: str, activity_column_name: str, timestamp_key: str, start_timestamp_key: str,
             sep: str, db):
    log_id = str(uuid4())

    event_log.create(log_id, 'Test.csv', case_column_name, activity_column_name, timestamp_key,
                     start_timestamp_key, sep, db)

    source_df.to_sql(
        log_id,
        engine_event_log,
        if_exists='replace',
        index=False,
        chunksize=500,
        dtype={
            "case:concept:name": String(),
            "concept:name": String()
        }
    )
    return log_id


# @router.post("/LoadCsv", dependencies=[Depends(cookie)])
@router.post("/LoadCsv")
async def load_csv(case_column_name: str = Form(...),
                   activity_column_name: str = Form(...),
                   timestamp_key: str = Form(...),
                   start_timestamp_key: str = Form(...),
                   cost_key: Optional[str] = Form(None),
                   resource_key: Optional[str] = Form(None),
                   sep: str = Form(...),
                   file: UploadFile = File(...),
                   db: Session = Depends(get_db),
                   # session_data: SessionData = Depends(verifier)
                   ):
    try:
        _csv = await file.read()  # async read
        stream = StringIO(_csv.decode("utf-8"))

        log_csv = pd.read_csv(stream, sep=sep)

        log_csv = prepare_dataset(log_csv, case_column_name, activity_column_name, timestamp_key,
                                  start_timestamp_key, cost_key, resource_key)

        log_id = save_log(log_csv, case_column_name, activity_column_name, timestamp_key, start_timestamp_key, sep, db)

        csv = log_csv.to_csv(index=False);

        return {
            'log_id': log_id,
            "csv": csv
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# @router.post("/LoadXlsx", dependencies=[Depends(cookie)])
@router.post("/LoadXlsx")
async def load_xlsx(case_column_name: str = Form(...),
                    activity_column_name: str = Form(...),
                    timestamp_key: str = Form(...),
                    start_timestamp_key: str = Form(...),
                    cost_key: Optional[str] = Form(None),
                    resource_key: Optional[str] = Form(None),
                    sheet_name: str = Form(...),
                    file: UploadFile = File(...),
                    db: Session = Depends(get_db),
                    # session_data: SessionData = Depends(verifier)
                    ):
    # try:
    #     os.mkdir("logs")
    #     print(os.getcwd())
    # except Exception as e:
    #     print(e)
    # file_name = os.getcwd() + "/logs/" + file.filename.replace(" ", "-")
    # with open(file_name, 'wb+') as f:
    #     f.write(file.file.read())
    #     f.close()

    # file = jsonable_encoder({"imagePath": file_name})
    # new_image = await add_image(file)
    # return {"filename": new_image}

    # csv = await file.read()  # async read
    # stream = StringIO(str(csv))
    #
    try:
        log_csv = pd.read_excel(file.file.read(), sheet_name=sheet_name)
        # log_csv['Name'] = log_csv['STATUS'].str.cat(log_csv['USERID'], sep=" ")

        case_id = 'case:consept:name';
        case_ids = case_column_name.split(';')
        if len(case_ids) == 1:
            log_csv['case:consept:name'] = log_csv[case_ids[0]].astype(str)
        if len(case_ids) == 2:
            log_csv['case:consept:name'] = log_csv[case_ids[0]].astype(str) + ' - ' + log_csv[case_ids[1]].astype(str)

        activity_key = 'case:consept';
        activity_keys = activity_column_name.split(';')

        if len(activity_keys) == 1:
            log_csv['case:consept'] = log_csv[activity_keys[0]].astype(str)
        if len(activity_keys) == 2:
            log_csv['case:consept'] = log_csv[activity_keys[0]].astype(str) + ' - ' + log_csv[activity_keys[1]].astype(
                str)

        log_csv = format_dataframe(log_csv, case_id=case_id, activity_key=activity_key,
                                   timestamp_key=timestamp_key, start_timestamp_key=start_timestamp_key)

        log_csv = dataframe_utils.convert_timestamp_columns_in_df(log_csv)

        # rename and convert cost field
        if cost_key is not None:
            if cost_key in log_csv.columns:
                log_csv = log_csv.rename(columns={cost_key: "concept:cost"})
                pd.to_numeric(log_csv['concept:cost'])

        # rename and convert resource field
        if resource_key is not None:
            if resource_key in log_csv.columns:
                log_csv = log_csv.rename(columns={resource_key: "org:resource"})

        log_csv = log_csv.sort_values('time:timestamp')

        log_id = str(uuid4())

        event_log.create(log_id, 'Test.csv', case_column_name, activity_column_name, timestamp_key,
                         start_timestamp_key, ',', db)

        log_csv.to_sql(
            log_id,
            engine_event_log,
            if_exists='replace',
            index=False,
            chunksize=500,
            dtype={
                "case:concept:name": String(),
                "concept:name": String()

            }
        )

        # session_data.Logs[log_id] = log_csv;
        csv = log_csv.to_csv(index=False);
        # print(session_data.Logs)
        # print(csv)
        # file.filename
        return {
            'log_id': log_id,
            "csv": csv
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# @router.post("/LoadXes", dependencies=[Depends(cookie)])
@router.post("/LoadXes")
async def load_xes(file: UploadFile = File(...), session_data: SessionData = Depends(verifier)):
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
    log = xes_importer.apply(file_name)
    log_csv = pm4py.convert_to_dataframe(log)
    # log_csv = format_dataframe(log_csv, case_id='Case ID', activity_key='Activity', timestamp_key='End Date')
    log_csv = dataframe_utils.convert_timestamp_columns_in_df(log_csv)
    #
    log_csv = log_csv.sort_values('time:timestamp')

    log_id = str(uuid4())
    log_csv.to_sql(
        log_id,
        engine,
        if_exists='append',
        index=False,
        chunksize=500,
        dtype={
            "case:concept:name": String(),
            "concept:name": String()
        }
    )

    session_data.Logs[log_id] = log_csv;
    print(session_data.Logs)
    # print(csv)
    # file.filename
    return {"id": log_id}


@router.post('/GetTraceCount', dependencies=[Depends(cookie)])
async def get_trace_count(
        session_id: str = Form(...),
        org_name: str = Form(...),
        db: Session = Depends(database.get_org_event_db)):
    df = await get_df_session_or_database('429edd7f-b3cd-4002-b925-0d019b53b848', session_id, db)

    db.close()
    return {'TraceCount': len(df['case:concept:name'].unique())}


@router.post('/GetEventDataInfo')
async def get_event_data_info(session_id: str = Form(...), project_id: str = Form(...)):
    try:
        handler: ParquetHandler = session_manager.get_handler_for_process_and_session(project_id, session_id)
        df = handler.dataframe
        # df = await get_df_session_or_database(project_id, session_id)

        trace_count = len(df['case:concept:name'].unique())
        event_count = len(df)

        start_dict = []
        acts = handler.get_start_activities()  # pm4py.get_start_activities(df)

        total_act_count = 0
        for act in acts:
            total_act_count += acts[act]

        for act in acts:
            start_dict.append({
                'activity_name': act,
                'frequency': str(acts[act]),
                'frequency_rate': (acts[act] / total_act_count) * 100
            })
            # start_dict[act] = str(acts[act])

        end_dict = []
        acts = handler.get_end_activities()  # pm4py.get_end_activities(df)

        total_act_count = 0
        for act in acts:
            total_act_count += acts[act]

        for act in acts:
            end_dict.append({
                'activity_name': act,
                'frequency': str(acts[act]),
                'frequency_rate': (acts[act] / total_act_count) * 100
            })
        # end_dict[act] = str(acts[act])

        mf = df.groupby('case:concept:name').agg(
            {"start_timestamp": "min", "time:timestamp": "max", "case:concept:name": "count"})

        mf.columns = ["min", "max", "count"]
        mf['min'] = pd.to_datetime(mf['min'])

        mf["Diff"] = mf["max"] - mf["min"]

        mf['case:concept:name'] = mf.index

        case_info = mf.to_dict(orient="records")

        max = mf["Diff"].max()
        min = mf["Diff"].min()
        mean = mf["Diff"].mean() if not str(mf["Diff"].mean()) == "NaT" else 0
        median = mf["Diff"].median() if not str(mf["Diff"].median()) == 'NaT' else 0

        df['Diff'] = df['time:timestamp'] - df['start_timestamp']

        act_df = df.groupby('concept:name').agg({"concept:name": "count", "Diff": ["mean", "median"]})
        act_df.columns = ["count", "mean", "median"]
        act_df["rate"] = act_df["count"].apply(lambda x: 100 * x / float(act_df["count"].sum()))

        return {
            "id": project_id,
            'trace_count': trace_count,
            'event_count': event_count,
            'mean': mean,
            'max': max,
            'min': min,
            'median': median,
            'start_activities': start_dict,
            'end_activities': end_dict,
            'case_info': case_info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/EventsPerTime')
async def events_per_time(session_id: str = Form(...), project_id: str = Form(...)):
    df = session_manager.get_handler_for_process_and_session(project_id, session_id).dataframe

    # svg = session_manager.get_handler_for_process_and_session(project_id, session_id).get_events_per_time_svg()

    graph_data = Vis.events_per_time(df)
    return {
        'x_values': graph_data[0],
        'y_values': graph_data[1]
    }


@router.post('/GetMainMetrics')
async def get_main_metrics(session_id: str = Form(...), project_id: str = Form(...)):
    handler: ParquetHandler = session_manager.get_handler_for_process_and_session(project_id, session_id)

    return {
        'median_case_duration': handler.get_median_case_duration(),
    }


@router.post('/AddFilter')
async def add_filter(request: Request, session_id: str = Form(...), project_id: str = Form(...)):
    df = session_manager.get_handler_for_process_and_session(project_id, session_id).dataframe

    svg = session_manager.get_handler_for_process_and_session(project_id, session_id).get_events_per_time_svg()

    graph_data = Vis.events_per_time(df)
    return {
        'x_values': graph_data[0],
        'y_values': graph_data[1]
    }


@router.post('/GetEventCount', dependencies=[Depends(cookie)])
async def get_event_count(log_id: str = Form(...), db: Session = Depends(get_db), session_id: UUID = Depends(cookie)):
    df = await get_df_session_or_database(log_id, session_id)

    return {'EventCount': len(df)}


# ----------------------------------------------------------------------------------------------------------------------

@router.post('/GetStartActivities')
async def get_start_activities(session_id: str = Form(...),
                               project_id: str = Form(...), db: Session = Depends(get_db)):
    """
       Gets the start activities from the log
       Returns
       ------------
       start_activities
           Dictionary of start activities
       """
    clean_expired_sessions()

    # reads the session
    session = session_id
    # reads the requested process name
    process = project_id

    logging.info("get_start_activities start session=" + str(session) + " process=" + str(process))

    if check_session_validity(session):
        user = get_user_from_session(session)
        if session_manager.check_user_log_visibility(user, process):
            dictio = session_manager.get_handler_for_process_and_session(process, session).get_start_activities()
            for entry in dictio:
                dictio[entry] = int(dictio[entry])
            list_act = sorted([(x, y) for x, y in dictio.items()], key=lambda x: x[1], reverse=True)
            logging.info(
                "get_start_activities complete session=" + str(session) + " process=" + str(process) + " user=" + str(
                    user))

            return {"startActivities": list_act}

    return {"startActivities": []}


@router.post('/GetEndActivities')
def get_end_activities(session_id: str = Form(...), project_id: str = Form(...), db: Session = Depends(get_db)):
    """
    Gets the end activities from the log
    Returns
    ------------
    end_activities
        Dictionary of end activities
    """
    clean_expired_sessions()

    # reads the session
    session = session_id
    # reads the requested process name
    process = project_id

    logging.info("get_end_activities start session=" + str(session) + " process=" + str(process))

    if check_session_validity(session):
        user = get_user_from_session(session)
        if session_manager.check_user_log_visibility(user, process):
            dictio = session_manager.get_handler_for_process_and_session(process, session).get_end_activities()
            for entry in dictio:
                dictio[entry] = int(dictio[entry])
            list_act = sorted([(x, y) for x, y in dictio.items()], key=lambda x: x[1], reverse=True)
            logging.info(
                "get_end_activities complete session=" + str(session) + " process=" + str(process) + " user=" + str(
                    user))

            return {"endActivities": list_act}

    return {"endActivities": []}


@router.post('/GetAllVariants')
def get_all_variants(session_id: str = Form(...), project_id: str = Form(...),
                     db: Session = Depends(get_db)):
    """
    Gets all the variants from the event log
    Returns
    ------------
    dictio
        JSONified dictionary that contains in the 'variants' entry the list of variants
    """

    # reads the session
    session = session_id
    # reads the requested process name
    process = project_id
    # reads the maximum number of variants to return
    max_no_variants = 100

    parameters = {
        "max_no_variants": int(max_no_variants),
        pm_constants.PARAMETER_CONSTANT_CASEID_KEY: 'case:concept:name',
        pm_constants.PARAMETER_CONSTANT_ACTIVITY_KEY: 'concept:name'

    }

    variants, log_summary = session_manager.get_handler_for_process_and_session(process,
                                                                                session).get_variant_statistics(
        parameters=parameters)

    dictio = {"variants": variants}
    for key in log_summary:
        dictio[key] = log_summary[key]

    return dictio


@router.post('/GetVariants')
def get_variants(session_id: str = Form(...), project_id: str = Form(...), db: Session = Depends(get_db)):
    """
    Gets variants data from the event log
    Returns
    ------------
    dictio
        JSONified dictionary that contains in the 'variants' entry the list of variants
    """

    # reads the session
    session = session_id
    # reads the requested process name
    process = project_id
    # reads the maximum number of variants to return
    max_no_variants = 100

    parameters = {
        pm_constants.PARAMETER_CONSTANT_CASEID_KEY: 'case:concept:name',
        pm_constants.PARAMETER_CONSTANT_ACTIVITY_KEY: 'concept:name'

    }

    # new_handler = session_manager.get_handler_for_process_and_session(process,
    #                                                                   session).add_filter(
    #     ['start_activities', ['Inbound Call']],
    #     [['start_activities', ['Inbound Call']], ['end_activities', ['Handle Case']]])
    #
    # session_manager.set_handler_for_process_and_session(process, session, new_handler)

    variants_df = session_manager.get_handler_for_process_and_session(process,
                                                                      session).get_variants_df()

    variants_df = variants_df.groupby('variant').agg(
        {'variant': "count", 'caseDuration': ['sum', 'mean', 'min', 'max']})

    variants_df.columns = ["count", "caseDuration_sum", "caseDuration_mean", "caseDuration_min",
                           "caseDuration_max"]
    variants_df['variant'] = variants_df.index
    variants_df["rate_count"] = variants_df["count"].apply(
        lambda x: 100 * x / float(variants_df["count"].sum()))
    variants_df["rate_duration"] = variants_df["caseDuration_sum"].apply(
        lambda x: 100 * x / float(variants_df["caseDuration_sum"].sum()))
    variants_df.sort_values(by='count', ascending=False, inplace=True)

    result = variants_df.to_dict(orient="records")

    return result


@router.post('/GetDFG', dependencies=[Depends(cookie)])
async def get_dfg(log_id: str = Form(...), db: Session = Depends(get_db), session_id: UUID = Depends(cookie)):
    df = await get_df_session_or_database(log_id, session_id)

    from pm4py.algo.discovery.dfg import algorithm as dfg_discovery
    from pm4py.visualization.dfg import visualizer as dfg_visualization

    log = log_converter.apply(df)

    dfg = dfg_discovery.apply(log, variant=dfg_discovery.Variants.PERFORMANCE)
    parameters = {dfg_visualization.Variants.PERFORMANCE.value.Parameters.FORMAT: "svg"}
    gviz = dfg_visualization.apply(dfg, log=log, variant=dfg_visualization.Variants.PERFORMANCE, parameters=parameters)
    svg = gviz.render(cleanup=True)
    lines = ''
    with open(svg) as f:
        lines = f.read()
    os.remove(svg)
    print(lines)
    return lines


@router.get('/GetSvg/{symbol_name:path}')
async def get_svg(symbol_name: str):
    file_path = os.path.join(os.getcwd(), "symbols", html.unescape(symbol_name) + '.svg')
    print(file_path)
    return FileResponse(file_path)


@router.get('/GetAllLogs')
async def get_all_logs(symbol_name: str, db: Session = Depends(get_db)):
    result = eventlog_repository.get_all(db)
    db.close()
    return result


@router.post('/GetLog')
async def get_log(log_id: str = Form(...), db: Session = Depends(get_db)):
    result = eventlog_repository.get(log_id, db)
    db.close()
    return result


@router.post('/GetAllVariants')
async def get_all_variants(process: str = Form('process'), session_id: str = Form(...),
                           max_no_variants: int = Form(constants.MAX_NO_VARIANTS_TO_RETURN), log_id: str = Form(...),
                           db: Session = Depends(get_db)):
    """
       Gets all the variants from the event log
       Returns
       ------------
       dictio
           JSONified dictionary that contains in the 'variants' entry the list of variants
       """
    clean_expired_sessions()

    # reads the session
    session = session_id
    # reads the requested process name
    process = process  # request.args.get('process', default='receipt', type=str)
    # reads the maximum number of variants to return
    max_no_variants = max_no_variants  # request.args.get('max_no_variants', default=constants.MAX_NO_VARIANTS_TO_RETURN, type=int)

    logging.info("get_all_variants start session=" + str(session) + " process=" + str(process))

    dictio = {}

    if check_session_validity(session):
        user = get_user_from_session(session)
        if session_manager.check_user_log_visibility(user, process):
            parameters = {}
            parameters["max_no_variants"] = int(max_no_variants)

            variants, log_summary = session_manager.get_handler_for_process_and_session(process,
                                                                                        session).get_variant_statistics(
                parameters=parameters)
            dictio = {"variants": variants}
            for key in log_summary:
                dictio[key] = log_summary[key]
        logging.info(
            "get_all_variants complete session=" + str(session) + " process=" + str(process) + " user=" + str(user))

    return dictio


from network import make_request
import aiohttp


@router.post('/LoginService')
async def login_service(user: str = Form(...), password: str = Form(...), session=Depends(get_session)):
    clean_expired_sessions()

    if Configuration.enable_session:
        # reads the user name
        user = user
        # reads the password
        password = password
        session_id = do_login(user, password)

        if session_id is not None:
            return ({"status": "OK", "sessionEnabled": True, "sessionId": session_id})
        else:
            return ({"status": "FAIL", "sessionEnabled": True, "sessionId": None})

    return ({"status": "OK", "sessionEnabled": False, "sessionId": None})


from threading import Semaphore
import traceback


class Commons:
    semaphore_matplot = Semaphore(1)


@router.post('/GetNumericAttributeGraph')
def get_numeric_attribute_graph(session: str = Form(...), process: str = Form('receipt'), attribute: str = Form(...)):
    """
    Gets the numeric attribute graph
    Returns
    -------------
    dictio
        JSONified dictionary that contains in the 'base64' entry the SVG representation
        of the case duration graph
    """
    clean_expired_sessions()

    # reads the session
    session = session
    # reads the requested process name
    process = process
    # reads the requested attribute
    attribute = attribute

    logging.info(
        "get_numeric_attribute_graph start session=" + str(session) + " process=" + str(process) + " attribute=" + str(
            attribute))

    dictio = {}
    if check_session_validity(session):
        user = get_user_from_session(session)
        if session_manager.check_user_log_visibility(user, process):
            Commons.semaphore_matplot.acquire()
            try:
                base64, gviz_base64, ret = session_manager.get_handler_for_process_and_session(process,
                                                                                               session).get_numeric_attribute_svg(
                    attribute)
                dictio = {"base64": base64.decode('utf-8'), "gviz_base64": gviz_base64.decode('utf-8'), "points": ret}
            except:
                logging.error(traceback.format_exc())
                dictio = {"base64": "", "gviz_base64": "", "points": []}
            Commons.semaphore_matplot.release()

        logging.info(
            "get_numeric_attribute_graph start session=" + str(session) + " process=" + str(
                process) + " attribute=" + str(
                attribute) + " user=" + str(user))

    return dictio


@router.post('/GetEventsPerTime')
def get_events_per_time(session_id: str = Form(...), project_id: str = Form(...)):
    """
    Gets the Event per Time graph
    Returns
    -------------
    dictio
        JSONified dictionary that contains in the 'base64' entry the SVG representation
        of the events per time graph
    """
    clean_expired_sessions()

    # reads the session
    session = session_id
    # reads the requested process name
    process = project_id

    logging.info("get_events_per_time start session=" + str(session) + " process=" + str(process))

    dictio = {}

    if check_session_validity(session):
        user = get_user_from_session(session)
        if session_manager.check_user_log_visibility(user, process):
            Commons.semaphore_matplot.acquire()
            try:
                base64, gviz_base64, ret = session_manager.get_handler_for_process_and_session(process,
                                                                                               session).get_events_per_time_svg()
                data_x = []
                data_y = []
                for i in range(len(ret)):
                    data_x.append(ret[i][0])
                    data_y.append(ret[i][1])

                dictio = {"base64": base64.decode('utf-8'), "gviz_base64": gviz_base64.decode('utf-8'), "points": ret,
                          "points_x": data_x, "points_y": data_y}
            except:
                logging.error(traceback.format_exc())
                dictio = {"base64": "", "gviz_base64": "", "points": [], "points_x": [], "points_y": []}
            Commons.semaphore_matplot.release()

        logging.info(
            "get_events_per_time complete session=" + str(session) + " process=" + str(process) + " user=" + str(user))

    return dictio


@router.post('/GetEvents')
def get_events(session_id: str = Form(...), process_id: str = Form(...)):
    """
    Gets the events from a Case ID
    Returns
    -------------
    dictio
        JSONified dictionary that contains in the 'events' entry the list of events
    """
    clean_expired_sessions()

    # reads the session
    session = session_id
    process = process_id

    logging.info("get_events start session=" + str(session) + " process=" + str(process))

    dictio = {}

    if check_session_validity(session):
        user = get_user_from_session(session)
        if session_manager.check_user_log_visibility(user, process):
            caseid = 'case:concept:name'
            events = session_manager.get_handler_for_process_and_session(process, session).get_events(caseid)
            i = 0
            while i < len(events):
                keys = list(events[i].keys())
                for key in keys:
                    if str(events[i][key]).lower() == "nan" or str(events[i][key]).lower() == "nat":
                        del events[i][key]
                i = i + 1
            dictio = {"events": events}

        logging.info("get_events complete session=" + str(session) + " process=" + str(process) + " user=" + str(user))

    return dictio


@router.post('/GetCaseDuration')
def get_case_duration(session_id: str = Form(...), project_id: str = Form(...)):
    """
    Gets the Case Duration graph
    Returns
    ------------
    dictio
        JSONified dictionary that contains in the 'base64' entry the SVG representation
        of the case duration graph
    """

    dictio = {}
    Commons.semaphore_matplot.acquire()
    try:
        base64, gviz_base64, ret = session_manager.get_handler_for_process_and_session(project_id,
                                                                                       session_id).get_case_duration_svg()
        data_x = []
        data_y = []
        for i in range(len(ret)):
            data_x.append(ret[i][0])
            data_y.append(ret[i][1])

        dictio = {"base64": base64.decode('utf-8'), "gviz_base64": gviz_base64.decode('utf-8'), "points": ret,
                  "points_x": data_x, "points_y": data_y}
    except:
        logging.error(traceback.format_exc())
        dictio = {"base64": "", "gviz_base64": "", "points": [], "points_x": [], "points_y": []}
    Commons.semaphore_matplot.release()

    return dictio


@router.post('/GetProcessSchema')
def get_process_schema(session_id: str = Form(...), project_id: str = Form(...), decoration: str = Form('freq'),
                       typeOfModel: str = Form('dfg'), simplicity: str = Form('1')):
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
    process = project_id

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
                simplicity = 0.65  # constants.DEFAULT_DEC_FACTOR # request.args.get('simplicity', default=constants.DEFAULT_DEC_FACTOR, type=float)
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

                dictio = {
                    "base64": base64.decode('utf-8'),
                    "model": model,
                    "format": format,
                    "handler": this_handler,
                    "activities": activities,
                    "start_activities": start_activities,
                    "end_activities": end_activities,
                    "gviz_base64": gviz_base64.decode('utf-8'),
                    "graph_rep": graph_rep,
                    "type_of_model": type_of_model,
                    "decoration": decoration,
                    "second_model": second_model,
                    "second_format": second_format,
                    "activity_key": activity_key}
                for key in log_summary:
                    dictio[key] = log_summary[key]
            except:
                logging.error(traceback.format_exc())
            Commons.semaphore_matplot.release()

            logging.info(
                "get_process_schema complete session=" + str(session) + " process=" + str(process) + " user=" + str(
                    user))
    return dictio


@router.post('/_GetProcessSchema')
def _get_process_schema(session_id: str = Form(...), project_id: str = Form(...), decoration: str = Form('perf'),
                        typeOfModel: str = Form('indbpmn'), simplicity: str = Form('1')):
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
    process = project_id

    logging.info(
        "get_process_schema start session=" + str(session) + " process=" + str(process))

    if check_session_validity(session):
        user = get_user_from_session(session)
        if session_manager.check_user_log_visibility(user, process):
            handler = session_manager.get_handler_for_process_and_session(process, session)
            df = handler.dataframe
            tree = pm4py.discover_process_tree_inductive(df)
            from pm4py.objects.conversion.process_tree import converter
            bpmn_graph = converter.apply(tree, variant=converter.Variants.TO_BPMN)
            from pm4py.objects.bpmn.layout import layouter
            bpmn_graph = layouter.apply(bpmn_graph)
            gviz = pm4py.visualization.bpmn.visualizer.apply(bpmn_graph, parameters={'format': 'svg'})
            gviz_base64 = base64.b64encode(str(gviz).encode('utf-8'))
            from pm4py.visualization.common.utils import get_base64_from_gviz
            _base64 = get_base64_from_gviz(gviz)
            dictio = {'base64': _base64.decode('utf-8')}
            pm4py.write_bpmn(bpmn_graph, "ru.bpmn", enable_layout=False)

            from pm4py.algo.discovery.inductive import algorithm as inductive_miner
            from pm4py.visualization.process_tree import visualizer as pt_visualizer

            net, initial_marking, final_marking = inductive_miner.apply(df)
            from pm4py.visualization.petri_net import visualizer as pn_vis_factory
            gviz = pn_vis_factory.apply(net, initial_marking, final_marking, parameters={"format": "svg"},
                                        variant=pn_vis_factory.Variants.FREQUENCY)

            pt_visualizer.view(gviz)

    return dictio


@router.post('/GetHappyPath')
def get_happy_path(session_id: str = Form(...),
                   project_id: str = Form(...)):
    """
       Gets the Happy Path
       Returns
       ------------
       dictio
           JSONified dictionary that contains in the 'base64' entry the SVG representation
           of the case duration grap
    """
    try:

        handler: ParquetHandler = session_manager.get_handler_for_process_and_session(project_id,
                                                                                      session_id)
        handler.get_variants_df()
        list = handler.get_most_common_variant()

        variants_df = session_manager.get_handler_for_process_and_session(project_id,
                                                                          session_id).get_variants_df()

        variants_df = variants_df.groupby('variant').agg(
            {'variant': "count", 'caseDuration': ['sum', 'mean', 'min', 'max']})

        variants_df.columns = ["count", "case_duration_sum", "case_duration_mean", "case_duration_min",
                               "case_duration_max"]
        variants_df['variant'] = variants_df.index
        variants_df["count_sum"] = variants_df["count"].sum()
        variants_df["case_duration_all_sum"] = variants_df["case_duration_sum"].sum()
        variants_df["case_duration_all_mean"] = variants_df["case_duration_sum"].mean()

        variants_df["rate_count"] = variants_df["count"].apply(
            lambda x: 100 * x / float(variants_df["count"].sum()))
        variants_df["rate_duration"] = variants_df["case_duration_sum"].apply(
            lambda x: 100 * x / float(variants_df["case_duration_sum"].sum()))
        variants_df.sort_values(by='count', ascending=False, inplace=True)

        result_df = variants_df[variants_df['variant'] == list]

        dictio = result_df.to_dict(orient="records")[0]

    except:
        logging.error(traceback.format_exc())
        dictio = {}

    return dictio


@router.post('/GetActivities')
def get_activities(
        session_id: str = Form(...),
        project_id: str = Form(...),
        activity_key: str = Form(...)):
    """
       Gets the Happy Path
       Returns
       ------------
       dictio
           JSONified dictionary that contains in the 'base64' entry the SVG representation
           of the case duration grap
    """

    dictio = {}
    list = []

    try:
        dictio = session_manager.get_handler_for_process_and_session(project_id,
                                                                     session_id).get_attribute_values(
            activity_key)
        df = session_manager.get_handler_for_process_and_session(project_id, session_id).dataframe
        case_count = len(df['case:concept:name'].unique())
        mf = df.groupby(by=['case:concept:name', 'concept:name']).agg({'case:concept:name': 'count'})
        mf.columns = ['count']
        mf = mf.reset_index()

        result = []
        for key in dictio:
            case_len = len(mf[mf['concept:name'] == key]['case:concept:name'].unique())
            result.append({
                'activity_name': key,
                'event_count': dictio[key],
                'total_case': case_count,
                'case_count': case_len,
                'case_rate': (case_len / case_count) * 100
            })

    except:
        logging.error(traceback.format_exc())
        result = []

    return result


@router.post('/GetActivitiesCount')
def get_activities_count(session: SessionInfo = Depends(get_session), project_id: str = Form(...),
                         activity_key: str = Form(...)):
    """
       Gets Activity Counts
       Returns
       ------------
       dictio
           JSONified dictionary that contains in the 'base64' entry the SVG representation
           of the case duration grap
    """

    dictio = {}
    list = []

    try:
        dictio = session_manager.get_handler_for_process_and_session(project_id,
                                                                     session.session_id).get_attribute_values(
            activity_key)
        dictio = sorted(dictio.items(), key=lambda x: x[1], reverse=True)

        result = {}
        for item in dictio:
            result[item[0]] = item[1]

        return result

    except:
        logging.error(traceback.format_exc())
        dictio = {}

    return dictio


@router.post('/GetLogSummary')
def get_log_summary(session_id: str = Form(...), project_id: str = Form(...)):
    """
       Gets a summary of the log
       Returns
       ------------
       log_summary
           Log summary
       """
    clean_expired_sessions()

    # reads the session
    session = session_id
    # reads the requested process name
    process = project_id

    logging.info("get_log_summary start session=" + str(session) + " process=" + str(process))

    dictio = {}

    if check_session_validity(session):
        user = get_user_from_session(session)
        if session_manager.check_user_log_visibility(user, process):

            try:
                dictio = session_manager.get_handler_for_process_and_session(process, session).get_log_summary_dictio()

            except:
                logging.error(traceback.format_exc())
                dictio = {}

        logging.info(
            "get_log_summary complete session=" + str(session) + " process=" + str(process) + " user=" + str(user))

    return dictio


@router.post('/GetAllVariantsAndCases')
def get_all_variants_and_cases(session_id: str = Form(...), project_id: str = Form(...)):
    """
    Gets all the variants from the event log
    Returns
    ------------
    dictio
        JSONified dictionary that contains in the 'variants' entry the list of variants
    """
    clean_expired_sessions()

    # reads the session
    session = session_id
    # reads the requested process name
    process = project_id
    # reads the maximum number of variants to return
    max_no_variants = constants.MAX_NO_VARIANTS_TO_RETURN  # request.args.get('max_no_variants', default=constants.MAX_NO_VARIANTS_TO_RETURN, type=int)

    parameters = {}
    parameters["max_no_variants"] = int(max_no_variants)

    handler = session_manager.get_handler_for_process_and_session(process, session)
    variants, log_summary = handler.get_variant_statistics(parameters=parameters)
    cases_list, log_summary = handler.get_case_statistics(parameters=parameters)

    dictio = {"variants": variants, "cases": cases_list}
    for key in log_summary:
        dictio[key] = log_summary[key]

    return dictio


@router.post('/GetAllPaths')
def get_all_paths(session: SessionInfo = Depends(get_session),
                  project_id: str = Form(...), attribute_key: str = Form('concept:name')):
    try:
        # reads the requested attribute
        attribute_key = attribute_key

        dictio = session_manager.get_handler_for_process_and_session(project_id, session.session_id).get_paths(
            attribute_key,
            measure='performance')
        list_values = sorted([("@@".join(x), y) for x, y in dictio.items()], key=lambda x: x[1], reverse=True)

        return {"paths": list_values}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/GetAttributeValues')
def get_attribute_values(session_id: str = Form(...), project_id: str = Form(...),
                         attribute_key: str = Form('concept:name')):
    clean_expired_sessions()

    # reads the session
    session = session_id
    # reads the requested process name
    process = project_id

    logging.info("get_attribute_values start session=" + str(session) + " process=" + str(process))

    # reads the requested attribute
    attribute_key = attribute_key
    if check_session_validity(session):
        user = get_user_from_session(session)
        if session_manager.check_user_log_visibility(user, process):
            dictio = session_manager.get_handler_for_process_and_session(process, session).get_attribute_values(
                attribute_key)
            list_values = sorted([(x, y) for x, y in dictio.items()], key=lambda x: x[1], reverse=True)
            logging.info(
                "get_attribute_values complete session=" + str(session) + " process=" + str(process) + " user=" + str(
                    user))

            return {"attributeValues": list_values}

    return {"attributeValues": []}


@router.post('/GetPerformanceDfg')
def performance_dfg(  # session: SessionInfo = Depends(get_session),
        session_id: str = Form(...),
        project_id: str = Form(...),
        attribute_key: str = Form('concept:name')):
    df = session_manager.get_handler_for_process_and_session(project_id, session_id).dataframe
    result = service.Discovery.performance_dfg(df)
    dicto = {
        'diagram': result
    }

    return dicto


@router.post('/GetDfgDiagram')
def dfg_diagram(  # session: SessionInfo = Depends(get_session),
        session_id: str = Form(...),
        project_id: str = Form(...),
        attribute_key: str = Form('concept:name')):
    df = session_manager.get_handler_for_process_and_session(project_id, session_id).dataframe

    dfg, start_activities, end_activities = pm4py.discover_dfg(df, case_id_key='case:concept:name',
                                                               activity_key='concept:name',
                                                               timestamp_key='time:timestamp')
    # pm4py.view_dfg(dfg, start_activities, end_activities, format='svg')
    # activities_df = df['concept:name'].nunique()
    # paths = []
    # for key in dfg:
    #   paths.append({
    #       'path': key[0] + ',' + key[1],
    #       'frequency': dfg[key]
    #   })

    format = 'svg'
    from pm4py.visualization.dfg import visualizer as dfg_visualizer
    dfg_parameters = dfg_visualizer.Variants.FREQUENCY.value.Parameters
    parameters = {}
    parameters[dfg_parameters.FORMAT] = format
    parameters[dfg_parameters.START_ACTIVITIES] = start_activities
    parameters[dfg_parameters.END_ACTIVITIES] = end_activities
    parameters["bgcolor"] = 'white'
    gviz = dfg_visualizer.apply(dfg, variant=dfg_visualizer.Variants.FREQUENCY,
                                parameters=parameters)

    res = str(gviz)
    dicto = {
        'diagram': res
    }

    return dicto


@router.post('/GetBpmnDiagram')
def get_bpmn_diagram(  # session: SessionInfo = Depends(get_session),
        session_id: str = Form(...),
        project_id: str = Form(...),
        attribute_key: str = Form('concept:name')):
    df = session_manager.get_handler_for_process_and_session(project_id, session_id).dataframe

    bpmn_graph = pm4py.discover_bpmn_inductive(df, activity_key='concept:name', case_id_key='case:concept:name',
                                               timestamp_key='time:timestamp')

    res = view_bpmn(bpmn_graph)
    dicto = {
        'diagram': res
    }

    return dicto


@router.post('/GetDailyCasesPerMonth')
def get_daily_cases_per_mounth(  # session: SessionInfo = Depends(get_session),
        session_id: str = Form(...),
        project_id: str = Form(...),
        attribute_key: str = Form('concept:name')):
    # logging.info("get_attribute_values start session=" + str(session.session_id) + " process=" + str(project_id))

    # reads the requested attribute
    attribute_key = attribute_key

    dicto = {}

    df = session_manager.get_handler_for_process_and_session(project_id, session_id).dataframe.copy()

    from pandasai import PandasAI
    from pandasai.llm.openai import OpenAI
    llm = OpenAI(api_token="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")
    pandas_ai = PandasAI(llm, conversational=False)

    # res = query_wrapper(df, 'suggest_improvements',
    #                     parameters={'api_key': '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'})

    # pandas_ai(df, prompt='En cok zaman alan aktiviteler hangileri')

    bpmn_graph = pm4py.discover_bpmn_inductive(df, activity_key='concept:name', case_id_key='case:concept:name',
                                               timestamp_key='time:timestamp')

    td = df['time:timestamp'].max() - df['time:timestamp'].min()
    day_count = td.days
    case_count = len(df['case:concept:name'].unique())
    event_count = len(df['concept:name'])
    case_per_day = case_count / day_count
    event_per_day = event_count / day_count

    df.index = df['time:timestamp']
    gr = df.groupby(by=[df.index.month, df.index.year]).agg({'case:concept:name': 'count'})
    gr.index.names = ['month', 'year']
    gr = gr.reset_index()
    gr.columns = ['month', 'year', 'case_count']
    gr['case_rate'] = gr['case_count'] / 30

    gr['date_index'] = gr['year'].apply(str) + '_' + gr['month'].apply(
        lambda x: "{}{}".format('0' if x < 10 else '', x))

    gr.sort_values(by='date_index', ascending=True, inplace=True)

    dicto = {
        'day_count': day_count,
        'event_count': event_count,
        'case_per_day': case_per_day,
        'event_per_day': event_per_day,
        'daily_cases_per_month': gr.to_dict(orient="records")
    }

    return dicto


@router.post('/GetThroughputTimes')
def get_throughput_times(session: SessionInfo = Depends(get_session),
                         project_id: str = Form(...),
                         attribute_key: str = Form('concept:name')):
    try:
        attribute_key = attribute_key

        dicto = {}
        df = session_manager.get_handler_for_process_and_session(project_id, session.session_id).dataframe

        mf = df.groupby(by='case:concept:name').agg({'time:timestamp': ['min', 'max']})
        mf = mf.reset_index()
        mf.columns = ['case', 'min', 'max']
        mf['diff'] = mf['max'] - mf['min']
        mf['diff_days'] = (mf['max'] - mf['min']).dt.days
        mf['diff_hours'] = mf['diff'] / np.timedelta64(1, 'h')
        mf['diff_minutes'] = mf['diff'] / np.timedelta64(1, 'm')
        mf['diff_seconds'] = mf['diff'] / np.timedelta64(1, 's')

        dicto = {
            '0 - 9 Days': len(mf[(mf['diff_days'] >= 0) & (mf['diff_days'] < 9)]),
            '9 - 18 Days': len(mf[(mf['diff_days'] >= 9) & (mf['diff_days'] < 18)]),
            '18 - 27 Days': len(mf[(mf['diff_days'] >= 18) & (mf['diff_days'] < 27)]),
            '27 - 36 Days': len(mf[(mf['diff_days'] >= 27) & (mf['diff_days'] < 36)]),
            '36 - 45 Days': len(mf[(mf['diff_days'] >= 36) & (mf['diff_days'] < 45)]),
            '45 - 54 Days': len(mf[(mf['diff_days'] >= 45) & (mf['diff_days'] < 54)]),
            '54 - 63 Days': len(mf[(mf['diff_days'] >= 54) & (mf['diff_days'] < 63)]),
            '63 - 72 Days': len(mf[(mf['diff_days'] >= 63) & (mf['diff_days'] < 72)]),
            '72 - 81 Days': len(mf[(mf['diff_days'] >= 72) & (mf['diff_days'] < 81)]),
            ' > 81 Days': len(mf[mf['diff_days'] > 81]),
        }

        return dicto
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/GetActivitiesThroughputTimes')
def get_activities_throughput_times(session: SessionInfo = Depends(get_session),
                                    project_id: str = Form(...),
                                    attribute_key: str = Form('concept:name')):
    try:
        attribute_key = attribute_key

        dicto = {}
        df = session_manager.get_handler_for_process_and_session(project_id, session.session_id).dataframe

        mf = df.groupby(by=['case:concept:name', 'concept:name']).agg({'time:timestamp': ['min', 'max']})
        mf = mf.reset_index()
        mf.columns = ['case', 'activity', 'min', 'max']
        mf['diff'] = mf['max'] - mf['min']
        mf['diff_days'] = (mf['max'] - mf['min']).dt.days
        mf['diff_hours'] = mf['diff'] / np.timedelta64(1, 'h')
        mf['diff_minutes'] = mf['diff'] / np.timedelta64(1, 'm')
        mf['diff_seconds'] = mf['diff'] / np.timedelta64(1, 's')

        mf = mf.groupby(by='activity').agg({'diff_hours': ['sum']})
        mf.columns = ['hours']
        mf.sort_values(by=['hours'], inplace=True, ascending=False)
        for index, row in mf.iterrows():
            dicto[index] = row['hours']

        return dicto
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/GetBottlenecks')
def get_bottlenecks(session_id: str = Form(...), project_id: str = Form(...),
                    attribute_key: str = Form('concept:name')):
    clean_expired_sessions()

    # reads the session
    session = session_id
    # reads the requested process name
    process = project_id

    logging.info("get_attribute_values start session=" + str(session) + " process=" + str(process))

    # reads the requested attribute
    attribute_key = attribute_key

    dicto = {}
    if check_session_validity(session):
        user = get_user_from_session(session)
        if session_manager.check_user_log_visibility(user, process):
            df = session_manager.get_handler_for_process_and_session(process, session).dataframe

            from pm4py.statistics.passed_time.pandas import algorithm as pt;
            pt.apply(df, 'Ekip Lideri Onayı')

            mf = df.groupby(by='case:concept:name').agg({'time:timestamp': ['min', 'max']})
            mf = mf.reset_index()
            mf.columns = ['case', 'min', 'max']
            mf['diff'] = mf['max'] - mf['min']
            mf['diff_days'] = (mf['max'] - mf['min']).dt.days
            mf['diff_hours'] = mf['diff'] / np.timedelta64(1, 'h')
            mf['diff_minutes'] = mf['diff'] / np.timedelta64(1, 'm')
            mf['diff_seconds'] = mf['diff'] / np.timedelta64(1, 's')

            dicto = {
                '0 - 9 Days': len(mf[(mf['diff_days'] >= 0) & (mf['diff_days'] < 9)]),
                '9 - 18 Days': len(mf[(mf['diff_days'] >= 9) & (mf['diff_days'] < 18)]),
                '18 - 27 Days': len(mf[(mf['diff_days'] >= 18) & (mf['diff_days'] < 27)]),
                '27 - 36 Days': len(mf[(mf['diff_days'] >= 27) & (mf['diff_days'] < 36)]),
                '36 - 45 Days': len(mf[(mf['diff_days'] >= 36) & (mf['diff_days'] < 45)]),
                '45 - 54 Days': len(mf[(mf['diff_days'] >= 45) & (mf['diff_days'] < 54)]),
                '54 - 63 Days': len(mf[(mf['diff_days'] >= 54) & (mf['diff_days'] < 63)]),
                '63 - 72 Days': len(mf[(mf['diff_days'] >= 63) & (mf['diff_days'] < 72)]),
                '72 - 81 Days': len(mf[(mf['diff_days'] >= 72) & (mf['diff_days'] < 81)]),
                ' > 81 Days': len(mf[mf['diff_days'] > 81]),
            }

            pm4py.view_performance_spectrum(
                df,
                ['Ekip Lideri Onayı', 'İşi Planlama Sorumlusu'], format='svg')
            return dicto

    return {}

# b.index = df.to_datetime(b['date'],format='%m/%d/%y %I:%M%p')
# gr = df.groupby(by=[df.index.month, df.index.year]).agg({'Case ID': 'count'})
# gr.index.names = ['month', 'year']
# gr.reset_index()
# gr['rate'] = gr['Case ID'] / 30
