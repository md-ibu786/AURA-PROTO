# Firebase Firestore Schema

## Collection: users

Document ID: `{uid}` (matches Firebase Auth UID)

### Schema Definition

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| uid | string | Yes | Primary key, matches Firebase Auth UID |
| email | string | Yes | User's email address |
| displayName | string | No | User's display name |
| role | string | Yes | Enum: 'admin', 'staff', 'student' |
| status | string | Yes | Enum: 'active', 'disabled' |
| departmentId | string | Conditional | Required for 'student' role. References departments/{id} |
| subjectIds | array<string> | Conditional | Required for 'staff' role. Array of subject references |
| createdAt | string (ISO 8601) | Yes | Document creation time |
| updatedAt | string (ISO 8601) | Yes | Last update time |
| _v | number | Yes | Schema version (current: 1) |

### Field Constraints

- role must be one of: 'admin', 'staff', 'student'
- status must be one of: 'active', 'disabled'
- departmentId required when role == 'student'
- subjectIds required when role == 'staff'
- subjectIds should be empty when role == 'admin' or 'student'
- uid must match request.auth.uid on create/update

### Example Documents

#### Admin User
```json
{
  "uid": "abc123",
  "email": "admin@aura.edu",
  "displayName": "System Administrator",
  "role": "admin",
  "status": "active",
  "departmentId": null,
  "subjectIds": [],
  "createdAt": "2026-02-04T10:00:00Z",
  "updatedAt": "2026-02-04T10:00:00Z",
  "_v": 1
}
```

#### Staff User
```json
{
  "uid": "def456",
  "email": "staff@aura.edu",
  "displayName": "Math Teacher",
  "role": "staff",
  "status": "active",
  "departmentId": "dept-math",
  "subjectIds": ["sub-calc-1", "sub-algebra"],
  "createdAt": "2026-02-04T10:00:00Z",
  "updatedAt": "2026-02-04T10:00:00Z",
  "_v": 1
}
```

#### Student User
```json
{
  "uid": "ghi789",
  "email": "student@aura.edu",
  "displayName": "John Doe",
  "role": "student",
  "status": "active",
  "departmentId": "dept-cs",
  "subjectIds": [],
  "createdAt": "2026-02-04T10:00:00Z",
  "updatedAt": "2026-02-04T10:00:00Z",
  "_v": 1
}
```

### Schema Versioning

- Include `_v: 1` on all user documents to track schema version.
- Increment `_v` when a breaking schema change is introduced.
- Migration scripts should read `_v` to apply correct transforms.

### Index Recommendations

- Single-field indexes (automatic): role, status, departmentId.
- Composite indexes (create as needed):
- role + status (admin filtering by active/disabled)
- role + departmentId (students by department)
- Array membership queries on subjectIds (Firestore supports array-contains).

### Security Considerations

- Enforce `request.auth.uid == resource.id` for user self-access.
- Only admins can create/update other users or change status.
- Do not store plaintext passwords in Firestore (mock-only legacy field should be removed in production).
- Validate role, departmentId, and subjectIds on every write.
- Use server timestamps for createdAt/updatedAt when possible.
