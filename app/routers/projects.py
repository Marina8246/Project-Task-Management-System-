import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ProjectDB, UserDB, TaskDB
from app.schemas import (
    Project,
    ProjectResponse,
    ProjectsListResponse
)

from app.dependencies import (
    verify_token,
    require_project_manager,
    require_admin,
    get_cache,
    set_cache,
    delete_cache,
    delete_cache_pattern
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Projects"])


def _project_to_dict(
    project: ProjectDB,
    db: Session
) -> dict:

    owner_username = None

    if project.owner_id:

        owner = db.query(UserDB).filter(
            UserDB.id == project.owner_id
        ).first()

        owner_username = owner.username if owner else None

    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "owner_id": project.owner_id,
        "owner_username": owner_username,
    }


@router.post(
    "/",
    status_code=201,
    response_model=ProjectResponse
)
def create_project(
    project: Project,
    payload: dict = Depends(require_project_manager),
    db: Session = Depends(get_db)
):
    try:

        new_project = ProjectDB(
            name=project.name,
            description=project.description,
            owner_id=payload["id"]
        )

        db.add(new_project)

        db.commit()

        db.refresh(new_project)

        delete_cache_pattern("projects:list:*")

        logger.info(
            f"PROJECT CREATED: User '{payload.get('sub')}' "
            f"created project '{new_project.name}'"
        )

        return _project_to_dict(new_project, db)

    except HTTPException:
        raise

    except Exception as e:

        logger.error(f"Unexpected error: {e}")

        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.get(
    "/",
    response_model=ProjectsListResponse
)
def get_projects(
    skip: int = 0,
    limit: int = 10,
    payload: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    try:

        role = payload.get("role")
        user_id = payload["id"]

        cache_key = f"projects:list:{role}:{user_id}:{skip}:{limit}"

        cached = get_cache(cache_key)

        if cached:
            return {"projects": cached}

        if role in ["admin", "project_manager"]:

            projects = db.query(ProjectDB).offset(skip).limit(limit).all()

        else:

            projects = db.query(ProjectDB).join(
                TaskDB,
                TaskDB.project_id == ProjectDB.id
            ).filter(
                TaskDB.assignee_id == user_id
            ).distinct().offset(skip).limit(limit).all()

        result = [
            _project_to_dict(project, db)
            for project in projects
        ]

        set_cache(cache_key, result, ttl=60)

        logger.info(
            f"PROJECTS FETCHED: User '{payload.get('sub')}' fetched projects"
        )

        return {"projects": result}

    except HTTPException:
        raise

    except Exception as e:

        logger.error(f"Unexpected error: {e}")

        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.get(
    "/{project_id}",
    response_model=ProjectResponse
)
def get_project(
    project_id: int,
    payload: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    try:

        role = payload.get("role")
        user_id = payload["id"]

        cache_key = f"projects:single:{project_id}"

        cached = get_cache(cache_key)

        if cached:

            if role not in ["admin", "project_manager"]:

                assigned_task = db.query(TaskDB).filter(
                    TaskDB.project_id == project_id,
                    TaskDB.assignee_id == user_id
                ).first()

                if not assigned_task:

                    raise HTTPException(
                        status_code=403,
                        detail="Access denied"
                    )

            return cached

        project = db.query(ProjectDB).filter(
            ProjectDB.id == project_id
        ).first()

        if not project:

            raise HTTPException(
                status_code=404,
                detail="Project not found"
            )

        if role not in ["admin", "project_manager"]:

            assigned_task = db.query(TaskDB).filter(
                TaskDB.project_id == project_id,
                TaskDB.assignee_id == user_id
            ).first()

            if not assigned_task:

                raise HTTPException(
                    status_code=403,
                    detail="Access denied"
                )

        result = _project_to_dict(project, db)

        set_cache(cache_key, result, ttl=60)

        logger.info(
            f"PROJECT FETCHED: User '{payload.get('sub')}' "
            f"fetched project id={project_id}"
        )

        return result

    except HTTPException:
        raise

    except Exception as e:

        logger.error(f"Unexpected error: {e}")

        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.put(
    "/{project_id}",
    response_model=ProjectResponse
)
def update_project(
    project_id: int,
    project: Project,
    payload: dict = Depends(require_project_manager),
    db: Session = Depends(get_db)
):
    try:

        existing_project = db.query(ProjectDB).filter(
            ProjectDB.id == project_id
        ).first()

        if not existing_project:

            raise HTTPException(
                status_code=404,
                detail="Project not found"
            )

        existing_project.name = project.name
        existing_project.description = project.description

        db.commit()

        db.refresh(existing_project)

        delete_cache(f"projects:single:{project_id}")
        delete_cache_pattern("projects:list:*")

        logger.info(
            f"PROJECT UPDATED: User '{payload.get('sub')}' "
            f"updated project id={project_id}"
        )

        return _project_to_dict(existing_project, db)

    except HTTPException:
        raise

    except Exception as e:

        logger.error(f"Unexpected error: {e}")

        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.delete(
    "/{project_id}",
    status_code=204
)
def delete_project(
    project_id: int,
    payload: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    try:

        project = db.query(ProjectDB).filter(
            ProjectDB.id == project_id
        ).first()

        if not project:

            raise HTTPException(
                status_code=404,
                detail="Project not found"
            )

        db.delete(project)

        db.commit()

        delete_cache(f"projects:single:{project_id}")
        delete_cache_pattern("projects:list:*")

        logger.info(
            f"PROJECT DELETED: Admin '{payload.get('sub')}' "
            f"deleted project id={project_id}"
        )

        return None

    except HTTPException:
        raise

    except Exception as e:

        logger.error(f"Unexpected error: {e}")

        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )