CREATE DATABASE IF NOT EXISTS kneesense
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;

USE kneesense;

-- User accounts: role is assigned by the backend, not by signup input.
CREATE TABLE users (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(254) NOT NULL UNIQUE,
    full_name VARCHAR(120) NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('PATIENT', 'DOCTOR', 'ADMIN')
        NOT NULL DEFAULT 'PATIENT',
    created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB;


-- Doctors can access only their assigned patients.
CREATE TABLE doctor_patient (
    doctor_id BIGINT UNSIGNED NOT NULL,
    patient_id BIGINT UNSIGNED NOT NULL,
    assigned_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    PRIMARY KEY (doctor_id, patient_id),
    INDEX idx_doctor_patient_patient (patient_id),

    FOREIGN KEY (doctor_id) REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (patient_id) REFERENCES users(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;


-- Store metadata and SHA-256 hash only. Never store the X-ray itself.
CREATE TABLE uploads (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    content_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    INDEX idx_uploads_user_created (user_id, created_at),

    FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;


-- One prediction result per upload.
CREATE TABLE results (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    upload_id BIGINT UNSIGNED NOT NULL UNIQUE,
    kl_grade TINYINT UNSIGNED NOT NULL,
    confidence DECIMAL(8,6) NOT NULL,
    source ENUM('live', 'cached') NOT NULL,
    created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    CHECK (kl_grade BETWEEN 0 AND 4),
    CHECK (confidence BETWEEN 0 AND 1),

    FOREIGN KEY (upload_id) REFERENCES uploads(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;


-- Store both generated reports without truncating their content.
CREATE TABLE reports (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    result_id BIGINT UNSIGNED NOT NULL UNIQUE,
    clinician_text LONGTEXT NOT NULL,
    patient_text LONGTEXT NOT NULL,
    created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    FOREIGN KEY (result_id) REFERENCES results(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;