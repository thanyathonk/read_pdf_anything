from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
import httpx
from app.config import settings
from app.services.database import database
from app.models.user import UserInDB, UserResponse, AuthProvider

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self):
        self.secret_key = settings.JWT_SECRET
        self.algorithm = settings.JWT_ALGORITHM
        self.expire_minutes = settings.JWT_EXPIRE_MINUTES

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash"""
        return pwd_context.verify(plain_password, hashed_password)

    def hash_password(self, password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)

    def create_access_token(
        self, data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + (
            expires_delta or timedelta(minutes=self.expire_minutes)
        )
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> Optional[dict]:
        """Decode and verify a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            return None

    async def get_user_by_email(self, email: str) -> Optional[dict]:
        """Get user by email from database"""
        if not database.is_connected:
            return None
        user = await database.users.find_one({"email": email})
        return user

    async def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """Get user by ID from database"""
        if not database.is_connected:
            return None
        from bson import ObjectId

        user = await database.users.find_one({"_id": ObjectId(user_id)})
        return user

    async def create_user(
        self,
        email: str,
        name: str,
        password: Optional[str] = None,
        provider: AuthProvider = AuthProvider.LOCAL,
        google_id: Optional[str] = None,
        avatar: Optional[str] = None,
    ) -> Optional[dict]:
        """Create a new user"""
        if not database.is_connected:
            return None

        user_data = {
            "email": email,
            "name": name,
            "hashed_password": self.hash_password(password) if password else None,
            "provider": provider.value,
            "google_id": google_id,
            "avatar": avatar,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_active": True,
            "chat_history": [],
            "pdf_history": [],
        }

        result = await database.users.insert_one(user_data)
        user_data["_id"] = str(result.inserted_id)
        return user_data

    async def authenticate_user(self, email: str, password: str) -> Optional[dict]:
        """Authenticate user with email and password"""
        user = await self.get_user_by_email(email)
        if not user:
            return None
        if not user.get("hashed_password"):
            return None  # User registered with OAuth
        if not self.verify_password(password, user["hashed_password"]):
            return None
        return user

    async def verify_google_token(self, credential: str) -> Optional[dict]:
        """Verify Google ID token and get user info"""
        try:
            # Verify token with Google
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://oauth2.googleapis.com/tokeninfo?id_token={credential}"
                )

                if response.status_code != 200:
                    return None

                token_info = response.json()

                # Verify audience (client ID)
                if (
                    settings.GOOGLE_CLIENT_ID
                    and token_info.get("aud") != settings.GOOGLE_CLIENT_ID
                ):
                    return None

                return {
                    "email": token_info.get("email"),
                    "name": token_info.get("name"),
                    "picture": token_info.get("picture"),
                    "google_id": token_info.get("sub"),
                }
        except Exception as e:
            print(f"Google token verification error: {e}")
            return None

    async def google_auth(self, credential: str) -> Optional[dict]:
        """Handle Google OAuth authentication"""
        # Verify Google token
        google_user = await self.verify_google_token(credential)
        if not google_user:
            return None

        # Check if user exists
        user = await self.get_user_by_email(google_user["email"])

        if user:
            # Update Google info if needed
            if user.get("provider") != AuthProvider.GOOGLE.value:
                await database.users.update_one(
                    {"email": google_user["email"]},
                    {
                        "$set": {
                            "google_id": google_user["google_id"],
                            "avatar": google_user.get("picture"),
                            "updated_at": datetime.utcnow(),
                        }
                    },
                )
            return user

        # Create new user
        user = await self.create_user(
            email=google_user["email"],
            name=google_user["name"],
            provider=AuthProvider.GOOGLE,
            google_id=google_user["google_id"],
            avatar=google_user.get("picture"),
        )
        return user

    def user_to_response(self, user: dict) -> UserResponse:
        """Convert user dict to UserResponse"""
        if not user:
            raise ValueError("User data is None")
        
        # Handle both ObjectId and string _id
        user_id = user.get("_id")
        if user_id is None:
            raise ValueError("User _id is missing")
        
        # Convert ObjectId to string if needed
        if hasattr(user_id, '__str__'):
            user_id = str(user_id)
        
        return UserResponse(
            id=user_id,
            email=user.get("email", ""),
            name=user.get("name", ""),
            avatar=user.get("avatar"),
            provider=user.get("provider", "local"),
            created_at=user.get("created_at", datetime.utcnow()),
        )


# Singleton instance
auth_service = AuthService()
