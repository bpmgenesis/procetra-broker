
from api.dpf.Activity import Activity
from api import database, schemas

class Start(Activity):
    async def execute(self, flow_variables):
        pass
       # flow_variables['result'] = {}

    @staticmethod
    def deserialize(activity_schema: schemas.ActivitySchema):
        return Start()
