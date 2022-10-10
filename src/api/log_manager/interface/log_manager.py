class LogHandler(object):
    def __init__(self, ex):
        # exception handler
        self.ex = ex

    def set_user_management(self, um):
        """
        Sets the user management
        Parameters
        ------------
        um
            User management
        """
        raise Exception("log_manager set_user_management not implemented!")

    def get_handlers(self):
        """
        Gets the current set of handlers
        Returns
        -----------
        handlers
            Handlers
        """
        raise Exception("log_manager get_handlers not implemented!")

    def remove_unneeded_sessions(self, all_sessions):
        """
        Remove expired sessions
        Parameters
        ------------
        all_sessions
            All valid sessions
        """
        raise Exception("log_manager remove_unneeded_sessions not implemented!")

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
        raise Exception("log_manager get_handler_for_process_and_session not implemented!")

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
        raise Exception("log_manager set_handler_for_process_and_session not implemented!")

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
        raise Exception("log_manager check_is_admin not implemented!")

    def manage_upload(self, user, basename, filepath):
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
        raise Exception("log_manager manage_upload not implemented!")

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
        raise Exception("log_manager check_user_log_visibility not implemented!")

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
        raise Exception("log_manager check_user_enabled_upload not implemented!")

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
        raise Exception("log_manager check_user_enabled_download not implemented!")

    def load_log_static(self, log_name, file_path, parameters=None):
        """
        Loads an event log inside the known handlers
        Parameters
        ------------
        log_name
            Log name
        file_path
            Full path (in the services machine) to the log
        parameters
            Possible parameters
        """
        raise Exception("log_manager load_log_static not implemented!")

    def load_log_from_db(self, log_id: str, parameters=None):
        raise Exception("log_manager load_log_from_db not implemented!")

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
        raise Exception("log_manager save_object_memory not implemented!")

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
        raise Exception("log_manager get_object_memory not implemented!")

    def get_user_eventlog_vis_down_remov(self):
        raise Exception("log_manager get_user_eventlog_vis_down_remov not implemented!")

    def add_user_eventlog_visibility(self, user, event_log):
        raise Exception("log_manager add_user_eventlog_visibility not implemented!")

    def remove_user_eventlog_visibility(self, user, event_log):
        raise Exception("log_manager remove_user_eventlog_visibility not implemented!")

    def add_user_eventlog_downloadable(self, user, event_log):
        raise Exception("log_manager add_user_eventlog_downloadable not implemented!")

    def remove_user_eventlog_downloadable(self, user, event_log):
        raise Exception("log_manager remove_user_eventlog_downloadable not implemented!")

    def add_user_eventlog_removable(self, user, event_log):
        raise Exception("log_manager add_user_eventlog_removable not implemented!")

    def remove_user_eventlog_removable(self, user, event_log):
        raise Exception("log_manager add_user_eventlog_removable not implemented!")

    def check_log_is_removable(self, log):
        raise Exception("log_manager check_log_is_removable not implemented!")

    def can_delete(self, user, log):
        raise Exception("log_manager can_delete not implemented!")