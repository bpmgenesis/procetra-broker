from pm4py.algo.filtering.common.filtering_constants import CASE_CONCEPT_NAME
from pm4py.algo.filtering.pandas.attributes import attributes_filter
from pm4py.algo.filtering.pandas.end_activities import end_activities_filter
from pm4py.algo.filtering.pandas.start_activities import start_activities_filter
from pm4py.algo.filtering.pandas.variants import variants_filter
from pm4py.objects.conversion.log import converter as conv_factory
#from pm4py.objects.log.adapters.pandas import csv_import_adapter
from pm4py.objects.log.exporter.xes.variants  import etree_xes_exp
#from pm4py.objects.log.importer.parquet import factory as parquet_importer
from pm4py.objects.log.util import xes
from pm4py.statistics.traces.generic.pandas import case_statistics
from pm4py.util import constants
import pandas as pd

from api.util import constants as ws_constants

from api.handlers.parquet.cases import variants
from api.handlers.parquet.ctmc import transient
from api.handlers.parquet.process_schema import factory as process_schema_factory
from api.handlers.parquet.sna import get_sna as sna_obtainer
from api.handlers.parquet.statistics import case_duration, events_per_time, numeric_attribute
from api.util import casestats
from api.handlers.parquet.filtering import factory as filtering_factory
from api.handlers.parquet.alignments import get_align
from pm4py.algo.discovery.dfg.adapters.pandas import df_statistics

from pm4py.objects.log.util.xes import DEFAULT_NAME_KEY, DEFAULT_TIMESTAMP_KEY

from api.util import format_recognition
from api.util.columns_recognition import assign_column_correspondence

from procetraconfiguration import configuration as Configuration

import pandas as pd
import time
import datetime
import math

from api import database, schemas, schemas

get_db = database.get_db



class ParquetHandler(object):
    def __init__(self, is_lazy=False):
        """
        Constructor (set all variables to None)
        """

        # sets the current dataframe to None
        self.dataframe = None
        # grouped dataframe
        self.grouped_dataframe = None
        # 'reduced' dataframe (concept name, activity and timestamp)
        self.reduced_dataframe = None
        # reduced grouped dataframe
        self.reduced_grouped_dataframe = None
        # sets the first ancestor (in the filtering chain) to None
        self.first_ancestor = self
        # sets the last ancestor (in the filtering chain) to None
        self.last_ancestor = self
        # sets the filter chain
        self.filters_chain = []
        # sets the variant dataframe (useful in variants retrieval)
        self.variants_df = None
        # most common variant (activities)
        self.most_common_variant = None
        # most common variant (paths)
        self.most_common_paths = None
        # number of variants
        self.variants_number = -1
        # number of cases
        self.cases_number = -1
        # number of events
        self.events_number = -1
        # classifier
        self.activity_key = None

        self.is_lazy = is_lazy
        self.sorted_dataframe_basilar = False
        self.sorted_dataframe_by_case_id = False

    def get_filters_chain_repr(self):
        """
        Gets the representation of the current filters chain
        Returns
        -----------
        stri
            Representation of the current filters chain
        """
        return str(self.filters_chain)

    def copy_from_ancestor(self, ancestor):
        """
        Copies from ancestor
        Parameters
        -------------
        ancestor
            Ancestor
        """
        self.first_ancestor = ancestor.first_ancestor
        self.last_ancestor = ancestor
        self.activity_key = ancestor.activity_key
        # self.filters_chain = ancestor.filters_chain
        self.dataframe = ancestor.dataframe
        # self.grouped_dataframe = ancestor.grouped_dataframe
        # self.reduced_dataframe = ancestor.reduced_dataframe
        # self.reduced_grouped_dataframe = ancestor.reduced_grouped_dataframe
        self.is_lazy = ancestor.is_lazy
        self.sorted_dataframe_by_case_id = ancestor.sorted_dataframe_by_case_id
        self.sorted_dataframe_basilar = ancestor.sorted_dataframe_basilar

    def build_from_path(self, path, parameters=None):
        """
        Builds the handler from the specified path to Parquet file
        Parameters
        -------------
        path
            Path to the log file
        parameters
            Parameters of the algorithm
        """
        if parameters is None:
            parameters = {}
        self.dataframe = parquet_importer.apply(path)
        # TODO: verify if this is the best way to act
        self.dataframe[DEFAULT_TIMESTAMP_KEY] = pd.to_datetime(self.dataframe[DEFAULT_TIMESTAMP_KEY], utc=True)
        if not str(self.dataframe[CASE_CONCEPT_NAME].dtype) == "object":
            self.dataframe[CASE_CONCEPT_NAME] = self.dataframe[CASE_CONCEPT_NAME].astype(str)
        self.postloading_processing_dataframe()
        if not self.is_lazy:
            self.sort_dataframe_basilar()
            self.build_grouped_dataframe()
            self.insert_case_number_in_grouped_df()
            self.sort_dataframe_by_case_id()
            self.build_reduced_dataframe()
            self.build_variants_df()
            self.build_reduced_grouped_dataframe()
            self.calculate_events_number()
            self.calculate_variants_number()
            self.calculate_cases_number()

    def build_from_csv(self, path, parameters=None):
        """
        Builds the handler from the specified path to CSV file
        Parameters
        -------------
        path
            Path to the log file
        parameters
            Parameters of the algorithm
        """
        if parameters is None:
            parameters = {}
        activity_key = parameters[
            constants.PARAMETER_CONSTANT_ACTIVITY_KEY] if constants.PARAMETER_CONSTANT_ACTIVITY_KEY in parameters else None
        timestamp_key = parameters[
            constants.PARAMETER_CONSTANT_TIMESTAMP_KEY] if constants.PARAMETER_CONSTANT_TIMESTAMP_KEY in parameters else None
        case_id_glue = parameters[
            constants.PARAMETER_CONSTANT_CASEID_KEY] if constants.PARAMETER_CONSTANT_CASEID_KEY in parameters else None
        recognized_format = format_recognition.get_format_from_csv(path)
        sep = parameters["sep"] if "sep" in parameters else recognized_format.delimiter
        quotechar = parameters["quotechar"] if "quotechar" in parameters else recognized_format.quotechar
        if quotechar is not None:
            self.dataframe = pd.read_csv(path, sep=sep, quotechar=quotechar)
        else:
            self.dataframe = csv_import_adapter.import_dataframe_from_path(path, sep=sep)
        case_id_glue1, activity_key1, timestamp_key1 = assign_column_correspondence(self.dataframe)
        if case_id_glue is None:
            case_id_glue = case_id_glue1
        if activity_key is None:
            activity_key = activity_key1
        if timestamp_key is None:
            timestamp_key = timestamp_key1
        if not activity_key == xes.DEFAULT_NAME_KEY:
            self.dataframe[xes.DEFAULT_NAME_KEY] = self.dataframe[activity_key]
        if not timestamp_key == xes.DEFAULT_TIMESTAMP_KEY:
            self.dataframe[xes.DEFAULT_TIMESTAMP_KEY] = self.dataframe[timestamp_key]
        if not case_id_glue == CASE_CONCEPT_NAME:
            self.dataframe[CASE_CONCEPT_NAME] = self.dataframe[case_id_glue]
        if not str(self.dataframe[CASE_CONCEPT_NAME].dtype) == "object":
            self.dataframe[CASE_CONCEPT_NAME] = self.dataframe[CASE_CONCEPT_NAME].astype(str)
        self.postloading_processing_dataframe()
        if not self.is_lazy:
            from pm4py.objects.log.util import dataframe_utils
            self.dataframe = dataframe_utils.convert_timestamp_columns_in_df(self.dataframe)
            self.sort_dataframe_basilar()
            self.build_grouped_dataframe()
            self.insert_case_number_in_grouped_df()
            self.sort_dataframe_by_case_id()
            self.build_reduced_dataframe()
            self.build_variants_df()
            self.build_reduced_grouped_dataframe()
            self.calculate_variants_number()
            self.calculate_cases_number()
            self.calculate_events_number()

    def build_from_org_db(self,org_name: str, log_id: str, parameters=None):
        """
        Builds the handler from the specified path to CSV file
        Parameters
        -------------
        path
            Path to the log file
        parameters
            Parameters of the algorithm
        """
        if parameters is None:
            parameters = {}
        activity_key = parameters[
            constants.PARAMETER_CONSTANT_ACTIVITY_KEY] if constants.PARAMETER_CONSTANT_ACTIVITY_KEY in parameters else None
        timestamp_key = parameters[
            constants.PARAMETER_CONSTANT_TIMESTAMP_KEY] if constants.PARAMETER_CONSTANT_TIMESTAMP_KEY in parameters else None
        case_id_glue = parameters[
            constants.PARAMETER_CONSTANT_CASEID_KEY] if constants.PARAMETER_CONSTANT_CASEID_KEY in parameters else None

        engine_event_log = database.get_organization_event_data_engine(org_name, log_id)

        self.dataframe = pd.read_sql_table(
            log_id,
            con=engine_event_log
        )

        case_id_glue1, activity_key1, timestamp_key1 = assign_column_correspondence(self.dataframe)
        if case_id_glue is None:
            case_id_glue = case_id_glue1
        if activity_key is None:
            activity_key = activity_key1
        if timestamp_key is None:
            timestamp_key = timestamp_key1
        if not activity_key == xes.DEFAULT_NAME_KEY:
            self.dataframe[xes.DEFAULT_NAME_KEY] = self.dataframe[activity_key]
        if not timestamp_key == xes.DEFAULT_TIMESTAMP_KEY:
            self.dataframe[xes.DEFAULT_TIMESTAMP_KEY] = self.dataframe[timestamp_key]
        if not case_id_glue == CASE_CONCEPT_NAME:
            self.dataframe[CASE_CONCEPT_NAME] = self.dataframe[case_id_glue]
        if not str(self.dataframe[CASE_CONCEPT_NAME].dtype) == "object":
            self.dataframe[CASE_CONCEPT_NAME] = self.dataframe[CASE_CONCEPT_NAME].astype(str)
        self.postloading_processing_dataframe()
        if not self.is_lazy:
            from pm4py.objects.log.util import dataframe_utils
            self.dataframe = dataframe_utils.convert_timestamp_columns_in_df(self.dataframe)
            self.sort_dataframe_basilar()
            self.build_grouped_dataframe()
            self.insert_case_number_in_grouped_df()
            self.sort_dataframe_by_case_id()
            self.build_reduced_dataframe()
            self.build_variants_df()
            self.build_reduced_grouped_dataframe()
            self.calculate_variants_number()
            self.calculate_cases_number()
            self.calculate_events_number()

    def postloading_processing_dataframe(self):
        """
        Postloading processing of the dataframe
        """

        self.activity_key = ws_constants.DEFAULT_CLASSIFIER_KEY
        if not str(self.dataframe[xes.DEFAULT_NAME_KEY].dtype) == "object":
            self.dataframe[xes.DEFAULT_NAME_KEY] = self.dataframe[xes.DEFAULT_NAME_KEY].astype(str)
        if xes.DEFAULT_TRANSITION_KEY in self.dataframe:
            if not str(self.dataframe[xes.DEFAULT_TRANSITION_KEY].dtype) == "object":
                self.dataframe[xes.DEFAULT_TRANSITION_KEY] = self.dataframe[xes.DEFAULT_TRANSITION_KEY].astype(str)

        if ws_constants.DEFAULT_CLASSIFIER_KEY not in self.dataframe:
            if xes.DEFAULT_TRANSITION_KEY in self.dataframe:
                self.dataframe[ws_constants.DEFAULT_CLASSIFIER_KEY] = self.dataframe[xes.DEFAULT_NAME_KEY] + "+" + \
                                                                      self.dataframe[xes.DEFAULT_TRANSITION_KEY]
            else:
                self.dataframe[ws_constants.DEFAULT_CLASSIFIER_KEY] = self.dataframe[xes.DEFAULT_NAME_KEY]

    def build_event_index(self):
        """
        Builds the index of events in the dataframe
        """
        if ws_constants.DEFAULT_EVENT_INDEX_KEY not in self.dataframe:
            self.dataframe[ws_constants.DEFAULT_EVENT_INDEX_KEY] = self.dataframe.index

    def sort_dataframe_basilar(self):
        """
        Do a basic sort of the dataframe
        """
        if not self.sorted_dataframe_basilar:
            self.build_event_index()
            self.dataframe = self.dataframe.sort_values([DEFAULT_TIMESTAMP_KEY, ws_constants.DEFAULT_EVENT_INDEX_KEY])
            self.dataframe = self.dataframe.reset_index(drop=True)
            self.sorted_dataframe_basilar = True

    def sort_dataframe_by_case_id(self):
        """
        Sort the dataframe by case ID
        """
        self.sort_dataframe_basilar()
        self.insert_case_number_in_grouped_df()
        if not self.sorted_dataframe_by_case_id:
            if xes.DEFAULT_TIMESTAMP_KEY in self.dataframe:
                self.dataframe = self.dataframe.sort_values(
                    [ws_constants.DEFAULT_CASE_INDEX_KEY, xes.DEFAULT_TIMESTAMP_KEY,
                     ws_constants.DEFAULT_EVENT_INDEX_KEY])
            else:
                self.dataframe = self.dataframe.sort_values(
                    [ws_constants.DEFAULT_CASE_INDEX_KEY, ws_constants.DEFAULT_EVENT_INDEX_KEY])
            self.sorted_dataframe_by_case_id = True

    def remove_filter(self, filter, all_filters):
        """
        Removes a filter from the current handler
        Parameters
        -----------
        filter
            Filter to remove
        all_filters
            All the filters that are still there
        Returns
        ------------
        new_handler
            New handler
        """
        if all_filters:
            new_handler = ParquetHandler()
            new_handler.copy_from_ancestor(self.first_ancestor)
            for filter in all_filters:
                new_handler.add_filter0(filter)
            new_handler.events_number = -1
            new_handler.cases_number = -1
            new_handler.variants_number = -1

            if not self.is_lazy:
                new_handler.build_grouped_dataframe()
                new_handler.build_reduced_dataframe()
                new_handler.build_variants_df()
                new_handler.build_reduced_grouped_dataframe()
                new_handler.calculate_cases_number()
                new_handler.calculate_variants_number()
                new_handler.calculate_events_number()
            return new_handler
        return self.first_ancestor

    def add_filter(self, filter, all_filters):
        """
        Adds a filter to the current handler
        Parameters
        -----------
        filter
            Filter to add
        all_filters
            All the filters that were added
        Returns
        ------------
        new_handler
            New handler
        """
        new_handler = ParquetHandler()
        new_handler.copy_from_ancestor(self.first_ancestor)
        for filter in all_filters:
            new_handler.add_filter0(filter)
        new_handler.events_number = -1
        new_handler.cases_number = -1
        new_handler.variants_number = -1

        if not self.is_lazy:
            new_handler.build_grouped_dataframe()
            new_handler.build_reduced_dataframe()
            new_handler.build_variants_df()
            new_handler.build_reduced_grouped_dataframe()
            new_handler.calculate_cases_number()
            new_handler.calculate_variants_number()
            new_handler.calculate_events_number()
        return new_handler

    def add_filter0(self, filter):
        """
        Technical, void, method to add a filter
        Parameters
        ------------
        filter
            Filter to add
        """
        parameters = {}
        parameters[constants.PARAMETER_CONSTANT_ACTIVITY_KEY] = self.activity_key
        parameters[constants.PARAMETER_CONSTANT_ATTRIBUTE_KEY] = self.activity_key
        if self.grouped_dataframe is not None:
            parameters[constants.GROUPED_DATAFRAME] = self.grouped_dataframe
        self.dataframe = filtering_factory.apply(self.dataframe, filter, parameters=parameters)
        self.filters_chain.append(filter)

    def build_variants_df(self, parameters=None):
        """
        Builds the variants dataframe
        Parameters
        --------------
        parameters
            Possible parameters of the algorithm
        """
        if self.variants_df is None:
            if parameters is None:
                parameters = {}
            parameters[constants.PARAMETER_CONSTANT_ACTIVITY_KEY] = self.activity_key
            parameters[constants.PARAMETER_CONSTANT_ATTRIBUTE_KEY] = self.activity_key

            if self.reduced_dataframe is not None:
                dataframe = self.reduced_dataframe
            else:
                dataframe = self.dataframe

            self.variants_df = case_statistics.get_variants_df_with_case_duration(dataframe,
                                                                                  parameters=parameters)
            self.save_most_common_variant(self.variants_df)

    def get_variants_df(self):
        """
        Returns the variant dataframe
        Returns
        --------------
        variants_df
            Variants dataframe
        """
        self.build_variants_df()

        return self.variants_df

    def build_reduced_dataframe(self):
        """
        Builds the reduced dataframe
        """
        if self.reduced_dataframe is None:
            self.reduced_dataframe = self.dataframe[[CASE_CONCEPT_NAME, self.activity_key, DEFAULT_TIMESTAMP_KEY]]

    def get_reduced_dataframe(self):
        """
        Gets the reduced dataframe
        Returns
        ---------------
        reduced_dataframe
            Dataframe containing only 3 columns
        """

        self.build_reduced_dataframe()
        return self.reduced_dataframe

    def build_grouped_dataframe(self):
        """
        Saves the grouped dataframe
        """
        if self.grouped_dataframe is None:
            self.grouped_dataframe = self.dataframe.groupby(CASE_CONCEPT_NAME, sort=False)

    def insert_case_number_in_grouped_df(self):
        """
        Inserts the case number in the grouped dataframe
        :return:
        """
        self.build_grouped_dataframe()
        if not ws_constants.DEFAULT_CASE_INDEX_KEY in self.dataframe:
            self.dataframe[ws_constants.DEFAULT_CASE_INDEX_KEY] = self.grouped_dataframe.ngroup()

    def get_grouped_dataframe(self):
        """
        Returns the grouped dataframe
        Returns
        --------------
        grouped_dataframe
            Grouped dataframe
        """
        self.build_grouped_dataframe()
        return self.grouped_dataframe

    def build_reduced_grouped_dataframe(self):
        """
        Saves the reduced grouped dataframe
        """
        if self.reduced_grouped_dataframe is None:
            reduced_dataframe = self.get_reduced_dataframe()
            self.reduced_grouped_dataframe = reduced_dataframe.groupby(CASE_CONCEPT_NAME)

    def get_reduced_grouped_dataframe(self):
        """
        Returns the reduced grouped dataframe
        Returns
        ----------------
        reduced_grouped_dataframe
            Reduced grouped dataframe
        """
        self.build_reduced_grouped_dataframe()
        return self.reduced_grouped_dataframe

    def save_most_common_variant(self, variants_df):
        variants_df["count"] = 1
        variants_df = variants_df.reset_index()
        variants_list = variants_df.groupby("variant").agg(
            {"caseDuration": "mean", "count": "sum"}).reset_index().to_dict('records')
        variants_list = sorted(variants_list, key=lambda x: (x["count"], x["variant"]), reverse=True)
        self.most_common_variant = None
        self.most_common_variant = []
        self.most_common_paths = None
        self.most_common_paths = []
        if variants_list:
            best_var_idx = 0
            for i in range(len(variants_list)):
                if len(variants_list[i]["variant"]) > 1:
                    best_var_idx = i
                    break
            self.most_common_variant = variants_list[best_var_idx]["variant"]
            for i in range(len(self.most_common_variant) - 1):
                self.most_common_paths.append((self.most_common_variant[i], self.most_common_variant[i + 1]))

    def get_most_common_variant(self):
        return self.most_common_variant

    def calculate_variants_number(self):
        """
        Calculate the number of variants in this log
        """
        self.variants_number = self.get_variants_df()["variant"].nunique()

    def calculate_cases_number(self):
        """
        Calculate the number of cases in this log
        """
        self.cases_number = self.dataframe["case:concept:name"].nunique()

    def calculate_events_number(self):
        """
        Calculate the number of events in this log
        """
        self.events_number = len(self.dataframe)

    def get_variants_number(self):
        """
        Returns the number of variants in the log
        Returns
        --------------
        variants_number
            Number of variants in the log
        """
        if self.variants_number == -1:
            self.calculate_variants_number()
        return self.variants_number

    def get_cases_number(self):
        """
        Returns the number of cases in the log
        Returns
        ---------------
        cases_number
            Number of cases in the log
        """
        if self.cases_number == -1:
            self.calculate_cases_number()
        return self.cases_number

    def get_events_number(self):
        """
        Returns the number of events in the log
        Returns
        --------------
        events_number
            Number of events in the log
        """
        if self.events_number == -1:
            self.calculate_events_number()
        return self.events_number

    def get_schema(self, variant=process_schema_factory.DFG_FREQ, parameters=None):
        """
        Gets the process schema in the specified variant and with the specified parameters
        Parameters
        -------------
        variant
            Variant of the algorithm
        parameters
            Parameters of the algorithm
        Returns
        ------------
        schema
            Process schema (in base64)
        model
            Model file possibly describing the process schema
        format
            Format of the process schema (e.g. PNML)
        """
        if parameters is None:
            parameters = {}
        parameters[constants.PARAMETER_CONSTANT_ACTIVITY_KEY] = self.activity_key
        parameters[constants.PARAMETER_CONSTANT_ATTRIBUTE_KEY] = self.activity_key

        if not self.sorted_dataframe_by_case_id:
            self.sort_dataframe_by_case_id()

        if self.most_common_variant is not None:
            parameters[ws_constants.PARAM_MOST_COMMON_VARIANT] = self.most_common_variant
            parameters[ws_constants.PARAM_MOST_COMMON_PATHS] = self.most_common_paths

        parameters[constants.GROUPED_DATAFRAME] = self.get_reduced_grouped_dataframe()

        if self.variants_df is not None:
            parameters["variants_df"] = self.variants_df

        return list(process_schema_factory.apply(self.get_reduced_dataframe(), variant=variant, parameters=parameters)) + [self.get_log_summary_dictio()]

    def get_numeric_attribute_svg(self, attribute, parameters=None):
        """
        Get the SVG of a numeric attribute
        Parameters
        ------------
        attribute
            Attribute
        parameters
            Other possible parameters
        """
        if parameters is None:
            parameters = {}
        parameters[constants.PARAMETER_CONSTANT_ACTIVITY_KEY] = self.activity_key
        parameters[constants.PARAMETER_CONSTANT_ATTRIBUTE_KEY] = self.activity_key
        if self.grouped_dataframe is not None:
            parameters[constants.GROUPED_DATAFRAME] = self.grouped_dataframe

        return numeric_attribute.get_numeric_attribute_distr_svg(self.dataframe, attribute, parameters=parameters)

    def get_median_case_duration(self,parameters=None):
        if parameters is None:
            parameters = {}

        return case_duration.get_median_case_duration(self.get_reduced_dataframe(), parameters=parameters)

    def get_case_duration_svg(self, parameters=None):
        """
        Gets the SVG of the case duration
        Parameters
        ------------
        parameters
            Parameters of the algorithm
        Returns
        -----------
        graph
            Case duration graph (expressed in Base 64)
        """
        if parameters is None:
            parameters = {}
        parameters[constants.PARAMETER_CONSTANT_ACTIVITY_KEY] = self.activity_key
        parameters[constants.PARAMETER_CONSTANT_ATTRIBUTE_KEY] = self.activity_key
        if self.reduced_grouped_dataframe is not None:
            parameters[constants.GROUPED_DATAFRAME] = self.reduced_grouped_dataframe

        return case_duration.get_case_duration_svg(self.get_reduced_dataframe(), parameters=parameters)

    def get_events_per_time_svg(self, parameters=None):
        """
        Gets the SVG of the events per time
        Parameters
        -------------
        parameters
            Parameters of the algorithm
        Returns
        -------------
        graph
            Events per time graph (expressed in Base 64)
        """
        if parameters is None:
            parameters = {}
        parameters[constants.PARAMETER_CONSTANT_ACTIVITY_KEY] = self.activity_key
        parameters[constants.PARAMETER_CONSTANT_ATTRIBUTE_KEY] = self.activity_key
        if self.reduced_grouped_dataframe is not None:
            parameters[constants.GROUPED_DATAFRAME] = self.reduced_grouped_dataframe

        return events_per_time.get_events_per_time_svg(self.get_reduced_dataframe(), parameters=parameters)

    def get_variant_statistics(self, parameters=None):
        """
        Gets the variants of the given log
        Parameters
        --------------
        parameters
            Parameters of the algorithm
        Returns
        --------------
        variants
            Variants of the log
        """
        if parameters is None:
            parameters = {}
        max_no_variants = parameters[
            "max_no_variants"] if "max_no_variants" in parameters else ws_constants.MAX_NO_VARIANTS_TO_RETURN
        parameters[constants.PARAMETER_CONSTANT_ACTIVITY_KEY] = self.activity_key
        parameters[constants.PARAMETER_CONSTANT_ATTRIBUTE_KEY] = self.activity_key
        if self.reduced_grouped_dataframe is not None:
            parameters[constants.GROUPED_DATAFRAME] = self.reduced_grouped_dataframe
        if self.variants_df is not None:
            parameters["variants_df"] = self.get_variants_df()
        variants_stats = variants.get_statistics(self.get_reduced_dataframe(), parameters=parameters)
        variants_stats = variants_stats[0:min(len(variants_stats), max_no_variants)]

        return [variants_stats] + [self.get_log_summary_dictio()]

    def get_sna(self, variant="handover", parameters=None):
        """
        Gets a Social Network representation from a given log
        Parameters
        -------------
        variant
            Variant of the algorithm (metric to use)
        parameters
            Parameters of the algorithm (e.g. arc threshold)
        Returns
        ------------
        sna
            SNA representation
        """
        if parameters is None:
            parameters = {}
        parameters[constants.PARAMETER_CONSTANT_ACTIVITY_KEY] = self.activity_key
        parameters[constants.PARAMETER_CONSTANT_ATTRIBUTE_KEY] = self.activity_key
        if not self.grouped_dataframe is None:
            parameters[constants.GROUPED_DATAFRAME] = self.grouped_dataframe

        return sna_obtainer.apply(self.dataframe, variant=variant, parameters=parameters)

    def get_transient(self, delay, parameters=None):
        """
        Perform CTMC simulation on a dataframe
        Parameters
        -------------
        delay
            Delay
        parameters
            Possible parameters of the algorithm
        Returns
        -------------
        graph
            Case duration graph
        """
        if parameters is None:
            parameters = {}
        parameters[constants.PARAMETER_CONSTANT_ACTIVITY_KEY] = self.activity_key
        parameters[constants.PARAMETER_CONSTANT_ATTRIBUTE_KEY] = self.activity_key
        if self.reduced_grouped_dataframe is not None:
            parameters[constants.GROUPED_DATAFRAME] = self.reduced_grouped_dataframe

        return transient.apply(self.get_reduced_dataframe(), delay, parameters=parameters)

    def get_case_statistics(self, parameters=None):
        """
        Gets the statistics on cases
        Parameters
        -------------
        parameters
            Possible parameters of the algorithm
        Returns
        -------------
        list_cases
            List of cases
        """
        if parameters is None:
            parameters = {}
        parameters[constants.PARAMETER_CONSTANT_ACTIVITY_KEY] = self.activity_key
        parameters[constants.PARAMETER_CONSTANT_ATTRIBUTE_KEY] = self.activity_key
        if self.reduced_grouped_dataframe is not None:
            parameters[constants.GROUPED_DATAFRAME] = self.reduced_grouped_dataframe
        # parameters["max_ret_cases"] = ws_constants.MAX_NO_CASES_TO_RETURN
        parameters["sort_by_column"] = parameters[
            "sort_by_column"] if "sort_by_column" in parameters else "caseDuration"
        parameters["sort_ascending"] = parameters["sort_ascending"] if "sort_ascending" in parameters else False

        if "variant" in parameters:
            var_to_filter = parameters["variant"]
            # TODO: TECHNICAL DEBT
            # quick turnaround for bug
            var_to_filter = var_to_filter.replace(" start", "+start")
            var_to_filter = var_to_filter.replace(" START", "+START")
            var_to_filter = var_to_filter.replace(" complete", "+complete")
            var_to_filter = var_to_filter.replace(" COMPLETE", "+COMPLETE")

            filtered_dataframe = variants_filter.apply(self.get_reduced_dataframe(), [var_to_filter],
                                                       parameters=parameters)
            return [casestats.include_key_in_value_list(
                case_statistics.get_cases_description(filtered_dataframe, parameters=parameters))] + [self.get_log_summary_dictio()]
        else:
            return [casestats.include_key_in_value_list(
                case_statistics.get_cases_description(self.get_reduced_dataframe(), parameters=parameters))] + [self.get_log_summary_dictio()]

    def get_events(self, caseid, parameters=None):
        """
        Gets the events of a case
        Parameters
        -------------
        caseid
            Case ID
        parameters
            Parameters of the algorithm
        Returns
        ------------
        list_events
            Events belonging to the case
        """
        if parameters is None:
            parameters = {}
        parameters[constants.PARAMETER_CONSTANT_ACTIVITY_KEY] = self.activity_key
        parameters[constants.PARAMETER_CONSTANT_ATTRIBUTE_KEY] = self.activity_key
        if not self.grouped_dataframe is None:
            parameters[constants.GROUPED_DATAFRAME] = self.grouped_dataframe
        return case_statistics.get_events(self.dataframe, caseid, parameters=parameters)

    def download_xes_log(self):
        """
        Downloads the XES log as string
        """
        return etree_xes_exp.export_log_as_string(conv_factory.apply(self.dataframe))

    def download_csv_log(self):
        """
        Downloads the CSV log as string
        """
        return self.dataframe.to_string()

    def get_start_activities(self, parameters=None):
        """
        Gets the start activities from the log
        Returns
        ------------
        start_activities_dict
            Dictionary of start activities
        """
        if parameters is None:
            parameters = {}
        parameters[constants.PARAMETER_CONSTANT_ACTIVITY_KEY] = self.activity_key
        parameters[constants.PARAMETER_CONSTANT_ATTRIBUTE_KEY] = self.activity_key
        if self.reduced_grouped_dataframe is not None:
            parameters[constants.GROUPED_DATAFRAME] = self.reduced_grouped_dataframe

        return start_activities_filter.get_start_activities(self.get_reduced_dataframe(), parameters=parameters)

    def get_end_activities(self, parameters=None):
        """
        Gets the end activities from the log
        Returns
        -------------
        end_activities_dict
            Dictionary of end activities
        """
        if parameters is None:
            parameters = {}
        parameters[constants.PARAMETER_CONSTANT_ACTIVITY_KEY] = self.activity_key
        parameters[constants.PARAMETER_CONSTANT_ATTRIBUTE_KEY] = self.activity_key
        if self.reduced_grouped_dataframe is not None:
            parameters[constants.GROUPED_DATAFRAME] = self.reduced_grouped_dataframe

        return end_activities_filter.get_end_activities(self.get_reduced_dataframe(), parameters=parameters)

    def get_attributes_list(self, parameters=None):
        """
        Gets the attributes list from the log
        Returns
        -------------
        attributes_list
            List of attributes
        """
        return list(self.dataframe.columns)

    def get_attribute_values(self, attribute_key, parameters=None):
        """
        Gets the attribute values from the log
        Returns
        -------------
        attribute_values
            List of values
        """
        if parameters is None:
            parameters = {}
        parameters[constants.PARAMETER_CONSTANT_ACTIVITY_KEY] = self.activity_key
        parameters[constants.PARAMETER_CONSTANT_ATTRIBUTE_KEY] = self.activity_key
        if not self.grouped_dataframe is None:
            parameters[constants.GROUPED_DATAFRAME] = self.grouped_dataframe

        initial_dict = attributes_filter.get_attribute_values(self.dataframe, attribute_key, parameters=parameters)
        return_dict = {}
        for key in initial_dict:
            return_dict[str(key)] = int(initial_dict[key])
        return return_dict

    def get_paths(self, attribute_key,measure='frequency', parameters=None):
        """
        Gets the paths from the log
        Parameters
        -------------
        attribute_key
            Attribute key
        measure
            frequency/performance
        Returns
        -------------
        paths
            List of paths
        """
        if parameters is None:
            parameters = {}

        dfg = df_statistics.get_dfg_graph(self.dataframe, activity_key=attribute_key, measure= measure,
                                          timestamp_key=DEFAULT_TIMESTAMP_KEY,
                                          case_id_glue=CASE_CONCEPT_NAME, sort_caseid_required=False,
                                          sort_timestamp_along_case_id=False)
        return dfg

    def get_alignments(self, petri_string, parameters=None):
        """
        Gets the alignments from a string
        Parameters
        -------------
        petri_string
            Petri string
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
        parameters[constants.PARAMETER_CONSTANT_ACTIVITY_KEY] = self.activity_key
        parameters[constants.PARAMETER_CONSTANT_ATTRIBUTE_KEY] = self.activity_key
        if self.reduced_grouped_dataframe is not None:
            parameters[constants.GROUPED_DATAFRAME] = self.reduced_grouped_dataframe

        return get_align.perform_alignments(self.get_reduced_dataframe(), petri_string, parameters=parameters)

    def get_events_for_dotted(self, attributes):
        """
        Get the events (for the dotted chart) with the corresponding list of attributes
        Parameters
        --------------
        attributes
            List of attributes to return
        Returns
        --------------
        attributes
            List of attributes
        """
        self.sort_dataframe_basilar()
        self.insert_case_number_in_grouped_df()

        attributes = [ws_constants.DEFAULT_EVENT_INDEX_KEY] + attributes
        attributes1 = list(set(attributes))
        attributes2 = list(set([ws_constants.DEFAULT_CASE_INDEX_KEY] + attributes))

        df2 = self.dataframe[attributes2].dropna()
        df2_len = len(df2)
        number_partitions = math.ceil(float(df2_len)/float(ws_constants.MAX_NO_EVENTS_PER_DOTTED))
        if number_partitions > 1:
            df2["@@dotted_grouped"] = df2.groupby(ws_constants.DEFAULT_CASE_INDEX_KEY).ngroup()
            df2["@@partition"] = df2["@@dotted_grouped"] % number_partitions
            df2 = df2[df2["@@partition"] == 0]
        df2 = df2[attributes1]
        stream = df2.to_dict('r')
        stream = sorted(stream, key=lambda x: (x[attributes[2]], x[attributes[1]], x[attributes[0]]))
        third_unique_values = []
        if len(attributes) > 3:
            third_unique_values = sorted(list(set(s[attributes[3]] for s in stream)))
        types = {}
        if stream:
            for attr in attributes:
                val = stream[0][attr]
                types[attr] = str(type(val))
                if type(val) is pd._libs.tslibs.timestamps.Timestamp:
                    for ev in stream:
                        ev[attr] = ev[attr].timestamp()
        traces = []
        if third_unique_values:
            for index, v in enumerate(third_unique_values):
                traces.append({})
                for index2, attr in enumerate(attributes):
                    if index2 < len(attributes) - 1:
                        traces[-1][attr] = [s[attr] for s in stream if s[attributes[3]] == v]
        else:
            third_unique_values.append("UNIQUE")
            traces.append({})
            for index2, attr in enumerate(attributes):
                traces[-1][attr] = [s[attr] for s in stream]
        return traces, types, attributes, third_unique_values

    def get_spec_event_by_idx(self, ev_idx):
        """
        Gets a specific event by its index
        Parameters
        --------------
        ev_idx
            Event index
        Returns
        --------------
        event
            Specific event
        """
        event = self.dataframe[self.dataframe[ws_constants.DEFAULT_EVENT_INDEX_KEY] == ev_idx]
        ret = event.to_dict('r')[0]
        keys = list(ret.keys())
        for key in keys:
            if str(ret[key]).lower() == "nan" or str(ret[key]).lower() == "nat":
                del ret[key]
        return ret

    def get_log_summary_dictio(self):
        this_variants_number = self.get_variants_number()
        this_cases_number = self.get_cases_number()
        this_events_number = self.get_events_number()
        ancestor_variants_number = self.first_ancestor.get_variants_number()
        ancestor_cases_number = self.first_ancestor.get_cases_number()
        ancestor_events_number = self.first_ancestor.get_events_number()

        dictio = {"this_variants_number": this_variants_number, "this_cases_number": this_cases_number,
                  "this_events_number": this_events_number, "ancestor_variants_number": ancestor_variants_number,
                  "ancestor_cases_number": ancestor_cases_number, "ancestor_events_number": ancestor_events_number}

        return dictio