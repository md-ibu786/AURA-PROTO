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
import { toast } from 'sonner';
import { useAuthStore, type UserRole } from '../stores/useAuthStore';
import { AdminHeader } from '../components/layout/AdminHeader';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { fetchApi } from '../api/client';
import {
    createDepartment, deleteDepartment,
    createSemester, deleteSemester,
    deleteSubject,
    updateDepartment, updateSemester, updateSubject,
} from '../api/explorerApi';
import { deleteUser } from '../api/userApi';
import '../styles/index.css';
import '../styles/admin-dashboard.css';

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

type TabType = 'users' | 'hierarchy';

export function AdminDashboard() {
    const user = useAuthStore(s => s.user);

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

    // Delete confirmation state
    const [userToDelete, setUserToDelete] = useState<string | null>(null);

    // Generic confirm dialog state
    const [confirmAction, setConfirmAction] = useState<{
        title: string;
        message: string;
        onConfirm: () => void;
    } | null>(null);

    // Selected department for semester view
    const [selectedDeptId, setSelectedDeptId] = useState<string>('');

    // Filter state
    const [roleFilter, setRoleFilter] = useState<string>('');
    const [departmentFilter, setDepartmentFilter] = useState<string>('');

    const fetchData = useCallback(async () => {
        setIsLoading(true);
        setError(null);

        try {
            // Build query params
            const params = new URLSearchParams();
            if (roleFilter) params.append('role', roleFilter);
            if (departmentFilter) params.append('department_id', departmentFilter);

            // Fetch users
            const usersData = await fetchApi<UserItem[]>(`/users?${params}`);
            setUsers(usersData);

            // Fetch departments and subjects grouped by department
            const deptRes = await fetchApi<{ departments: Department[] }>('/departments');
            const fetchedDepartments = deptRes.departments || [];
            setDepartments(fetchedDepartments);

            // Fetch subjects grouped by department for staff assignment
            const deptMap = new Map<string, Subject[]>();
            for (const dept of fetchedDepartments) {
                try {
                    const deptSubjRes = await fetchApi<{ subjects: Subject[] }>(`/departments/${dept.id}/subjects`);
                    deptMap.set(dept.id, deptSubjRes.subjects || []);
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
    }, [departmentFilter, roleFilter]);

    const fetchSemesters = useCallback(async (deptId: string) => {
        try {
            const res = await fetchApi<{ semesters: Semester[] }>(`/departments/${deptId}/semesters`);
            setSemesters(res.semesters || []);
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

            await fetchApi('/users', {
                method: 'POST',
                body: JSON.stringify(requestBody),
            });

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

    const confirmDeleteUser = async () => {
        if (!userToDelete) return;

        try {
            await deleteUser(userToDelete);

            fetchData();
        } catch (err) {
            if (err instanceof Error && err.message.includes('404')) {
                setUsers(prev => prev.filter(u => u.id !== userToDelete));
                return;
            }
            toast.error(err instanceof Error ? err.message : 'Failed to delete user');
        } finally {
            setUserToDelete(null);
        }
    };

    const handleDeleteUser = (userId: string) => {
        setUserToDelete(userId);
    };

    const handleToggleStatus = async (userId: string, currentStatus: string) => {
        const newStatus = currentStatus === 'active' ? 'disabled' : 'active';

        try {
            await fetchApi(`/users/${userId}`, {
                method: 'PUT',
                body: JSON.stringify({ status: newStatus }),
            });

            fetchData();
        } catch (err) {
            toast.error(err instanceof Error ? err.message : 'Failed to update status');
        }
    };

    // Handle updating staff subject assignments
    const handleUpdateSubjects = async () => {
        if (!editingUserId || editingSubjectIds.length === 0) {
            toast.error('Please select at least one subject');
            return;
        }

        try {
            await fetchApi(`/users/${editingUserId}`, {
                method: 'PUT',
                body: JSON.stringify({ subject_ids: editingSubjectIds }),
            });

            setEditingUserId(null);
            setEditingSubjectIds([]);
            fetchData();
        } catch (err) {
            toast.error(err instanceof Error ? err.message : 'Failed to update subjects');
        }
    };

    // Department CRUD
    const handleCreateDepartment = async (e: FormEvent) => {
        e.preventDefault();
        setDeptLoading(true);
        try {
            await createDepartment(deptForm.name, deptForm.code);
            setDeptForm({ name: '', code: '' });
            setShowDeptForm(false);
            fetchData();
        } catch (err) {
            toast.error(err instanceof Error ? err.message : 'Failed to create department');
        } finally {
            setDeptLoading(false);
        }
    };

    const handleDeleteDepartment = (deptId: string) => {
        setConfirmAction({
            title: 'Delete Department',
            message: 'Delete this department and all its contents?',
            onConfirm: async () => {
                setConfirmAction(null);
                try {
                    await deleteDepartment(deptId);
                    fetchData();
                    if (selectedDeptId === deptId) setSelectedDeptId('');
                } catch (err) {
                    toast.error(err instanceof Error ? err.message : 'Failed to delete department');
                }
            },
        });
    };

    // Semester CRUD
    const handleCreateSemester = async (e: FormEvent) => {
        e.preventDefault();
        setSemLoading(true);
        try {
            await createSemester(semForm.department_id, semForm.semester_number, semForm.name);
            setSemForm({ department_id: selectedDeptId, name: '', semester_number: 1 });
            setShowSemForm(false);
            fetchSemesters(selectedDeptId);
        } catch (err) {
            toast.error(err instanceof Error ? err.message : 'Failed to create semester');
        } finally {
            setSemLoading(false);
        }
    };

    const handleDeleteSemester = (semId: string) => {
        setConfirmAction({
            title: 'Delete Semester',
            message: 'Delete this semester and all its contents?',
            onConfirm: async () => {
                setConfirmAction(null);
                try {
                    await deleteSemester(semId);
                    fetchSemesters(selectedDeptId);
                    if (selectedSemId === semId) {
                        setSelectedSemId('');
                        setSubjects([]);
                    }
                } catch (err) {
                    toast.error(err instanceof Error ? err.message : 'Failed to delete semester');
                }
            },
        });
    };

    // Subject functions
    const fetchSubjects = async (semesterId: string) => {
        if (!semesterId) {
            setSubjects([]);
            return;
        }
        try {
            const res = await fetchApi<{ subjects: Subject[] }>(`/semesters/${semesterId}/subjects?department_id=${selectedDeptId}`);
            setSubjects(res.subjects || []);
        } catch (err) {
            console.error('Failed to fetch subjects:', err);
        }
    };

    const handleCreateSubject = async (e: FormEvent) => {
        e.preventDefault();
        if (!selectedSemId) return;
        setSubjLoading(true);
        try {
            await fetchApi('/subjects', {
                method: 'POST',
                body: JSON.stringify({
                    semester_id: selectedSemId,
                    department_id: selectedDeptId,
                    name: subjForm.name,
                    code: subjForm.code
                }),
            });
            setSubjForm({ semester_id: selectedSemId, name: '', code: '' });
            setShowSubjForm(false);
            fetchSubjects(selectedSemId);
        } catch (err) {
            toast.error(err instanceof Error ? err.message : 'Failed to create subject');
        } finally {
            setSubjLoading(false);
        }
    };

    const handleDeleteSubject = (subjId: string) => {
        setConfirmAction({
            title: 'Delete Subject',
            message: 'Delete this subject and all its contents?',
            onConfirm: async () => {
                setConfirmAction(null);
                try {
                    await deleteSubject(subjId);
                    fetchSubjects(selectedSemId);
                } catch (err) {
                    toast.error(err instanceof Error ? err.message : 'Failed to delete subject');
                }
            },
        });
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
            switch (renamingType) {
                case 'department':
                    await updateDepartment(renamingId, { name: renameValue.trim() });
                    break;
                case 'semester':
                    await updateSemester(renamingId, { name: renameValue.trim() });
                    break;
                case 'subject':
                    await updateSubject(renamingId, { name: renameValue.trim() });
                    break;
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
            toast.error(err instanceof Error ? err.message : 'Failed to rename');
        }
    };

    return (
        <div className="admin-dashboard">
            {/* Header */}
            <AdminHeader title="Admin Dashboard" />

            {/* Tabs */}
            <div className="admin-tabs" role="tablist">
                <button
                    role="tab"
                    aria-selected={activeTab === 'users'}
                    className={`tab-btn ${activeTab === 'users' ? 'active' : ''}`}
                    onClick={() => setActiveTab('users')}
                >
                    User Management
                </button>
                <button
                    role="tab"
                    aria-selected={activeTab === 'hierarchy'}
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
                                                                            setCreateForm(prev => ({ ...prev, subject_ids: allSelected }));
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
                    <div
                        className="modal-overlay"
                        role="dialog"
                        aria-modal="true"
                        aria-labelledby="edit-subjects-title"
                        onClick={() => {
                            setEditingUserId(null);
                            setEditingSubjectIds([]);
                            setEditingCurrentDeptId('');
                        }}>
                        <div className="modal-content modal-large" onClick={e => e.stopPropagation()}>
                            <h3 id="edit-subjects-title">Edit Subject Access</h3>
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

            <ConfirmDialog 
                isOpen={!!userToDelete}
                title="Delete User"
                message="Are you sure you want to delete this user? This action cannot be undone."
                confirmLabel="Delete"
                variant="danger"
                destructive={true}
                onConfirm={confirmDeleteUser}
                onCancel={() => setUserToDelete(null)}
            />

            <ConfirmDialog
                isOpen={!!confirmAction}
                title={confirmAction?.title ?? ''}
                message={confirmAction?.message ?? ''}
                confirmLabel="Delete"
                variant="danger"
                destructive
                onConfirm={() => confirmAction?.onConfirm()}
                onCancel={() => setConfirmAction(null)}
            />
        </div>
    );
}
