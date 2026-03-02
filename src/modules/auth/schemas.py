from pydantic import BaseModel

class UserRegisterRequest(BaseModel):
    phone: str
    name: str

class UserLoginRequest(BaseModel):
    phone: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
