from api.dpf.Activity import Activity
from api import database, schemas

class ChangeCaseActivity(Activity):
    __datasource_name: str = '';
    __source_column_name = ""
    __target_column_name = ""
    __upper_case = False

    def __init__(self, datasource_name:str, source_column_name: str, target_column_name: str, upper_case: bool):
        self.__datasource_name = datasource_name
        self.__source_column_name = source_column_name
        self.__target_column_name = target_column_name
        self.__upper_case = upper_case

    async def execute(self, flow_variables):
        df = flow_variables[self.__datasource_name]

        if self.__upper_case:
            df[self.__target_column_name] = df[self.__source_column_name].astype(str).str.upper()
        else:
            df[self.__target_column_name] = df[self.__source_column_name].astype(str).str.lower()

        flow_variables['current_event_data'] = flow_variables[self.__datasource_name] = df

    @staticmethod
    def deserialize(activity_schema: schemas.ActivitySchema):
        if 'datasource_name' not in activity_schema.variables:
            return None
        if activity_schema.variables['source_column_name'] is None:
            return None
        if activity_schema.variables['target_column_name'] is None:
            return None
        if activity_schema.variables['upper_case'] is None:
            return None
        aa = ChangeCaseActivity(str(activity_schema.variables['datasource_name']),
                                    str(activity_schema.variables['source_column_name']),
                                  str(activity_schema.variables['target_column_name']),
                                  bool(activity_schema.variables['upper_case']))
        return aa