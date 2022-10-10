from typing import List
from api.dpf.Activity import Activity
from api import database, schemas
from api.dpf.SelectLog import  SelectLog
from api.dpf.LoadEventData import LoadEventData
from api.dpf.EndActivity import EndActivity
from api.dpf.ChangeCaseActivity import ChangeCaseActivity
from api.dpf.JoinColumnsActivity import JoinColumnsActivity
from api.dpf.ActivityTypes import ActivityTypes
from api.dpf.Start import Start
from api.dpf.ImportCsv import ImportCsv
from api.dpf.MergeDataset import MergeDatasetActivity


class DPFContext:
    flow_variables = {};
    activities: List[Activity] = [];
    async def execute(self):
        for activity in self.activities:
            if activity is not None:
                await activity.execute(self.flow_variables);

        result = self.flow_variables['result']
        del self.flow_variables['result']

        return result

    @staticmethod
    def deserialize(flow_schema: schemas.FlowSchema):
        flow_context = DPFContext()
        for activity in flow_schema.activities:
            if ActivityTypes[activity.name] == ActivityTypes.Start:
                new_act = Start.deserialize(activity)
                flow_context.activities.append(new_act)
            elif ActivityTypes[activity.name] == ActivityTypes.ImportCsv:
                new_act = ImportCsv.deserialize(activity)
                flow_context.activities.append(new_act)
            elif activity.name == 'SelectLog':
                new_act = SelectLog.deserialize(activity)
                flow_context.activities.append(new_act)
            elif activity.name == 'LoadEventData':
                new_act = LoadEventData.deserialize(activity)
                flow_context.activities.append(new_act)
            elif ActivityTypes[activity.name] == ActivityTypes.ChangeCase:
                new_act = ChangeCaseActivity.deserialize(activity)
                flow_context.activities.append(new_act)
            elif ActivityTypes[activity.name] == ActivityTypes.JoinColumns:
                new_act = JoinColumnsActivity.deserialize(activity)
                flow_context.activities.append(new_act)
            elif ActivityTypes[activity.name] == ActivityTypes.End:
                new_act = EndActivity.deserialize(activity)
                flow_context.activities.append(new_act)
            elif ActivityTypes[activity.name] == ActivityTypes.MergeDataset:
                new_act = MergeDatasetActivity.deserialize(activity)
                flow_context.activities.append(new_act)

        return flow_context
