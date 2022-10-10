from api.user_iam import factory as user_iam_factory
from api.requests_logging import factory as logging_factory
from api.log_manager import factory as session_manager_factory
from procetraconfiguration import configuration as Configuration;
from fastapi import Form, HTTPException

ex = logging_factory.apply()
user_manager = user_iam_factory.apply(ex)
session_manager = session_manager_factory.apply(ex, variant=Configuration.log_manager_default_variant)
session_manager.set_user_management(user_manager)


def clean_expired_sessions():
    """
    Cleans expired sessions
    """
    user_manager.clean_expired_sessions()
    sessions = user_manager.get_all_sessions()
    session_manager.remove_unneeded_sessions(sessions)

def check_session_validity(session_id):
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
    if Configuration.enable_session:
        clean_expired_sessions()

        validity = user_manager.check_session_validity(session_id)
        return validity
    return True


def do_login(user, password):
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
    ret = user_manager.do_login(user, password)

    clean_expired_sessions()

    return ret

def get_user_from_session(session_id):
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
    if Configuration.enable_session:
        user = user_manager.get_user_from_session(session_id)
        return user
    return None

def get_user(session_id: str = Form(...)):
    clean_expired_sessions()
    if check_session_validity(session_id):
        user = get_user_from_session(session_id)
        return user
    raise HTTPException(status_code=404, detail= 'Invalid session.')