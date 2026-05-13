import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db

from app.models import (
    UserDB,
    ProjectDB,
    TaskDB
)

from app.schemas import (
    UpdateRole,
    UserResponse,
    UsersListResponse
)

from app.dependencies import (
    verify_token,
    require_admin,
    get_cache,
    set_cache,
    delete_cache_pattern
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Users"])


def _user_to_dict(user: UserDB) -> dict:

    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "email": user.email,
    }


@router.get(
    "/me",
    response_model=UserResponse
)
def get_me(
    payload: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    try:

        cache_key = f"users:me:{payload['id']}"

        cached = get_cache(cache_key)

        if cached:
            return cached

        user = db.query(UserDB).filter(
            UserDB.id == payload["id"]
        ).first()

        if not user:

            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        result = _user_to_dict(user)

        set_cache(
            cache_key,
            result,
            ttl=120
        )

        logger.info(
            f"USER FETCHED: "
            f"User '{payload.get('sub')}' fetched own profile"
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


@router.get(
    "/",
    response_model=UsersListResponse
)
def get_all_users(
    payload: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    try:

        cache_key = "users:all"

        cached = get_cache(cache_key)

        if cached:
            return {"users": cached}

        users = db.query(UserDB).all()

        result = [
            _user_to_dict(user)
            for user in users
        ]

        set_cache(
            cache_key,
            result,
            ttl=60
        )

        logger.info(
            f"USERS FETCHED: "
            f"Admin '{payload.get('sub')}' fetched all users"
        )

        return {"users": result}

    except HTTPException:
        raise

    except Exception as e:

        logger.error(f"Unexpected error: {e}")

        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.get(
    "/{user_id}",
    response_model=UserResponse
)
def get_user(
    user_id: int,
    payload: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    try:

        cache_key = f"users:single:{user_id}"

        cached = get_cache(cache_key)

        if cached:
            return cached

        user = db.query(UserDB).filter(
            UserDB.id == user_id
        ).first()

        if not user:

            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        result = _user_to_dict(user)

        set_cache(
            cache_key,
            result,
            ttl=120
        )

        logger.info(
            f"USER FETCHED: "
            f"Admin '{payload.get('sub')}' fetched user id={user_id}"
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
    "/{user_id}/role"
)
def update_user_role(
    user_id: int,
    data: UpdateRole,
    payload: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    try:

        if payload["id"] == user_id:

            raise HTTPException(
                status_code=400,
                detail="Cannot change your own role"
            )

        user = db.query(UserDB).filter(
            UserDB.id == user_id
        ).first()

        if not user:

            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        user.role = data.role

        db.commit()

        db.refresh(user)

        delete_cache_pattern("users:*")

        logger.info(
            f"ROLE UPDATED: "
            f"Admin '{payload.get('sub')}' "
            f"updated user id={user_id} "
            f"role to '{data.role}'"
        )

        return {
            "message": "Role updated successfully",
            "user_id": user_id,
            "new_role": data.role
        }

    except HTTPException:
        raise

    except Exception as e:

        logger.error(f"Unexpected error: {e}")

        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.delete(
    "/{user_id}"
)
def delete_user(
    user_id: int,
    payload: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    try:

        if payload["id"] == user_id:

            raise HTTPException(
                status_code=400,
                detail="Cannot delete your own account"
            )

        user = db.query(UserDB).filter(
            UserDB.id == user_id
        ).first()

        if not user:

            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        has_projects = db.query(ProjectDB).filter(
            ProjectDB.owner_id == user.id
        ).first()

        if has_projects:

            raise HTTPException(
                status_code=400,
                detail="Cannot delete user with existing projects"
            )

        has_tasks = db.query(TaskDB).filter(
            TaskDB.assignee_id == user.id
        ).first()

        if has_tasks:

            raise HTTPException(
                status_code=400,
                detail="Cannot delete user with assigned tasks"
            )

        db.delete(user)

        db.commit()

        delete_cache_pattern("users:*")

        logger.info(
            f"USER DELETED: "
            f"Admin '{payload.get('sub')}' "
            f"deleted user id={user_id}"
        )

        return {
            "message": "User deleted successfully"
        }

    except HTTPException:
        raise

    except Exception as e:

        logger.error(f"Unexpected error: {e}")

        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )