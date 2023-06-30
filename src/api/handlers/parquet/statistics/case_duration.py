from pm4py.statistics.traces.generic.pandas import case_statistics
from pm4py.visualization.common.utils import get_base64_from_file
from pm4py.visualization.graphs import visualizer as graphs_factory

import base64


def get_case_duration_svg(dataframe, parameters=None):
    """
    Gets the SVG of the case duration graph
    Parameters
    -------------
    dataframe
        Dataframe
    parameters
        Possible parameters of the algorithm
    Returns
    -------------
    graph
        Case duration graph
    """
    if parameters is None:
        parameters = {}

    x, y = case_statistics.get_kde_caseduration(dataframe, parameters)
    gviz = graphs_factory.apply_plot(x, y, variant=graphs_factory.Variants.CASES, parameters={"format": "svg"})

    gviz_base64 = base64.b64encode(str(gviz).encode('utf-8'))

    ret = []
    for i in range(len(x)):
        ret.append((x[i], y[i]))

    return get_base64_from_file(gviz), gviz_base64, ret


def get_median_case_duration(dataframe, parameters=None):
    """
    Gets the median case duration
    Parameters
    -------------
    dataframe
        Dataframe
    parameters
        Possible parameters of the algorithm
    Returns
    -------------
    median value
        Case duration median value
    """
    if parameters is None:
        parameters = {}

    median_case_duration = case_statistics.get_median_case_duration(dataframe, parameters)

    return median_case_duration

