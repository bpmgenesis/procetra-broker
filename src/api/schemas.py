from typing import List, Optional, Dict
from pydantic import BaseModel
from pm4py.util import constants, xes_constants

class ActivitySchema(BaseModel):
    name: str = ""
    variables = {}

class FlowSchema(BaseModel):
    activities:List[ActivitySchema]

class IProject(BaseModel):
    id: int;
    name: str;

    class Config():
        orm_mode = True


class IProjectCreate(BaseModel):
    name: str;


class User(BaseModel):
    organization_id: int
    name: str
    email: str
    password: str


class SessionData(BaseModel):
    username: str
    Logs: Optional[Dict] = {}
    TransactionDataFlames: Optional[Dict] = {}
    TransactionLogs: Optional[Dict] = {}


class CreateDatasetRequest(BaseModel):
    project_id: int
    dataset_name: str


class CreateDatasetResponse(BaseModel):
    project_id: int
    dataset_id: str
    message: str

class GetDatasetsResponse(BaseModel):
    project_id: int
    dataset_id: str
    message: str


class LoadCsvRequest(BaseModel):
    case_id: str = constants.CASE_CONCEPT_NAME;
    activity_key: str = xes_constants.DEFAULT_NAME_KEY;
    timestamp_key: str = xes_constants.DEFAULT_TIMESTAMP_KEY;
    start_timestamp_key: str = xes_constants.DEFAULT_START_TIMESTAMP_KEY;
