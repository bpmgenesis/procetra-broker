def include_key_in_value_list(dictio):
    """
    Returns a list that contains the cases in the log,
    starting from the dictionary returned by PM4Py
    Parameters
    ---------------
    dictio
        Dictionary of cases
    Returns
    ---------------
    list_cases
        List of cases
    """
    ret = []
    for key in dictio:
        val = dictio[key]
        val["caseId"] = key
        ret.append(val)
    return ret