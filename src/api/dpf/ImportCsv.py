import pandas as pd
from api.dpf.Activity import Activity
from api import database, schemas
import base64
from io import StringIO

def stringToBase64(s):
    return base64.b64encode(s.encode('utf-8'))

def base64ToString(b):
    return base64.b64decode(b).decode('utf-8')

class ImportCsv(Activity):
    __name: str = ''
    __csv_string ="";
    __sep = ","

    def __init__(self, name:str, base64_csv_string, sep):
        self.__name = name;
        self.__csv_string = base64ToString(base64_csv_string);
        self.__sep = sep

    async def execute(self, flow_variables):
        csv_stream = StringIO(self.__csv_string)
        df = pd.read_csv(csv_stream, self.__sep)
        flow_variables['result'] = flow_variables[self.__name] = df
        print('CSV import executed.')

    @staticmethod
    def deserialize(activity_schema: schemas.ActivitySchema):
        if 'name' not in activity_schema.variables:
            return None
        if 'base64_csv_string' not in activity_schema.variables:
            return None
        if 'sep' not in activity_schema.variables:
            return None
        return ImportCsv(str(activity_schema.variables['name']),
                         str(activity_schema.variables['base64_csv_string']),
                         str(activity_schema.variables['sep']))
