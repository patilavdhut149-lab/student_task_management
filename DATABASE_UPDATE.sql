-- Student Task Manager - database changes for Student Login + task status
-- The Flask application also performs these changes automatically at startup.

CREATE TABLE IF NOT EXISTS student_accounts (
    account_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL UNIQUE,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_student_account
        FOREIGN KEY (student_id) REFERENCES students(student_id)
        ON DELETE CASCADE
);

-- If your existing student_tasks table does not already have status,
-- run this once:
-- ALTER TABLE student_tasks
-- ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'Pending';
