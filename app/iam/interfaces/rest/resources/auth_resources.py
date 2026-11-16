from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.shared.domain.value_objects import Role


class AccessTokenResource(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    role: Role
    # When true, every endpoint but change-password and me answers 403 until it is changed.
    must_change_password: bool


class ChangePasswordResource(BaseModel):
    current_password: str = Field(examples=["Temporal7k"])
    new_password: str = Field(examples=["mi-clave-segura"])


class ForgotPasswordResource(BaseModel):
    email: EmailStr = Field(examples=["admin@bodegarosita.pe"])


class ResetPasswordResource(BaseModel):
    token: str = Field(max_length=100)
    new_password: str = Field(examples=["mi-clave-segura"])


class CurrentUserResource(BaseModel):
    id: int
    username: str
    full_name: str | None
    role: Role
    store_id: int | None
    customer_id: int | None
    must_change_password: bool
