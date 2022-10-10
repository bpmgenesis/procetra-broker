from pm4py.algo.discovery.dfg.adapters.pandas import df_statistics
from pm4py.algo.discovery.inductive import algorithm as inductive_miner
from pm4py.algo.filtering.pandas.auto_filter import auto_filter
from pm4py.objects.log.util import xes
from pm4py.objects.petri_net.exporter.variants.pnml import export_petri_as_string
from pm4py.visualization.common.utils import get_base64_from_gviz, get_base64_from_file
from pm4py.visualization.petri_net import visualizer as pn_vis_factory
from pm4py.visualization.petri_net.util.vis_trans_shortest_paths import get_decorations_from_dfg_spaths_acticount
from pm4py.visualization.petri_net.util.vis_trans_shortest_paths import get_shortest_paths
from pm4py.algo.filtering.pandas.attributes import attributes_filter
from pm4py.algo.filtering.pandas.start_activities import start_activities_filter
from pm4py.algo.filtering.pandas.end_activities import end_activities_filter
from pm4pybpmn.visualization.bpmn.util import convert_performance_map
from pm4pybpmn.objects.bpmn.exporter import bpmn20 as bpmn_exporter
from pm4py.util import constants as pm4_constants
from pm4py.algo.filtering.common.filtering_constants import CASE_CONCEPT_NAME
from api.util import get_graph
import base64

from api.util import constants

from pm4pybpmn.objects.conversion.petri_to_bpmn import factory as petri_to_bpmn
from pm4pybpmn.visualization.bpmn import factory as bpmn_vis_factory
from pm4pybpmn.visualization.bpmn.util import bpmn_embedding
from pm4pybpmn.objects.bpmn.util import bpmn_diagram_layouter
from pm4pybpmn.visualization.bpmn.util import convert_performance_map

from pm4py.algo.filtering.dfg.dfg_filtering import clean_dfg_based_on_noise_thresh

def apply(dataframe, parameters=None):
    """
    Gets the Petri net through Inductive Miner, decorated by frequency metric
    Parameters
    ------------
    dataframe
        Dataframe
    parameters
        Parameters of the algorithm
    Returns
    ------------
    base64
        Base64 of an SVG representing the model
    model
        Text representation of the model
    format
        Format of the model
    """
    if parameters is None:
        parameters = {}

    decreasingFactor = parameters[
        "decreasingFactor"] if "decreasingFactor" in parameters else constants.DEFAULT_DEC_FACTOR

    activity_key = parameters[pm4_constants.PARAMETER_CONSTANT_ACTIVITY_KEY] if pm4_constants.PARAMETER_CONSTANT_ACTIVITY_KEY in parameters else xes.DEFAULT_NAME_KEY
    timestamp_key = parameters[pm4_constants.PARAMETER_CONSTANT_TIMESTAMP_KEY] if pm4_constants.PARAMETER_CONSTANT_TIMESTAMP_KEY in parameters else xes.DEFAULT_TIMESTAMP_KEY
    case_id_glue = parameters[pm4_constants.PARAMETER_CONSTANT_CASEID_KEY] if pm4_constants.PARAMETER_CONSTANT_CASEID_KEY in parameters else CASE_CONCEPT_NAME

    parameters[pm4_constants.RETURN_EA_COUNT_DICT_AUTOFILTER] = True
    dataframe = attributes_filter.filter_df_keeping_spno_activities(dataframe, activity_key=activity_key,
                                                                    max_no_activities=constants.MAX_NO_ACTIVITIES)
    dataframe, end_activities = auto_filter.apply_auto_filter(dataframe, parameters=parameters)
    end_activities = list(end_activities.keys())
    activities_count = attributes_filter.get_attribute_values(dataframe, activity_key, parameters=parameters)
    activities = list(activities_count.keys())
    start_activities = list(start_activities_filter.get_start_activities(dataframe, parameters=parameters).keys())

    dfg = df_statistics.get_dfg_graph(dataframe, activity_key=activity_key, timestamp_key=timestamp_key, case_id_glue=case_id_glue, sort_caseid_required=False, sort_timestamp_along_case_id=False)
    dfg = clean_dfg_based_on_noise_thresh(dfg, activities, decreasingFactor * constants.DEFAULT_DFG_CLEAN_MULTIPLIER,
                                          parameters=parameters)
    net, im, fm = inductive_miner.apply_dfg(dfg, parameters, activities=activities, start_activities=start_activities, end_activities=end_activities)
    spaths = get_shortest_paths(net)

    bpmn_graph, el_corr, inv_el_corr, el_corr_keys_map = petri_to_bpmn.apply(net, im, fm)

    aggregated_statistics = get_decorations_from_dfg_spaths_acticount(net, dfg, spaths,
                                                                      activities_count,
                                                                      variant="frequency")

    bpmn_aggreg_statistics = convert_performance_map.convert_performance_map_to_bpmn(aggregated_statistics,
                                                                                     inv_el_corr)
    bpmn_graph = bpmn_embedding.embed_info_into_bpmn(bpmn_graph, bpmn_aggreg_statistics, "frequency")
    bpmn_graph = bpmn_diagram_layouter.apply(bpmn_graph)
    bpmn_string = bpmn_exporter.get_string_from_bpmn(bpmn_graph)

    gviz = bpmn_vis_factory.apply_petri(net, im, fm, aggregated_statistics=aggregated_statistics, variant="frequency", parameters={"format": "svg"})
    gviz2 = bpmn_vis_factory.apply_petri(net, im, fm, aggregated_statistics=aggregated_statistics, variant="frequency", parameters={"format": "dot"})

    gviz_base64 = get_base64_from_file(gviz2.name)

    ret_graph = get_graph.get_graph_from_petri(net, im, fm)

    return get_base64_from_file(gviz.name), export_petri_as_string(net, im, fm), ".pnml", "parquet", activities, start_activities, end_activities, gviz_base64, ret_graph, "indbpmn", "freq", bpmn_string, ".bpmn", activity_key
