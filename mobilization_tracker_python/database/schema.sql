CREATE TABLE IF NOT EXISTS users (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(190) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('Administrator','Center Manager','Mobilizer','View Only') NOT NULL DEFAULT 'Mobilizer',
    active TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS shared_workspace (
    id TINYINT UNSIGNED NOT NULL PRIMARY KEY,
    data_json LONGTEXT NOT NULL,
    updated_by BIGINT UNSIGNED NULL,
    updated_at DATETIME NULL,
    CONSTRAINT fk_workspace_user FOREIGN KEY (updated_by) REFERENCES users(id)
);
