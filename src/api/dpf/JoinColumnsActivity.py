from api.dpf.Activity import Activity
from api import database, schemas
from .ChangeCaseActivity import ChangeCaseActivity

import re


class JoinColumnsActivity(Activity):
    __datasource_name: str
    __column_one_name = ""
    __column_two_name = ""
    __target_column_name = ""
    __sep = ""

    def __init__(self, datasource_name: str, column_one_name: str, column_two_name: str, target_column_name: str,
                 sep: str = ""):
        self.__datasource_name = datasource_name
        self.__column_one_name = column_one_name.replace("\ufeff", "")
        self.__column_two_name = column_two_name
        self.__target_column_name = target_column_name
        self.__sep = sep

    async def execute(self, flow_variables):
        df = flow_variables[self.__datasource_name]
        regex = r"\{(.*?)\}"
        if re.match(regex, self.__sep):
            df[self.__target_column_name] = df.apply(
                lambda x: self.__sep.format(col1=str(x[self.__column_one_name]), col2=str(x[self.__column_two_name])),
                axis=1)
        else:
            df[self.__target_column_name] = df[self.__column_one_name].apply(str) + self.__sep + df[
                self.__column_two_name].apply(str)

        flow_variables["current_event_data"] = flow_variables[self.__datasource_name] = df
        print('Join Executed')

    @staticmethod
    def deserialize(activity_schema: schemas.ActivitySchema):
        if 'datasource_name' not in activity_schema.variables:
            return None
        if activity_schema.variables['column_one_name'] is None:
            return None
        if activity_schema.variables['column_two_name'] is None:
            return None
        if activity_schema.variables['target_column_name'] is None:
            return None
        if 'sep' not in activity_schema.variables:
            activity_schema.variables['sep'] = ""

        aa = JoinColumnsActivity(str(activity_schema.variables['datasource_name']),
                                 str(activity_schema.variables['column_one_name']),
                                 str(activity_schema.variables['column_two_name']),
                                 str(activity_schema.variables['target_column_name']),
                                 str(activity_schema.variables['sep']))

        return aa
