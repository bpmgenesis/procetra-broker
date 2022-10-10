
from api.dpf.Activity import Activity
import pandas as pd
from api import database, schemas

get_db = database.get_db
engine = database.engine

class LoadEventData(Activity):

    async def execute(self, flow_variables):
        table_df = pd.read_sql_table(
            flow_variables["log_id"],
            con=engine
        )
        flow_variables["current_event_data"] = table_df

    @staticmethod
    def deserialize(activity_schema: schemas.ActivitySchema):
        return LoadEventData()
