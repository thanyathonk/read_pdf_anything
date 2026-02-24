import logging
from fastapi import APIRouter, HTTPException, Depends, Header, Query
from typing import Optional, List
from app.models.user import (
    UserCreate,
    UserLogin,
    TokenResponse,
    UserResponse,
    GoogleAuthRequest,
    AuthResponse,
)
from app.services.auth_service import auth_service
from app.services.database import database
from app.services.gmail_service import gmail_service
from app.config import settings
from app.models.user import AuthProvider
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# Define GuestDataMigration inline to avoid import issues
class GuestDataMigration(BaseModel):
    pdf_ids: List[str] = []
    chat_messages: List[dict] = []


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
async def register(user_data: UserCreate):
    """Register a new user"""
    if not database.is_connected:
        raise HTTPException(
            status_code=503, detail="Database not available. Please try again later."
        )

    # Check if email already exists
    existing_user = await auth_service.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    if not user_data.password:
        raise HTTPException(status_code=400, detail="Password is required")

    # Create user
    user = await auth_service.create_user(
        email=user_data.email, name=user_data.name, password=user_data.password
    )

    if not user:
        raise HTTPException(status_code=500, detail="Failed to create user")

    # Create token
    access_token = auth_service.create_access_token({"sub": str(user["_id"])})

    return AuthResponse(
        success=True,
        message="Registration successful",
        data=TokenResponse(
            access_token=access_token, user=auth_service.user_to_response(user)
        ),
    )


@router.post("/login", response_model=AuthResponse)
async def login(credentials: UserLogin):
    """Login with email and password"""
    if not database.is_connected:
        raise HTTPException(
            status_code=503, detail="Database not available. Please try again later."
        )

    user = await auth_service.authenticate_user(credentials.email, credentials.password)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Create token
    access_token = auth_service.create_access_token({"sub": str(user["_id"])})

    return AuthResponse(
        success=True,
        message="Login successful",
        data=TokenResponse(
            access_token=access_token, user=auth_service.user_to_response(user)
        ),
    )


@router.post("/google", response_model=AuthResponse)
async def google_auth(request: GoogleAuthRequest):
    """Authenticate with Google (ID Token - for simple login)"""
    user = await auth_service.google_auth(request.credential)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid Google credentials")

    # Create token
    access_token = auth_service.create_access_token({"sub": str(user["_id"])})

    return AuthResponse(
        success=True,
        message="Google authentication successful",
        data=TokenResponse(
            access_token=access_token, user=auth_service.user_to_response(user)
        ),
    )


@router.get("/google/authorize")
async def google_authorize(
    state: Optional[str] = Query(None), simple: bool = Query(False)
):
    """Get Google OAuth authorization URL"""
    try:
        if simple:
            # Simple login (no Gmail access) - use basic OAuth flow
            from urllib.parse import urlencode

            # Use the same redirect URI as configured (will route to simple-callback via query param)
            redirect_uri = settings.GOOGLE_REDIRECT_URI
            params = {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": "openid email profile",
                "access_type": "offline",
                "prompt": "consent",
            }
            if state:
                params["state"] = state
            # Add simple=true to state so callback knows it's simple login
            if not state:
                params["state"] = "simple=true"
            elif "simple" not in state:
                params["state"] = f"{state}&simple=true"
            auth_url = (
                f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
            )
        else:
            # Full OAuth with Gmail access
            auth_url = gmail_service.get_authorization_url(state=state)

        return {"success": True, "authorization_url": auth_url}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate authorization URL: {str(e)}"
        )


@router.get("/google/simple-callback")
async def google_simple_callback(
    code: str = Query(...), state: Optional[str] = Query(None)
):
    """Handle Google OAuth callback for simple login (no Gmail)"""
    try:
        import httpx

        # Exchange code for tokens
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,  # Use same redirect URI
                },
            )

            if token_response.status_code != 200:
                raise HTTPException(
                    status_code=400, detail="Failed to exchange code for tokens"
                )

            token_data = token_response.json()
            id_token_str = token_data.get("id_token")

            if not id_token_str:
                raise HTTPException(status_code=400, detail="No ID token received")

            # Verify and decode ID token using Google's public keys (secure)
            if not settings.GOOGLE_CLIENT_ID:
                raise HTTPException(
                    status_code=500,
                    detail="Google OAuth is not configured. Contact administrator.",
                )
            try:
                from google.oauth2 import id_token as google_id_token
                from google.auth.transport import requests as google_requests

                decoded = google_id_token.verify_oauth2_token(
                    id_token_str,
                    google_requests.Request(),
                    settings.GOOGLE_CLIENT_ID,
                )
            except ValueError:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid Google ID token. Authentication failed.",
                )

            email = decoded.get("email")
            name = decoded.get("name", email.split("@")[0] if email else "User")
            picture = decoded.get("picture")
            google_id = decoded.get("sub")

            if not email:
                raise HTTPException(status_code=400, detail="No email in ID token")

            # Check if MongoDB is connected
            if not database.is_connected:
                raise HTTPException(
                    status_code=503,
                    detail="MongoDB is not connected. Please start MongoDB to enable user authentication.",
                )

            # Check if user exists or create new
            user = await auth_service.get_user_by_email(email)

            if not user:
                # Create new user
                user = await auth_service.create_user(
                    email=email,
                    name=name,
                    provider=AuthProvider.GOOGLE,
                    google_id=google_id,
                    avatar=picture,
                )

                # Check if user creation failed
                if not user:
                    raise HTTPException(
                        status_code=500,
                        detail="Failed to create user. MongoDB may not be connected.",
                    )
            else:
                # Update user info if needed
                from bson import ObjectId
                from datetime import datetime

                await database.users.update_one(
                    {"_id": ObjectId(user["_id"])},
                    {
                        "$set": {
                            "avatar": picture,
                            "google_id": google_id,
                            "updated_at": datetime.utcnow(),
                        }
                    },
                )
                # Refresh user data
                user = await auth_service.get_user_by_email(email)

            # Verify user exists and has _id
            if not user or not user.get("_id"):
                raise HTTPException(
                    status_code=500, detail="User data is invalid. Please try again."
                )

            # Create JWT token
            access_token = auth_service.create_access_token({"sub": str(user["_id"])})

            return {
                "success": True,
                "message": "Google authentication successful",
                "data": {
                    "access_token": access_token,
                    "token_type": "bearer",
                    "user": auth_service.user_to_response(user),
                },
            }
    except Exception as e:
        logger.exception("Google OAuth callback error")
        raise HTTPException(
            status_code=500, detail="Authentication failed. Please try again."
        )


@router.get("/google/callback")
async def google_callback(code: str = Query(...), state: Optional[str] = Query(None)):
    """Handle Google OAuth callback - routes to simple or full callback based on state"""
    # Check if this is a simple login request
    if state and "simple=true" in state:
        # Route to simple callback handler
        return await google_simple_callback(code, state)

    # Otherwise, handle full OAuth with Gmail
    try:
        # Exchange code for tokens
        token_data = gmail_service.exchange_code_for_tokens(code)

        # Get user info from Gmail profile
        profile = gmail_service.get_profile(token_data)
        email = profile["email_address"]

        # Check if user exists or create new
        user = await auth_service.get_user_by_email(email)

        if not user:
            # Create new user
            user = await auth_service.create_user(
                email=email,
                name=email.split("@")[0],  # Use email prefix as name
                provider=AuthProvider.GOOGLE,
                google_id=email,
                avatar=None,
            )

        # Store Gmail tokens in user document
        if database.is_connected:
            from bson import ObjectId
            from datetime import datetime

            await database.users.update_one(
                {"_id": ObjectId(user["_id"])},
                {"$set": {"gmail_tokens": token_data, "updated_at": datetime.utcnow()}},
            )

        # Fetch emails
        emails = []
        try:
            emails = gmail_service.fetch_emails(token_data, max_results=10)
        except Exception as e:
            print(f"Failed to fetch emails: {e}")
            # Continue even if email fetch fails

        # Create JWT token
        access_token = auth_service.create_access_token({"sub": str(user["_id"])})

        return {
            "success": True,
            "message": "Google authentication successful",
            "data": {
                "access_token": access_token,
                "token_type": "bearer",
                "user": auth_service.user_to_response(user),
                "emails": emails,
                "email_count": len(emails),
            },
        }
    except Exception as e:
        logger.exception("Google OAuth callback error")
        raise HTTPException(
            status_code=500, detail="Authentication failed. Please try again."
        )


@router.post("/migrate-guest-data")
async def migrate_guest_data(
    guest_data: GuestDataMigration, authorization: Optional[str] = Header(None)
):
    """Migrate guest data (PDFs and chat messages) to user account"""
    if not database.is_connected:
        raise HTTPException(
            status_code=503, detail="Database not available. Please try again later."
        )

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.split(" ")[1]
    payload = auth_service.decode_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    user = await auth_service.get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        from bson import ObjectId
        from datetime import datetime

        # Get existing user data
        existing_pdf_history = user.get("pdf_history", [])
        existing_chat_history = user.get("chat_history", [])

        # Extract guest data
        pdf_ids = guest_data.pdf_ids or []
        chat_messages = guest_data.chat_messages or []

        # Merge PDF IDs (avoid duplicates)
        merged_pdf_ids = list(set(existing_pdf_history + pdf_ids))

        # Merge chat messages (add guest messages to existing)
        merged_chat_history = existing_chat_history + chat_messages

        # Update user document
        await database.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "pdf_history": merged_pdf_ids,
                    "chat_history": merged_chat_history,
                    "updated_at": datetime.utcnow(),
                }
            },
        )

        return {
            "success": True,
            "message": "Guest data migrated successfully",
            "migrated": {
                "pdfs_count": len(pdf_ids),
                "messages_count": len(chat_messages),
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to migrate guest data: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user(authorization: Optional[str] = Header(None)):
    """Get current authenticated user"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.split(" ")[1]
    payload = auth_service.decode_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    user = await auth_service.get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return auth_service.user_to_response(user)


@router.post("/logout")
async def logout():
    """Logout (client-side token removal)"""
    return {"success": True, "message": "Logged out successfully"}


@router.get("/gmail/emails")
async def get_emails(
    authorization: Optional[str] = Header(None), max_results: int = Query(10)
):
    """Fetch emails from Gmail for authenticated user"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.split(" ")[1]
    payload = auth_service.decode_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    user = await auth_service.get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get Gmail tokens
    gmail_tokens = user.get("gmail_tokens")
    if not gmail_tokens:
        raise HTTPException(
            status_code=400, detail="Gmail not connected. Please connect Gmail first."
        )

    try:
        # Refresh token if needed
        gmail_tokens = gmail_service.refresh_access_token(gmail_tokens)

        # Fetch emails
        emails = gmail_service.fetch_emails(gmail_tokens, max_results=max_results)

        return {"success": True, "emails": emails, "count": len(emails)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch emails: {str(e)}")


@router.get("/chat/history")
async def get_chat_history(authorization: Optional[str] = Header(None)):
    """Get chat history for authenticated user"""
    if not database.is_connected:
        raise HTTPException(
            status_code=503, detail="Database not available. Please try again later."
        )

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.split(" ")[1]
    payload = auth_service.decode_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    user = await auth_service.get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    chat_history = user.get("chat_history", [])

    return {"success": True, "chat_history": chat_history, "count": len(chat_history)}


@router.post("/chat/history")
async def save_chat_history(
    messages: List[dict], authorization: Optional[str] = Header(None)
):
    """Save chat history for authenticated user"""
    if not database.is_connected:
        raise HTTPException(
            status_code=503, detail="Database not available. Please try again later."
        )

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.split(" ")[1]
    payload = auth_service.decode_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    user = await auth_service.get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        from bson import ObjectId
        from datetime import datetime

        # Update user document with chat history
        await database.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"chat_history": messages, "updated_at": datetime.utcnow()}},
        )

        return {
            "success": True,
            "message": "Chat history saved successfully",
            "count": len(messages),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save chat history: {str(e)}"
        )


@router.get("/status")
async def auth_status():
    """Check authentication service status"""
    return {
        "database_connected": database.is_connected,
        "google_oauth_enabled": bool(auth_service.secret_key),
        "gmail_api_enabled": settings.GMAIL_API_ENABLED,
    }
