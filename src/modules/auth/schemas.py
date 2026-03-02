from pydantic import BaseModel

class UserRegisterRequest(BaseModel):
    phone: str
    name: str

class UserLoginRequest(BaseModel):
    phone: str
