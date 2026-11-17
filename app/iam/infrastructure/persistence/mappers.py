from app.iam.domain.model.aggregates.password_reset_token import PasswordResetToken
from app.iam.domain.model.aggregates.user import User
from app.iam.infrastructure.persistence.models import PasswordResetTokenModel, UserModel
from app.shared.domain.value_objects import Role


def to_domain(model: UserModel) -> User:
    return User(
        username=model.username,
        password_hash=model.password_hash,
        role=Role(model.role),
        store_id=model.store_id,
        full_name=model.full_name,
        must_change_password=model.must_change_password,
        is_active=model.is_active,
        password_version=model.password_version,
        id=model.id,
    )


def copy_to_model(user: User, model: UserModel) -> UserModel:
    model.username = user.username
    model.password_hash = user.password_hash
    model.role = user.role.value
    model.store_id = user.store_id
    model.full_name = user.full_name
    model.must_change_password = user.must_change_password
    model.is_active = user.is_active
    model.password_version = user.password_version
    return model


def token_to_domain(model: PasswordResetTokenModel) -> PasswordResetToken:
    return PasswordResetToken(
        user_id=model.user_id,
        token_hash=model.token_hash,
        expires_at=model.expires_at,
        used_at=model.used_at,
        id=model.id,
    )


def token_to_model(token: PasswordResetToken) -> PasswordResetTokenModel:
    return PasswordResetTokenModel(
        user_id=token.user_id,
        token_hash=token.token_hash,
        expires_at=token.expires_at,
        used_at=token.used_at,
    )
