from sqlalchemy.orm import Session
from api import models, schemas
from fastapi import HTTPException, status
import json
from typing import List, Dict


def create(realm_id: str, tenant_id: str, project_id: str, project_name: str, admin: str, is_public: bool,
           disable_cache: bool,
           project_info: dict, case_count: int, event_count: int,
           db: Session):
    new_project = models.Project(realm_id=realm_id, tenant_id=tenant_id, project_id=project_id,
                                 project_name=project_name, admin=admin,
                                 is_public=is_public,
                                 is_data_loaded=False,
                                 disable_cache=disable_cache, project_info=json.dumps(project_info),
                                 case_count=case_count, event_count=event_count)
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project


def get(realm_id: str, tenant_id: str, project_id: str, db: Session) -> models.Project:
    log_info = db.query(models.Project).filter_by(realm_id=realm_id, tenant_id=tenant_id,
                                                  project_id=project_id).first();
    return log_info


def is_data_loaded(realm_id: str, tenant_id: str, project_id: str, db: Session) -> bool:
    log_info = db.query(models.Project).filter_by(realm_id=realm_id, tenant_id=tenant_id,
                                                  project_id=project_id).first();
    return log_info.is_data_loaded


def get_all_projects(realm_id: str, tenant_id: str, db: Session) -> List[models.Project]:
    projects = db.query(models.Project).filter_by(realm_id=realm_id, tenant_id=tenant_id)
    return projects


def create_project_item(realm_id: str, tenant_id: str, project_id: str, model_id: str, item_id: str, item_info: dict,
                        db: Session):
    new_project_item = models.ProjectItems(realm_id=realm_id, tenant_id=tenant_id, project_id=project_id,
                                           model_id=model_id,
                                           item_id=item_id, item_info=json.dumps(item_info))
    db.add(new_project_item)
    db.commit()
    db.refresh(new_project_item)
    return new_project_item.item_id


def get_all_project_items(realm_id: str, tenant_id: str, project_id: str, model_id: str, db: Session) -> List[
    models.ProjectItems]:
    project_items = db.query(models.ProjectItems).filter_by(realm_id=realm_id, tenant_id=tenant_id,
                                                            project_id=project_id,
                                                            model_id=model_id)
    return project_items


def get_project_info(realm_id: str, tenant_id: str, project_id: str, db: Session) -> models.Project:
    project = db.query(models.Project).filter_by(realm_id=realm_id, tenant_id=tenant_id, project_id=project_id).first();
    if project is not None:
        project_info_str = project.project_info
        if project_info_str is not None and project_info_str != '':
            project_info = json.loads(project_info_str)
            return project_info

    return None


def update_project_info(realm_id: str, tenant_id: str, project_id: str, project_info: Dict, db: Session) -> bool:
    project = db.query(models.Project).filter_by(realm_id=realm_id, tenant_id=tenant_id, project_id=project_id).first();
    if project is not None:
        project.project_info = json.dumps(project_info)
        db.commit()
        return True

    return False
