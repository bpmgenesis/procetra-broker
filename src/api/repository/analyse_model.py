from api import models, schemas
from sqlalchemy.orm import Session
from typing import List


def create(realm_id: str, tenant_id: str, project_id: str, id: str, name: str, db: Session):
    new_analyse_model = models.AnalyseModel(realm_id=realm_id, tenant_id=tenant_id, project_id=project_id, id=id,
                                            name=name)
    db.add(new_analyse_model)
    db.commit()
    db.refresh(new_analyse_model)
    return new_analyse_model.id


def get_analyse_model_by_id(realm_id: str, tenant_id: str, project_id: str, id: str,
                            db: Session) -> models.AnalyseModel:
    analys_model = db.query(models.AnalyseModel).filter_by(realm_id=realm_id, tenant_id=tenant_id,
                                                           project_id=project_id, id=id).first()
    return analys_model


def get_analyse_models(realm_id: str, tenant_id: str, project_id: str, db: Session) -> List[models.AnalyseModel]:
    analys_models = db.query(models.AnalyseModel).filter_by(realm_id=realm_id, tenant_id=tenant_id,
                                                            project_id=project_id)
    return analys_models


def delete_analyse_model_by_id(realm_id: str, tenant_id: str, project_id: str, id: str,
                               db: Session) -> bool:
    analys_model_filter = db.query(models.AnalyseModel).filter_by(realm_id=realm_id, tenant_id=tenant_id,
                                                           project_id=project_id, id=id)
    if analys_model_filter is not None:
        analys_model_filter.delete()
        db.commit()
        return True
    else:
        return False
