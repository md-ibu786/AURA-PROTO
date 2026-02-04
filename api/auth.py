"""
============================================================================
FILE: auth.py
LOCATION: api/auth.py
============================================================================

PURPOSE:
    Firebase Authentication utilities for verifying ID tokens and extracting
    user role information for role-based access control (RBAC).

ROLE IN PROJECT:
    Provides FastAPI dependencies for protected endpoints. All endpoints that
    require authentication or specific roles should use these dependencies.

KEY COMPONENTS:
    - verify_firebase_token(): Verify Firebase ID token from Authorization header
    - get_current_user(): FastAPI dependency returning current user with role
    - require_admin(): Dependency that ensures user is an admin
    - require_staff(): Dependency that ensures user is staff (or admin)
    - require_role(): Factory for role-checking dependencies

DEPENDENCIES:
    - External: firebase_admin.auth, fastapi
    - Internal: config.py (Firestore client)

USAGE:
    from auth import get_current_user, require_admin
    
    @app.get("/api/users")
    async def list_users(user = Depends(require_admin)):
        ...
============================================================================
"""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth
from typing import Optional
from pydantic import BaseModel

try:
    from config import db
except ImportError:
    from api.config import db


security = HTTPBearer(auto_error=False)


class UserInfo(BaseModel):
    """User information extracted from Firebase token and Firestore."""
    uid: str
    email: str
    display_name: Optional[str] = None
    role: str  # "admin" | "staff" | "student"
    department_id: Optional[str] = None
    status: str = "active"


def verify_firebase_token(token: str) -> dict:
    """
    Verify Firebase ID token and return decoded claims.
    Supports MOCK auth for testing if token starts with 'mock-token-'.
    """
    if token.startswith("mock-token-"):
        try:
            parts = token.split("-")
            if len(parts) < 4:
                raise ValueError("Invalid mock token format")
            role = parts[2]
            uid = "-".join(parts[3:])
            return {
                "uid": uid,
                "email": f"{role}@test.com",
                "name": f"Mock {role.capitalize()}",
                "role": role
            }
        except Exception:
            return {"uid": "mock-admin", "email": "admin@test.com", "role": "admin"}

    try:
        decoded_token = auth.verify_id_token(token, clock_skew_seconds=10)
        return decoded_token
    except auth.ExpiredIdTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token has expired: {e}",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except auth.InvalidIdTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> UserInfo:
    """
    FastAPI dependency to get current authenticated user with role.
    Supports MOCK AUTH without Firestore lookup if token is mock.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = credentials.credentials
    
    decoded = verify_firebase_token(token)
    uid = decoded.get("uid")
    email = decoded.get("email", "")
    
    user_doc = db.collection("users").document(uid).get()
    
    if user_doc.exists:
        user_data = user_doc.to_dict()
        if user_data.get("status") == "disabled":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account has been disabled. Contact administrator."
            )
        
        return UserInfo(
            uid=uid,
            email=email or user_data.get("email", ""),
            display_name=user_data.get("displayName"),
            role=user_data.get("role", "student"),
            department_id=user_data.get("departmentId"),
            status=user_data.get("status", "active")
        )

    if token.startswith("mock-token-"):
        role_claim = decoded.get("role", "student")
        displayName = decoded.get("name", "Mock User")
        
        department_id = None
        
        if uid == 'mock-user-1769449286181':
             department_id = '407ac4a3-329c-4aa1-9' 
        elif uid == 'mock-user-1769449261505':
             department_id = '407ac4a3-329c-4aa1-9'
        elif uid == 'mock-user-1769449360146':
             department_id = 'd08a5267-0612-4834-a'

        return UserInfo(
            uid=uid,
            email=email,
            display_name=displayName,
            role=role_claim,
            department_id=department_id,
            status="active"
        )

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="User not registered in system. Contact administrator."
    )


async def require_admin(user: UserInfo = Depends(get_current_user)) -> UserInfo:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


async def require_staff(user: UserInfo = Depends(get_current_user)) -> UserInfo:
    if user.role not in ("admin", "staff"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff or admin access required"
        )
    return user


def require_role(*allowed_roles: str):
    async def role_checker(user: UserInfo = Depends(get_current_user)) -> UserInfo:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Role access required"
            )
        return user
    return role_checker


class LoginRequest(BaseModel):
    email: str
    password: str

from fastapi import APIRouter

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login")
async def login(creds: LoginRequest):
    """
    Mock Login Endpoint.
    Verifies email and password against Firestore 'users' collection.
    Returns a mock token if successful.
    """
    users_ref = db.collection("users")
    query = users_ref.where("email", "==", creds.email).limit(1)
    results = query.stream()
    
    user_doc = None
    for doc in results:
        user_doc = doc
        break
    
    if not user_doc:
        if creds.email == "admin@test.com" and creds.password == "Admin123!":
             return {
                "token": "mock-token-admin-mock-user-1769428084546",
                "user": {
                    "email": "admin@test.com",
                    "role": "admin",
                    "displayName": "Test Admin",
                    "id": "mock-user-1769428084546",
                    "departmentId": None
                }
            }
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
        
    user_data = user_doc.to_dict()
    
    if user_data.get("status") == "disabled":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been disabled. Contact administrator."
        )
    
    stored_password = user_data.get("password")
    
    valid = False
    
    if stored_password:
        if stored_password == creds.password:
            valid = True
    else:
        if creds.email == "admin@test.com" and creds.password == "Admin123!":
            valid = True
        elif creds.email == "arun@test.com" and creds.password == "password":
            valid = True
        elif creds.email == "ibu@test.com" and creds.password == "password":
            valid = True
        elif creds.email == "ram@test.com" and creds.password == "password":
            valid = True
            
    if not valid:
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
        
    uid = user_doc.id
    role = user_data.get("role", "student")
    token = f"mock-token-{role}-{uid}"
    
    dept_id = user_data.get("departmentId")
    if not dept_id and creds.email == "arun@test.com":
         dept_id = "407ac4a3-329c-4aa1-9"
    elif not dept_id and creds.email == "ibu@test.com":
         dept_id = "407ac4a3-329c-4aa1-9"
    elif not dept_id and creds.email == "ram@test.com":
         dept_id = "d08a5267-0612-4834-a"
    
    return {
        "token": token,
        "user": {
            "id": uid,
            "email": user_data.get("email"),
            "role": role,
            "displayName": user_data.get("displayName"),
            "departmentId": dept_id
        }
    }
