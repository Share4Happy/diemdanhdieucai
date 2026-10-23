from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def clean_email(cls, v: str) -> str:
        if isinstance(v, str):
            return "".join(v.strip().split()).lower()
        return v

    @field_validator("password", mode="before")
    @classmethod
    def clean_password(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip()
        return v


class ForgotPasswordRequest(BaseModel):
    email: str

    @field_validator("email", mode="before")
    @classmethod
    def clean_email(cls, v: str) -> str:
        if isinstance(v, str):
            return "".join(v.strip().split()).lower()
        return v


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(min_length=8)

    @field_validator("password", mode="before")
    @classmethod
    def clean_password(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip()
        return v


class UserCreateRequest(BaseModel):
    email: str
    full_name: str = ""
    password: str = Field(min_length=8)
    role: str = "staff"

    @field_validator("email", mode="before")
    @classmethod
    def clean_email(cls, v: str) -> str:
        if isinstance(v, str):
            return "".join(v.strip().split()).lower()
        return v

    @field_validator("password", mode="before")
    @classmethod
    def clean_password(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip()
        return v


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
