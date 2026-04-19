from pydantic import BaseModel, EmailStr


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    phone: str
    username: str


class UserLoginRequest(BaseModel):
    identifier: str  # email veya kullanıcı adı
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
