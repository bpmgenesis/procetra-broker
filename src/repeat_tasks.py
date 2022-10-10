from api.repository import project as project_rep, analyse_model as analyse_model_rep, \
    servis_registration as service_registration_rep
from api.database import get_org_event_db
import requests
from requests.structures import CaseInsensitiveDict
import pandas as pd
from pm4py import format_dataframe
from pm4py.objects.log.util import dataframe_utils
from api.database import get_organization_event_data_engine, get_org_event_db
from uuid import UUID, uuid4
from api.repository import event_log
from sqlalchemy.types import Integer, Text, String, DateTime
from logging import basicConfig, getLogger, DEBUG, FileHandler, Formatter
from api.requests_logging.DBHandler import DBHandler

basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%d-%b-%y %H:%M:%S',
            level=DEBUG)
format = Formatter('%(message)s')

backup_logger = getLogger('backup_logger')
file_handler = FileHandler('file.log')
file_handler.setLevel(DEBUG)
file_handler.setFormatter(format)
backup_logger.addHandler(file_handler)

db_logger = getLogger('logger')
db_handler = DBHandler(backup_logger_name='backup_logger')
db_handler.setLevel(DEBUG)
db_handler.setFormatter(format)
db_logger.addHandler(db_handler)


# db_logger.debug('debug: hello world!')
# db_logger.info('info: hello world!')
# db_logger.warning('warning: hello world!')
# db_logger.error('error: hello world!')
# db_logger.critical('critical: hello world!!!!')

def save_log_org(project_id: str, org_name: str, source_df, case_column_name: str, activity_column_name: str,
                 timestamp_key: str,
                 start_timestamp_key: str,
                 sep: str, db):
    engine_event_log = get_organization_event_data_engine(org_name, project_id)

    log_id = save_log(project_id, engine_event_log, source_df, case_column_name, activity_column_name, timestamp_key,
                      start_timestamp_key, sep, db)

    return log_id


def save_log(project_id, engine, source_df, case_column_name: str, activity_column_name: str,
             timestamp_key: str,
             start_timestamp_key: str,
             sep: str, db):
    log_id = str(uuid4())

    event_log.create(log_id, 'Test.csv', case_column_name, activity_column_name, timestamp_key,
                     start_timestamp_key, sep, db)

    source_df.to_sql(
        project_id,
        engine,
        if_exists='replace',
        index=False,
        chunksize=500,
        dtype={
            "case:concept:name": String(),
            "concept:name": String()
        }
    )
    return log_id


def prepare_dataset(source_df, case_column_name: str, activity_column_name: str, timestamp_key: str,
                    start_timestamp_key: str,
                    cost_key: str, resource_key: str):
    case_id = 'case:consept:name';

    case_ids = case_column_name.split(';')

    # case id setting up
    try:
        if len(case_ids) == 1:
            source_df['case:consept:name'] = source_df[case_ids[0]].astype(str)
        elif len(case_ids) == 2:
            source_df['case:consept:name'] = source_df[case_ids[0]].astype(str) + ' - ' + source_df[case_ids[1]].astype(
                str)
    except Exception as e:
        raise Exception("Error occured in setting up case:concept:name")

    # activity key setting up
    try:
        activity_key = 'case:consept';
        activity_keys = activity_column_name.split(';')

        if len(activity_keys) == 1:
            source_df['case:consept'] = source_df[activity_keys[0]].astype(str)
        elif len(activity_keys) == 2:
            source_df['case:consept'] = source_df[activity_keys[0]].astype(str) + ' - ' + source_df[
                activity_keys[1]].astype(str)
    except Exception as e:
        raise Exception("Error occured in setting up case:name")

    # formatting dataset
    source_df = format_dataframe(source_df, case_id=case_id, activity_key=activity_key,
                                 timestamp_key=timestamp_key, start_timestamp_key=start_timestamp_key,
                                 timest_format='%d.%m.%y %H:%M')

    source_df = dataframe_utils.convert_timestamp_columns_in_df(source_df, timest_format='%d.%m.%y %H:%M')

    # rename and convert cost field
    if cost_key is not None:
        if cost_key in source_df.columns:
            source_df = source_df.rename(columns={cost_key: "concept:cost"})
            source_df.to_numeric(source_df['concept:cost'])

    # rename and convert resource field
    if resource_key is not None:
        if resource_key in source_df.columns:
            source_df = source_df.rename(columns={resource_key: "org:resource"})

    #
    return source_df.sort_values('time:timestamp')


def load_csv(
        tenant_id: str,
        project_id: str,
        case_column_name: str,
        activity_column_name: str,
        timestamp_key: str,
        start_timestamp_key: str,
        data) -> pd.DataFrame:
    try:

        df = pd.DataFrame(data)
        df = prepare_dataset(df, case_column_name, activity_column_name, timestamp_key,
                             start_timestamp_key, None, None)

        db = next(get_org_event_db())
        log_id = save_log_org(project_id, tenant_id, df, case_column_name, activity_column_name,
                              timestamp_key,
                              start_timestamp_key, ';', db)

        return df


    except Exception as e:
        raise Exception(str(e))
    return


def get_csp_projects(domain_address, token, language):
    url = domain_address + '/apis/studio/GetProjects'  # "https://dev.bimser.net/apis/studio/GetProjects"

    headers = CaseInsensitiveDict()
    headers["Content-Type"] = "application/json"

    data = f"""
                           {{
                               "domainAddress": "{domain_address}",
                               "token": "{token}",
                               "language": "{language}"
                           }}
                           """

    resp = requests.post(url, headers=headers, data=data)
    result = resp.json()['result']['projects']
    return result


def get_csp_project_flows(project_id, domain_address, token, language):
    url = domain_address + '/apis/studio/GetFlows'  # "https://dev.bimser.net/apis/studio/GetProjects"

    headers = CaseInsensitiveDict()
    headers["Content-Type"] = "application/json"

    data = f"""
                           {{
                               "domainAddress": "{domain_address}",
                               "token": "{token}",
                               "language": "{language}",
                               "ProjectId" :"{project_id}"
                           }}
                           """

    resp = requests.post(url, headers=headers, data=data)
    result = resp.json()['result']['flows']
    return result


def get_csp_project_flows_processes(project_id, flow_id, domain_address, token, language):
    result_list = []
    url = domain_address + '/apis/studio/GetProcesses'  # "https://dev.bimser.net/apis/studio/GetProjects"

    headers = CaseInsensitiveDict()
    headers["Content-Type"] = "application/json"
    requested = 50
    result = 50
    index = 0
    while requested == result:
        data = f"""
                               {{
                                   "domainAddress": "{domain_address}",
                                   "token": "{token}",
                                   "language": "{language}",
                                   "ProjectId" :"{project_id}",
                                   "FlowId" :"{flow_id}",
                                   "loadOptions":{{
                                          "pagination":{{
                                              "skip": {index * 50},
                                              "take": {requested}
                                          }}
                                    
                                      }}
                               }}
                               """
        index += 1
        resp = requests.post(url, headers=headers, data=data)
        try:
            resp_list = resp.json()['result']['processes'];
            result = len(resp_list)
            result_list.extend(resp_list)
        except:
            result = 0
    return result_list


def Task1():
    db = next(get_org_event_db())
    csp_service_registrations = service_registration_rep.get_by_service_name('csp', db)
    for csp_registration in csp_service_registrations:
        db_logger.info(f'CSP Project import started for {csp_registration.realm_name}.')
        try:
            realm_url = csp_registration.realm_url + '/api/GetCspServiceInfos'
            headers = CaseInsensitiveDict()
            resp = requests.post(realm_url, headers=headers)
            tenants = resp.json()
            for tenant in tenants:
                result = get_csp_projects(tenant['domain_address'], tenant['token'], tenant['language'])
                index = 0
                for x in result:
                    index = index + 1
                    project = project_rep.get(csp_registration.realm_name, tenant['tenant_id'], x['id'], db)
                    if project is None:
                        project = project_rep.create(csp_registration.realm_name, tenant_id=tenant['tenant_id'],
                                                     project_id=x['id'],
                                                     project_name=x['name'],
                                                     admin='admin',
                                                     is_public=True,
                                                     case_count=0,
                                                     event_count=0,
                                                     disable_cache=False, project_info={
                                'csp_project_name': x['name'],
                                'csp_project_id': x['id'],
                                'csp_domain': tenant['domain_address']
                            }, db=db)

                        print('Project Created :' + x['name'] + f'  ({index} / {len(result)})')
                    flows = get_csp_project_flows(project.project_id, tenant['domain_address'], tenant['token'],
                                                  tenant['language'])
                    for x in flows:
                        flow = analyse_model_rep.get_analyse_model_by_id(csp_registration.realm_name,
                                                                         tenant['tenant_id'], project.project_id,
                                                                         x['id'],
                                                                         db)
                        if flow is None:
                            analyse_model_rep.create(csp_registration.realm_name, tenant['tenant_id'],
                                                     project.project_id, x['id'], x['name'], db)
                            print('Analyse Model Created :' + x['name'])

        except Exception as e:
            print(str(e))
        finally:
            db.close()
    return


def Task2():
    db = next(get_org_event_db())
    csp_service_registrations = service_registration_rep.get_by_service_name('csp', db)
    for csp_registration in csp_service_registrations:
        db_logger.info('CSP log aktarımı başladı.')
        try:
            realm_url = csp_registration.realm_url + '/api/GetCspServiceInfos'
            headers = CaseInsensitiveDict()
            resp = requests.post(realm_url, headers=headers)
            tenants = resp.json()

            for tenant in tenants:
                result = get_csp_projects(tenant['domain_address'], tenant['token'], tenant['language'])
                for x in result:
                    project = project_rep.get(csp_registration.realm_name, tenant['tenant_id'], x['id'], db)
                    if project is not None:
                        flows = get_csp_project_flows(project.project_id, tenant['domain_address'], tenant['token'],
                                                      tenant['language'])
                        for x in flows:
                            flow = analyse_model_rep.get_analyse_model_by_id(csp_registration.realm_name,
                                                                             tenant['tenant_id'], project.project_id,
                                                                             x['id'],
                                                                             db)
                            if flow is not None:
                                # project.project_id, flow.id,'566251bc-41e0-4094-a75b-9aab2575df93', '6e4cd57f-760d-4762-b008-ad57e0cc8074'
                                processes = get_csp_project_flows_processes(project.project_id, flow.id,
                                                                            tenant['domain_address'], tenant['token'],
                                                                            tenant['language'])
                                log = []
                                for process in processes:
                                    for step in process['steps']:
                                        if step['responseDate'] is not None:
                                            log.append({
                                                'case:concept:name': process['processId'],
                                                'concept:name': step['stepName'],
                                                'start:time:timestamp': step['requestDate'],
                                                'time:timestamp': step['responseDate']
                                            })
                                if len(log) > 0:  # Event data found
                                    df = load_csv(tenant['tenant_id'], project.project_id, 'case:concept:name',
                                                  'concept:name',
                                                  'time:timestamp', 'start:time:timestamp', log)
                                    case_count = len(df['case:concept:name'].unique())
                                    event_count = len(df['concept:name'])

                                    project = project_rep.get(csp_registration.realm_name, tenant['tenant_id'],
                                                              project.project_id, db)
                                    if project is not None:
                                        project.case_count = case_count
                                        project.event_count = event_count
                                        project.is_data_loaded = True
                                        db.commit()
                                else:  # event data not found
                                    project = project_rep.get(csp_registration.realm_name, tenant['tenant_id'],
                                                              project.project_id, db)
                                    project.is_data_loaded = False
                                    db.commit()

                db.close()
        except Exception as e:
            print(str(e))
        finally:
            db.close()
    return
