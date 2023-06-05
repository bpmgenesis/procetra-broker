import pandas as pd
import pm4py
from pandas import DataFrame
from typing import Tuple, Union, List, Dict, Any, Optional


class Discovery:

    @staticmethod
    def performance_dfg(log: DataFrame,
                        activity_key: str = 'concept:name',
                        timestamp_key: str = 'time:timestamp',
                        case_id_key: str = 'case:concept:name') :

        dfg, start_activities, end_activities = pm4py.discover_dfg(log, case_id_key='case:concept:name',
                                                                   activity_key='concept:name',
                                                                   timestamp_key='time:timestamp')
        # pm4py.view_dfg(dfg, start_activities, end_activities, format='svg')

        format = 'svg'
        from pm4py.visualization.dfg import visualizer as dfg_visualizer
        dfg_parameters = dfg_visualizer.Variants.PERFORMANCE.value.Parameters
        parameters = {}
        parameters[dfg_parameters.FORMAT] = format
        parameters[dfg_parameters.START_ACTIVITIES] = start_activities
        parameters[dfg_parameters.END_ACTIVITIES] = end_activities
        parameters[dfg_parameters.AGGREGATION_MEASURE] = 'mean'
        parameters["bgcolor"] = 'white'
        gviz = dfg_visualizer.apply(dfg, variant=dfg_visualizer.Variants.PERFORMANCE,
                                    parameters=parameters)

        return str(gviz)