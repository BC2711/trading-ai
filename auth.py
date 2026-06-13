from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.deps import get_db
from app.schemas.trading import TokenResponse, UserLogin, UserCreate, UserRead, CurrentUserRead, RefreshTokenRequest, NavigationItemRead
from app.services.admin import authenticate_user, register_user, permissions_for_user, create_access_token, create_refresh_token, decode_refresh_token, revoke_refresh_token
from app.db.auth import get_current_user as require_current_user
from app.models import User

router = APIRouter()

@router.post("/register", response_model=UserRead)
def post_register(payload: UserCreate, db: Session = Depends(get_db)):
    try:
        return register_user(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.post("/login", response_model=TokenResponse)
def post_login(payload: UserLogin, request: Request, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    return TokenResponse(
        access_token=create_access_token(str(user.id), user.role),
        refresh_token=create_refresh_token(str(user.id), user.role),
        token_type="bearer",
    )

@router.post("/refresh", response_model=TokenResponse)
def post_refresh_token(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    token_payload = decode_refresh_token(payload.refresh_token)
    if not token_payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    user = db.get(User, int(token_payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User inactive")

    return TokenResponse(
        access_token=create_access_token(str(user.id), user.role),
        refresh_token=create_refresh_token(str(user.id), user.role),
        token_type="bearer",
    )

@router.post("/logout")
def post_logout(payload: RefreshTokenRequest, user: User = Depends(require_current_user), db: Session = Depends(get_db)):
    revoke_refresh_token(db, payload.refresh_token)
    return {"logged_out": True}

@router.get("/me", response_model=CurrentUserRead)
def get_me(db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    return CurrentUserRead(
        id=user.id,
        name=user.full_name,
        role=user.role,
        permissions=permissions_for_user(db, user),
    )

@router.get("/navigation", response_model=list[NavigationItemRead])
def get_navigation(db: Session = Depends(get_db), user: User = Depends(require_current_user)):
    # Implementation logic moved from routes.py
    from app.api.routes import NAVIGATION_ITEMS
    permissions = set(permissions_for_user(db, user))
    items = []
    for item in NAVIGATION_ITEMS:
        if item["permission"] in permissions:
            filtered = {**item, "children": [c for c in item["children"] if c["permission"] in permissions]}
            items.append(NavigationItemRead.model_validate(filtered))
    return items