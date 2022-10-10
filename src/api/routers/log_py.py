
@router.post('/GetStartItems')
async def get_start_items(log_id: str = Form(...), item_name=Form(...), db: Session = Depends(get_db)):
    # df = await get_df_session_or_database(log_id, session_id)
    df = pd.read_sql_table(log_id, con=engine_event_log)

    response_dict = {}
    acts = get.get_start_activities(df, parameters={start_activities_filter.Parameters.CASE_ID_KEY: "case:concept:name",
                                                    start_activities_filter.Parameters.ACTIVITY_KEY: item_name})
    for act in acts:
        response_dict[act] = str(acts[act])

    return response_dict


@router.post('/GetEndActivities')
async def get_end_activities(log_id: str = Form(...), db: Session = Depends(get_db)):
    df = pd.read_sql_table(log_id, con=engine_event_log)

    response_dict = {}
    acts = pm4py.get_end_activities(df)
    for act in acts:
        response_dict[act] = str(acts[act])

    return response_dict


@router.post('/GetEndItems')
async def get_end_items(log_id: str = Form(...), item_name=Form(...), db: Session = Depends(get_db)):
    # df = await get_df_session_or_database(log_id, session_id)
    df = pd.read_sql_table(log_id, con=engine_event_log)

    response_dict = {}
    acts = get_end.get_end_activities(df, parameters={end_activities_filter.Parameters.CASE_ID_KEY: "case:concept:name",
                                                      end_activities_filter.Parameters.ACTIVITY_KEY: item_name})
    for act in acts:
        response_dict[act] = str(acts[act])

    return response_dict

@router.post('/GetVariants', dependencies=[Depends(cookie)])
async def get_variants(log_id: str = Form(...), db: Session = Depends(get_db), session_id: UUID = Depends(cookie)):
    df = await get_df_session_or_database(log_id, session_id)

    response_dict = {}
    acts = pm4py.get_variants(df)
    print(acts)
    for act in acts:
        response_dict[act] = str(acts[act])

    return response_dict