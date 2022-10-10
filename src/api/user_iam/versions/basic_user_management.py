import uuid
import hashlib
import sqlite3

from api.user_iam.interface.user_management import UserManagement
from procetraconfiguration import configuration as Configuration

def singleton(class_):
    instances = {}
    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]
    return getinstance


@singleton
class BasicUserManagement(UserManagement):
    def __init__(self, ex, parameters=None):
        self.user_db = Configuration.users_db_path
        UserManagement.__init__(self, ex)

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
        conn_users = sqlite3.connect(self.user_db)
        curs_users = conn_users.cursor()
        if Configuration.md5_password_backend and not Configuration.md5_password_frontend:
            password = hashlib.md5(password.encode()).hexdigest()
        curs_users.execute("SELECT USER_ID FROM USERS WHERE USER_ID = ? AND PASSWORD = ?", (user, password))
        results = curs_users.fetchone()
        if results is not None:
            session_id = str(uuid.uuid4())
            curs_users.execute("DELETE FROM SESSIONS WHERE USER_ID = ? AND USER_ID = ?", (user, user))
            curs_users.execute("INSERT INTO SESSIONS VALUES (?,?,DateTime('now'))", (session_id, user))
            conn_users.commit()
            return session_id
        return None

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
        validity = False
        conn_users = sqlite3.connect(self.user_db)
        curs_users = conn_users.cursor()
        sid = str(session_id)
        curs_users.execute("SELECT USER_ID FROM SESSIONS WHERE SESSION_ID = ? AND SESSION_ID = ?", (sid, sid))
        results = curs_users.fetchone()
        if results is not None:
            validity = True
        conn_users.close()
        return validity

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
        user = None
        conn_users = sqlite3.connect(self.user_db)
        curs_users = conn_users.cursor()
        sid = str(session_id)
        curs_users.execute("SELECT USER_ID FROM SESSIONS WHERE SESSION_ID = ? AND SESSION_ID = ?", (sid, sid))
        results = curs_users.fetchone()
        if results is not None:
            user = str(results[0])
        conn_users.close()
        return user

    def clean_expired_sessions(self):
        """
        Cleans the expired sessions in IAM
        """
        conn_users = sqlite3.connect(self.user_db)
        curs_users = conn_users.cursor()

        expired_sessions = []

        curs_users.execute(
            "SELECT SESSION_ID FROM SESSIONS WHERE Cast ((JulianDay(datetime('now')) - JulianDay(CREATION_DATE)) * 24 * 60 * 60 As Integer) >= "+str(
                Configuration.session_duration))
        results = curs_users.fetchall()
        if results is not None:
            for result in results:
                expired_sessions.append(str(result[0]))

        if expired_sessions:
            curs_users.execute(
                "DELETE FROM SESSIONS WHERE Cast ((JulianDay(datetime('now')) - JulianDay(CREATION_DATE)) * 24 * 60 * 60 As Integer) >= " + str(
                    Configuration.session_duration))
            conn_users.commit()
        else:
            #print("NO EXPIRED")
            pass

        conn_users.close()

    def get_all_sessions(self):
        """
        Gets all sessions from the users database
        Returns
        -----------
        sessions
            List of sessions
        """

        sessions = []
        conn_users = sqlite3.connect(self.user_db)
        curs_users = conn_users.cursor()
        curs_users.execute("SELECT SESSION_ID FROM SESSIONS")
        results = curs_users.fetchall()
        if results is not None:
            for result in results:
                sessions.append(str(result[0]))
        conn_users.close()
        return sessions

    def get_all_users(self):
        """
        Possibly get all the users from the users database
        Returns
        -------------
        users
            List of users
        """

        users = []

        conn_users = sqlite3.connect(self.user_db)
        curs_users = conn_users.cursor()

        cur = curs_users.execute("SELECT USER_ID, USER_ID FROM USERS")

        for res in cur.fetchall():
            users.append(str(res[0]))

        conn_users.close()

        return users