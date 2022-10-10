
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.orm import decl_api
import json
import datetime

def new_alchemy_encoder():
    _visited_objs = []

    class AlchemyEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj.__class__, DeclarativeMeta):
                # don't re-visit self
                if obj in _visited_objs:
                    return None
                _visited_objs.append(obj)

                # an SQLAlchemy class
                fields = {}
                for field in [x for x in dir(obj) if not x.startswith('_') and x != 'metadata']:
                    if type(obj.__getattribute__(field)) == decl_api.registry:
                        continue
                    if type(obj.__getattribute__(field)) == datetime.timedelta:
                        fields[field] = str(obj.__getattribute__(field))
                    elif type(obj.__getattribute__(field)) == datetime.datetime:
                        fields[field] = obj.__getattribute__(field).isoformat()
                    else:
                        fields[field] = obj.__getattribute__(field)
                # a json-encodable dict
                return fields

            return json.JSONEncoder.default(self, obj)

    return AlchemyEncoder

def orm_to_dict(obj):
    result = json.dumps(obj, cls=new_alchemy_encoder(), check_circular=False)

    return json.loads(result)