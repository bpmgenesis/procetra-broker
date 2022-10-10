from logging import Handler, getLogger
from traceback import print_exc
from api.models import Log
from api.database import get_org_event_db
import requests
import asyncio
import threading
import time
import os

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class DBHandler(Handler):
    backup_logger = None

    def __init__(self, level=0, backup_logger_name=None):
        super().__init__(level)
        if backup_logger_name:
            self.backup_logger = getLogger(backup_logger_name)

    def emit(self, record):
        try:
            message = self.format(record)
            try:
                last_line = message.rsplit('\n', 1)[-1]
            except:
                last_line = None

            try:
                def function_asyc(message):
                    time.sleep(5)

                    url = os.getenv('tracker_url') + "/CreateLog"

                    data = {"message": message}
                    headers = {
                        "apikey": os.getenv('apirealm_token'),
                        "application": "procetra"
                    }

                    response = requests.request("POST", url, headers=headers, data=data, verify=False)

                    status_code = response.status_code
                    print('Log Send')

                print('Log Enter')
                t = threading.Thread(target=function_asyc, args=[message])
                t.start()
                print('Log Exit')

                # db = next(get_org_event_db())
                # new_log = Log(module=record.module,
                #               thread_name=record.threadName,
                #               file_name=record.filename,
                #               func_name=record.funcName,
                #               level_name=record.levelname,
                #               line_no=record.lineno,
                #               process_name=record.processName,
                #               message=message,
                #               last_line=last_line)
                #
                #
                # db.add(new_log)
                # db.commit()
            except:
                if self.backup_logger:
                    try:
                        getattr(self.backup_logger, record.levelname.lower())(record.message)
                    except:
                        print_exc()
                else:
                    print_exc()

        except:
            print_exc()
