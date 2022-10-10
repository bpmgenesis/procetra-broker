POSSIBLE_CASE_ID_COLUMNS = ["case:concept:name", "case", "instance", "process", "execution"]
POSSIBLE_ACTIVITY_COLUMNS = ["concept:name", "activity", "act"]
POSSIBLE_TIMESTAMP_COLUMNS = ["time:timestamp", "time", "date"]


def assign_column_correspondence(df):
    """
    Assigns column correspondence to dataframe
    Parameters
    --------------
    df
        Pandas dataframe
    Returns
    --------------
    case_id_column
        Column that is most likely associated to the case ID
    activity_column
        Column associated to the activity
    timestamp_column
    :param df:
    :return:
    """
    columns = [str(x) for x in df.columns]

    case_id_column = None
    activity_column = None
    timestamp_column = None

    for ca in POSSIBLE_CASE_ID_COLUMNS:
        for co in columns:
            if co.lower().startswith(ca):
                case_id_column = co
                break

    for ac in POSSIBLE_ACTIVITY_COLUMNS:
        for co in columns:
            if co.lower().startswith(ac):
                activity_column = co
                break

    for ti in POSSIBLE_TIMESTAMP_COLUMNS:
        for co in columns:
            if co.lower().startswith(ti):
                timestamp_column = co
                break

    return case_id_column, activity_column, timestamp_column