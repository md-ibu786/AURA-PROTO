-- Database schema for hierarchical academic notes (PostgreSQL)

-- Departments
CREATE TABLE IF NOT EXISTS departments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    code VARCHAR(50) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Semesters
CREATE TABLE IF NOT EXISTS semesters (
    id SERIAL PRIMARY KEY,
    department_id INTEGER NOT NULL,
    semester_number INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(department_id, semester_number),
    FOREIGN KEY(department_id) REFERENCES departments(id) ON DELETE CASCADE
);

-- Subjects
CREATE TABLE IF NOT EXISTS subjects (
    id SERIAL PRIMARY KEY,
    semester_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(semester_id, code),
    FOREIGN KEY(semester_id) REFERENCES semesters(id) ON DELETE CASCADE
);

-- Modules
CREATE TABLE IF NOT EXISTS modules (
    id SERIAL PRIMARY KEY,
    subject_id INTEGER NOT NULL,
    module_number INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(subject_id, module_number),
    FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);

-- Notes (metadata only)
CREATE TABLE IF NOT EXISTS notes (
    id SERIAL PRIMARY KEY,
    module_id INTEGER NOT NULL,
    title VARCHAR(500) NOT NULL,
    pdf_url VARCHAR(1000) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(module_id) REFERENCES modules(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_semesters_department_id ON semesters(department_id);
CREATE INDEX IF NOT EXISTS idx_subjects_semester_id ON subjects(semester_id);
CREATE INDEX IF NOT EXISTS idx_modules_subject_id ON modules(subject_id);
CREATE INDEX IF NOT EXISTS idx_notes_module_id ON notes(module_id);
