from api.log_manager.versions.basic_log_manager import BasicLogSessionHandler
from api.log_manager.versions.multinode_file_based import MultiNodeSessionHandler


BASIC_LOG_SESSION_HANDLING = "basic_log_session_handling"
MULTINODE_FILE_BASED = "multinode_file_based"

VERSIONS = {BASIC_LOG_SESSION_HANDLING: BasicLogSessionHandler,
            MULTINODE_FILE_BASED: MultiNodeSessionHandler}


def apply(ex, variant=BASIC_LOG_SESSION_HANDLING):
    """
    Gets the session handler according to the variant
    Parameters
    -----------
    ex
        Exception handler
    variant
        Variant
    Returns
    -----------
    session_handler
        Session handler
    """
    return VERSIONS[variant](ex)