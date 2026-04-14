from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import Optional
from services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str


class UserInDB(BaseModel):
    id: int
    email: str
    name: str
    role: str
    is_active: bool


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    payload = auth_service.verify_token(token, "access")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = auth_service.get_user_by_id(int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def get_current_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    try:
        user = auth_service.create_user(
            email=user_data.email,
            password=user_data.password,
            name=user_data.name,
            role="user",
        )
        return UserResponse(**user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = auth_service.authenticate(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth_service.create_access_token(user)
    refresh_token = auth_service.create_refresh_token(user)

    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=Token)
async def refresh(refresh_token: str):
    payload = auth_service.verify_token(refresh_token, "refresh")
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = auth_service.get_user_by_id(int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_access_token = auth_service.create_access_token(user)
    new_refresh_token = auth_service.create_refresh_token(user)

    return Token(access_token=new_access_token, refresh_token=new_refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user["name"],
        role=current_user["role"],
    )


@router.get("/users", response_model=list[UserResponse])
async def list_users(current_user: dict = Depends(get_current_admin)):
    from services.auth_service import auth_service

    data = auth_service._load_users()
    return [
        UserResponse(id=u["id"], email=u["email"], name=u["name"], role=u["role"])
        for u in data.get("users", [])
    ]


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, current_user: dict = Depends(get_current_admin)):
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    success = auth_service.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}
