from fastapi import APIRouter, Depends, status, File, UploadFile, Form, Response
from api.schemas import SessionData
from uuid import UUID, uuid4
from api.session import backend, cookie, verifier

router = APIRouter(
    prefix="/session",
    tags=['Session']
)


@router.post("/create_session/{name}")
async def create_session(name: str, response: Response):

    session = uuid4()
    data = SessionData(username=name)

    await backend.create(session, data)
    cookie.attach_to_response(response, session)

    # return f"created session for {name}"
    return str(session)


@router.get("/whoami", dependencies=[Depends(cookie)])
async def whoami(session_data: SessionData = Depends(verifier)):
    print(session_data)
    return session_data


@router.post("/delete_session")
async def del_session(response: Response, session_id: UUID = Depends(cookie)):
    await backend.delete(session_id)
    cookie.delete_from_response(response)
    return "deleted session"