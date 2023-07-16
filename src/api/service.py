import pandas as pd
import pm4py
from pandas import DataFrame
from typing import Tuple, Union, List, Dict, Any, Optional
from pm4py.algo.discovery.dfg.adapters.pandas import df_statistics

class Discovery:
    @staticmethod
    def performance_dfg(log: DataFrame,
                        activity_key: str = 'concept:name',
                        timestamp_key: str = 'time:timestamp',
                        case_id_key: str = 'case:concept:name'):
        dfg, start_activities, end_activities = pm4py.discover_dfg(log, case_id_key='case:concept:name',
                                                                   activity_key='concept:name',
                                                                   timestamp_key='time:timestamp')

        dfg, start_activities, end_activities = pm4py.discover_performance_dfg(log)

        # result = df_statistics.get_dfg_graph(log,measure="both")
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


class Vis:
    @staticmethod
    def events_per_time(log: DataFrame,
                        activity_key: str = 'concept:name',
                        timestamp_key: str = 'time:timestamp',
                        case_id_key: str = 'case:concept:name'):
        from pm4py.statistics.attributes.pandas import get as attributes_get
        from pm4py.utils import get_properties

        graph = attributes_get.get_kde_date_attribute(log, parameters=get_properties(log, activity_key=activity_key,
                                                                                     case_id_key=case_id_key,
                                                                                     timestamp_key=timestamp_key))



        return ( list(map(lambda n: n.timestamp() * 1000, graph[0].to_pydatetime())), graph[1].tolist())
