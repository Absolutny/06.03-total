from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.models import Hall, User
from app.repositories.hall_repository import HallRepository
from app.schemas.hall import HallCreate
from app.services.audit_service import AuditService


class HallService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = HallRepository(db)
        self.audit = AuditService(db)

    def list_all(self) -> list[Hall]:
        return self.repo.list_all()

    def create(self, data: HallCreate, actor: User) -> Hall:
        if self.repo.get_by_name(data.name):
            raise ConflictError("Зал с таким названием уже существует")
        hall = self.repo.add(Hall(name=data.name, capacity=data.capacity))
        self.audit.log("HALL_CREATED", f"Создан зал '{hall.name}' ({hall.capacity} мест)", actor.id)
        self.db.commit()
        return hall
