import re
from pydantic import BaseModel, EmailStr, field_validator

USERNAME_RE = re.compile(r'^[a-z0-9_]+$')


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    phone: str
    username: str

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        if not USERNAME_RE.match(v):
            raise ValueError("Kullanıcı adı yalnızca küçük İngilizce harf, rakam ve alt çizgi içerebilir.")
        return v


class UserLoginRequest(BaseModel):
    identifier: str  # email veya kullanıcı adı
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
