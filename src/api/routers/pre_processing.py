from fastapi import APIRouter
from api import database, schemas, schemas
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, status, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse
import html
from fastapi.encoders import jsonable_encoder
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
from api.repository import event_log
import os
import pm4py
from pm4py.objects.log.importer.xes import importer as xes_importer

import sys
from io import StringIO
from api.dpf import DPFContext, SelectLog, LoadEventData, EndActivity, ChangeCaseActivity
import json
import base64

def stringToBase64(s):
   return base64.b64encode(s.encode('utf-8'))

def base64ToString(b):
    return base64.b64decode(b).decode('utf-8')

router = APIRouter(
    prefix="/preprocessing",
    tags=['Event Data Preprocessing']
)

get_db = database.get_db
engine = database.engine


async def get_df_session_or_database(log_id: str, session_id: UUID):
    session_data = await backend.read(session_id)
    table_df = None
    if log_id in session_data.Logs:
        print('found in session')
        table_df = session_data.Logs[log_id]
    else:
        print('found in db')
        table_df = pd.read_sql_table(
            log_id,
            con=engine
        )
        session_data.Logs[log_id] = table_df;
        await backend.update(session_id, session_data)

    return table_df


@router.post('/Start/{session_id}')
async def start(session_id: str, log_id: str = Form(...), db: Session = Depends(get_db)):
    session_data = await backend.read(UUID(session_id))
    transection_id = str(uuid4())

    df = await get_df_session_or_database(log_id, UUID(session_id))
    if df is None:
        raise HTTPException(status_code=404, detail="Event data not found")

    session_data.TransactionDataFlames[transection_id] = df;
    session_data.TransactionLogs[transection_id] = log_id;

    await backend.update(UUID(session_id), session_data)
    return transection_id


@router.post('/DateDiff/{session_id}/{transaction_id}')
async def datediff(session_id: str, transaction_id: str, date1_column: str = Form(...), date2_column: str = Form(...),
                   new_column: str = Form(...),
                   db: Session = Depends(get_db)):
    session_data = await backend.read(UUID(session_id))
    if transaction_id not in session_data.TransactionDataFlames:
        raise HTTPException(status_code=404, detail="Item not found")

    df = session_data.TransactionDataFlames[transaction_id]

    df[new_column] = df[date2_column] - df[date1_column]

    session_data.TransactionDataFlames[transaction_id] = df;

    await backend.update(UUID(session_id), session_data)
    return transaction_id


@router.post('/ChangeCase/{session_id}/{transaction_id}')
async def chamge_case(session_id: str, transaction_id: str, column_name: str = Form(...),
                      target_column_name: str = Form(...), upper_case: bool = Form(...),
                      db: Session = Depends(get_db)):
    session_data = await backend.read(UUID(session_id))
    if transaction_id not in session_data.TransactionDataFlames:
        raise HTTPException(status_code=404, detail="Item not found")

    df = session_data.TransactionDataFlames[transaction_id]

    if upper_case:
        df[target_column_name] = df[column_name].str.upper()
    else:
        df[target_column_name] = df[column_name].str.lower()

    session_data.TransactionDataFlames[transaction_id] = df;

    await backend.update(UUID(session_id), session_data)
    return transaction_id


@router.post('/End/{session_id}/{transaction_id}')
async def end(session_id: str, transaction_id: str,
              db: Session = Depends(get_db)):
    session_data = await backend.read(UUID(session_id))
    if transaction_id not in session_data.TransactionDataFlames:
        raise HTTPException(status_code=404, detail="Item not found")

    df = session_data.TransactionDataFlames[transaction_id]

    df.to_sql(
        session_data.TransactionLogs[transaction_id],
        engine,
        if_exists='replace',
        index=False,
        chunksize=500,
        dtype={
            "case:concept:name": String(),
            "concept:name": String()
        }
    )

    del session_data.TransactionDataFlames[transaction_id]
    del session_data.TransactionLogs[transaction_id]

    return df.to_json(orient='records', force_ascii=False)


@router.post('/Execute')
async def execute(flow_schema: schemas.FlowSchema, db: Session = Depends(get_db)):
    flow_context = DPFContext.deserialize(flow_schema)

    # select_log = SelectLog('0cf145f9-bbe0-4643-97d4-5932b2b2ae05')
    # flow_context.activities.append(select_log)
    # flow_context.activities.append(LoadEventData())
    # flow_context.activities.append(EndActivity())
    result = await flow_context.execute()
    if isinstance(result, pd.DataFrame):
        cols_types = dict(result.dtypes)
        for col_name in cols_types:
            cols_types[col_name] = cols_types[col_name].name

        df = {
                'columns': cols_types,
                'data': stringToBase64(result.to_json(orient='records', force_ascii=False))
               }
    else:
        return '{ "result":"John", "age":30, "city":"New York"}'

    return df

@router.post('/ExecuteCsv')
async def execute(flow_schema: schemas.FlowSchema, db: Session = Depends(get_db)):
    flow_context = DPFContext.deserialize(flow_schema)

    # select_log = SelectLog('0cf145f9-bbe0-4643-97d4-5932b2b2ae05')
    # flow_context.activities.append(select_log)
    # flow_context.activities.append(LoadEventData())
    # flow_context.activities.append(EndActivity())
    result = await flow_context.execute()
    if isinstance(result, pd.DataFrame):
        cols_types = dict(result.dtypes)
        for col_name in cols_types:
            cols_types[col_name] = cols_types[col_name].name

        df = {
                'columns': cols_types,
                'data': stringToBase64(result.to_csv(index=False))
               }
    else:
        return '{ "result":"John", "age":30, "city":"New York"}'

    return df
