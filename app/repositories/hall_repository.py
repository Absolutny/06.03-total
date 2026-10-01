from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Hall


class HallRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, hall_id: int) -> Hall | None:
        return self.db.get(Hall, hall_id)

    def get_by_name(self, name: str) -> Hall | None:
        return self.db.scalar(select(Hall).where(Hall.name == name))

    def list_all(self) -> list[Hall]:
        return list(self.db.scalars(select(Hall).order_by(Hall.name)))

    def add(self, hall: Hall) -> Hall:
        self.db.add(hall)
        self.db.flush()
        return hall
