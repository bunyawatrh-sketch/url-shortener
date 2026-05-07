from fastapi import APIRouter, Depends, HTTPException, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import timedelta
from jose import JWTError, jwt
from .. import models
from ..database import get_db
from ..auth import verify_password, create_access_token, SECRET_KEY, ALGORITHM
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/admin", tags=["Admin"])
templates = Jinja2Templates(directory="app/templates")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin1234")


def get_admin_from_cookie(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("admin_token")
    if not token:
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("role") != "admin":
            raise HTTPException(status_code=302, headers={"Location": "/admin/login"})
    except JWTError:
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})
    return True


@router.get("/login", response_class=HTMLResponse)
def admin_login_page(request: Request):
    return templates.TemplateResponse("admin/login.html", {"request": request})


@router.post("/login")
def admin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    if username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
        return templates.TemplateResponse(
            "admin/login.html", {"request": request, "error": "Invalid credentials"}
        )
    token = create_access_token({"sub": username, "role": "admin"}, timedelta(hours=8))
    response = RedirectResponse(url="/admin/dashboard", status_code=302)
    response.set_cookie("admin_token", token, httponly=True)
    return response


@router.get("/logout")
def admin_logout():
    response = RedirectResponse(url="/admin/login", status_code=302)
    response.delete_cookie("admin_token")
    return response


@router.get("/dashboard", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    _=Depends(get_admin_from_cookie),
):
    total_users = db.query(models.User).count()
    total_urls = db.query(models.URL).count()
    total_clicks = db.query(models.URL).with_entities(
        models.URL.clicks
    ).all()
    clicks_sum = sum(c[0] for c in total_clicks)
    recent_urls = (
        db.query(models.URL).order_by(models.URL.created_at.desc()).limit(5).all()
    )
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "total_users": total_users,
            "total_urls": total_urls,
            "total_clicks": clicks_sum,
            "recent_urls": recent_urls,
        },
    )


@router.get("/urls", response_class=HTMLResponse)
def admin_urls(
    request: Request,
    db: Session = Depends(get_db),
    _=Depends(get_admin_from_cookie),
):
    urls = db.query(models.URL).order_by(models.URL.created_at.desc()).all()
    return templates.TemplateResponse("admin/urls.html", {"request": request, "urls": urls})


@router.post("/urls/{url_id}/delete")
def admin_delete_url(
    url_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_admin_from_cookie),
):
    url = db.query(models.URL).filter(models.URL.id == url_id).first()
    if url:
        db.delete(url)
        db.commit()
    return RedirectResponse(url="/admin/urls", status_code=302)


@router.get("/users", response_class=HTMLResponse)
def admin_users(
    request: Request,
    db: Session = Depends(get_db),
    _=Depends(get_admin_from_cookie),
):
    users = db.query(models.User).order_by(models.User.created_at.desc()).all()
    return templates.TemplateResponse("admin/users.html", {"request": request, "users": users})


@router.post("/users/{user_id}/toggle")
def admin_toggle_user(
    user_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_admin_from_cookie),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        user.is_active = not user.is_active
        db.commit()
    return RedirectResponse(url="/admin/users", status_code=302)
