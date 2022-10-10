import aiohttp
import async_timeout
import ssl
import certifi

from conf import settings


# import requests
# from requests.structures import CaseInsensitiveDict
#
# url = "https://bpmgenesis.com/broker/realm/v1/LoginService"
#
# headers = CaseInsensitiveDict()
# headers["Content-Type"] = "application/x-www-form-urlencoded"
#
# data = "user=stan&password=0"
#
#
# resp = requests.post(url, headers=headers, data=data, verify = False)

# print(resp.status_code)

async def make_request(
        url: str,
        method: str,
        data: dict = None,
        headers: dict = None
):
    """
    Args:
        url: is the url for one of the in-network services
        method: is the lower version of one of the HTTP methods: GET, POST, PUT, DELETE # noqa
        data: is the payload
        headers: is the header to put additional headers into request
    Returns:
        service result coming / non-blocking http request (coroutine)
        e.g:   {
                    "id": 2,
                    "username": "baranbartu",
                    "email": "baran@baran.com",
                    "full_name": "Baran Bartu Demirci",
                    "user_type": "baran",
                    "hashed_password": "***",
                    "created_by": 1
                }
    """
    if not data:
        data = {}

    ssl_context = ssl.create_default_context(cafile=certifi.where())
    conn = aiohttp.TCPConnector(ssl=ssl_context)
    # trust_env = True
    with async_timeout.timeout(settings.GATEWAY_TIMEOUT):
        async with aiohttp.ClientSession(trust_env=True) as session:
            # request = getattr(session, method)
            if method == 'GET':
                async with session.get(url, verify_ssl = False) as response:
                    res = await response.read()
                    return (res, response.content_type, response.status)
            elif method == 'POST':
                async with session.post(url, data=data, headers=headers, verify_ssl = False) as response:
                    res = await response.read()
                    return (res, response.content_type, response.status)
