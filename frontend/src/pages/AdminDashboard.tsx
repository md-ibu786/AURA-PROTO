/**
 * ============================================================================
 * FILE: AdminDashboard.tsx
 * LOCATION: frontend/src/pages/AdminDashboard.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Admin dashboard page for managing users, departments, and semesters.
 *    Uses the Explorer theme for visual consistency.
 *
 * ROLE IN PROJECT:
 *    Central administration interface for:
 *    - Creating new users (staff/students)
 *    - Managing departments and semesters
 *    - Assigning users to departments
 *    - Viewing user list with filters
 *
 * DEPENDENCIES:
 *    - External: react, react-router-dom
 *    - Internal: stores/useAuthStore, styles/index.css
 *
 * USAGE:
 *    Route: /admin (protected, admin-only)
 * ============================================================================
 */

import { useState, useEffect, useCallback, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore, type UserRole } from '../stores/useAuthStore';
import '../styles/index.css';

// User interface for the list
interface UserItem {
    id: string;
    email: string;
    display_name: string | null;
    role: UserRole;
    department_id: string | null;
    department_name: string | null;
    subject_ids: string[] | null;
    subject_names: string[] | null;
    status: string;
    created_at: string | null;
}

// Department interface
interface Department {
    id: string;
    name: string;
    code?: string;
}

// Semester interface
interface Semester {
    id: string;
    name: string;
    semester_number: number;
    department_id: string;
}

// Subject interface
interface Subject {
    id: string;
    name: string;
    code: string;
    semester_id: string;
}

const API_BASE = '/api';

type TabType = 'users' | 'hierarchy';

export function AdminDashboard() {
    const navigate = useNavigate();
    const { user, logout, getIdToken } = useAuthStore();

    // Tab state
    const [activeTab, setActiveTab] = useState<TabType>('users');

    // State
    const [users, setUsers] = useState<UserItem[]>([]);
    const [departments, setDepartments] = useState<Department[]>([]);
    const [semesters, setSemesters] = useState<Semester[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Create user form state
    const [showCreateForm, setShowCreateForm] = useState(false);
    const [createForm, setCreateForm] = useState({
        email: '',
        password: '',
        display_name: '',
        role: 'staff' as UserRole,
        department_id: '',
        subject_ids: [] as string[],
    });
    const [createLoading, setCreateLoading] = useState(false);
    const [createError, setCreateError] = useState<string | null>(null);

    // Department form state
    const [showDeptForm, setShowDeptForm] = useState(false);
    const [deptForm, setDeptForm] = useState({ name: '', code: '' });
    const [deptLoading, setDeptLoading] = useState(false);

    // Semester form state
    const [showSemForm, setShowSemForm] = useState(false);
    const [semForm, setSemForm] = useState({ department_id: '', name: '', semester_number: 1 });
    const [semLoading, setSemLoading] = useState(false);

    // Subject state
    const [subjects, setSubjects] = useState<Subject[]>([]);
    const [showSubjForm, setShowSubjForm] = useState(false);
    const [subjForm, setSubjForm] = useState({ semester_id: '', name: '', code: '' });
    const [subjLoading, setSubjLoading] = useState(false);
    const [selectedSemId, setSelectedSemId] = useState<string>('');

    // All subjects for staff assignment (grouped by department)
    const [departmentSubjects, setDepartmentSubjects] = useState<Map<string, Subject[]>>(new Map());
    const [currentDeptForSubjects, setCurrentDeptForSubjects] = useState<string>('');
    const [selectedSubjectsByDept, setSelectedSubjectsByDept] = useState<Map<string, string[]>>(new Map());

    // Edit subjects modal state
    const [editingUserId, setEditingUserId] = useState<string | null>(null);
    const [editingSubjectIds, setEditingSubjectIds] = useState<string[]>([]);
    const [editingCurrentDeptId, setEditingCurrentDeptId] = useState<string>('');

    // Rename state for inline editing
    const [renamingId, setRenamingId] = useState<string | null>(null);
    const [renamingType, setRenamingType] = useState<'department' | 'semester' | 'subject' | null>(null);
    const [renameValue, setRenameValue] = useState('');

    // Selected department for semester view
    const [selectedDeptId, setSelectedDeptId] = useState<string>('');

    // Filter state
    const [roleFilter, setRoleFilter] = useState<string>('');
    const [departmentFilter, setDepartmentFilter] = useState<string>('');

    const fetchData = useCallback(async () => {
        setIsLoading(true);
        setError(null);

        try {
            const token = await getIdToken();
            if (!token) throw new Error('Not authenticated');

            // Build query params
            const params = new URLSearchParams();
            if (roleFilter) params.append('role', roleFilter);
            if (departmentFilter) params.append('department_id', departmentFilter);

            // Fetch users
            const usersRes = await fetch(`${API_BASE}/users?${params}`, {
                headers: { 'Authorization': `Bearer ${token}` },
            });
            if (!usersRes.ok) throw new Error('Failed to fetch users');
            const usersData = await usersRes.json();
            setUsers(usersData);

            // Fetch departments and subjects grouped by department
            const deptRes = await fetch('/departments');
            let fetchedDepartments: Department[] = [];
            if (deptRes.ok) {
                const deptData = await deptRes.json();
                fetchedDepartments = deptData.departments || [];
                setDepartments(fetchedDepartments);
            }

            // Fetch subjects grouped by department for staff assignment
            const deptMap = new Map<string, Subject[]>();
            for (const dept of fetchedDepartments) {
                try {
                    const deptSubjRes = await fetch(`${API_BASE}/departments/${dept.id}/subjects`, {
                        headers: { 'Authorization': `Bearer ${token}` },
                    });
                    if (deptSubjRes.ok) {
                        const deptSubjData = await deptSubjRes.json();
                        deptMap.set(dept.id, deptSubjData.subjects || []);
                    }
                } catch {
                    deptMap.set(dept.id, []);
                }
            }
            setDepartmentSubjects(deptMap);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'An error occurred');
        } finally {
            setIsLoading(false);
        }
    }, [departmentFilter, getIdToken, roleFilter]);

    const fetchSemesters = useCallback(async (deptId: string) => {
        try {
            const res = await fetch(`/departments/${deptId}/semesters`);
            if (res.ok) {
                const data = await res.json();
                setSemesters(data.semesters || []);
            }
        } catch (err) {
            console.error('Failed to fetch semesters', err);
        }
    }, []);

    // Fetch users and departments on mount
    useEffect(() => {
        fetchData();
    }, [fetchData]);

    // Fetch semesters when selected department changes
    useEffect(() => {
        if (selectedDeptId) {
            fetchSemesters(selectedDeptId);
        } else {
            setSemesters([]);
        }
    }, [fetchSemesters, selectedDeptId]);

    const handleCreateUser = async (e: FormEvent) => {
        e.preventDefault();
        setCreateLoading(true);
        setCreateError(null);

        try {
            const token = await getIdToken();
            if (!token) throw new Error('Not authenticated');

            // Build request body based on role
            const requestBody: Record<string, unknown> = {
                email: createForm.email,
                password: createForm.password,
                display_name: createForm.display_name,
                role: createForm.role,
            };

            if (createForm.role === 'staff') {
                // Staff requires subject_ids
                if (createForm.subject_ids.length === 0) {
                    throw new Error('At least one subject is required for staff');
                }
                requestBody.subject_ids = createForm.subject_ids;
            } else if (createForm.role === 'student') {
                // Student requires department_id
                if (!createForm.department_id) {
                    throw new Error('Department is required for students');
                }
                requestBody.department_id = createForm.department_id;
            }

            const response = await fetch(`${API_BASE}/users`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to create user');
            }

            // Reset form and refresh list
            setCreateForm({
                email: '',
                password: '',
                display_name: '',
                role: 'staff',
                department_id: '',
                subject_ids: [],
            });
            setShowCreateForm(false);
            fetchData();
        } catch (err) {
            let message = err instanceof Error ? err.message : 'Failed to create user';
            if (message.includes('already exists')) {
                message = "This email address is already registered. Please use a different email or check the existing user list.";
            }
            setCreateError(message);
        } finally {
            setCreateLoading(false);
        }
    };

    const handleDeleteUser = async (userId: string) => {
        if (!confirm('Are you sure you want to delete this user?')) return;

        try {
            const token = await getIdToken();
            if (!token) throw new Error('Not authenticated');

            const response = await fetch(`${API_BASE}/users/${userId}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` },
            });

            if (!response.ok) {
                // If 404, it's already gone, so just update UI
                if (response.status === 404) {
                    setUsers(prev => prev.filter(u => u.id !== userId));
                    return;
                }
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to delete user');
            }

            // Refresh list
            fetchData();
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Failed to delete user');
        }
    };

    const handleToggleStatus = async (userId: string, currentStatus: string) => {
        const newStatus = currentStatus === 'active' ? 'disabled' : 'active';

        try {
            const token = await getIdToken();
            if (!token) throw new Error('Not authenticated');

            const response = await fetch(`${API_BASE}/users/${userId}`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ status: newStatus }),
            });

            if (!response.ok) {
                throw new Error('Failed to update user status');
            }

            fetchData();
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Failed to update status');
        }
    };

    // Handle updating staff subject assignments
    const handleUpdateSubjects = async () => {
        if (!editingUserId || editingSubjectIds.length === 0) {
            alert('Please select at least one subject');
            return;
        }

        try {
            const token = await getIdToken();
            if (!token) throw new Error('Not authenticated');

            const response = await fetch(`${API_BASE}/users/${editingUserId}`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ subject_ids: editingSubjectIds }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Failed to update subjects');
            }

            // Close modal and refresh
            setEditingUserId(null);
            setEditingSubjectIds([]);
            fetchData();
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Failed to update subjects');
        }
    };

    // Department CRUD
    const handleCreateDepartment = async (e: FormEvent) => {
        e.preventDefault();
        setDeptLoading(true);
        try {
            const token = await getIdToken();
            const res = await fetch(`${API_BASE}/departments`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(deptForm),
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || 'Failed to create department');
            }
            setDeptForm({ name: '', code: '' });
            setShowDeptForm(false);
            fetchData();
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Failed to create department');
        } finally {
            setDeptLoading(false);
        }
    };

    const handleDeleteDepartment = async (deptId: string) => {
        if (!confirm('Delete this department and all its contents?')) return;
        try {
            const token = await getIdToken();
            const res = await fetch(`${API_BASE}/departments/${deptId}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` },
            });
            if (!res.ok) throw new Error('Failed to delete department');
            fetchData();
            if (selectedDeptId === deptId) setSelectedDeptId('');
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Failed to delete department');
        }
    };

    // Semester CRUD
    const handleCreateSemester = async (e: FormEvent) => {
        e.preventDefault();
        setSemLoading(true);
        try {
            const token = await getIdToken();
            const res = await fetch(`${API_BASE}/semesters`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(semForm),
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || 'Failed to create semester');
            }
            setSemForm({ department_id: selectedDeptId, name: '', semester_number: 1 });
            setShowSemForm(false);
            fetchSemesters(selectedDeptId);
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Failed to create semester');
        } finally {
            setSemLoading(false);
        }
    };

    const handleDeleteSemester = async (semId: string) => {
        if (!confirm('Delete this semester and all its contents?')) return;
        try {
            const token = await getIdToken();
            const res = await fetch(`${API_BASE}/semesters/${semId}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` },
            });
            if (!res.ok) throw new Error('Failed to delete semester');
            fetchSemesters(selectedDeptId);
            if (selectedSemId === semId) {
                setSelectedSemId('');
                setSubjects([]);
            }
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Failed to delete semester');
        }
    };

    // Subject functions
    const fetchSubjects = async (semesterId: string) => {
        if (!semesterId) {
            setSubjects([]);
            return;
        }
        try {
            const token = await getIdToken();
            const res = await fetch(`/semesters/${semesterId}/subjects?department_id=${selectedDeptId}`, {
                headers: { 'Authorization': `Bearer ${token}` },
            });
            if (res.ok) {
                const data = await res.json();
                setSubjects(data.subjects || []);
            }
        } catch (err) {
            console.error('Failed to fetch subjects:', err);
        }
    };

    const handleCreateSubject = async (e: FormEvent) => {
        e.preventDefault();
        if (!selectedSemId) return;
        setSubjLoading(true);
        try {
            const token = await getIdToken();
            const res = await fetch(`${API_BASE}/subjects`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    semester_id: selectedSemId,
                    department_id: selectedDeptId,
                    name: subjForm.name,
                    code: subjForm.code
                }),
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || 'Failed to create subject');
            }
            setSubjForm({ semester_id: selectedSemId, name: '', code: '' });
            setShowSubjForm(false);
            fetchSubjects(selectedSemId);
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Failed to create subject');
        } finally {
            setSubjLoading(false);
        }
    };

    const handleDeleteSubject = async (subjId: string) => {
        if (!confirm('Delete this subject and all its contents?')) return;
        try {
            const token = await getIdToken();
            const res = await fetch(`${API_BASE}/subjects/${subjId}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` },
            });
            if (!res.ok) throw new Error('Failed to delete subject');
            fetchSubjects(selectedSemId);
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Failed to delete subject');
        }
    };

    // Rename handlers
    const startRename = (id: string, type: 'department' | 'semester' | 'subject', currentName: string) => {
        setRenamingId(id);
        setRenamingType(type);
        setRenameValue(currentName);
    };

    const cancelRename = () => {
        setRenamingId(null);
        setRenamingType(null);
        setRenameValue('');
    };

    const handleRename = async () => {
        if (!renamingId || !renamingType || !renameValue.trim()) return;

        try {
            const token = await getIdToken();
            let endpoint = '';

            switch (renamingType) {
                case 'department':
                    endpoint = `${API_BASE}/departments/${renamingId}`;
                    break;
                case 'semester':
                    endpoint = `${API_BASE}/semesters/${renamingId}`;
                    break;
                case 'subject':
                    endpoint = `${API_BASE}/subjects/${renamingId}`;
                    break;
            }

            const res = await fetch(endpoint, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name: renameValue.trim() }),
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || 'Failed to rename');
            }

            // Refresh data
            if (renamingType === 'department') {
                fetchData();
            } else if (renamingType === 'semester') {
                fetchSemesters(selectedDeptId);
            } else if (renamingType === 'subject') {
                fetchSubjects(selectedSemId);
            }

            cancelRename();
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Failed to rename');
        }
    };

    const handleLogout = async () => {
        await logout();
        navigate('/login');
    };

    return (
        <div className="admin-dashboard">
            {/* Header */}
            <header className="admin-header">
                <div className="header-left">
                    <h1>Admin Dashboard</h1>
                    <span className="user-badge">
                        Logged in as: {user?.displayName || user?.email}
                    </span>
                </div>
                <div className="header-actions">
                    <button
                        className="btn btn-ghost"
                        onClick={handleLogout}
                    >
                        Logout
                    </button>
                </div>
            </header>

            {/* Tabs */}
            <div className="admin-tabs">
                <button
                    className={`tab-btn ${activeTab === 'users' ? 'active' : ''}`}
                    onClick={() => setActiveTab('users')}
                >
                    User Management
                </button>
                <button
                    className={`tab-btn ${activeTab === 'hierarchy' ? 'active' : ''}`}
                    onClick={() => setActiveTab('hierarchy')}
                >
                    Hierarchy Management
                </button>
            </div>

            {/* Main Content */}
            <main className="admin-content">
                {/* Stats Cards */}
                <div className="stats-grid">
                    <div className="stat-card">
                        <div className="stat-value">{users.filter(u => u.role === 'admin').length}</div>
                        <div className="stat-label">Admins</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-value">{users.filter(u => u.role === 'staff').length}</div>
                        <div className="stat-label">Staff</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-value">{users.filter(u => u.role === 'student').length}</div>
                        <div className="stat-label">Students</div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-value">{departments.length}</div>
                        <div className="stat-label">Departments</div>
                    </div>
                </div>

                {activeTab === 'users' && (
                    <section>
                        <div className="panel-header">
                            <h2>User Management</h2>
                            <button
                                className="btn btn-primary"
                                onClick={() => setShowCreateForm(!showCreateForm)}
                            >
                                {showCreateForm ? 'Cancel' : '+ Create User'}
                            </button>
                        </div>

                        {/* Create User Form */}
                        {showCreateForm && (
                            <form onSubmit={handleCreateUser} className="create-form">
                                <h3>Create New User</h3>

                                <div className="form-row">
                                    <div className="form-group">
                                        <label>Email</label>
                                        <input
                                            type="email"
                                            value={createForm.email}
                                            onChange={e => setCreateForm({ ...createForm, email: e.target.value })}
                                            required
                                        />
                                        {users.some(u => u.email.toLowerCase() === createForm.email.toLowerCase()) && (
                                            <div style={{ color: '#ef4444', fontSize: '0.75rem', marginTop: '4px' }}>
                                                ⚠️ This email belongs to an existing user.
                                            </div>
                                        )}
                                    </div>
                                    <div className="form-group">
                                        <label>Password</label>
                                        <input
                                            type="password"
                                            value={createForm.password}
                                            onChange={e => setCreateForm({ ...createForm, password: e.target.value })}
                                            required
                                            minLength={6}
                                        />
                                    </div>
                                </div>

                                <div className="form-row">
                                    <div className="form-group">
                                        <label>Display Name</label>
                                        <input
                                            type="text"
                                            value={createForm.display_name}
                                            onChange={e => setCreateForm({ ...createForm, display_name: e.target.value })}
                                            required
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label>Role</label>
                                        <select
                                            value={createForm.role}
                                            onChange={e => setCreateForm({ ...createForm, role: e.target.value as UserRole })}
                                        >
                                            <option value="staff">Staff</option>
                                            <option value="student">Student</option>
                                            <option value="admin">Admin</option>
                                        </select>
                                    </div>
                                    {createForm.role === 'student' && (
                                        <div className="form-group">
                                            <label>Department</label>
                                            <select
                                                value={createForm.department_id}
                                                onChange={e => setCreateForm({ ...createForm, department_id: e.target.value })}
                                                required
                                            >
                                                <option value="">Select Department</option>
                                                {departments.map(dept => (
                                                    <option key={dept.id} value={dept.id}>{dept.name}</option>
                                                ))}
                                            </select>
                                        </div>
                                    )}
                                </div>

                                {createForm.role === 'staff' && (
                                    <div className="form-group">
                                        <label>Assign Subjects (by Department)</label>
                                        <div className="subject-hierarchy-container">
                                            {/* Step 1: Select Department */}
                                            <div className="dept-selection-row">
                                                <select
                                                    value={currentDeptForSubjects}
                                                    onChange={e => setCurrentDeptForSubjects(e.target.value)}
                                                    className="dept-select"
                                                >
                                                    <option value="">Select a Department</option>
                                                    {departments.map(dept => (
                                                        <option key={dept.id} value={dept.id}>{dept.name}</option>
                                                    ))}
                                                </select>
                                            </div>

                                            {/* Step 2: Show subjects from selected department */}
                                            {currentDeptForSubjects && (
                                                <div className="subject-selection-panel">
                                                    <h4 className="dept-subheading">
                                                        {departments.find(d => d.id === currentDeptForSubjects)?.name} Subjects:
                                                    </h4>
                                                    {departmentSubjects.get(currentDeptForSubjects)?.length === 0 ? (
                                                        <div className="no-subjects-msg">No subjects in this department</div>
                                                    ) : (
                                                        <div className="subject-checkboxes">
                                                            {departmentSubjects.get(currentDeptForSubjects)?.map(subj => (
                                                                <label key={subj.id} className="subject-checkbox">
                                                                    <input
                                                                        type="checkbox"
                                                                        checked={selectedSubjectsByDept.get(currentDeptForSubjects)?.includes(subj.id) || false}
                                                                        onChange={e => {
                                                                            const currentDeptSubjects = selectedSubjectsByDept.get(currentDeptForSubjects) || [];
                                                                            let newDeptSubjects: string[];
                                                                            if (e.target.checked) {
                                                                                newDeptSubjects = [...currentDeptSubjects, subj.id];
                                                                            } else {
                                                                                newDeptSubjects = currentDeptSubjects.filter(id => id !== subj.id);
                                                                            }
                                                                            const newMap = new Map(selectedSubjectsByDept);
                                                                            newMap.set(currentDeptForSubjects, newDeptSubjects);
                                                                            setSelectedSubjectsByDept(newMap);
                                                                            const allSelected = Array.from(newMap.values()).flat();
                                                                            setCreateForm({ ...createForm, subject_ids: allSelected });
                                                                        }}
                                                                    />
                                                                    <span>{subj.name} ({subj.code})</span>
                                                                </label>
                                                            ))}
                                                        </div>
                                                    )}
                                                </div>
                                            )}

                                            {/* Step 3: Show currently selected subjects by department */}
                                            {createForm.subject_ids.length > 0 && (
                                                <div className="selected-subjects-summary">
                                                    <h4>Selected Subjects:</h4>
                                                    {Array.from(selectedSubjectsByDept.entries()).map(([deptId, subjIds]) => {
                                                        if (subjIds.length === 0) return null;
                                                        const dept = departments.find(d => d.id === deptId);
                                                        const subjNames = subjIds.map(id => {
                                                            const allDeptSubjs = departmentSubjects.get(deptId) || [];
                                                            const s = allDeptSubjs.find(s => s.id === id);
                                                            return s ? `${s.name} (${s.code})` : id;
                                                        });
                                                        return (
                                                            <div key={deptId} className="selected-dept-group">
                                                                <strong>{dept?.name || 'Unknown Department'}:</strong>
                                                                <span className="selected-subj-list">{subjNames.join(', ')}</span>
                                                            </div>
                                                        );
                                                    })}
                                                </div>
                                            )}
                                        </div>
                                        <small className="form-hint">Select a department, then choose subjects. Repeat for multiple departments.</small>
                                    </div>
                                )}

                                {createError && (
                                    <div className="error-message">{createError}</div>
                                )}

                                <button
                                    type="submit"
                                    className="btn btn-primary"
                                    disabled={createLoading}
                                >
                                    {createLoading ? 'Creating...' : 'Create User'}
                                </button>
                            </form>
                        )}

                        {/* Filters */}
                        <div className="filters">
                            <select
                                value={roleFilter}
                                onChange={e => setRoleFilter(e.target.value)}
                            >
                                <option value="">All Roles</option>
                                <option value="admin">Admin</option>
                                <option value="staff">Staff</option>
                                <option value="student">Student</option>
                            </select>
                            <select
                                value={departmentFilter}
                                onChange={e => setDepartmentFilter(e.target.value)}
                            >
                                <option value="">All Departments</option>
                                {departments.map(dept => (
                                    <option key={dept.id} value={dept.id}>{dept.name}</option>
                                ))}
                            </select>
                        </div>

                        {/* Users Table */}
                        {isLoading ? (
                            <div className="loading">Loading users...</div>
                        ) : error ? (
                            <div className="error-message">{error}</div>
                        ) : (
                            <table className="data-table user-table">
                                <thead>
                                    <tr>
                                        <th>Name</th>
                                        <th>Email</th>
                                        <th>Role</th>
                                        <th>Department/Subjects</th>
                                        <th>Status</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {users.length === 0 ? (
                                        <tr>
                                            <td colSpan={6} className="no-data">No users found</td>
                                        </tr>
                                    ) : (
                                        users.map(u => (
                                            <tr key={u.id}>
                                                <td>{u.display_name || '-'}</td>
                                                <td>{u.email}</td>
                                                <td>
                                                    <span className={`role-badge role-${u.role}`}>
                                                        {u.role}
                                                    </span>
                                                </td>
                                                <td>
                                                    {u.role === 'staff'
                                                        ? (u.subject_names?.length
                                                            ? u.subject_names.join(', ')
                                                            : 'No subjects assigned')
                                                        : (u.department_name || '-')}
                                                </td>
                                                <td>
                                                    <span className={`status-badge status-${u.status}`}>
                                                        {u.status}
                                                    </span>
                                                </td>
                                                <td className="actions">
                                                    <div className="flex items-center gap-xs">
                                                        {u.role === 'staff' && (
                                                            <button
                                                                className="btn btn-ghost btn-small"
                                                                onClick={() => {
                                                                    setEditingUserId(u.id);
                                                                    setEditingSubjectIds(u.subject_ids || []);
                                                                }}
                                                            >
                                                                Edit Subjects
                                                            </button>
                                                        )}
                                                        <button
                                                            className="btn btn-ghost btn-small"
                                                            onClick={() => handleToggleStatus(u.id, u.status)}
                                                            disabled={u.id === user?.id}
                                                        >
                                                            {u.status === 'active' ? 'Disable' : 'Enable'}
                                                        </button>
                                                        <button
                                                            className="btn btn-danger btn-small"
                                                            onClick={() => handleDeleteUser(u.id)}
                                                            disabled={u.id === user?.id}
                                                        >
                                                            Delete
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>
                                        ))
                                    )}
                                </tbody>
                            </table>
                        )}
                    </section>
                )}

                {activeTab === 'hierarchy' && (
                    <section className="panel hierarchy-panel">
                        <div className="hierarchy-grid">
                            {/* Departments Column */}
                            <div className="hierarchy-column">
                                <div className="panel-header">
                                    <h2>Departments</h2>
                                    <button
                                        className="btn btn-primary btn-small"
                                        onClick={() => setShowDeptForm(!showDeptForm)}
                                    >
                                        {showDeptForm ? 'Cancel' : '+ Add'}
                                    </button>
                                </div>

                                {showDeptForm && (
                                    <form onSubmit={handleCreateDepartment} className="inline-form">
                                        <input
                                            type="text"
                                            placeholder="Department Name"
                                            value={deptForm.name}
                                            onChange={e => setDeptForm({ ...deptForm, name: e.target.value })}
                                            required
                                        />
                                        <input
                                            type="text"
                                            placeholder="Code (e.g. CS)"
                                            value={deptForm.code}
                                            onChange={e => setDeptForm({ ...deptForm, code: e.target.value })}
                                            required
                                        />
                                        <button type="submit" className="btn btn-primary btn-small" disabled={deptLoading}>
                                            {deptLoading ? '...' : 'Create'}
                                        </button>
                                    </form>
                                )}

                                <div className="hierarchy-list">
                                    {departments.length === 0 ? (
                                        <div className="no-data">No departments</div>
                                    ) : (
                                        departments.map(dept => (
                                            <div
                                                key={dept.id}
                                                className={`hierarchy-item ${selectedDeptId === dept.id ? 'selected' : ''}`}
                                                onClick={() => {
                                                    if (renamingId !== dept.id) {
                                                        setSelectedDeptId(dept.id);
                                                        setSemForm({ ...semForm, department_id: dept.id });
                                                    }
                                                }}
                                            >
                                                {renamingId === dept.id && renamingType === 'department' ? (
                                                    <>
                                                        <input
                                                            type="text"
                                                            value={renameValue}
                                                            onChange={e => setRenameValue(e.target.value)}
                                                            onClick={e => e.stopPropagation()}
                                                            onKeyDown={e => {
                                                                if (e.key === 'Enter') handleRename();
                                                                if (e.key === 'Escape') cancelRename();
                                                            }}
                                                            autoFocus
                                                            className="rename-input"
                                                        />
                                                        <button
                                                            className="btn btn-primary btn-icon"
                                                            onClick={(e) => { e.stopPropagation(); handleRename(); }}
                                                            title="Save"
                                                        >
                                                            ✓
                                                        </button>
                                                        <button
                                                            className="btn btn-ghost btn-icon"
                                                            onClick={(e) => { e.stopPropagation(); cancelRename(); }}
                                                            title="Cancel"
                                                        >
                                                            ✕
                                                        </button>
                                                    </>
                                                ) : (
                                                    <>
                                                        <span className="item-name">{dept.name}</span>
                                                        <span className="item-code">{dept.code}</span>
                                                        <div className="item-actions">
                                                            <button
                                                                className="btn btn-ghost btn-icon"
                                                                onClick={(e) => { e.stopPropagation(); startRename(dept.id, 'department', dept.name); }}
                                                                title="Rename"
                                                            >
                                                                ✎
                                                            </button>
                                                            <button
                                                                className="btn btn-danger btn-icon"
                                                                onClick={(e) => { e.stopPropagation(); handleDeleteDepartment(dept.id); }}
                                                                title="Delete"
                                                            >
                                                                ✕
                                                            </button>
                                                        </div>
                                                    </>
                                                )}
                                            </div>
                                        ))
                                    )}
                                </div>
                            </div>

                            {/* Semesters Column */}
                            <div className="hierarchy-column">
                                <div className="panel-header">
                                    <h2>Semesters {selectedDeptId && `(${departments.find(d => d.id === selectedDeptId)?.name})`}</h2>
                                    {selectedDeptId && (
                                        <button
                                            className="btn btn-primary btn-small"
                                            onClick={() => setShowSemForm(!showSemForm)}
                                        >
                                            {showSemForm ? 'Cancel' : '+ Add'}
                                        </button>
                                    )}
                                </div>

                                {!selectedDeptId ? (
                                    <div className="no-data">Select a department to view semesters</div>
                                ) : (
                                    <>
                                        {showSemForm && (
                                            <form onSubmit={handleCreateSemester} className="inline-form">
                                                <input
                                                    type="number"
                                                    placeholder="Semester #"
                                                    value={semForm.semester_number}
                                                    onChange={e => setSemForm({ ...semForm, semester_number: parseInt(e.target.value) || 1 })}
                                                    required
                                                    min={1}
                                                    style={{ width: '80px' }}
                                                />
                                                <input
                                                    type="text"
                                                    placeholder="Semester Name"
                                                    value={semForm.name}
                                                    onChange={e => setSemForm({ ...semForm, name: e.target.value })}
                                                    required
                                                />
                                                <button type="submit" className="btn btn-primary btn-small" disabled={semLoading}>
                                                    {semLoading ? '...' : 'Create'}
                                                </button>
                                            </form>
                                        )}

                                        <div className="hierarchy-list">
                                            {semesters.length === 0 ? (
                                                <div className="no-data">No semesters</div>
                                            ) : (
                                                semesters.map(sem => (
                                                    <div
                                                        key={sem.id}
                                                        className={`hierarchy-item ${selectedSemId === sem.id ? 'selected' : ''}`}
                                                        onClick={() => {
                                                            if (renamingId !== sem.id) {
                                                                setSelectedSemId(sem.id);
                                                                setSubjForm({ ...subjForm, semester_id: sem.id });
                                                                fetchSubjects(sem.id);
                                                            }
                                                        }}
                                                    >
                                                        {renamingId === sem.id && renamingType === 'semester' ? (
                                                            <>
                                                                <input
                                                                    type="text"
                                                                    value={renameValue}
                                                                    onChange={e => setRenameValue(e.target.value)}
                                                                    onClick={e => e.stopPropagation()}
                                                                    onKeyDown={e => {
                                                                        if (e.key === 'Enter') handleRename();
                                                                        if (e.key === 'Escape') cancelRename();
                                                                    }}
                                                                    autoFocus
                                                                    className="rename-input"
                                                                />
                                                                <button
                                                                    className="btn btn-primary btn-icon"
                                                                    onClick={(e) => { e.stopPropagation(); handleRename(); }}
                                                                    title="Save"
                                                                >
                                                                    ✓
                                                                </button>
                                                                <button
                                                                    className="btn btn-ghost btn-icon"
                                                                    onClick={(e) => { e.stopPropagation(); cancelRename(); }}
                                                                    title="Cancel"
                                                                >
                                                                    ✕
                                                                </button>
                                                            </>
                                                        ) : (
                                                            <>
                                                                <span className="item-number">#{sem.semester_number}</span>
                                                                <span className="item-name">{sem.name}</span>
                                                                <div className="item-actions">
                                                                    <button
                                                                        className="btn btn-ghost btn-icon"
                                                                        onClick={(e) => { e.stopPropagation(); startRename(sem.id, 'semester', sem.name); }}
                                                                        title="Rename"
                                                                    >
                                                                        ✎
                                                                    </button>
                                                                    <button
                                                                        className="btn btn-danger btn-icon"
                                                                        onClick={(e) => { e.stopPropagation(); handleDeleteSemester(sem.id); }}
                                                                        title="Delete"
                                                                    >
                                                                        ✕
                                                                    </button>
                                                                </div>
                                                            </>
                                                        )}
                                                    </div>
                                                ))
                                            )}
                                        </div>
                                    </>
                                )}
                            </div>

                            {/* Subjects Column */}
                            <div className="hierarchy-column">
                                <div className="panel-header">
                                    <h2>Subjects {selectedSemId && `(${semesters.find(s => s.id === selectedSemId)?.name})`}</h2>
                                    {selectedSemId && (
                                        <button
                                            className="btn btn-primary btn-small"
                                            onClick={() => setShowSubjForm(!showSubjForm)}
                                        >
                                            {showSubjForm ? 'Cancel' : '+ Add'}
                                        </button>
                                    )}
                                </div>

                                {!selectedSemId ? (
                                    <div className="no-data">Select a semester to view subjects</div>
                                ) : (
                                    <>
                                        {showSubjForm && (
                                            <form onSubmit={handleCreateSubject} className="inline-form">
                                                <input
                                                    type="text"
                                                    placeholder="Subject Code"
                                                    value={subjForm.code}
                                                    onChange={e => setSubjForm({ ...subjForm, code: e.target.value })}
                                                    required
                                                    style={{ width: '80px' }}
                                                />
                                                <input
                                                    type="text"
                                                    placeholder="Subject Name"
                                                    value={subjForm.name}
                                                    onChange={e => setSubjForm({ ...subjForm, name: e.target.value })}
                                                    required
                                                />
                                                <button type="submit" className="btn btn-primary btn-small" disabled={subjLoading}>
                                                    {subjLoading ? '...' : 'Create'}
                                                </button>
                                            </form>
                                        )}

                                        <div className="hierarchy-list">
                                            {subjects.length === 0 ? (
                                                <div className="no-data">No subjects</div>
                                            ) : (
                                                subjects.map(subj => (
                                                    <div key={subj.id} className="hierarchy-item">
                                                        {renamingId === subj.id && renamingType === 'subject' ? (
                                                            <>
                                                                <input
                                                                    type="text"
                                                                    value={renameValue}
                                                                    onChange={e => setRenameValue(e.target.value)}
                                                                    onKeyDown={e => {
                                                                        if (e.key === 'Enter') handleRename();
                                                                        if (e.key === 'Escape') cancelRename();
                                                                    }}
                                                                    autoFocus
                                                                    className="rename-input"
                                                                />
                                                                <button
                                                                    className="btn btn-primary btn-icon"
                                                                    onClick={() => handleRename()}
                                                                    title="Save"
                                                                >
                                                                    ✓
                                                                </button>
                                                                <button
                                                                    className="btn btn-ghost btn-icon"
                                                                    onClick={() => cancelRename()}
                                                                    title="Cancel"
                                                                >
                                                                    ✕
                                                                </button>
                                                            </>
                                                        ) : (
                                                            <>
                                                                <span className="item-code">{subj.code}</span>
                                                                <span className="item-name">{subj.name}</span>
                                                                <div className="item-actions">
                                                                    <button
                                                                        className="btn btn-ghost btn-icon"
                                                                        onClick={() => startRename(subj.id, 'subject', subj.name)}
                                                                        title="Rename"
                                                                    >
                                                                        ✎
                                                                    </button>
                                                                    <button
                                                                        className="btn btn-danger btn-icon"
                                                                        onClick={() => handleDeleteSubject(subj.id)}
                                                                        title="Delete"
                                                                    >
                                                                        ✕
                                                                    </button>
                                                                </div>
                                                            </>
                                                        )}
                                                    </div>
                                                ))
                                            )}
                                        </div>
                                    </>
                                )}
                            </div>
                        </div>
                    </section>
                )}

                {/* Edit Subjects Modal */}
                {editingUserId && (
                    <div className="modal-overlay" onClick={() => {
                        setEditingUserId(null);
                        setEditingSubjectIds([]);
                        setEditingCurrentDeptId('');
                    }}>
                        <div className="modal-content modal-large" onClick={e => e.stopPropagation()}>
                            <h3>Edit Subject Access</h3>
                            <p className="modal-subtitle">Select subjects by department:</p>

                            <div className="modal-layout">
                                {/* Left panel: Department selector + subjects */}
                                <div className="modal-left-panel">
                                    <label className="panel-label">Choose Department:</label>
                                    <select
                                        value={editingCurrentDeptId}
                                        onChange={e => setEditingCurrentDeptId(e.target.value)}
                                        className="dept-select-modal"
                                    >
                                        <option value="">Select Department</option>
                                        {departments.map(dept => (
                                            <option key={dept.id} value={dept.id}>{dept.name}</option>
                                        ))}
                                    </select>

                                    {editingCurrentDeptId && (
                                        <div className="modal-subject-list">
                                            <h4 className="panel-subheading">
                                                {departments.find(d => d.id === editingCurrentDeptId)?.name} Subjects:
                                            </h4>
                                            {departmentSubjects.get(editingCurrentDeptId)?.length === 0 ? (
                                                <div className="no-subjects-msg">No subjects in this department</div>
                                            ) : (
                                                <div className="subject-checkboxes-modal">
                                                    {departmentSubjects.get(editingCurrentDeptId)?.map(subj => (
                                                        <label key={subj.id} className="subject-checkbox">
                                                            <input
                                                                type="checkbox"
                                                                checked={editingSubjectIds.includes(subj.id)}
                                                                onChange={e => {
                                                                    if (e.target.checked) {
                                                                        setEditingSubjectIds([...editingSubjectIds, subj.id]);
                                                                    } else {
                                                                        setEditingSubjectIds(editingSubjectIds.filter(id => id !== subj.id));
                                                                    }
                                                                }}
                                                            />
                                                            <span>{subj.name} ({subj.code})</span>
                                                        </label>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>

                                {/* Right panel: Currently selected */}
                                <div className="modal-right-panel">
                                    <h4 className="panel-heading">Currently Selected:</h4>
                                    {editingSubjectIds.length === 0 ? (
                                        <div className="no-selection-msg">No subjects selected</div>
                                    ) : (
                                        <div className="selected-subjects-list">
                                            {Array.from(
                                                editingSubjectIds.reduce((acc, subjId) => {
                                                    // Find which department this subject belongs to
                                                    for (const [deptId, subjects] of departmentSubjects.entries()) {
                                                        const subj = subjects.find(s => s.id === subjId);
                                                        if (subj) {
                                                            if (!acc.has(deptId)) acc.set(deptId, []);
                                                            acc.get(deptId)?.push(subj);
                                                            break;
                                                        }
                                                    }
                                                    return acc;
                                                }, new Map<string, Subject[]>())
                                            ).map(([deptId, subjs]) => {
                                                const dept = departments.find(d => d.id === deptId);
                                                return (
                                                    <div key={deptId} className="selected-group">
                                                        <strong className="dept-name">{dept?.name || 'Unknown'}:</strong>
                                                        <ul className="subj-list">
                                                            {subjs.map(s => (
                                                                <li key={s.id} className="subj-item">
                                                                    {s.name} ({s.code})
                                                                    <button
                                                                        className="btn-remove"
                                                                        onClick={() => setEditingSubjectIds(editingSubjectIds.filter(id => id !== s.id))}
                                                                        title="Remove"
                                                                    >
                                                                        ✕
                                                                    </button>
                                                                </li>
                                                            ))}
                                                        </ul>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    )}
                                </div>
                            </div>

                            <div className="modal-actions">
                                <button
                                    className="btn btn-primary"
                                    onClick={handleUpdateSubjects}
                                    disabled={editingSubjectIds.length === 0}
                                >
                                    Save Changes
                                </button>
                                <button
                                    className="btn btn-ghost"
                                    onClick={() => {
                                        setEditingUserId(null);
                                        setEditingSubjectIds([]);
                                        setEditingCurrentDeptId('');
                                    }}
                                >
                                    Cancel
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </main>

            <style>{`
                .admin-dashboard {
                    min-height: 100vh;
                    background: var(--color-bg-primary);
                    color: var(--color-text-primary);
                    display: flex;
                    flex-direction: column;
                }

                .admin-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: var(--spacing-md) var(--spacing-lg);
                    background: var(--color-bg-secondary);
                    border-bottom: 1px solid var(--color-border);
                }

                .header-left h1 {
                    margin: 0;
                    font-size: 1.5rem;
                    color: var(--color-primary);
                }

                .user-badge {
                    font-size: 0.875rem;
                    color: var(--color-text-muted);
                }

                .header-actions {
                    display: flex;
                    gap: var(--spacing-sm);
                }

                .admin-tabs {
                    display: flex;
                    gap: 0;
                    background: var(--color-bg-secondary);
                    border-bottom: 1px solid var(--color-border);
                    padding: 0 var(--spacing-lg);
                }

                .tab-btn {
                    padding: var(--spacing-md) var(--spacing-lg);
                    font-size: 0.875rem;
                    font-weight: 500;
                    color: var(--color-text-secondary);
                    border-bottom: 2px solid transparent;
                    transition: all var(--transition-fast);
                }

                .tab-btn:hover {
                    color: var(--color-text-primary);
                    background: var(--color-bg-hover);
                }

                .tab-btn.active {
                    color: var(--color-primary);
                    border-bottom-color: var(--color-primary);
                }

                .admin-content {
                    padding: var(--spacing-lg);
                    max-width: 1400px;
                    margin: 0 auto;
                    width: 100%;
                    flex: 1;
                    overflow-y: auto;
                }

                .stats-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                    gap: var(--spacing-md);
                    margin-bottom: var(--spacing-lg);
                }

                .stat-card {
                    background: var(--color-bg-secondary);
                    border: 1px solid var(--color-border);
                    border-radius: var(--radius-md);
                    padding: var(--spacing-lg);
                    text-align: center;
                }

                .stat-value {
                    font-size: 2rem;
                    font-weight: 700;
                    color: var(--color-primary);
                }

                .stat-label {
                    font-size: 0.875rem;
                    color: var(--color-text-muted);
                    margin-top: var(--spacing-xs);
                }

                .panel {
                    background: var(--color-bg-secondary);
                    border: 1px solid var(--color-border);
                    border-radius: var(--radius-md);
                    padding: var(--spacing-lg);
                }

                .panel-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: var(--spacing-md);
                }

                .panel-header h2 {
                    margin: 0;
                    font-size: 1.125rem;
                }

                .create-form {
                    background: var(--color-bg-tertiary);
                    border-radius: var(--radius-sm);
                    padding: var(--spacing-md);
                    margin-bottom: var(--spacing-md);
                }

                .create-form h3 {
                    margin: 0 0 var(--spacing-md) 0;
                    font-size: 1rem;
                }

                .create-form input {
                    width: 100%;
                    padding: 8px 12px;
                    margin-bottom: var(--spacing-sm);
                    border: 1px solid var(--color-border);
                    border-radius: var(--radius-sm);
                    background: var(--color-bg-primary);
                    color: var(--color-text-primary);
                }

                .create-form input:focus {
                    outline: none;
                    border-color: var(--color-primary);
                }

                .form-row {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: var(--spacing-md);
                    margin-bottom: var(--spacing-md);
                }

                .form-group {
                    display: flex;
                    flex-direction: column;
                    gap: var(--spacing-xs);
                }

                .form-group label {
                    font-size: 0.875rem;
                    color: var(--color-text-secondary);
                }

                .filters {
                    display: flex;
                    gap: var(--spacing-sm);
                    margin-bottom: var(--spacing-md);
                }

                .data-table {
                    width: 100%;
                    border-collapse: collapse;
                }

                .data-table th,
                .data-table td {
                    padding: var(--spacing-sm) var(--spacing-md);
                    text-align: left;
                    border-bottom: 1px solid var(--color-border);
                }

                .data-table th {
                    font-weight: 600;
                    color: var(--color-text-secondary);
                    font-size: 0.75rem;
                    text-transform: uppercase;
                }

                .no-data {
                    text-align: center;
                    color: var(--color-text-muted);
                    padding: var(--spacing-xl) !important;
                }

                .role-badge {
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 0.75rem;
                    font-weight: 600;
                    text-transform: uppercase;
                }

                .role-admin { background: rgba(139, 92, 246, 0.2); color: #a78bfa; }
                .role-staff { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }
                .role-student { background: rgba(16, 185, 129, 0.2); color: #34d399; }

                .status-badge {
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 0.75rem;
                }

                .status-active { background: rgba(16, 185, 129, 0.2); color: #34d399; }
                .status-disabled { background: rgba(239, 68, 68, 0.2); color: #f87171; }

                .actions {
                    display: flex;
                    gap: var(--spacing-xs);
                }

                .btn-small {
                    padding: var(--spacing-xs) var(--spacing-sm);
                    font-size: 0.75rem;
                }

                .btn-danger {
                    background: rgba(239, 68, 68, 0.2);
                    color: #f87171;
                }

                .btn-danger:hover {
                    background: rgba(239, 68, 68, 0.3);
                }

                .btn-icon {
                    width: 24px;
                    height: 24px;
                    padding: 0;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 12px;
                }

                .loading {
                    text-align: center;
                    padding: var(--spacing-xl);
                    color: var(--color-text-muted);
                }

                .error-message {
                    background: rgba(239, 68, 68, 0.1);
                    border: 1px solid rgba(239, 68, 68, 0.3);
                    color: #f87171;
                    padding: var(--spacing-sm) var(--spacing-md);
                    border-radius: var(--radius-sm);
                    margin-bottom: var(--spacing-md);
                }

                /* Hierarchy Management Styles */
                .hierarchy-panel {
                    padding: 0;
                    overflow: hidden;
                }

                .hierarchy-grid {
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    min-height: 450px;
                }

                .hierarchy-column {
                    padding: var(--spacing-md);
                    border-right: 1px solid var(--color-border);
                    display: flex;
                    flex-direction: column;
                    background: var(--color-bg-secondary);
                }

                .hierarchy-column:nth-child(2) {
                    background: rgba(0, 0, 0, 0.2);
                }

                .hierarchy-column:nth-child(3) {
                    background: rgba(0, 0, 0, 0.3);
                }

                .hierarchy-column:last-child {
                    border-right: none;
                }

                .inline-form {
                    display: flex;
                    gap: var(--spacing-sm);
                    margin-bottom: var(--spacing-md);
                    padding: var(--spacing-sm);
                    background: var(--color-bg-tertiary);
                    border-radius: var(--radius-sm);
                }

                .inline-form input {
                    flex: 1;
                }

                .hierarchy-list {
                    display: flex;
                    flex-direction: column;
                    gap: var(--spacing-xs);
                }

                .hierarchy-item {
                    display: flex;
                    align-items: center;
                    gap: var(--spacing-sm);
                    padding: var(--spacing-sm) var(--spacing-md);
                    background: var(--color-bg-tertiary);
                    border: 1px solid var(--color-border);
                    border-radius: var(--radius-sm);
                    cursor: pointer;
                    transition: all var(--transition-fast);
                }

                .hierarchy-item:hover {
                    border-color: var(--color-primary);
                    background: var(--color-bg-hover);
                }

                .hierarchy-item.selected {
                    border-color: var(--color-primary);
                    background: var(--color-primary-dim);
                }

                .item-name {
                    flex: 1;
                    font-weight: 500;
                }

                .item-code, .item-number {
                    color: var(--color-text-muted);
                    font-size: 0.75rem;
                    white-space: nowrap;
                }

                .item-actions {
                    display: flex;
                    gap: 4px;
                    margin-left: auto;
                }

                .rename-input {
                    flex: 1;
                    padding: 4px 8px;
                    border-radius: var(--radius-sm);
                    border: 1px solid var(--color-primary);
                    background: var(--color-bg-primary);
                    color: var(--color-text-primary);
                    font-size: 0.875rem;
                }

                .rename-input:focus {
                    outline: none;
                    box-shadow: 0 0 0 2px var(--color-primary-dim);
                }

                /* Fix status badge truncation */
                .status-badge {
                    white-space: nowrap;
                }

                /* Subject selection styles */
                .subject-select-container {
                    max-height: 200px;
                    overflow-y: auto;
                    border: 1px solid var(--color-border);
                    border-radius: var(--radius-sm);
                    padding: var(--spacing-sm);
                    background: var(--color-bg-tertiary);
                }

                .subject-checkboxes {
                    display: flex;
                    flex-direction: column;
                    gap: var(--spacing-xs);
                }

                .subject-checkbox {
                    display: flex;
                    align-items: center;
                    gap: var(--spacing-sm);
                    padding: var(--spacing-xs);
                    cursor: pointer;
                    border-radius: var(--radius-sm);
                    transition: background var(--transition-fast);
                }

                .subject-checkbox:hover {
                    background: var(--color-bg-hover);
                }

                .subject-checkbox input[type="checkbox"] {
                    cursor: pointer;
                    width: 16px;
                    height: 16px;
                }

                .form-hint {
                    color: var(--color-text-muted);
                    font-size: 0.75rem;
                    margin-top: 4px;
                }

                /* Hierarchical Subject Selection Styles */
                .subject-hierarchy-container {
                    border: 1px solid var(--color-border);
                    border-radius: var(--radius-sm);
                    padding: var(--spacing-md);
                    background: var(--color-bg-tertiary);
                    display: flex;
                    flex-direction: column;
                    gap: var(--spacing-md);
                }

                .dept-selection-row {
                    display: flex;
                    gap: var(--spacing-sm);
                }

                .dept-select {
                    flex: 1;
                    padding: 8px 12px;
                    border: 1px solid var(--color-border);
                    border-radius: var(--radius-sm);
                    background: var(--color-bg-primary);
                    color: var(--color-text-primary);
                    font-size: 0.875rem;
                }

                .subject-selection-panel {
                    background: var(--color-bg-primary);
                    border: 1px solid var(--color-border);
                    border-radius: var(--radius-sm);
                    padding: var(--spacing-sm);
                }

                .dept-subheading {
                    margin: 0 0 var(--spacing-sm) 0;
                    font-size: 0.875rem;
                    color: var(--color-primary);
                    font-weight: 600;
                }

                .no-subjects-msg {
                    color: var(--color-text-muted);
                    font-size: 0.875rem;
                    padding: var(--spacing-sm);
                    text-align: center;
                }

                .selected-subjects-summary {
                    background: var(--color-bg-primary);
                    border: 1px solid var(--color-primary);
                    border-radius: var(--radius-sm);
                    padding: var(--spacing-sm);
                }

                .selected-subjects-summary h4 {
                    margin: 0 0 var(--spacing-sm) 0;
                    font-size: 0.875rem;
                    color: var(--color-text-primary);
                }

                .selected-dept-group {
                    margin-bottom: var(--spacing-xs);
                    font-size: 0.8rem;
                }

                .selected-dept-group strong {
                    color: var(--color-primary);
                }

                .selected-subj-list {
                    color: var(--color-text-secondary);
                    margin-left: var(--spacing-sm);
                }

                /* Modal styles */
                .modal-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0, 0, 0, 0.5);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 1000;
                }

                .modal-content {
                    background: var(--color-bg-secondary);
                    border: 1px solid var(--color-border);
                    border-radius: var(--radius-md);
                    padding: var(--spacing-lg);
                    min-width: 400px;
                    max-width: 600px;
                    max-height: 80vh;
                    overflow-y: auto;
                }

                .modal-content h3 {
                    margin-top: 0;
                    margin-bottom: var(--spacing-sm);
                    color: var(--color-primary);
                }

                .subject-edit-list {
                    max-height: 300px;
                    overflow-y: auto;
                    border: 1px solid var(--color-border);
                    border-radius: var(--radius-sm);
                    padding: var(--spacing-sm);
                    margin: var(--spacing-md) 0;
                    background: var(--color-bg-tertiary);
                }

                .modal-actions {
                    display: flex;
                    gap: var(--spacing-sm);
                    justify-content: flex-end;
                    margin-top: var(--spacing-md);
                }

                /* Modal with two-panel layout */
                .modal-large {
                    min-width: 700px;
                    max-width: 900px;
                }

                .modal-subtitle {
                    color: var(--color-text-muted);
                    margin-bottom: var(--spacing-md);
                }

                .modal-layout {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: var(--spacing-lg);
                    margin: var(--spacing-md) 0;
                }

                .modal-left-panel,
                .modal-right-panel {
                    background: var(--color-bg-tertiary);
                    border: 1px solid var(--color-border);
                    border-radius: var(--radius-sm);
                    padding: var(--spacing-md);
                    max-height: 400px;
                    overflow-y: auto;
                }

                .panel-label {
                    display: block;
                    font-size: 0.875rem;
                    font-weight: 500;
                    color: var(--color-text-secondary);
                    margin-bottom: var(--spacing-xs);
                }

                .dept-select-modal {
                    width: 100%;
                    padding: 8px 12px;
                    border: 1px solid var(--color-border);
                    border-radius: var(--radius-sm);
                    background: var(--color-bg-primary);
                    color: var(--color-text-primary);
                    margin-bottom: var(--spacing-sm);
                }

                .panel-subheading {
                    margin: var(--spacing-sm) 0;
                    font-size: 0.875rem;
                    color: var(--color-primary);
                }

                .modal-subject-list {
                    margin-top: var(--spacing-sm);
                }

                .subject-checkboxes-modal {
                    display: flex;
                    flex-direction: column;
                    gap: var(--spacing-xs);
                }

                .panel-heading {
                    margin: 0 0 var(--spacing-sm) 0;
                    font-size: 0.875rem;
                    color: var(--color-text-primary);
                }

                .no-selection-msg {
                    color: var(--color-text-muted);
                    font-size: 0.875rem;
                    text-align: center;
                    padding: var(--spacing-md);
                }

                .selected-group {
                    margin-bottom: var(--spacing-sm);
                }

                .dept-name {
                    color: var(--color-primary);
                    font-size: 0.8rem;
                    display: block;
                    margin-bottom: 4px;
                }

                .subj-list {
                    list-style: none;
                    margin: 0;
                    padding: 0;
                    padding-left: var(--spacing-sm);
                }

                .subj-item {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 4px 0;
                    font-size: 0.8rem;
                    color: var(--color-text-secondary);
                    border-bottom: 1px solid var(--color-border);
                }

                .subj-item:last-child {
                    border-bottom: none;
                }

                .btn-remove {
                    background: transparent;
                    border: none;
                    color: var(--color-danger);
                    cursor: pointer;
                    font-size: 0.75rem;
                    padding: 2px 6px;
                    border-radius: 3px;
                    transition: background var(--transition-fast);
                }

                .btn-remove:hover {
                    background: rgba(239, 68, 68, 0.2);
                }

                @media (max-width: 768px) {
                    .form-row {
                        grid-template-columns: 1fr;
                    }

                    .hierarchy-grid {
                        grid-template-columns: 1fr;
                    }

                    .hierarchy-column {
                        border-right: none;
                        border-bottom: 1px solid var(--color-border);
                        padding: var(--spacing-sm);
                    }

                    .hierarchy-column .panel-header {
                        flex-direction: column;
                        gap: var(--spacing-xs);
                        align-items: stretch;
                    }

                    .hierarchy-column .panel-header h2 {
                        font-size: 1rem;
                    }

                    .inline-form {
                        flex-direction: column;
                    }

                    .hierarchy-item {
                        padding: var(--spacing-md);
                        min-height: 44px;
                    }

                    .item-actions {
                        gap: var(--spacing-xs);
                    }

                    .btn-icon {
                        width: 36px;
                        height: 36px;
                        font-size: 1rem;
                    }

                    /* Smaller stats cards on mobile */
                    .stats-grid {
                        grid-template-columns: repeat(2, 1fr);
                        gap: var(--spacing-sm);
                        margin-bottom: var(--spacing-md);
                    }

                    .stat-card {
                        padding: var(--spacing-sm);
                    }

                    .stat-value {
                        font-size: 1.25rem;
                    }

                    .stat-label {
                        font-size: 0.75rem;
                    }

                    /* Sticky name column in user table */
                    .user-table th:first-child,
                    .user-table td:first-child {
                        position: sticky;
                        left: 0;
                        background: var(--color-bg-secondary);
                        z-index: 1;
                    }

                    .user-table th:first-child {
                        background: var(--color-bg-tertiary);
                    }
                }
            `}</style>
        </div>
    );
}

export default AdminDashboard;
