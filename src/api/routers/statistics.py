from fastapi import APIRouter
from api import database, schemas, schemas
from api.repository import event_log as eventlog_repository
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, status, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse
import html
from fastapi.encoders import jsonable_encoder
from api.repository import project
from api import oauth2
from typing import List
from uuid import UUID, uuid4
import numpy as np

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

router = APIRouter(
    prefix="/v1",
    tags=['Event Data Statistics']
)

get_db = database.get_db
engine_event_log = database.engine_log


# 02d1d63f-bd4e-4564-be5b-2121b1846d98
@router.post('/GetStatistics')
async def get_statistics(log_id: str = Form(...), activity_name: str = Form(...), db: Session = Depends(get_db)):
    df = pd.read_sql_table(log_id, con=engine_event_log)
    mf = df.groupby(activity_name).agg({activity_name: "count"})
    mf.columns = ["count"]
    mf["rate"] = mf["count"].apply(lambda x: 100 * x / float(mf["count"].sum()))
    mf["max_rate"] = mf["rate"].max()

    mf['item_name'] = mf.index
    cols = mf.columns.tolist()
    cols = cols[-1:] + cols[:-1]
    mf = mf[cols]
    mf = mf.sort_values(by=["count"], ascending=False)
    case_info = mf.to_dict(orient="records")

    db.close()
    return case_info


@router.post('/GetActivityStatistics')
async def get_activity_statistics(log_id: str = Form(...), db: Session = Depends(get_db)):
    mf = df = pd.read_sql_table(log_id, con=engine_event_log)

    if 'start_timestamp' in df.columns:
        df["time:timestamp"] = pd.to_datetime(df["time:timestamp"])
        df["start_timestamp"] = pd.to_datetime(df["start_timestamp"])

        df["diff"] = df["time:timestamp"] - df["start_timestamp"]
        # mf = df.groupby('concept:name').agg({"concept:name": "count"})
        # mf["rate"] = mf["count"].apply(lambda x: 100 * x / float(mf["count"].sum()))
        if 'concept:cost' in df.columns:
            mf = df.groupby('concept:name').agg(
                {"concept:name": "count", "diff": ["mean", "median", "max", "min"], 'concept:cost': ['sum']})
            mf.columns = ["count", "mean", "median", "max", "min", 'cost']
        else:
            mf = df.groupby('concept:name').agg({"concept:name": "count", "diff": ["mean", "median", "max", "min"]})
            mf.columns = ["count", "mean", "median", "max", "min"]
        mf['duration_range'] = mf['max'] - mf['min']
    else:
        if 'concept:cost' in df.columns:
            mf = df.groupby('concept:name').agg({"concept:name": "count", 'concept:cost': ['sum']})
            mf.columns = ["count", 'cost']
        else:
            mf = df.groupby('concept:name').agg({"concept:name": "count"})
            mf.columns = ["count"]

    mf["rate"] = mf["count"].apply(lambda x: 100 * x / float(mf["count"].sum()))

    if 'concept:cost' in df.columns:
        mf["cost_rate"] = mf["cost"].apply(lambda x: 100 * x / float(mf["cost"].sum()))

    mf["min_freq"] = mf["count"].min()
    mf["mean_freq"] = mf["count"].mean()
    mf["max_freq"] = mf["count"].max()
    mf["max_rate"] = mf["rate"].max()

    # mf['median'] = mf['median'] * 1000  # convert to miliseconds

    mf = mf.sort_values(by=["count"], ascending=False)
    mf['concept:name'] = mf.index
    cols = mf.columns.tolist()
    cols = cols[-1:] + cols[:-1]
    mf = mf[cols]

    case_info = mf.to_dict(orient="records")

    db.close()
    return case_info


@router.post('/GetEventsOverTime')
async def get_events_overtime(log_id: str = Form(...), db: Session = Depends(get_db)):
    df = pd.read_sql_table(log_id, con=engine_event_log)
    df['start_timestamp'] = df['start_timestamp'].dt.floor('s')
    df['time:timestamp'] = df['time:timestamp'].dt.floor('s')

    delta = df['time:timestamp'].max() - df['start_timestamp'].min()
    step = delta.total_seconds() / 60
    minuteStep = int(step / 622)
    np.random.seed(0)
    rng = pd.date_range(df['start_timestamp'].min(), df['time:timestamp'].max(), freq=str(minuteStep) + "min")
    df_dates = pd.DataFrame({'Val': np.random.randn(len(rng))}, index=rng)
    df_dates['Val'] = 0
    df_dates['dates'] = df_dates.index

    result = df_dates.apply(
        lambda row: df[(df['start_timestamp'] <= row['dates']) & (df['time:timestamp'] >= row['dates'])][
            '@@index'].count(), axis=1)
    result.index = result.index.astype(np.int64)
    case_info = result.to_dict()

    db.close()
    return case_info


@router.post('/GetResourceOverview')
async def get_resource_overview(log_id: str = Form(...), db: Session = Depends(get_db)):
    mf = df = pd.read_sql_table(log_id, con=engine_event_log)

    if 'start_timestamp' in df.columns:
        df["time:timestamp"] = pd.to_datetime(df["time:timestamp"])
        df["start_timestamp"] = pd.to_datetime(df["start_timestamp"])

        df["diff"] = df["time:timestamp"] - df["start_timestamp"]
        # mf = df.groupby('concept:name').agg({"concept:name": "count"})
        # mf["rate"] = mf["count"].apply(lambda x: 100 * x / float(mf["count"].sum()))
        if 'concept:cost' in df.columns:
            mf = df.groupby('org:resource').agg(
                {"org:resource": "count", "diff": ["mean", "median", "max", "min"], 'concept:cost': ['sum']})
            mf.columns = ["count", "mean", "median", "max", "min", 'cost']
        else:
            mf = df.groupby('org:resource').agg({"org:resource": "count", "diff": ["mean", "median", "max", "min"]})
            mf.columns = ["count", "mean", "median", "max", "min"]
        mf['duration_range'] = mf['max'] - mf['min']
    else:
        if 'concept:cost' in df.columns:
            mf = df.groupby('org:resource').agg({"org:resource": "count", 'concept:cost': ['sum']})
            mf.columns = ["count", 'cost']
        else:
            mf = df.groupby('org:resource').agg({"org:resource": "count"})
            mf.columns = ["count"]

    mf["rate"] = mf["count"].apply(lambda x: 100 * x / float(mf["count"].sum()))

    if 'concept:cost' in df.columns:
        mf["cost_rate"] = mf["cost"].apply(lambda x: 100 * x / float(mf["cost"].sum()))

    mf["min_freq"] = mf["count"].min()
    mf["mean_freq"] = mf["count"].mean()
    mf["max_freq"] = mf["count"].max()

    # mf['median'] = mf['median'] * 1000  # convert to miliseconds

    mf = mf.sort_values(by=["count"], ascending=False)
    mf['org:resource'] = mf.index
    cols = mf.columns.tolist()
    cols = cols[-1:] + cols[:-1]
    mf = mf[cols]

    case_info = mf.to_dict(orient="records")

    db.close()
    return case_info
