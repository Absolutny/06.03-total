from fastapi import APIRouter, Depends, status

from app.api.deps import hall_service
from app.models import User
from app.schemas.hall import HallCreate, HallResponse
from app.security.dependencies import get_current_user, require_staff
from app.services.hall_service import HallService

router = APIRouter(prefix="/api/v1/halls", tags=["Halls"])


@router.get("", response_model=list[HallResponse], summary="Список залов")
def list_halls(_: User = Depends(get_current_user), service: HallService = Depends(hall_service)):
    return service.list_all()


@router.post("", response_model=HallResponse, status_code=status.HTTP_201_CREATED,
             summary="Создать зал (ADMIN/MANAGER)")
def create_hall(data: HallCreate, actor: User = Depends(require_staff), service: HallService = Depends(hall_service)):
    return service.create(data, actor)
