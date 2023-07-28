import os

from fastapi import APIRouter
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
from sqlalchemy import create_engine
from api.repository import project as project_repository
from session import get_session

import random

router = APIRouter(
    prefix="/v1",
    tags=['Import Event Data']
)

get_db = database.get_db


def save_log_org(project_id: str, org_name: str, source_df, case_column_name: str, activity_column_name: str,
                 timestamp_key: str,
                 start_timestamp_key: str,
                 sep: str, db):
    engine_event_log = database.get_organization_event_data_engine(org_name, project_id)

    log_id = save_log(project_id, engine_event_log, source_df, case_column_name, activity_column_name, timestamp_key,
                      start_timestamp_key, sep, db)

    return log_id


def save_log(project_id, engine, source_df, case_column_name: str, activity_column_name: str,
             timestamp_key: str,
             start_timestamp_key: str,
             sep: str, db):
    log_id = str(uuid4())

    event_log.create(log_id, 'Test.csv', case_column_name, activity_column_name, timestamp_key,
                     start_timestamp_key, sep, db)

    source_df.to_sql(
        project_id,
        engine,
        if_exists='replace',
        index=False,
        chunksize=500,
        dtype={
            "case:concept:name": String(),
            "concept:name": String()
        }
    )
    return log_id


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
    # format = ''%d.%m.%y %H:%M'
    format = '%Y-%m-%dT%H:%M:%S.%fZ'
    source_df = format_dataframe(source_df, case_id=case_id, activity_key=activity_key,
                                 timestamp_key=timestamp_key, start_timestamp_key=start_timestamp_key,
                                 timest_format=format)

    source_df = dataframe_utils.convert_timestamp_columns_in_df(source_df, timest_format=format)

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


@router.post("/ImportCsvFile")
async def load_csv(
        session=Depends(get_session),
        project_id: str = Form(...),
        case_column_name: str = Form(...),
        activity_column_name: str = Form(...),
        timestamp_key: str = Form(...),
        start_timestamp_key: str = Form(...),
        cost_key: Optional[str] = Form(None),
        resource_key: Optional[str] = Form(None),
        sep: str = Form(...),
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        # session_data: SessionData = Depends(verifier)
        db_event_info: Session = Depends(database.get_org_event_db)):
    try:
        _csv = await file.read()  # async read
        stream = StringIO(_csv.decode("utf-8"))

        log_csv = pd.read_csv(stream, sep=sep)

        #if (len(log_csv) > random.randint(15000, 20500) and os.getenv('ENV') != 'dev'):
        #    raise Exception("Insufficient memory")

        log_csv = prepare_dataset(log_csv, case_column_name, activity_column_name, timestamp_key,
                                  start_timestamp_key, cost_key, resource_key)

        log_id = save_log_org(project_id, session.tenant_id, log_csv, case_column_name, activity_column_name,
                              timestamp_key,
                              start_timestamp_key, sep, db_event_info)
        # # update project data
        # project = project_repository.get(session.realm_id, session.tenant_id, project_id, db_event_info)
        # if project is None:
        #     raise Exception("Project Not Found")
        #
        # project.is_data_loaded = True;
        db_event_info.commit()

        return {
            'log_id': log_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))