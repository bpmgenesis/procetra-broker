'''
    This file is part of PM4Py (More Info: https://pm4py.fit.fraunhofer.de).

    PM4Py is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    PM4Py is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with PM4Py.  If not, see <https://www.gnu.org/licenses/>.
'''

from typing import Optional, Dict, Any, Collection
import pandas as pd
from fastapi import APIRouter, Form
from pm4py.objects.log.obj import EventLog, EventStream
from pm4py.objects.ocel.obj import OCEL
from pm4py.algo.querying.openai import log_to_dfg_descr, log_to_variants_descr, log_to_cols_descr
from pm4py.algo.querying.openai import stream_to_descr
from pm4py.algo.transformation.ocel.description import algorithm as ocel_description
from pm4py.algo.querying.openai import ocel_ocdfg_descr, ocel_fea_descr
from pm4py.algo.querying.openai import perform_query
from pm4py.objects.conversion.log import converter as log_converter
from typing import Union, Tuple
from enum import Enum
from pm4py.util import exec_utils, constants, xes_constants

import os

from api.handlers.parquet.parquet import ParquetHandler
from api.routers.globals import session_manager

#os.environ["PM4PY_OPENAI_API_KEY"] = "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"

import openai

openai.api_key = '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'



class Parameters(Enum):
    EXECUTE_QUERY = "execute_query"
    API_KEY = "api_key"
    EXEC_RESULT = "exec_result"
    ACTIVITY_KEY = constants.PARAMETER_CONSTANT_ACTIVITY_KEY






router = APIRouter(
    prefix="/v1",
    tags=['Log Handling']
)


@router.post('/ProsessAI')
def process_ai(session_id: str = Form(...), project_id: str = Form(...), query: str = Form(...)):
    handler: ParquetHandler = session_manager.get_handler_for_process_and_session(project_id, session_id)
    # return query_wrapper(handler.dataframe, query)

    parameters = {}

    log_obj = log_converter.apply(handler.dataframe, variant=log_converter.Variants.TO_DATA_FRAME,
                                  parameters=parameters)
    activity_key = exec_utils.get_param_value(Parameters.ACTIVITY_KEY, parameters, xes_constants.DEFAULT_NAME_KEY)

    # api_key = exec_utils.get_param_value(Parameters.API_KEY, parameters, constants.OPENAI_API_KEY)

    api_key = ''
    execute_query = exec_utils.get_param_value(Parameters.EXECUTE_QUERY, parameters, api_key is not None)
    exec_result = exec_utils.get_param_value(Parameters.EXEC_RESULT, parameters, constants.OPENAI_EXEC_RESULT)

    full_query = log_to_variants_descr.apply(log_obj, parameters=parameters)
    full_query += query
    full_query += """ Please only data and process specific considerations, not general considerations. 
    Please your answers will be html.
       """
    #execute_query = False
    if not execute_query:
        return query

    res = perform_query.apply(full_query, parameters=parameters)

    return res
