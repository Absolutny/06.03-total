from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import RefreshToken


class TokenRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, user_id: int, jti_hash: str, expires_at: datetime) -> None:
        self.db.add(RefreshToken(user_id=user_id, jti_hash=jti_hash, expires_at=expires_at.replace(tzinfo=None)))

    def get_by_hash(self, jti_hash: str) -> RefreshToken | None:
        return self.db.scalar(select(RefreshToken).where(RefreshToken.jti_hash == jti_hash))

    def revoke_all_for_user(self, user_id: int) -> None:
        self.db.execute(update(RefreshToken).where(RefreshToken.user_id == user_id).values(revoked=True))
