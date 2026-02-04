# AURA-PROTO Authentication System Documentation

## Overview

This document provides a comprehensive overview of the authentication system implemented in the AURA-PROTO admin panel project. It covers user types, privileges, file structure, and provides detailed implementation guidance for porting the same authentication system to the AURA-NOTES-MANAGER project.

---

## Table of Contents

1. [User Types and Privileges](#user-types-and-privileges)
2. [Architecture Overview](#architecture-overview)
3. [File Inventory](#file-inventory)
4. [Backend Implementation Details](#backend-implementation-details)
5. [Frontend Implementation Details](#frontend-implementation-details)
6. [Database Schema](#database-schema)
7. [Mock Authentication System](#mock-authentication-system)
8. [Implementation Guide for AURA-NOTES-MANAGER](#implementation-guide-for-aura-notes-manager)
9. [Security Considerations](#security-considerations)

---

## User Types and Privileges

The authentication system supports three distinct user roles, each with specific privileges and access levels:

### 1. **Admin**

**Description:** System administrators with full access to all features and data.

**Privileges:**
- Full CRUD access to all users (create, read, update, delete)
- View all departments, semesters, subjects, and modules across the system
- Access the Admin Dashboard for user management
- Can enable/disable user accounts
- Can manage system-wide settings
- Can access any department's data regardless of assignment
- Can read all notes and files across the system
- Cannot upload notes (design decision - admins manage users, not content)

**Database Properties:**
```json
{
  "role": "admin",
  "departmentId": null,
  "subjectIds": null,
  "status": "active"
}
```

---

### 2. **Staff**

**Description:** Teaching staff members who can manage educational content within their assigned department.

**Privileges:**
- Access to their assigned department's hierarchy (departments, semesters, subjects, modules)
- Can upload notes to their department's modules
- Can manage modules within their department
- Can view notes within their department
- Cannot access other departments' data
- Cannot access admin panel features
- Cannot manage users

**Database Properties:**
```json
{
  "role": "staff",
  "departmentId": "department-uuid-here",
  "subjectIds": ["subject-uuid-1", "subject-uuid-2"],
  "status": "active"
}
```

---

### 3. **Student**

**Description:** Regular students who can view and access educational content.

**Privileges:**
- Read-only access to their assigned department's hierarchy
- Can view and download notes within their department
- Cannot upload, modify, or delete any content
- Cannot access admin panel features
- Cannot access other departments' data

**Database Properties:**
```json
{
  "role": "student",
  "departmentId": "department-uuid-here",
  "subjectIds": null,
  "status": "active"
}
```

---

## Privilege Matrix

| Feature | Admin | Staff | Student |
|---------|-------|-------|---------|
| View All Departments | ✅ | Own Dept | Own Dept |
| View Hierarchy | ✅ | Own Dept | Own Dept |
| Upload Notes | ❌ | ✅ Own Dept | ❌ |
| Manage Users | ✅ | ❌ | ❌ |
| Disable Accounts | ✅ | ❌ | ❌ |
| View All Notes | ✅ | Own Dept | Own Dept |
| Delete Notes | ✅ | ❌ | ❌ |
| Access Admin Panel | ✅ | ❌ | ❌ |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ LoginPage    │  │ ProtectedRoute│ │ useAuthStore (Zustand)│ │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬────────────┘ │
│         │                 │                      │              │
│         │    Login       │  Route Guard        │ Auth State   │
│         └────────────────┼─────────────────────┼──────────────┘
│                          │                     │                │
└──────────────────────────┼─────────────────────┼────────────────
                           │                     │                │
┌──────────────────────────┼─────────────────────┼────────────────
│                          │                     │                │
│  ┌──────────────────────▼─────────────────────▼────────────┐  │
│  │                   API Client                              │  │
│  │  - Attaches Bearer token to requests                      │  │
│  │  - Handles 401/403 responses                              │  │
│  └───────────────────────┬─────────────────────────────────┘  │
│                          │                                      │
└──────────────────────────┼────────────────────────────────────┘
                           │
┌──────────────────────────┼────────────────────────────────────┐
│                          │                                      │
│  ┌──────────────────────▼───────────────────────────────┐    │
│  │                  BACKEND (FastAPI)                      │    │
│  ├────────────────────────────────────────────────────────┤    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │    │
│  │  │ auth.py     │  │ users.py    │  │ main.py     │   │    │
│  │  │ - verify    │  │ - CRUD      │  │ - Routes    │   │    │
│  │  │ - deps      │  │ - Profile   │  │ - CORS      │   │    │
│  │  │ - login     │  │             │  │             │   │    │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘   │    │
│  └─────────┼────────────────┼────────────────┼───────────┘    │
│            │                │                │                  │
│  ┌─────────▼────────────────▼────────────────▼───────────┐    │
│  │              Dependency Chain                          │    │
│  │  get_current_user → require_admin → require_staff      │    │
│  └───────────────────────┬──────────────────────────────┘    │
│                          │                                      │
└──────────────────────────┼────────────────────────────────────┘
                           │
┌──────────────────────────┼────────────────────────────────────┐
│                          │                                      │
│  ┌──────────────────────▼───────────────────────────────┐    │
│  │                  FIREBASE                             │    │
│  │  - Authentication (Firebase Auth)                     │    │
│  │  - Firestore (Database)                               │    │
│  └──────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────────┘
```

---

## File Inventory

### Backend Files

| File | Location | Purpose |
|------|----------|---------|
| **auth.py** | `api/auth.py` | Core authentication module with FastAPI dependencies |
| **config.py** | `api/config.py` | Firebase initialization and database client setup |
| **users.py** | `api/users.py` | User management endpoints (CRUD operations) |
| **main.py** | `api/main.py` | Application entry point, CORS, router mounting |
| **mock_firestore.py** | `api/mock_firestore.py` | Mock database for local development |

### Frontend Files

| File | Location | Purpose |
|------|----------|---------|
| **useAuthStore.ts** | `frontend/src/stores/useAuthStore.ts` | Zustand store for authentication state |
| **LoginPage.tsx** | `frontend/src/pages/LoginPage.tsx` | Login form and authentication UI |
| **ProtectedRoute.tsx** | `frontend/src/components/ProtectedRoute.tsx` | Route guard component |
| **App.tsx** | `frontend/src/App.tsx` | Main app with route configuration |
| **firebaseClient.ts** | `frontend/src/api/firebaseClient.ts` | Firebase client initialization |
| **client.ts** | `frontend/src/api/client.ts` | API client with auth headers |

### Configuration Files

| File | Location | Purpose |
|------|----------|---------|
| **requirements.txt** | `requirements.txt` | Python dependencies (firebase-admin, fastapi) |
| **package.json** | `frontend/package.json` | Node dependencies (firebase, zustand) |
| **vite.config.ts** | `frontend/vite.config.ts` | Vite config with proxy settings |
| **.env** | `.env` | Environment variables (Firebase credentials) |

---

## Backend Implementation Details

### 1. **auth.py** (`api/auth.py`)

This is the core authentication module providing FastAPI dependencies for protected endpoints.

#### Key Components:

**UserInfo Pydantic Model:**
```python
class UserInfo(BaseModel):
    uid: str
    email: str
    display_name: Optional[str] = None
    role: str  # "admin" | "staff" | "student"
    department_id: Optional[str] = None
    status: str = "active"
```

**Token Verification (verify_firebase_token):**
```python
def verify_firebase_token(token: str) -> dict:
    """
    Verify Firebase ID token and return decoded claims.
    Supports MOCK auth for testing if token starts with 'mock-token-'.
    """
    if token.startswith("mock-token-"):
        # Parse mock token format: mock-token-{role}-{uid}
        parts = token.split("-")
        role = parts[2]
        uid = "-".join(parts[3:])
        return {
            "uid": uid,
            "email": f"{role}@test.com",
            "name": f"Mock {role.capitalize()}",
            "role": role
        }
    
    # Real Firebase token verification
    decoded_token = auth.verify_id_token(token, clock_skew_seconds=10)
    return decoded_token
```

**Authentication Dependencies:**

1. **get_current_user:**
   - Verifies Firebase ID token
   - Looks up user in Firestore `users` collection
   - Returns `UserInfo` with role and department data
   - Raises 401 if not authenticated
   - Raises 403 if user is disabled or not in database

2. **require_admin:**
```python
async def require_admin(user: UserInfo = Depends(get_current_user)) -> UserInfo:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user
```

3. **require_staff:**
```python
async def require_staff(user: UserInfo = Depends(get_current_user)) -> UserInfo:
    if user.role not in ("admin", "staff"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff or admin access required"
        )
    return user
```

4. **require_role Factory:**
```python
def require_role(*allowed_roles: str):
    """
    Factory to create a dependency that checks for specific roles.
    
    Usage:
        @app.get("/api/something")
        async def something(user = Depends(require_role("admin", "staff"))):
            ...
    """
    async def role_checker(user: UserInfo = Depends(get_current_user)) -> UserInfo:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {' or '.join(allowed_roles)}"
            )
        return user
    return role_checker
```

5. **require_department_access Factory:**
```python
def require_department_access(department_id: str):
    """
    Factory to create a dependency that checks user belongs to a department.
    Admins always have access to all departments.
    """
    async def department_checker(user: UserInfo = Depends(get_current_user)) -> UserInfo:
        if user.role == "admin":
            return user
        if user.department_id != department_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No access to this department"
            )
        return user
    return department_checker
```

#### Mock Login Endpoint:

```python
@router.post("/login")
async def login(creds: LoginRequest):
    """
    Mock Login Endpoint.
    Verifies email and password against Firestore 'users' collection.
    Returns a mock token if successful.
    """
    # 1. Search for user by email
    users_ref = db.collection("users")
    query = users_ref.where("email", "==", creds.email).limit(1)
    results = query.stream()
    
    user_doc = None
    for doc in results:
        user_doc = doc
        break
    
    # 2. Check if Account is Disabled
    if user_data.get("status") == "disabled":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been disabled. Contact administrator."
        )
    
    # 3. Check Password
    stored_password = user_data.get("password")
    valid = False
    
    if stored_password:
        if stored_password == creds.password:
            valid = True
    else:
        # Legacy users (seed data) without stored password
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
    
    # 4. Generate Mock Token
    uid = user_doc.id
    role = user_data.get("role", "student")
    token = f"mock-token-{role}-{uid}"
    
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
```

---

### 2. **config.py** (`api/config.py`)

Handles Firebase initialization and provides database clients.

#### Key Features:

**Mock Database Fallback:**
```python
USE_MOCK_DB = os.environ.get("USE_REAL_FIREBASE", "False").lower() == "true"
if not USE_MOCK_DB:
    USE_MOCK_DB = True  # Default to mock for local development

def init_firebase():
    """Initializes Firebase Admin SDK and returns Firestore client."""
    global USE_MOCK_DB
    
    if USE_MOCK_DB:
        return MockFirestoreClient()
    
    # Real Firebase initialization logic
    if not firebase_admin._apps:
        key_path = os.environ.get("FIREBASE_CREDENTIALS")
        if not key_path:
            specific_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "firebase_key.json")
            if os.path.exists(specific_file):
                key_path = specific_file
        
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)
        return firestore.client()
```

**Async Client Support:**
```python
def init_async_firebase():
    """Returns an async Firestore client."""
    if USE_MOCK_DB:
        return MockFirestoreClient()
    # Async client initialization...
```

---

### 3. **users.py** (`api/users.py`)

User management API endpoints for the admin panel.

#### Endpoints:

| Method | Path | Description | Required Role |
|--------|------|-------------|---------------|
| GET | `/api/auth/me` | Get current user profile | Any authenticated |
| GET | `/api/users` | List all users | Admin |
| POST | `/api/users` | Create new user | Admin |
| GET | `/api/users/{id}` | Get user by ID | Admin or self |
| PUT | `/api/users/{id}` | Update user | Admin |
| DELETE | `/api/users/{id}` | Delete user | Admin |
| GET | `/api/subjects/all` | Get all subjects | Admin |
| GET | `/api/departments/{id}/subjects` | Get department subjects | Admin |

#### Request/Response Models:

**UserCreate:**
```python
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    display_name: str
    role: Literal["admin", "staff", "student"]
    department_id: Optional[str] = None
    subject_ids: Optional[List[str]] = None
```

**UserUpdate:**
```python
class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    role: Optional[Literal["admin", "staff", "student"]] = None
    department_id: Optional[str] = None
    subject_ids: Optional[List[str]] = None
    status: Optional[Literal["active", "disabled"]] = None
```

**UserResponse:**
```python
class UserResponse(BaseModel):
    id: str
    email: str
    display_name: Optional[str]
    role: str
    department_id: Optional[str]
    department_name: Optional[str] = None
    subject_ids: Optional[List[str]] = None
    subject_names: Optional[List[str]] = None
    status: str
    created_at: Optional[str]
    updated_at: Optional[str]
```

---

## Frontend Implementation Details

### 1. **useAuthStore.ts** (`frontend/src/stores/useAuthStore.ts`)

Zustand-based authentication state management.

#### State Interface:

```typescript
interface AuthState {
    // State
    user: AuthUser | null;
    firebaseUser: FirebaseUser | null;
    isLoading: boolean;
    isInitialized: boolean;
    error: string | null;

    // Computed (as functions)
    isAuthenticated: () => boolean;
    isAdmin: () => boolean;
    isStaff: () => boolean;
    isStudent: () => boolean;
    canManageHierarchy: () => boolean;
    canManageModules: (departmentId?: string) => boolean;
    canUploadNotes: (departmentId?: string) => boolean;
    canReadNotes: (departmentId?: string) => boolean;

    // Actions
    login: (email: string, password: string) => Promise<void>;
    logout: () => Promise<void>;
    refreshUser: () => Promise<void>;
    setUser: (user: AuthUser | null) => void;
    setFirebaseUser: (user: FirebaseUser | null) => void;
    setLoading: (loading: boolean) => void;
    setError: (error: string | null) => void;
    setInitialized: (initialized: boolean) => void;
    getIdToken: () => Promise<string | null>;
}
```

#### AuthUser Interface:

```typescript
export interface AuthUser {
    id: string;
    email: string;
    displayName: string | null;
    role: UserRole;
    departmentId: string | null;
    departmentName: string | null;
    subjectIds: string[] | null;
    status: string;
}
```

#### Permission Functions:

```typescript
canManageHierarchy: () => get().user?.role === 'admin',

canManageModules: (departmentId?: string) => {
    const { user } = get();
    if (!user) return false;
    if (user.role === 'admin') return false;
    if (user.role === 'staff') {
        if (!departmentId) return true;
        return user.departmentId === departmentId;
    }
    return false;
},

canUploadNotes: (departmentId?: string) => {
    const { user } = get();
    if (!user) return false;
    if (user.role === 'admin') return false;
    if (user.role === 'student') return false;
    if (user.role === 'staff') {
        if (!departmentId) return true;
        return user.departmentId === departmentId;
    }
    return false;
},

canReadNotes: (departmentId?: string) => {
    const { user } = get();
    if (!user) return false;
    if (user.role === 'admin') return true;
    if (!departmentId) return true;
    return user.departmentId === departmentId;
}
```

#### Login Action:

```typescript
login: async (email: string, password: string) => {
    set({ isLoading: true, error: null });

    try {
        // Call the mock login endpoint
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Login failed");
        }

        const data = await res.json();
        const { token, user: userData } = data;

        const authUser: AuthUser = {
            id: userData.id,
            email: userData.email,
            displayName: userData.displayName || 'User',
            role: userData.role,
            departmentId: userData.departmentId,
            departmentName: null,
            subjectIds: userData.subjectIds || null,
            status: 'active'
        };

        // Store in LocalStorage
        localStorage.setItem('mock_token', token);
        localStorage.setItem('mock_user', JSON.stringify(authUser));

        set({
            user: authUser,
            firebaseUser: null,
            isLoading: false,
            error: null,
        });

    } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Login failed';
        set({
            user: null,
            isLoading: false,
            error: errorMessage
        });
        throw error;
    }
}
```

#### Auth Initialization:

```typescript
export function initAuthListener() {
    const store = useAuthStore.getState();

    // MOCK AUTH INITIALIZATION
    const mockToken = localStorage.getItem('mock_token');
    const mockUserStr = localStorage.getItem('mock_user');

    if (mockToken && mockUserStr) {
        try {
            const mockUser = JSON.parse(mockUserStr);
            store.setUser(mockUser);
            store.setFirebaseUser(null);
            store.setInitialized(true);
            store.refreshUser();
            return () => { };
        } catch (e) {
            console.error("Failed to restore mock session", e);
            localStorage.removeItem('mock_token');
            localStorage.removeItem('mock_user');
        }
    }

    // Real Firebase auth listener
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
        if (firebaseUser) {
            store.setFirebaseUser(firebaseUser);
            await store.refreshUser();
        } else {
            if (!localStorage.getItem('mock_token')) {
                store.setUser(null);
                store.setFirebaseUser(null);
                store.setLoading(false);
            }
        }
        store.setInitialized(true);
    });

    return unsubscribe;
}
```

---

### 2. **LoginPage.tsx** (`frontend/src/pages/LoginPage.tsx`)

Login form component with validation and error handling.

#### Key Features:
- Email/password form with validation
- Loading state during authentication
- Error display for failed login attempts
- Redirect to appropriate page after login (admin → /admin, others → /)
- Styled with Tailwind CSS

---

### 3. **ProtectedRoute.tsx** (`frontend/src/components/ProtectedRoute.tsx`)

Route guard component for protected pages.

#### Props Interface:

```typescript
interface ProtectedRouteProps {
    children: ReactNode;
    requiredRole?: UserRole | UserRole[];
    requiredDepartment?: string;
}
```

#### Implementation:

```typescript
export function ProtectedRoute({
    children,
    requiredRole,
    requiredDepartment
}: ProtectedRouteProps) {
    const location = useLocation();
    const { user, isLoading, isInitialized } = useAuthStore();

    // Show loading state while auth is initializing
    if (!isInitialized || isLoading) {
        return <LoadingSpinner />;
    }

    // Redirect to login if not authenticated
    if (!user) {
        return <Navigate to="/login" state={{ from: location.pathname }} replace />;
    }

    // Check role requirement
    if (requiredRole) {
        const roles = Array.isArray(requiredRole) ? requiredRole : [requiredRole];
        if (!roles.includes(user.role)) {
            return <Navigate to="/" replace />;
        }
    }

    // Check department requirement
    if (requiredDepartment && user.role !== 'admin') {
        if (user.departmentId !== requiredDepartment) {
            return <Navigate to="/" replace />;
        }
    }

    return <>{children}</>;
}
```

---

### 4. **App.tsx** (`frontend/src/App.tsx`)

Root application component with routing configuration.

```typescript
function App() {
    useEffect(() => {
        const unsubscribe = initAuthListener();
        return () => unsubscribe();
    }, []);

    return (
        <BrowserRouter>
            <Toaster position="bottom-right" richColors closeButton />
            <Routes>
                <Route path="/login" element={<LoginPage />} />

                <Route path="/admin/*" element={
                    <ProtectedRoute requiredRole="admin">
                        <AdminDashboard />
                    </ProtectedRoute>
                } />

                <Route path="/*" element={
                    <ProtectedRoute>
                        <ExplorerPage />
                    </ProtectedRoute>
                } />
            </Routes>
        </BrowserRouter>
    );
}
```

---

## Database Schema

### Firestore Collections

#### **users** Collection

| Field | Type | Description |
|-------|------|-------------|
| id | string | User UID (document ID) |
| email | string | User email address |
| displayName | string | User's display name |
| role | string | User role ("admin", "staff", "student") |
| departmentId | string | Assigned department ID (null for admin) |
| subjectIds | array | Array of subject IDs (for staff) |
| status | string | Account status ("active", "disabled") |
| password | string | Stored password (plain text for mock auth only!) |
| createdAt | string | ISO timestamp of creation |
| updatedAt | string | ISO timestamp of last update |

#### Sample Documents:

**Admin User:**
```json
{
  "id": "mock-user-1769428084546",
  "email": "admin@test.com",
  "displayName": "Test Admin",
  "role": "admin",
  "departmentId": null,
  "subjectIds": null,
  "status": "active",
  "password": "Admin123!",
  "createdAt": "2024-01-01T00:00:00.000Z",
  "updatedAt": "2024-01-01T00:00:00.000Z"
}
```

**Staff User:**
```json
{
  "id": "mock-user-arun",
  "email": "arun@test.com",
  "displayName": "Arun",
  "role": "staff",
  "departmentId": "407ac4a3-329c-4aa1-9",
  "subjectIds": ["subject-uuid-1", "subject-uuid-2"],
  "status": "active",
  "password": "password",
  "createdAt": "2024-01-01T00:00:00.000Z",
  "updatedAt": "2024-01-01T00:00:00.000Z"
}
```

**Student User:**
```json
{
  "id": "mock-user-ibu",
  "email": "ibu@test.com",
  "displayName": "Ibu",
  "role": "student",
  "departmentId": "407ac4a3-329c-4aa1-9",
  "subjectIds": null,
  "status": "active",
  "password": "password",
  "createdAt": "2024-01-01T00:00:00.000Z",
  "updatedAt": "2024-01-01T00:00:00.000Z"
}
```

---

## Mock Authentication System

### Overview

The mock authentication system is designed for local development and testing without requiring real Firebase credentials.

### Token Format

```
mock-token-{role}-{uid}
```

**Examples:**
- Admin: `mock-token-admin-mock-user-1769428084546`
- Staff: `mock-token-staff-mock-user-arun`
- Student: `mock-token-student-mock-user-ibu`

### Mock Token Verification

```python
def verify_firebase_token(token: str) -> dict:
    if token.startswith("mock-token-"):
        parts = token.split("-")
        role = parts[2]
        uid = "-".join(parts[3:])
        
        return {
            "uid": uid,
            "email": f"{role}@test.com",
            "name": f"Mock {role.capitalize()}",
            "role": role
        }
    # Fall through to real Firebase verification...
```

### Mock Login Flow

1. User enters email/password on LoginPage
2. Frontend calls `/api/auth/login` endpoint
3. Backend queries Firestore `users` collection by email
4. Backend checks password (plain text or legacy)
5. Backend generates mock token: `mock-token-{role}-{uid}`
6. Backend returns token and user data
7. Frontend stores token in localStorage
8. Frontend sets authentication state

### Mock Users (Seed Data)

| Email | Password | Role | Department |
|-------|----------|------|------------|
| admin@test.com | Admin123! | admin | - |
| arun@test.com | password | staff | Computer Science |
| ibu@test.com | password | student | Computer Science |
| ram@test.com | password | student | Electrical |

---

## Implementation Guide for AURA-NOTES-MANAGER

### Overview

The AURA-NOTES-MANAGER project currently lacks authentication. Below is a step-by-step guide to implement the same authentication system.

---

### Step 1: Create Backend auth.py

**File:** `api/auth.py`

Copy the entire content from `AURA-PROTO---ADMIN-PANEL/api/auth.py` to `AURA-NOTES-MANAGER/api/auth.py`

**Changes Required:**
1. Update file header comments to reflect new project location
2. Ensure import paths work with AURA-NOTES-MANAGER structure:
   ```python
   # Change from:
   from config import db
   # To (with fallback):
   try:
       from config import db
   except ImportError:
       from api.config import db
   ```

---

### Step 2: Update config.py

**File:** `api/config.py`

Ensure the following functionality exists:
1. Firebase initialization with credentials path resolution
2. Mock database fallback (`USE_REAL_FIREBASE` env var)
3. Async Firestore client support
4. Export both `db` and `auth` variables

**Key Functions:**
```python
def init_firebase():
    """Initialize Firebase Admin SDK and return Firestore client."""
    USE_MOCK_DB = os.environ.get("USE_REAL_FIREBASE", "False").lower() == "true"
    if not USE_MOCK_DB:
        USE_MOCK_DB = True
    
    if USE_MOCK_DB:
        from mock_firestore import MockFirestoreClient
        return MockFirestoreClient()
    
    # Real Firebase initialization...
```

---

### Step 3: Copy or Create mock_firestore.py

**File:** `api/mock_firestore.py`

This file provides a complete mock implementation of Firestore for local development.

**Key Classes:**
1. `MockFirestoreClient` - Sync Firestore client
2. `MockAuth` - Mock Firebase Auth
3. `MockDocumentSnapshot` - Document snapshot wrapper
4. `MockQuery` - Query builder with where/limit support

**Key Methods:**
```python
class MockFirestoreClient:
    def collection(self, name):
        """Get a collection reference."""
        return MockCollection(name)
    
    def collection_group(self, name):
        """Get a collection group reference."""
        return MockCollectionGroup(name)

class MockCollection:
    def document(self, doc_id=None):
        """Get a document reference."""
        return MockDocumentReference(self, doc_id)
    
    def where(self, field, op, value):
        """Add a where clause."""
        return MockQuery(self, field, op, value)
    
    def stream(self):
        """Execute query and yield documents."""
        # Implementation...

class MockDocumentReference:
    def get(self):
        """Get document snapshot."""
        return MockDocumentSnapshot(self._data, self._id)
    
    def set(self, data):
        """Set document data."""
        self._data = data
    
    def update(self, data):
        """Update document data."""
        self._data.update(data)
    
    def delete(self):
        """Delete document."""
        self._data = None

class MockAuth:
    def create_user(self, email, password, display_name):
        """Create a user."""
        return MockUser(email, uid=f"mock-uid-{email}")
    
    def verify_id_token(self, token, clock_skew_seconds=10):
        """Verify ID token."""
        if token.startswith("mock-token-"):
            # Parse and return claims...
```

---

### Step 4: Update main.py

**File:** `api/main.py`

Add the auth router and CORS configuration:

```python
# Import auth router
from auth import router as auth_router
app.include_router(auth_router)  # Mock Auth endpoint

# CORS configuration
origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

### Step 5: Create users.py for User Management

**File:** `api/users.py`

Implement user CRUD endpoints:

```python
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Literal
from datetime import datetime

try:
    from config import db, auth as firebase_auth
    from auth import get_current_user, require_admin, UserInfo
except ImportError:
    from api.config import db, auth as firebase_auth
    from api.auth import get_current_user, require_admin, UserInfo

router = APIRouter(prefix="/api", tags=["users"])

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    display_name: str
    role: Literal["admin", "staff", "student"]
    department_id: Optional[str] = None
    subject_ids: Optional[List[str]] = None

class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    role: Optional[Literal["admin", "staff", "student"]] = None
    department_id: Optional[str] = None
    subject_ids: Optional[List[str]] = None
    status: Optional[Literal["active", "disabled"]] = None

@router.get("/auth/me")
async def get_me(user: UserInfo = Depends(get_current_user)):
    """Get current authenticated user profile."""
    user_doc = db.collection("users").document(user.uid).get()
    user_data = user_doc.to_dict() if user_doc.exists else {}
    return {
        "id": user.uid,
        "email": user.email,
        "displayName": user.display_name,
        "role": user.role,
        "departmentId": user.department_id,
        "departmentName": None,
        "status": user.status,
        "createdAt": user_data.get("createdAt"),
        "updatedAt": user_data.get("updatedAt"),
    }

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    role: Optional[str] = None,
    department_id: Optional[str] = None,
    admin: UserInfo = Depends(require_admin),
):
    """List all users. Admin only."""
    # Implementation...

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate, admin: UserInfo = Depends(require_admin)):
    """Create a new user. Admin only."""
    # Implementation...

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, update_data: UserUpdate, admin: UserInfo = Depends(require_admin)):
    """Update a user. Admin only."""
    # Implementation...

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str, admin: UserInfo = Depends(require_admin)):
    """Delete a user. Admin only."""
    # Implementation...
```

---

### Step 6: Frontend Authentication

#### Step 6.1: Copy useAuthStore.ts

**File:** `frontend/src/stores/useAuthStore.ts`

Copy from `AURA-PROTO---ADMIN-PANEL/frontend/src/stores/useAuthStore.ts`

**Changes Required:**
1. Update file header comments
2. Verify API base URL: `/api` (or match AURA-NOTES-MANAGER backend port)

#### Step 6.2: Copy LoginPage.tsx

**File:** `frontend/src/pages/LoginPage.tsx`

Copy from `AURA-PROTO---ADMIN-PANEL/frontend/src/pages/LoginPage.tsx`

#### Step 6.3: Copy ProtectedRoute.tsx

**File:** `frontend/src/components/ProtectedRoute.tsx`

Copy from `AURA-PROTO---ADMIN-PANEL/frontend/src/components/ProtectedRoute.tsx`

#### Step 6.4: Update App.tsx

**File:** `frontend/src/App.tsx`

Add authentication initialization and protected routes:

```typescript
import { useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Toaster } from 'sonner';
import { initAuthListener } from './stores/useAuthStore';
import { ProtectedRoute } from './components/ProtectedRoute';
import LoginPage from './pages/LoginPage';
import Dashboard from './pages/Dashboard';

function App() {
    useEffect(() => {
        const unsubscribe = initAuthListener();
        return () => unsubscribe();
    }, []);

    return (
        <BrowserRouter>
            <Toaster position="bottom-right" richColors closeButton />
            <Routes>
                <Route path="/login" element={<LoginPage />} />
                
                <Route path="/admin/*" element={
                    <ProtectedRoute requiredRole="admin">
                        <AdminDashboard />
                    </ProtectedRoute>
                } />
                
                <Route path="/*" element={
                    <ProtectedRoute>
                        <Dashboard />
                    </ProtectedRoute>
                } />
            </Routes>
        </BrowserRouter>
    );
}

export default App;
```

---

### Step 7: Update API Client

**File:** `frontend/src/api/client.ts`

Ensure API requests include auth headers:

```typescript
const API_BASE = '/api';

async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
    const token = localStorage.getItem('mock_token');
    
    const headers = {
        ...options.headers,
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    };
    
    return fetch(`${API_BASE}${url}`, {
        ...options,
        headers,
    });
}

export async function apiGet<T>(url: string): Promise<T> {
    const response = await fetchWithAuth(url);
    if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
    }
    return response.json();
}

export async function apiPost<T>(url: string, data: unknown): Promise<T> {
    const response = await fetchWithAuth(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
    }
    return response.json();
}
```

---

### Step 8: Create Seed Data

Create initial users in Firestore for testing:

```python
# In a script or via Admin Dashboard
SEED_USERS = [
    {
        "id": "mock-admin-001",
        "email": "admin@aura.local",
        "displayName": "System Admin",
        "role": "admin",
        "departmentId": None,
        "subjectIds": None,
        "status": "active",
        "password": "Admin123!",
        "createdAt": "2024-01-01T00:00:00.000Z",
        "updatedAt": "2024-01-01T00:00:00.000Z"
    },
    {
        "id": "mock-staff-001",
        "email": "staff@aura.local",
        "displayName": "Teaching Staff",
        "role": "staff",
        "departmentId": "dept-cs-001",
        "subjectIds": ["subject-001", "subject-002"],
        "status": "active",
        "password": "Staff123!",
        "createdAt": "2024-01-01T00:00:00.000Z",
        "updatedAt": "2024-01-01T00:00:00.000Z"
    },
    {
        "id": "mock-student-001",
        "email": "student@aura.local",
        "displayName": "Student User",
        "role": "student",
        "departmentId": "dept-cs-001",
        "subjectIds": None,
        "status": "active",
        "password": "Student123!",
        "createdAt": "2024-01-01T00:00:00.000Z",
        "updatedAt": "2024-01-01T00:00:00.000Z"
    },
]

# Insert into Firestore
for user in SEED_USERS:
    db.collection("users").document(user["id"]).set(user)
```

---

### Step 9: Install Dependencies

**Backend (`requirements.txt`):**
```
firebase-admin>=6.0.0
fastapi>=0.100.0
uvicorn>=0.23.0
python-multipart>=0.0.6
python-dotenv>=1.0.0
slowapi>=0.1.8
google-cloud-firestore>=2.11.0
```

**Frontend (`frontend/package.json`):**
```json
{
  "dependencies": {
    "firebase": "^10.0.0",
    "zustand": "^4.4.0",
    "react-router-dom": "^6.20.0",
    "sonner": "^1.2.0"
  },
  "devDependencies": {
    "@types/react-router-dom": "^5.3.3"
  }
}
```

---

### Step 10: Environment Configuration

**File:** `.env` (project root)
```
# Set to "true" to use real Firebase
USE_REAL_FIREBASE=false

# Firebase credentials (only needed for real Firebase)
FIREBASE_CREDENTIALS=serviceAccountKey.json
GOOGLE_APPLICATION_CREDENTIALS=serviceAccountKey.json

# Frontend proxy
VITE_API_URL=http://localhost:8001
```

---

## Security Considerations

### 1. Password Handling

**Current Implementation (INSECURE):**
- Passwords stored in plain text (mock auth only)
- Passwords stored in Firestore documents

**Production Requirements:**
- Use Firebase Auth for user management
- Never store passwords in Firestore
- Use Firebase Auth's `create_user`, `update_user`, `delete_user`
- Implement proper password reset via Firebase Auth

### 2. Token Security

**Current Implementation:**
- Mock tokens stored in localStorage
- No token expiration
- Simple token format (mock-token-{role}-{uid})

**Production Requirements:**
- Use Firebase ID tokens (JWT)
- Tokens automatically expire (1 hour)
- Use Firebase Auth's `verify_id_token`
- Implement token refresh mechanism

### 3. API Security

**Current Implementation:**
- Bearer token authentication
- Role-based endpoint protection
- Department access validation

**Enhancements:**
- Rate limiting (already implemented via slowapi)
- Request logging
- Input validation with Pydantic
- CORS configuration

### 4. Firestore Security Rules

**Required Rules:**
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users can read their own profile
    match /users/{userId} {
      allow read: if request.auth != null && request.auth.uid == userId;
      allow write: if request.auth != null && request.auth.uid == userId 
                   && request.resource.data.role == resource.data.role;
    }
    
    // Admins can manage all users
    match /users/{userId} {
      allow read, write: if request.auth != null 
                          && get(/databases/$(database)/documents/users/$(request.auth.uid)).data.role == 'admin';
    }
    
    // Hierarchical data access rules...
  }
}
```

---

## Testing Checklist

### Backend Testing

- [ ] Mock login endpoint returns correct token format
- [ ] Token verification extracts role correctly
- [ ] `require_admin` blocks non-admin users
- [ ] `require_staff` allows both admin and staff
- [ ] `require_department_access` validates department
- [ ] User CRUD operations work correctly
- [ ] Disabled accounts cannot authenticate

### Frontend Testing

- [ ] Login page redirects to appropriate page
- [ ] ProtectedRoute redirects to login when unauthenticated
- [ ] Role-based route protection works
- [ ] Department-based access restriction works
- [ ] Auth state persists after page refresh
- [ ] Logout clears auth state

---

## Summary

This authentication system provides:

1. **Three-tier role-based access** (admin, staff, student)
2. **Department-level data isolation** for staff and students
3. **Protected routes** with FastAPI dependencies
4. **Mock authentication** for local development
5. **Zustand state management** on the frontend
6. **Route guards** with role requirements
7. **User management** CRUD operations

To implement in AURA-NOTES-MANAGER:
1. Copy `auth.py`, `config.py`, `users.py`, and `mock_firestore.py` to backend
2. Copy frontend files (`useAuthStore.ts`, `LoginPage.tsx`, `ProtectedRoute.tsx`, `App.tsx`)
3. Update import paths and API base URLs
4. Install required dependencies
5. Create seed users for testing
6. Configure environment variables

---

**Document Version:** 1.0  
**Last Updated:** 2026-02-03  
**Project:** AURA-PROTO-ADMIN-PANEL
