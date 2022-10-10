from pm4py.algo.filtering.pandas.attributes import attributes_filter
from pm4py.visualization.common.utils import get_base64_from_file
from pm4py.visualization.graphs import variants, visualizer as graphs_factory
import base64

def get_events_per_time_svg(dataframe, parameters=None):
    """
    Gets the SVG of the events per time graph
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

    x, y = attributes_filter.get_kde_date_attribute(dataframe, parameters=parameters)

    gviz = graphs_factory.apply_plot(x, y, variant=variants.dates, parameters={"format": "svg"})

    gviz_base64 = base64.b64encode(str(gviz).encode('utf-8'))

    ret = []
    for i in range(len(x)):
        ret.append((x[i].replace(tzinfo=None).timestamp(), y[i]))

    return get_base64_from_file(gviz), gviz_base64, ret