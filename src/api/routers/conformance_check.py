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
import pm4py
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
from api import database, schemas
from api.handlers.parquet.parquet import ParquetHandler
from api.models import ConformanceBPMNDiagramModel
from api.routers.globals import session_manager
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, status, File, UploadFile, Form, HTTPException

from api.utils import create_id
from session import get_session, SessionInfo
from api import models, schemas
from io import StringIO

from pm4py.objects.bpmn.importer import importer as bpmn_importer
from pm4py.objects.conversion.bpmn import converter as bpmn_converter

from pm4py.objects.log.util import filtering_utils

router = APIRouter(
    prefix="/v1",
    tags=['Log Handling']
)


@router.post('/LoadBPMNModelForConformance')
def process_ai(
        session: SessionInfo = Depends(get_session),
        scope_id: str = Form(...),
        model_name: str = Form(...),
        model_content: str = Form(...),
        db: Session = Depends(database.get_org_event_db)):
    db_model: ConformanceBPMNDiagramModel = models.ConformanceBPMNDiagramModel(id=create_id(),
                                                                               realm_id=session.realm_id,
                                                                               tenant_id=session.tenant_id,
                                                                               scope_id=scope_id, model_name=model_name,
                                                                               model_content=model_content)
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    return db_model

@router.post('/GetBPMNModelForConformance')
def process_ai(
        session: SessionInfo = Depends(get_session),
        scope_id: str = Form(...),
      #  model_name: str = Form(...),
      #  model_content: str = Form(...),
        db: Session = Depends(database.get_org_event_db)):
    model = db.query(models.ConformanceBPMNDiagramModel).filter_by(realm_id=session.realm_id,
                                                                   tenant_id=session.tenant_id,
                                                                   scope_id=scope_id).first()
    if model is not None:
        return model.model_content
    return ''


@router.post('/ConformanceCheck')
def conformance_check(
        session: SessionInfo = Depends(get_session),
        scope_id: str = Form(...),
        # model_name: str = Form(...),
        db: Session = Depends(database.get_org_event_db)):
    import tempfile
    from os.path import exists

    # print tempfile.gettempdir()  # prints the current temporary directory

    try:
        tmp = tempfile.NamedTemporaryFile()

        model = db.query(models.ConformanceBPMNDiagramModel).filter_by(realm_id=session.realm_id,
                                                                       tenant_id=session.tenant_id,
                                                                       scope_id=scope_id).first()
        if (model is not None):
            with open(tmp.name, 'w') as f:
                tmp.write(model.model_content.encode('utf-8'))  # where `stuff` is, y'know... stuff to write (a string)
                tmp.flush()

            file_exists = exists(os.path.join(tmp.name))
            bpmn_graph = bpmn_importer.apply(os.path.join(tmp.name))

            net, im, fm = bpmn_converter.apply(bpmn_graph, variant=bpmn_converter.Variants.TO_PETRI_NET)

            handler: ParquetHandler = session_manager.get_handler_for_process_and_session(scope_id, session.session_id)
            log = pm4py.convert.convert_to_event_log(handler.dataframe)
            log = filtering_utils.keep_one_trace_per_variant(handler.dataframe)

            for index, trace in enumerate(log):
                check_petri = pm4py.check_is_fitting(trace, net, im, fm)
                print(check_petri)

            result4 = []
            result = pm4py.conformance_diagnostics_token_based_replay(log, net, im, fm)
            variants_statistics = handler.get_variants_statistics()

            total_case_count_fitting = 0
            total_case_count_not_fitting = 0
            index = 0
            for a in result:
                trace_len = len(log[index])
                trace = []
                for x in range(trace_len):
                    trace.append(log[index][x]['concept:name'])
                if result[index]["trace_is_fit"]:
                    total_case_count_fitting += variants_statistics[index]["count"]
                else:
                    total_case_count_not_fitting += variants_statistics[index]["count"]

                result4.append( {
                    "trace": trace,
                    "trace_is_fit":result[index]["trace_is_fit"],
                    "trace_fitness": result[index]["trace_fitness"],
                    "caseDuration_max":variants_statistics[index]["caseDuration_max"],
                    "caseDuration_mean": variants_statistics[index]["caseDuration_mean"],
                    "caseDuration_min": variants_statistics[index]["caseDuration_min"],
                    "caseDuration_sum": variants_statistics[index]["caseDuration_sum"],
                    "count": variants_statistics[index]["count"],
                    "rate_count": variants_statistics[index]["rate_count"],
                    "rate_duration": variants_statistics[index]["rate_duration"]
                })
                index = index + 1

            result1 = pm4py.conformance_diagnostics_alignments(log, net, im, fm)
            result2 = pm4py.fitness_token_based_replay(log, net, im, fm)
            result3 = pm4py.fitness_alignments(log, net, im, fm)


    finally:
        tmp.close()

    return {
        "result": result1,
        "result1": result2,
        "result2":result3,
        "result3":result4,
        "conforming_cases":total_case_count_fitting,
        "non_conforming_cases": total_case_count_not_fitting
    }
