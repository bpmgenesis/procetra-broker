from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text, Numeric
from api.database import Base, OrgDbBase
from sqlalchemy.orm import relationship
import datetime


class AnalyseModel(OrgDbBase):
    __tablename__ = 'analyse_models'
    realm_id = Column(String(length=100), index=True)
    tenant_id = Column(String(length=100), index=True)
    project_id = Column(String(length=100), index=True)
    id = Column(String(length=100), primary_key=True, index=True)
    name = Column(String(length=100))


class MappingModel(OrgDbBase):
    __tablename__ = 'mappings'
    realm_id = Column(String(length=100),  index=True)
    tenant_id = Column(String(length=100),  index=True)
    project_id = Column(String(length=100),  index=True)
    mapping_id = Column(String(length=100), primary_key=True, index=True)
    mapping_name = Column(String(length=100))
    mapping_file_name = Column(String(length=100))
    mapping_data = Column(Text())


class Project(OrgDbBase):
    __tablename__ = 'projects'

    realm_id = Column(String(length=100),  index=True)
    tenant_id = Column(String(length=100),  index=True)
    project_id = Column(String(length=100), primary_key=True, index=True)
    project_name = Column(String(length=100))
    admin = Column(String(length=100))
    is_public = Column(Boolean())
    is_data_loaded = Column(Boolean())
    disable_cache = Column(Boolean())
    project_info = Column(Text())
    case_count =Column(Numeric())
    event_count = Column(Numeric())


class ProjectItems(OrgDbBase):
    __tablename__ = 'project_items'

    realm_id = Column(String(length=100),  index=True)
    tenant_id = Column(String(length=100),  index=True)
    project_id = Column(String(length=100),  index=True)
    model_id = Column(String(length=100),  index=True)
    item_id = Column(String(length=100), primary_key=True, index=True)
    item_info = Column(String(length=100))


class Dataset(Base):
    __tablename__ = 'datasets'

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, index=True)
    name = Column(String(length=250))


class EventLog(OrgDbBase):
    __tablename__ = 'event_data'

    id = Column(String(length=100), primary_key=True, index=True)
    log_name = Column(String(length=250))
    case_id_column = Column(String(length=250))
    activity_column = Column(String(length=250))
    timestamp_key = Column(String(length=250))
    start_timestamp_key = Column(String(length=250))
    sep = Column(String(length=250))
    uploaded_date = Column(DateTime)


class User(Base):
    __tablename__ = 'USERS'

    user_id = Column(String(length=100), primary_key=True, index=True)
    password = Column(String(length=250))

class ServisRegistration(OrgDbBase):
    __tablename__ = 'service_registration'

    service_name = Column(String(length=100), primary_key=True, index=True)
    realm_name = Column(String(length=100), primary_key=True, index=True)
    realm_url = Column(String(length=255))
    token = Column(String(length=255))

class Log(OrgDbBase):
    __tablename__ = "log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(DateTime, nullable=False, default=datetime.datetime.now)
    level_name = Column(String(10), nullable=True)
    module = Column(String(200), nullable=True)
    thread_name = Column(String(200), nullable=True)
    file_name = Column(String(200), nullable=True)
    func_name = Column(String(200), nullable=True)
    line_no = Column(Integer, nullable=True)
    process_name = Column(String(200), nullable=True)
    message = Column(Text)
    last_line = Column(Text)

from api.database import procetra_mysql_engine
OrgDbBase.metadata.create_all(procetra_mysql_engine)