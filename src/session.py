from network import make_request
import aiohttp
from fastapi import APIRouter, Depends, status, File, UploadFile, Form, HTTPException, Request, Header
import json
from pydantic import BaseModel


class SessionInfo(BaseModel):
    session_id: str
    realm_id: str
    account_id: str
    account_name: str
    tenant_id: str
    tenant_name: str
    is_real_admin: bool
    is_tenant_admin: bool


async def get_session_info(root_url: str, session_id: str):
    form = aiohttp.FormData()
    form.add_field('session_id', session_id)

    resp_data, content_type, status_code_from_service = await make_request(root_url + '/api/GetSessionInfo',
                                                                           'POST', form, {"ticket": session_id})
    my_json = resp_data.decode('utf8');
    response_dict = json.loads(my_json)
    if status_code_from_service == 200:
        return response_dict
    else:
        return None


async def get_session(request: Request, ticket=Header(...)) -> SessionInfo:
    root_url = request.headers.get('origin')
    print('rootUrl', root_url)
    if root_url is None:
        raise Exception('Invalid root url.')
        # root_url = "https://bpmgenesis.com/"
    session_info = await get_session_info(root_url, ticket)
    if session_info is not None:
        si = SessionInfo(session_id=ticket, realm_id=session_info['realm_id'], account_id=session_info['account_id'],
                         account_name=session_info['account_name'],
                         tenant_id=session_info['tenant_id'], tenant_name=session_info['tenant_name'],
                         is_real_admin=session_info['is_real_admin'], is_tenant_admin=session_info['is_tenant_admin'])
        return si
    else:
        raise Exception('Invalid session.')
