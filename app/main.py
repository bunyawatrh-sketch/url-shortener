from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from .database import engine, get_db
from . import models
from .routers import auth, urls, admin, user
import os
from dotenv import load_dotenv

load_dotenv()

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="URL Shortener API",
    description="ระบบย่อ URL พัฒนาด้วย FastAPI",
    version="1.0.0",
)

app.include_router(auth.router)
app.include_router(urls.router)
app.include_router(admin.router)
app.include_router(user.router)


@app.get("/{short_code}", tags=["Redirect"])
def redirect_url(short_code: str, db: Session = Depends(get_db)):
    url = db.query(models.URL).filter(
        models.URL.short_code == short_code,
        models.URL.is_active == True,
    ).first()
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")
    url.clicks += 1
    db.commit()
    return RedirectResponse(url=url.original_url, status_code=301)
