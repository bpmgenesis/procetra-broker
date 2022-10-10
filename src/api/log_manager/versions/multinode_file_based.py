import sqlite3

from procetraconfiguration import configuration as Configuration
from api.handlers.parquet.parquet import ParquetHandler
# from api.handlers.xes.xes import XesHandler
from api.log_manager.interface.log_manager import LogHandler
from pm4py.objects.log.exporter.xes import exporter as xes_exporter
# from pm4py.objects.log.exporter.parquet import factory as parquet_exporter

import time
import os


def singleton(class_):
    instances = {}
    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]
    return getinstance

@singleton
class MultiNodeSessionHandler(LogHandler):
    def __init__(self, ex):
        # path to the database
        self.database_path = Configuration.event_log_db_path

        self.logs_correspondence = {}

        self.objects_memory = {}
        self.objects_timestamp = {}

        self.user_management = None

        conn_logs = sqlite3.connect(self.database_path)
        curs_logs = conn_logs.cursor()
        curs_logs.execute("DELETE FROM EVENT_LOGS WHERE IS_TEMPORARY = 1")
        conn_logs.commit()

        self.load_log_correspondence()

        LogHandler.__init__(self, ex)

    def load_log_correspondence(self):
        """
        Loads the log reference in the database
        """
        conn_logs = sqlite3.connect(self.database_path)
        curs_logs = conn_logs.cursor()

        curs_logs.execute("SELECT LOG_NAME, LOG_PATH FROM EVENT_LOGS")

        logs_corr = {}

        for res in curs_logs.fetchall():
            logs_corr[res[0]] = res[1]

        self.logs_correspondence = logs_corr

    def load_temp_log_if_it_is_there(self, log_name, session, parameters=None):
        """
        Load a log associated to a session if it exists in the temp logs folder
        Parameters
        --------------
        log_name
            Log name
        session
            Session ID
        parameters
            Possible parameters of the algorithm
        """
        if parameters is None:
            parameters = {}
        force_reload = parameters["force_reload"] if "force_reload" in parameters else False
        if force_reload:
            return None

        handler = None
        file_path = self.logs_correspondence[log_name]
        is_parquet = False
        extension = "xes"
        if file_path.endswith(".parquet") or file_path.endswith(".csv"):
            is_parquet = True
            extension = "parquet"
        temp_log_path = os.path.join(Configuration.temp_logs_path, str(log_name)+"_"+str(session)+"."+extension)
        if os.path.exists(temp_log_path):
            if is_parquet:
                handler = ParquetHandler(is_lazy=True)
                handler.build_from_path(temp_log_path)
            else:
                handler = XesHandler()
                handler.build_from_path(temp_log_path)
        return handler

    def load_log_on_request(self, log_name):
        """
        Loads an event log on request
        Parameters
        ------------
        log_path
            Log name
        """
        handler = None
        file_path = self.logs_correspondence[log_name]

        if file_path.endswith(".parquet"):
            handler = ParquetHandler(is_lazy=True)
            handler.build_from_path(file_path)
        elif file_path.endswith(".csv"):
            handler = ParquetHandler(is_lazy=True)
            handler.build_from_csv(file_path)
        elif file_path.endswith(".xes") or file_path.endswith(".xes.gz"):
            handler = XesHandler()
            handler.build_from_path(file_path)
        return handler

    def set_user_management(self, um):
        """
        Sets the user management
        Parameters
        ------------
        um
            User management
        """
        self.user_management = um

    def remove_unneeded_sessions(self, all_sessions):
        """
        Remove expired sessions
        Parameters
        ------------
        all_sessions
            All valid sessions
        """
        # shk = list(self.session_handlers.keys())
        # for session in shk:
        #    if session not in all_sessions and (not str(session) == "null" and not str(session) == "None"):
        #        print("removing handler for " + str(session))
        #        del self.session_handlers[session]

        pass

    def get_handlers(self):
        """
        Gets the current set of handlers
        Returns
        -----------
        handlers
            Handlers
        """
        self.load_log_correspondence()
        return self.logs_correspondence

    def get_handler_for_process_and_session(self, process, session, parameters=None):
        """
        Gets an handler for a given process and session
        Parameters
        -------------
        process
            Process
        session
            Session
        parameters
            Possible parameters of the algorithm
        Returns
        -------------
        handler
            Handler
        """
        self.load_log_correspondence()
        if process in self.logs_correspondence:
            handler = self.load_temp_log_if_it_is_there(process, session, parameters=parameters)
            if handler is not None:
                return handler
            handler = self.load_log_on_request(process)
            return handler
        return None

    def set_handler_for_process_and_session(self, process, session, handler):
        """
        Sets the handler for the current process and session
        Parameters
        -------------
        process
            Process
        session
            Session
        handler
            Handler
        """
        self.load_log_correspondence()
        if process in self.logs_correspondence:
            if type(handler) is ParquetHandler:
                df = handler.dataframe
                target_path = os.path.join(Configuration.temp_logs_path, str(process)+"_"+str(session)+".parquet")
                # parquet_exporter.export_df(df, target_path)
            elif type(handler) is XesHandler:
                log = handler.log
                target_path = os.path.join(Configuration.temp_logs_path, str(process)+"_"+str(session)+".xes")
                xes_exporter.export_log(log, target_path)

    def check_is_admin(self, user):
        """
        Checks if the user is an administrator
        Parameters
        -------------
        user
            User
        Returns
        -------------
        boolean
            Boolean value
        """
        if Configuration.enable_session:
            conn_logs = sqlite3.connect(self.database_path)
            curs_logs = conn_logs.cursor()
            curs_logs.execute("SELECT USER_ID FROM ADMINS WHERE USER_ID = ? AND USER_ID = ?", (user, user))
            results = curs_logs.fetchone()
            if results is not None:
                return True
            return False
        return True

    def manage_upload(self, user, basename, filepath, is_temporary=False):
        """
        Manages an event log that is uploaded
        Parameters
        ------------
        user
            Current user
        basename
            Name of the log
        filepath
            Log path
        """
        conn_logs = sqlite3.connect(self.database_path)
        curs_logs = conn_logs.cursor()
        if is_temporary:
            curs_logs.execute("INSERT INTO EVENT_LOGS VALUES (?,?,1,0,1)", (basename, filepath))
        else:
            curs_logs.execute("INSERT INTO EVENT_LOGS VALUES (?,?,0,1,1)", (basename, filepath))
        curs_logs.execute("INSERT INTO USER_LOG_VISIBILITY VALUES (?,?)", (user, basename))
        curs_logs.execute("INSERT INTO USER_LOG_DOWNLOADABLE VALUES (?,?)", (user, basename))
        curs_logs.execute("INSERT INTO USER_LOG_REMOVAL VALUES (?,?)", (user, basename))
        conn_logs.commit()
        conn_logs.close()

    def check_user_log_visibility(self, user, process):
        """
        Checks if the user has visibility on the given process
        Parameters
        -------------
        user
            User
        process
            Process
        """
        if Configuration.enable_session:
            conn_logs = sqlite3.connect(self.database_path)
            curs_logs = conn_logs.cursor()
            curs_logs.execute("SELECT USER_ID FROM USER_LOG_VISIBILITY WHERE USER_ID = ? AND LOG_NAME = ?",
                              (user, process))
            results = curs_logs.fetchone()
            if results is not None:
                return True
            return self.check_is_admin(user)
        return True

    def check_user_enabled_upload(self, user):
        """
        Checks if the user is enabled to upload a log
        Parameters
        ------------
        user
            User
        Returns
        ------------
        boolean
            Boolean value
        """
        if Configuration.enable_session:
            conn_logs = sqlite3.connect(self.database_path)
            curs_logs = conn_logs.cursor()
            curs_logs.execute("SELECT USER_ID FROM USER_UPLOADABLE WHERE USER_ID = ? AND USER_ID = ?", (user, user))
            results = curs_logs.fetchone()
            if results is not None:
                return True
            return self.check_is_admin(user)
        return True

    def check_user_enabled_download(self, user, process):
        """
        Checks if the user is enabled to download a log
        Parameters
        ------------
        user
            User
        process
            Process
        Returns
        ------------
        boolean
            Boolean value
        """
        if Configuration.enable_session:
            conn_logs = sqlite3.connect(self.database_path)
            curs_logs = conn_logs.cursor()
            curs_logs.execute("SELECT USER_ID FROM USER_LOG_DOWNLOADABLE WHERE USER_ID = ? AND LOG_NAME = ?",
                              (user, process))
            results = curs_logs.fetchone()
            if results is not None:
                return True
            return self.check_is_admin(user)
        return True

    def load_log_static(self, log_name, file_path, parameters=None):
        pass

    def save_object_memory(self, key, value):
        """
        Saves an object into the objects memory
        Parameters
        ------------
        key
            Key
        value
            Value
        """
        self.objects_memory[key] = value
        self.objects_timestamp[key] = time.time()

    def get_object_memory(self, key):
        """
        Gets an object from the objects memory
        Parameters
        ------------
        key
            Key
        value
            Value
        """
        if key in self.objects_memory:
            return self.objects_memory[key]
        return None

    def get_user_eventlog_vis_down_remov(self):
        conn_logs = sqlite3.connect(self.database_path)
        curs_logs = conn_logs.cursor()

        users = self.user_management.get_all_users()

        admin_list = []
        user_log_vis = {}
        all_logs = set()

        cur = curs_logs.execute("SELECT LOG_NAME, LOG_NAME FROM EVENT_LOGS")
        for res in cur.fetchall():
            all_logs.add(str(res[0]))

        cur = curs_logs.execute("SELECT USER_ID, USER_ID FROM ADMINS")
        for res in cur.fetchall():
            admin_list.append(str(res[0]))

        for user in users:
            if user not in user_log_vis:
                user_log_vis[user] = {}

        cur = curs_logs.execute("SELECT USER_ID, USER_ID FROM OTHER_USERS")
        for res in cur.fetchall():
            user = str(res[0])
            if user not in user_log_vis:
                user_log_vis[user] = {}

        cur = curs_logs.execute("SELECT USER_ID, LOG_NAME FROM USER_LOG_VISIBILITY")
        for res in cur.fetchall():
            user = str(res[0])
            log = str(res[1])
            if user not in user_log_vis:
                user_log_vis[user] = {}
            if log not in user_log_vis[user]:
                user_log_vis[user][log] = {"visibility": False, "downloadable": False, "removable": False}
            user_log_vis[user][log]["visibility"] = True

        cur = curs_logs.execute("SELECT USER_ID, LOG_NAME FROM USER_LOG_DOWNLOADABLE")
        for res in cur.fetchall():
            user = str(res[0])
            log = str(res[1])
            if user not in user_log_vis:
                user_log_vis[user] = {}
            if log not in user_log_vis[user]:
                user_log_vis[user][log] = {"visibility": False, "downloadable": False, "removable": False}
            user_log_vis[user][log]["downloadable"] = True

        cur = curs_logs.execute("SELECT USER_ID, LOG_NAME FROM USER_LOG_REMOVAL")
        for res in cur.fetchall():
            user = str(res[0])
            log = str(res[1])
            if user not in user_log_vis:
                user_log_vis[user] = {}
            if log not in user_log_vis[user]:
                user_log_vis[user][log] = {"visibility": False, "downloadable": False, "removable": False}
            user_log_vis[user][log]["removable"] = True

        # remove admins
        for adm in admin_list:
            if adm in user_log_vis:
                del user_log_vis[adm]

        for user in user_log_vis:
            for log in all_logs:
                if log not in user_log_vis[user]:
                    user_log_vis[user][log] = {"visibility": False, "downloadable": False, "removable": False}

        sorted_users = sorted(list(user_log_vis.keys()))
        sorted_logs = sorted(list(all_logs))

        conn_logs.close()

        return sorted_users, sorted_logs, user_log_vis

    def add_user_eventlog_visibility(self, user, event_log):
        print("start add_user_eventlog_visibility " + str(user) + " " + str(event_log))
        conn_logs = sqlite3.connect(self.database_path)
        curs_logs = conn_logs.cursor()

        curs_logs.execute("DELETE FROM USER_LOG_VISIBILITY WHERE USER_ID = ? AND LOG_NAME = ?", (user, event_log))
        curs_logs.execute("INSERT INTO USER_LOG_VISIBILITY VALUES (?,?)", (user, event_log))

        conn_logs.commit()
        conn_logs.close()

        print("end add_user_eventlog_visibility " + str(user) + " " + str(event_log))

    def remove_user_eventlog_visibility(self, user, event_log):
        print("start remove_user_eventlog_visibility " + str(user) + " " + str(event_log))
        conn_logs = sqlite3.connect(self.database_path)
        curs_logs = conn_logs.cursor()

        curs_logs.execute("DELETE FROM USER_LOG_VISIBILITY WHERE USER_ID = ? AND LOG_NAME = ?", (user, event_log))

        conn_logs.commit()
        conn_logs.close()
        print("end remove_user_eventlog_visibility " + str(user) + " " + str(event_log))

    def add_user_eventlog_downloadable(self, user, event_log):
        print("start add_user_eventlog_downloadable " + str(user) + " " + str(event_log))
        conn_logs = sqlite3.connect(self.database_path)
        curs_logs = conn_logs.cursor()

        curs_logs.execute("DELETE FROM USER_LOG_DOWNLOADABLE WHERE USER_ID = ? AND LOG_NAME = ?", (user, event_log))
        curs_logs.execute("INSERT INTO USER_LOG_DOWNLOADABLE VALUES (?,?)", (user, event_log))

        conn_logs.commit()
        conn_logs.close()

        print("end add_user_eventlog_downloadable " + str(user) + " " + str(event_log))

    def remove_user_eventlog_downloadable(self, user, event_log):
        print("start remove_user_eventlog_downloadable " + str(user) + " " + str(event_log))
        conn_logs = sqlite3.connect(self.database_path)
        curs_logs = conn_logs.cursor()

        curs_logs.execute("DELETE FROM USER_LOG_DOWNLOADABLE WHERE USER_ID = ? AND LOG_NAME = ?", (user, event_log))

        conn_logs.commit()
        conn_logs.close()

        print("end remove_user_eventlog_downloadable " + str(user) + " " + str(event_log))

    def add_user_eventlog_removable(self, user, event_log):
        print("start add_user_eventlog_removable " + str(user) + " " + str(event_log))
        conn_logs = sqlite3.connect(self.database_path)
        curs_logs = conn_logs.cursor()

        curs_logs.execute("DELETE FROM USER_LOG_REMOVAL WHERE USER_ID = ? AND LOG_NAME = ?", (user, event_log))
        curs_logs.execute("INSERT INTO USER_LOG_REMOVAL VALUES (?,?)", (user, event_log))

        conn_logs.commit()
        conn_logs.close()

        print("end add_user_eventlog_removable " + str(user) + " " + str(event_log))

    def remove_user_eventlog_removable(self, user, event_log):
        print("start remove_user_eventlog_removable " + str(user) + " " + str(event_log))
        conn_logs = sqlite3.connect(self.database_path)
        curs_logs = conn_logs.cursor()

        curs_logs.execute("DELETE FROM USER_LOG_REMOVAL WHERE USER_ID = ? AND LOG_NAME = ?", (user, event_log))

        conn_logs.commit()
        conn_logs.close()

        print("end remove_user_eventlog_removable " + str(user) + " " + str(event_log))

    def check_log_is_removable(self, log):
        res = False
        conn_logs = sqlite3.connect(self.database_path)
        curs_logs = conn_logs.cursor()

        curs_logs.execute("SELECT * FROM EVENT_LOGS WHERE LOG_NAME = ? AND LOG_NAME = ? AND CAN_REMOVED = 1",
                          (log, log))

        cur = curs_logs.fetchall()

        if cur is not None:
            for r in cur:
                res = True
                break

        conn_logs.commit()
        conn_logs.close()

        return res

    def can_delete(self, user, log):
        res = False
        is_admin = self.check_is_admin(user)
        is_removable = self.check_log_is_removable(log)

        if not is_removable:
            return False

        if is_admin:
            res = True

        conn_logs = sqlite3.connect(self.database_path)
        curs_logs = conn_logs.cursor()

        curs_logs.execute("SELECT * FROM USER_LOG_REMOVAL WHERE USER_ID = ? AND LOG_NAME = ?", (user, log))

        cur = curs_logs.fetchall()

        if cur is not None:
            for r in cur:
                res = True
                break

        conn_logs.commit()
        conn_logs.close()

        return res

    def delete_log(self, log):
        conn_logs = sqlite3.connect(self.database_path)
        curs_logs = conn_logs.cursor()

        curs_logs.execute("DELETE FROM EVENT_LOGS WHERE LOG_NAME = ? AND LOG_NAME = ?", (log, log))
        curs_logs.execute("DELETE FROM USER_LOG_VISIBILITY WHERE LOG_NAME = ? AND LOG_NAME = ?", (log, log))
        curs_logs.execute("DELETE FROM USER_LOG_REMOVAL WHERE LOG_NAME = ? AND LOG_NAME = ?", (log, log))
        curs_logs.execute("DELETE FROM USER_LOG_DOWNLOADABLE WHERE LOG_NAME = ? AND LOG_NAME = ?", (log, log))

        conn_logs.commit()
        conn_logs.close()

        del self.logs_correspondence[log]
        for session in self.session_handlers:
            if log in self.session_handlers[session]:
                del self.session_handlers[session][log]