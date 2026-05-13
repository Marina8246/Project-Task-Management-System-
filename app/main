import logging
import os

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi

from sqlalchemy.orm import Session

from passlib.context import CryptContext

from dotenv import load_dotenv

load_dotenv()


from app.database import (
    Base,
    engine,
    SessionLocal
)

from app.models import UserDB

from app.routers.tasks import router as tasks_router
from app.routers.monitoring import router as monitoring_router 

from app.routers import (
    auth_router,
    users_router,
    projects_router
)


logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s - "
        "%(name)s - "
        "%(levelname)s - "
        "%(message)s"
    )
)

logger = logging.getLogger(__name__)


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def create_default_admin(db: Session):

    existing_admin = db.query(UserDB).filter(
        UserDB.username == "admin"
    ).first()

    if not existing_admin:

        admin = UserDB(
    username="admin",
    password=pwd_context.hash("admin123"),
    role="admin"
)
        db.add(admin)

        db.commit()

        db.refresh(admin)

        logger.info("Default admin created")


@asynccontextmanager
async def lifespan(app: FastAPI):

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:

        create_default_admin(db)

    finally:

        db.close()

    yield


app = FastAPI(
    title="Task Management System",
    description=(
        "Task Management System API "
        "with JWT authentication, "
        "RBAC, Redis caching, "
        "and task lifecycle validation."
    ),
    version="1.0.0",
    lifespan=lifespan
)


@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception
):

    logger.exception(
        f"Unhandled error on {request.url}"
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error"
        }
    )


def custom_openapi():

    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title="Task Management System",
        version="1.0.0",
        description=(
            "Task Management System API "
            "using FastAPI"
        ),
        routes=app.routes,
    )

    schema["components"]["securitySchemes"] = {
        "Admin": {
            "type": "http",
            "scheme": "bearer",
            "description": "Admin token"
        },

        "ProjectManager": {
            "type": "http",
            "scheme": "bearer",
            "description": "Project Manager token"
        },

        "Employee": {
            "type": "http",
            "scheme": "bearer",
            "description": "Employee token"
        }
    }

    app.openapi_schema = schema

    return app.openapi_schema


app.openapi = custom_openapi


app.include_router(
    auth_router,
    prefix="/auth",
    tags=["Auth"]
)

app.include_router(
    users_router,
    prefix="/users",
    tags=["Users"]
)

app.include_router(
    projects_router,
    prefix="/projects",
    tags=["Projects"]
)

app.include_router(
    tasks_router,
    prefix="/tasks",
    tags=["Tasks"]
)
app.include_router(
    monitoring_router,
    prefix="/monitoring",
    tags=["Monitoring"]
)
