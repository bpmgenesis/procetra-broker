from api.user_iam.versions.basic_user_management import BasicUserManagement

BASIC_USER_MANAGEMENT = "basic_user_management"
KEYCLOAK_USER_MANAGEMENT = "keycloak_user_management"

VERSIONS = {BASIC_USER_MANAGEMENT: BasicUserManagement}


def apply(ex, variant=BASIC_USER_MANAGEMENT, parameters=None):
    """
    Gets the user manager according to the variant
    Parameters
    -----------
    ex
        Exception handler
    variant
        Variant
    Returns
    -----------
    user_manager
        User manager
    """
    return VERSIONS[variant](ex, parameters=parameters)