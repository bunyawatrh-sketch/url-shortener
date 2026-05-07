import random
import string
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..auth import get_current_user

router = APIRouter(prefix="/api/urls", tags=["URLs"])


def generate_short_code(length: int = 6) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


@router.post("/shorten", response_model=schemas.URLOut, status_code=201)
def shorten_url(
    url_in: schemas.URLCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    short_code = generate_short_code()
    while db.query(models.URL).filter(models.URL.short_code == short_code).first():
        short_code = generate_short_code()

    url = models.URL(
        original_url=str(url_in.original_url),
        short_code=short_code,
        user_id=current_user.id,
    )
    db.add(url)
    db.commit()
    db.refresh(url)
    return url


@router.get("/", response_model=list[schemas.URLOut])
def list_my_urls(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return db.query(models.URL).filter(models.URL.user_id == current_user.id).all()


@router.delete("/{url_id}", status_code=204)
def delete_url(
    url_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    url = db.query(models.URL).filter(
        models.URL.id == url_id, models.URL.user_id == current_user.id
    ).first()
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")
    db.delete(url)
    db.commit()
