
from api.dpf.Activity import Activity
from api import database, schemas

class EndActivity(Activity):

    async def execute(self, flow_variables):
        flow_variables["result"] = flow_variables["current_event_data"]
        for k in list(flow_variables.keys()):
            if k != 'result':
                del flow_variables[k]

    @staticmethod
    def deserialize(activity_schema: schemas.ActivitySchema):
        return EndActivity()