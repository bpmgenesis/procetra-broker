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
from fastapi import APIRouter, Form, Depends
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
import json
import os
from api import database, schemas, schemas
from api.handlers.parquet.parquet import ParquetHandler
from api.routers.globals import session_manager

# os.environ["PM4PY_OPENAI_API_KEY"] = "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"

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

   # training_data_path = os.getcwd() + "/training_data.json"

    # Veri kümesini yükleyin
    # def load_training_data(path):
    #     with open(path, 'r') as file:
    #         data = json.load(file)
    #     return data

    # load_training_data(training_data_path)
    training_data = [
        {"role": "user",
         "content": "Aşağıda Satınalma sürecinin performans ve frekans verilerini içeren bilfgiler vardır."},
        {"role": "user", "content": """ 
            Sektör Onayı-Giriş -> Sektör Onayı-Kapanış -> Onayı-Sektör Onayı ( frequency = 5  performance = 7908.0 )
            Mevzuat Onayı-Giriş -> Mevzuat Onayı-Kapanış -> Kampanya İnceleme Onayı ( frequency = 5  performance = 1080.0 )
            Pazarlama Onayı-Giriş -> Pazarlama Onayı-Kapanış -> Onayı-Pazarlama Onayı ( frequency = 4  performance = 683865.0 )
            Sektör Onayı-Giriş -> Onayı-Sektör Onayı -> Sektör Onayı-Kapanış ( frequency = 4  performance = 5070.0 )
            Mevzuat Onayı-Giriş -> Kampanya İnceleme Onayı -> Mevzuat Onayı-Kapanış ( frequency = 4  performance = 960.0 )
            Kampanya Yönetimi-Giriş -> Yönetimi-İşlem Onayı -> Pazarlama Müdür Onayı -> Kampanya Yönetimi-Kapanış -> Yönetimi-Kurumsal İletişim ( frequency = 3  performance = 11240.0 )
            Giriş -> Yönetimi-İşlem Onayı -> Pazarlama Müdür Onayı -> Yönetimi-Kurumsal İletişim -> Kampanya Yönetimi-Kapanış ( frequency = 1  performance = 2743680.0 )
            Kampanya Yönetimi-Giriş -> Yönetimi-İşlem Onayı -> Pazarlama Müdür Onayı -> Yönetimi-Kurumsal İletişim -> Kampanya Yönetimi-Kapanış ( frequency = 1  performance = 20040.0 )
            Pazarlama Onayı-Giriş -> Onayı-Pazarlama Onayı -> Pazarlama Onayı-Kapanış ( frequency = 1  performance = 2040.0 )
            Mevzuat Onayı-Giriş -> Kampanya İnceleme Onayı ( frequency = 1  performance = 240.0 )
            Kampanya Yönetimi-Giriş -> Yönetimi-İşlem Onayı ( frequency = 1  performance = 60.0 )
            Pazarlama Onayı-Giriş -> Onayı-Pazarlama Onayı ( frequency = 1  performance = 0.0 )"""
         },
        {"role": "user",
         "content": "Yukarıdaki süreçle ilgili soru soruldugunda mutlaka bu süreç özelinde cevap ver"},
        {"role": "user",
         "content": "Please provide responses in html format."},
    ]

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
    # execute_query = False

    openai.api_key = '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'
    openai.organization = 'org-FHpsYObt6rUzipCfijAqLuHE'

    messages = training_data.append({"role": "user", "content": full_query})

    response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=training_data)
    return response["choices"][0]["message"]["content"]

    if not execute_query:
        return query

    res = perform_query.apply(full_query, parameters=parameters)

    return res


def fine():
    training_data_path = os.getcwd() + "/training_data.json"

    # Veri kümesini yükleyin
    def load_training_data(path):
        with open(path, 'r') as file:
            data = json.load(file)
        return data

    # Veri kümesini alın
    training_data = load_training_data(training_data_path)

    # Eğitim işlemi için OpenAI API'sine bağlanın
    openai.api_key = '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'

    # Eğitim verilerini kullanarak GPT-3 modelini eğitin
    def fine_tune_gpt3(training_data):
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # GPT-3'ü özel olarak eğitirken "davinci" veya "gpt-3.5-turbo" gibi modeli belirtin.
            #  examples=training_data,
            messages=training_data,
            # prompt="Ürün dokümantasyonu için chatbot eğitimi.",
            max_tokens=1000,
            temperature=0.7,
            n=1,
            stop=["\n"]
        )
        return response

    # Eğitimi başlatın
    response = fine_tune_gpt3(training_data)

    # Eğitim sonuçlarını kaydedin (isteğe bağlı)
    with open(os.getcwd() + "/fine_tuned_model.txt", "w") as file:
        file.write(response['choices'][0]['message']['content'])

    return ""
