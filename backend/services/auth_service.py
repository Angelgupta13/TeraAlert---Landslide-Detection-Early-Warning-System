from datetime import datetime, timedelta
from typing import Optional, Dict
import jwt
import bcrypt
import os
import json
import secrets
from pathlib import Path


class AuthService:
    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET", secrets.token_urlsafe(32))
        self.algorithm = "HS256"
        self.access_token_expire = 30
        self.refresh_token_expire = 7
        self.users_file = Path(__file__).parent.parent / "users.json"
        self._init_users_file()

    def _init_users_file(self):
        if not self.users_file.exists():
            default_users = {
                "users": [
                    {
                        "id": 1,
                        "email": "admin@landslide.local",
                        "password_hash": self._hash_password("admin123"),
                        "name": "System Admin",
                        "role": "admin",
                        "created_at": datetime.now().isoformat(),
                        "is_active": True,
                    }
                ]
            }
            with open(self.users_file, "w") as f:
                json.dump(default_users, f, indent=2)

    def _hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def _verify_password(self, password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode(), hashed.encode())

    def _load_users(self) -> Dict:
        try:
            with open(self.users_file, "r") as f:
                return json.load(f)
        except:
            return {"users": []}

    def _save_users(self, data: Dict):
        with open(self.users_file, "w") as f:
            json.dump(data, f, indent=2)

    def authenticate(self, email: str, password: str) -> Optional[Dict]:
        data = self._load_users()
        for user in data.get("users", []):
            if user["email"] == email and user.get("is_active", True):
                if self._verify_password(password, user["password_hash"]):
                    return user
        return None

    def create_access_token(self, user: Dict) -> str:
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire)
        payload = {
            "sub": str(user["id"]),
            "email": user["email"],
            "role": user["role"],
            "exp": expire,
            "type": "access",
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user: Dict) -> str:
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire)
        payload = {"sub": str(user["id"]), "exp": expire, "type": "refresh"}
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict]:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            if payload.get("type") != token_type:
                return None
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        data = self._load_users()
        for user in data.get("users", []):
            if user["id"] == user_id:
                return user
        return None

    def create_user(
        self, email: str, password: str, name: str, role: str = "user"
    ) -> Dict:
        data = self._load_users()

        if any(u["email"] == email for u in data.get("users", [])):
            raise ValueError("Email already registered")

        new_id = max([u["id"] for u in data.get("users", [])], default=0) + 1

        new_user = {
            "id": new_id,
            "email": email,
            "password_hash": self._hash_password(password),
            "name": name,
            "role": role,
            "created_at": datetime.now().isoformat(),
            "is_active": True,
        }

        data.setdefault("users", []).append(new_user)
        self._save_users(data)

        return {"id": new_id, "email": email, "name": name, "role": role}

    def update_user(self, user_id: int, updates: Dict) -> Optional[Dict]:
        data = self._load_users()
        for user in data.get("users", []):
            if user["id"] == user_id:
                if "password" in updates:
                    user["password_hash"] = self._hash_password(updates["password"])
                if "name" in updates:
                    user["name"] = updates["name"]
                if "role" in updates:
                    user["role"] = updates["role"]
                self._save_users(data)
                return user
        return None

    def delete_user(self, user_id: int) -> bool:
        data = self._load_users()
        users = data.get("users", [])
        for i, user in enumerate(users):
            if user["id"] == user_id:
                users.pop(i)
                data["users"] = users
                self._save_users(data)
                return True
        return False


auth_service = AuthService()
