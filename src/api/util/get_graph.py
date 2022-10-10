def get_graph_from_dfg(dfg, start_activities, end_activities, parameters=None):
    """
    Get a graph representation (nodes/edges) from a DFG and the list of
    edges
    Parameters
    -------------
    dfg
        DFG
    start_activities
        Start activities
    end_activities
        End activities
    parameters
        Possible parameters
    Returns
    --------------
    graph
        Graph representation
    """
    map_activities = {}

    nodes = []
    edges = []

    for el in dfg:
        act1 = el[0]
        act2 = el[1]

        if act1 not in map_activities:
            map_activities[act1] = len(map_activities)
            is_start = False
            is_end = False
            if act1 in start_activities:
                is_start = True
            if act1 in end_activities:
                is_end = True
            nodes.append([act1, "node", is_start, is_end])

        if act2 not in map_activities:
            map_activities[act2] = len(map_activities)
            is_start = False
            is_end = False
            if act2 in start_activities:
                is_start = True
            if act2 in end_activities:
                is_end = True
            nodes.append([act2, "node", is_start, is_end])

        edges.append([map_activities[act1], map_activities[act2], None])

    return ["dfg", nodes, edges]


def get_graph_from_petri(net, im, fm):
    """
    Get a graph representation (nodes/edges) from a Petri net
    Parameters
    -------------
    net
        Petri net
    im
        Initial marking
    fm
        Final marking
    Returns
    --------------
    graph
        Graph representation
    """
    map = {}

    nodes = []
    edges = []

    for place in net.places:
        map[place.name] = len(map)
        is_in_im = False
        is_in_fm = False
        if place in im:
            is_in_im = True
        if place in fm:
            is_in_fm = True
        nodes.append([place.name, place.name, "place", is_in_im, is_in_fm])

    for transition in net.transitions:
        map[transition.name] = len(map)
        nodes.append([transition.name, transition.label, "transition", not transition.label is None])

    for arc in net.arcs:
        edges.append([map[arc.source.name], map[arc.target.name], None])

    return ["petri", nodes, edges]