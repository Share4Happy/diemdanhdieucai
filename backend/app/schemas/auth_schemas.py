from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(min_length=8)


class UserCreateRequest(BaseModel):
    email: str
    full_name: str = ""
    password: str = Field(min_length=8)
    role: str = "staff"


class UserUpdateRequest(BaseModel):
    email: str | None = None
    full_name: str | None = None
    password: str | None = None
    role: str | None = None


class UserStatusRequest(BaseModel):
    is_active: bool


class UserPublic(BaseModel):
    id: int
    email: str
    full_name: str | None = ""
    role: str = "staff"
    is_active: bool | None = True

    model_config = {"from_attributes": True}
