
from api.dpf.Activity import Activity
from api import database, schemas

class SelectLog(Activity):
    log_id ="";

    def __init__(self, log_id):
        self.log_id = log_id;

    async def execute(self, flow_variables):
        flow_variables["log_id"] = self.log_id;

    @staticmethod
    def deserialize(activity_schema: schemas.ActivitySchema):
        if activity_schema.variables['log_id'] is None:
            return None
        return SelectLog(str(activity_schema.variables['log_id']))
