from sqlalchemy import create_engine, MetaData, Table, Column, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fastapi import Form, Request
from pathlib import Path
import os
from pymongo import MongoClient

SQLALCHAMY_DATABASE_URL = 'sqlite:///./db/procetra.db'
SQLALCHAMY_EVENT_LOG_DATABASE_URL = 'sqlite:///./files/databases/organizations/{org_name}/event_data/{log_id}.db'

ORG_DATABASE_URL_TEMPLATE = 'sqlite:///./files/databases/organizations/{org_name}/event_data/{log_id}.db'
# ORG_EVENT_INFO_DATABASE_URL_TEMPLATE = 'sqlite:///./files/databases/organizations/{org_name}/info.db'
ORG_EVENT_INFO_DATABASE_URL_TEMPLATE = 'mysql+pymysql://doadmin:AVNS_O6rF3QIeuE3liLH0k9B@bpmgenesis-db-do-user-605598-0.b.db.ondigitalocean.com:25060/procetra'

engine = create_engine(SQLALCHAMY_DATABASE_URL, pool_recycle=3600)
engine_log = create_engine(SQLALCHAMY_EVENT_LOG_DATABASE_URL, pool_recycle=3600)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, )

Base = declarative_base()
OrgDbBase = declarative_base()


def get_mongo_db(request: Request):
    client = MongoClient(
        'mongodb+srv://doadmin:053j72a8NtCcb1e4@db-mongo-9740cdb5.mongo.ondigitalocean.com/admin?tlsInsecure=true&authSource=admin&replicaSet=db-mongo')
    try:
        yield client['procetra']
    finally:
        client.close()
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

procetra_mysql_engine = create_engine(ORG_EVENT_INFO_DATABASE_URL_TEMPLATE, pool_recycle=3600)
procetra_mysql_session = sessionmaker(bind=procetra_mysql_engine, autocommit=False, autoflush=False)

def get_org_event_db(org_name: str = Form('bpmgenesis')):
    # meta2 = MetaData(bind=engine)
    # table = Table('event_data', meta2, autoload=True, autoload_with=engine)
    # table.append_column(Column('nickname', String(50), nullable=False))
    # meta2.create_all(engine)
    # session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = procetra_mysql_session()
    try:
        yield db
    finally:
        db.close()


def get_organization_event_data_engine(org_name: str, project_id: str):
    is_exist =  os.path.isdir("./files/databases/organizations/{org_name}/event_data".replace("{org_name}", org_name))
    if not is_exist:
        Path("./files/databases/organizations/{org_name}/event_data".replace("{org_name}", org_name)).mkdir(parents=True, exist_ok=True)
    engine = create_engine(ORG_DATABASE_URL_TEMPLATE.replace('{org_name}', org_name).replace('{log_id}', project_id),
                           pool_recycle=3600)
    return engine
