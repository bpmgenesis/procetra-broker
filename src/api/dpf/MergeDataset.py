from api.dpf.Activity import Activity
from api import database, schemas
from .ChangeCaseActivity import ChangeCaseActivity


class MergeDatasetActivity(Activity):
    __datasource_one_name: str
    __left_column_name = ""
    __datasource_two_name = ""
    __right_column_name = ""

    def __init__(self, datasource_one_name: str, left_column_name: str, datasource_two_name: str, right_column_name: str):
        self.__datasource_one_name = datasource_one_name
        self.__left_column_name = left_column_name
        self.__datasource_two_name = datasource_two_name
        self.__right_column_name = right_column_name

    async def execute(self, flow_variables):
        df_one = flow_variables[self.__datasource_one_name]
        df_two = flow_variables[self.__datasource_two_name]

        # col_list = df_two.columns.to_list()
        # del col_list[col_list.index(self.__right_column_name)]
        df_result = flow_variables[self.__datasource_one_name]  = df_one.merge(df_two, left_on= self.__left_column_name, right_on=self.__right_column_name, how='left')

        flow_variables["current_event_data"] = flow_variables[self.__datasource_one_name] ;

    @staticmethod
    def deserialize(activity_schema: schemas.ActivitySchema):
        if 'datasource_one_name' not in activity_schema.variables:
            return None
        if 'left_column_name' not in activity_schema.variables:
            return None
        if 'datasource_two_name' not in activity_schema.variables:
            return None
        if 'right_column_name' not in activity_schema.variables:
            return None

        aa = MergeDatasetActivity(str(activity_schema.variables['datasource_one_name']),
                                 str(activity_schema.variables['left_column_name']),
                                 str(activity_schema.variables['datasource_two_name']),
                                 str(activity_schema.variables['right_column_name']))

        return aa
