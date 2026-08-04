from pydantic import BaseModel


class UssdRequest(BaseModel):
    session_id: str
    phone: str
    text: str
    network_code: str | None = None
    service_code: str | None = None


class UssdResponse(BaseModel):
    response: str
    session_id: str
