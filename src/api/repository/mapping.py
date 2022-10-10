from api import models, schemas
from sqlalchemy.orm import Session
from typing import List, Dict


def create(realm_id: str, tenant_id: str, project_id: str, id: str, name: str, file_name: str, mapping_data: str,
           db: Session):
    new_mapping_model = models.MappingModel(realm_id=realm_id, tenant_id=tenant_id, project_id=project_id,
                                            mapping_id=id, mapping_name=name,
                                            mapping_file_name=file_name, mapping_data=mapping_data)
    db.add(new_mapping_model)
    db.commit()
    db.refresh(new_mapping_model)
    return new_mapping_model.mapping_id


def get_mapping_models(tenant_id: str, project_id: str, db: Session) -> List[models.MappingModel]:
    mapping_models = db.query(models.MappingModel).filter_by(tenant_id=tenant_id, project_id=project_id)
    return mapping_models
