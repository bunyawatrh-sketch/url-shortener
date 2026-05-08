import random
import string
import os
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from datetime import timedelta
from .. import models
from ..database import get_db
from ..auth import (
    hash_password, verify_password, create_access_token,
    SECRET_KEY, ALGORITHM,
)
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(tags=["User"])
templates = Jinja2Templates(directory="app/templates")


def get_base_url(request: Request) -> str:
    base = os.getenv("BASE_URL", "").strip()
    if base:
        return base
    return str(request.base_url).rstrip("/")


def get_user_from_cookie(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("user_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            return None
        return db.query(models.User).filter(models.User.username == username).first()
    except JWTError:
        return None


def generate_short_code(length: int = 6) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


# -------- Root / Login / Register --------

@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookie(request, db)
    if user:
        return RedirectResponse(url="/dashboard")
    return RedirectResponse(url="/login")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Username หรือ Password ไม่ถูกต้อง"}
        )
    if not user.is_active:
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "บัญชีนี้ถูกระงับ"}
        )
    token = create_access_token({"sub": user.username}, timedelta(hours=8))
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie("user_token", token, httponly=True)
    return response


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/register")
def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    if db.query(models.User).filter(models.User.username == username).first():
        return templates.TemplateResponse(
            "register.html", {"request": request, "error": "Username นี้ถูกใช้แล้ว"}
        )
    if db.query(models.User).filter(models.User.email == email).first():
        return templates.TemplateResponse(
            "register.html", {"request": request, "error": "Email นี้ถูกใช้แล้ว"}
        )
    user = models.User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
    )
    db.add(user)
    db.commit()
    response = RedirectResponse(url="/login?success=1", status_code=302)
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("user_token")
    return response


# -------- Dashboard --------

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    url_rows = db.query(models.URL).filter(models.URL.user_id == user.id).order_by(
        models.URL.created_at.desc()
    ).all()
    # Convert to plain dicts so template has no SQLAlchemy dependency
    urls = [
        {"id": u.id, "original_url": u.original_url,
         "short_code": u.short_code, "clicks": u.clicks}
        for u in url_rows
    ]
    html = templates.env.get_template("dashboard.html").render(
        request=request,
        username=user.username,
        urls=urls,
        base_url=get_base_url(request),
    )
    return HTMLResponse(content=html)


@router.post("/shorten")
def shorten(
    request: Request,
    original_url: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")

    short_code = generate_short_code()
    while db.query(models.URL).filter(models.URL.short_code == short_code).first():
        short_code = generate_short_code()

    new_url = models.URL(
        original_url=original_url,
        short_code=short_code,
        user_id=user.id,
    )
    db.add(new_url)
    db.commit()
    db.refresh(new_url)

    new_url_dict = {"short_code": new_url.short_code}
    url_rows = db.query(models.URL).filter(models.URL.user_id == user.id).order_by(
        models.URL.created_at.desc()
    ).all()
    urls = [
        {"id": u.id, "original_url": u.original_url,
         "short_code": u.short_code, "clicks": u.clicks}
        for u in url_rows
    ]
    html = templates.env.get_template("dashboard.html").render(
        request=request,
        username=user.username,
        urls=urls,
        new_url=new_url_dict,
        base_url=get_base_url(request),
    )
    return HTMLResponse(content=html)


@router.post("/delete/{url_id}")
def delete_url(url_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    url = db.query(models.URL).filter(
        models.URL.id == url_id, models.URL.user_id == user.id
    ).first()
    if url:
        db.delete(url)
        db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)
