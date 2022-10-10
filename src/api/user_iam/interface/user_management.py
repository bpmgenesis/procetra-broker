

class UserManagement(object):
    def __init__(self, ex):
        # saves the exception handler
        self.ex = ex

    def do_login(self, user, password):
        """
        Logs in a user and returns a session id
        Parameters
        ------------
        user
            Username
        password
            Password
        Returns
        ------------
        session_id
            Session ID
        """
        raise Exception("user_management do_login not implemented!")

    def check_session_validity(self, session_id):
        """
        Checks the validity of a session
        Parameters
        ------------
        session_id
            Session ID
        Returns
        ------------
        boolean
            Boolean value
        """
        raise Exception("user_management check_session_validity not implemented!")

    def clean_expired_sessions(self):
        """
        Cleans the expired sessions in IAM
        """
        raise Exception("user_management clean_expired_sessions not implemented!")

    def get_user_from_session(self, session_id):
        """
        Gets the user from the session
        Parameters
        ------------
        session_id
            Session ID
        Returns
        ------------
        user
            User ID
        """
        raise Exception("user_management get_user_from_session not implemented!")

    def get_all_sessions(self):
        """
        Gets all sessions from the users database
        Returns
        -----------
        sessions
            List of sessions
        """

        raise Exception("user_management get_all_sessions not implemented!")

    def get_all_users(self):
        """
        Possibly get all the users from the users database
        Returns
        -------------
        users
            List of users
        """

        raise Exception("user_management get_all_users not implemented!")