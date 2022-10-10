from pm4py.algo.conformance.alignments.petri_net import algorithm as align_factory
from pm4py.objects.petri_net.importer import importer as pnml
from pm4py.visualization.align_table import visualizer as align_table_factory
from pm4py.visualization.common.utils import get_base64_from_gviz
from pm4py.visualization.petri_net import visualizer as pn_vis_factory
from pm4py.visualization.petri_net.util import alignments_decoration
from pm4py.objects.conversion.log import converter as log_conv_factory
from copy import copy

def perform_alignments(df, petri_string, parameters=None):
    """
    Perform alignments
    Parameters
    ------------
    df
        Dataframe
    net
        Petri net
    parameters
        Parameters of the algorithm
    Returns
    -------------
    petri
        SVG of the decorated Petri
    table
        SVG of the decorated table
    """
    if parameters is None:
        parameters = {}

    net, im, fm = pnml.import_petri_from_string(petri_string, parameters=parameters)

    parameters_conv = copy(parameters)
    parameters_conv["return_variants"] = True
    log, all_variants = log_conv_factory.apply(df, variant=log_conv_factory.DF_TO_EVENT_LOG_NV, parameters=parameters_conv)

    parameters_align = {}
    parameters_align["ret_tuple_as_trans_desc"] = True
    parameters_align["variants_idx"] = all_variants

    alignments = align_factory.apply(log, net, im, fm, parameters=parameters_align)
    decorations = alignments_decoration.get_alignments_decoration(net, im, fm, aligned_traces=alignments)

    gviz_on_petri = pn_vis_factory.apply(net, im, fm, aggregated_statistics=decorations, variant="alignments", parameters={"format": "svg"})
    svg_on_petri = get_base64_from_gviz(gviz_on_petri)

    parameters_table = {}
    parameters_table["format"] = "svg"

    gviz_table = align_table_factory.apply(log, alignments, parameters=parameters_table)
    svg_table = get_base64_from_gviz(gviz_table)

    return svg_on_petri, svg_table