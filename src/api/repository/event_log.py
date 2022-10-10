from sqlalchemy.orm import Session
from api import models, schemas
from fastapi import HTTPException, status
from datetime import datetime
from typing import List


def create(id: str, log_name: str,
           case_id_column: str, activity_column: str, timestamp_key: str,
           start_timestamp_key: str, sep: str, db: Session):
    new_log = models.EventLog(id=id, log_name=log_name, case_id_column=case_id_column,
                              activity_column=activity_column, timestamp_key=timestamp_key,
                              start_timestamp_key=start_timestamp_key, sep=sep,
                              uploaded_date=datetime.now())
    db.add(new_log)
    db.commit()
    # db.refresh(new_log)
    return new_log


def get(log_id: str, db: Session) -> models.EventLog:
    log_info = db.query(models.EventLog).filter_by(id=log_id).first();
    return log_info


def get_all(db: Session) -> models.EventLog:
    logs = db.query(models.EventLog).all();
    db.close()
    return logs
