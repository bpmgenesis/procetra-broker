from api.requests_logging.versions.basic import BasicLoggingHandler

BASIC_LOGGING_HANDLER = "basic_logging_handler"

VERSIONS = {BASIC_LOGGING_HANDLER: BasicLoggingHandler}


def apply(variant=BASIC_LOGGING_HANDLER):
    """
    Create a logging handler of the given variant
    Parameters
    ------------
    variant
        Variant
    """
    return VERSIONS[variant]()