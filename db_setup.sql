-- ============================================================
-- SECTION 1: CREATE TABLES
-- ============================================================

CREATE TABLE ROLES (
    RoleID SERIAL PRIMARY KEY,
    RoleName VARCHAR(50) NOT NULL,
    PermissionLevel VARCHAR(50) NOT NULL
);

CREATE TABLE USERS (
    UserID SERIAL PRIMARY KEY,
    Username VARCHAR(100) NOT NULL UNIQUE,
    RoleID INT NOT NULL,
    ContactNumber VARCHAR(20),
    FOREIGN KEY (RoleID) REFERENCES ROLES(RoleID)
);

CREATE TABLE USER_LOGIN (
    LoginID SERIAL PRIMARY KEY,
    UserID INT NOT NULL UNIQUE,
    PasswordHash VARCHAR(256) NOT NULL,
    LastLogin TIMESTAMP,
    FOREIGN KEY (UserID) REFERENCES USERS(UserID)
);

CREATE TABLE INCIDENTS (
    IncidentID SERIAL PRIMARY KEY,
    Type VARCHAR(100) NOT NULL,
    Severity VARCHAR(20) NOT NULL,
    Details TEXT,
    DetailsEncrypted BYTEA,
    ReporterID INT NOT NULL,
    Status VARCHAR(20) DEFAULT 'Active', -- ADD THIS LINE!
    CreatedAt TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (ReporterID) REFERENCES USERS(UserID)
);

CREATE TABLE AUDIT_LOGS (
    AuditID SERIAL PRIMARY KEY,
    UserID INT,
    ActionType VARCHAR(100) NOT NULL,
    ActionTime TIMESTAMP DEFAULT NOW(),
    Status VARCHAR(50),
    FOREIGN KEY (UserID) REFERENCES USERS(UserID)
);

-- ============================================================
-- SECTION 2: SEED DATA
-- ============================================================

INSERT INTO ROLES (RoleName, PermissionLevel) VALUES
('Admin', 'Full'),
('Analyst', 'ReadWrite'),
('Viewer', 'ReadOnly');

INSERT INTO USERS (Username, RoleID, ContactNumber) VALUES
('alex', 1, '0111000001'),
('amy', 2, '0111000002'),
('noah', 3, '0111000003');

INSERT INTO USER_LOGIN (UserID, PasswordHash, LastLogin) VALUES
(1, '$2b$12$qh7tHbvAyrIg2.wXjIEiwOBDAvbzq2l.wPs/GnwEa4ziHDpXzHarS', NOW()),
(2, '$2b$12$qh7tHbvAyrIg2.wXjIEiwOBDAvbzq2l.wPs/GnwEa4ziHDpXzHarS', NOW()),
(3, '$2b$12$qh7tHbvAyrIg2.wXjIEiwOBDAvbzq2l.wPs/GnwEa4ziHDpXzHarS', NOW());

INSERT INTO INCIDENTS (Type, Severity, Details, ReporterID) VALUES
('Unauthorised Access', 'High', 'Detected login from unknown IP at 2AM', 1),
('Data Leak', 'Critical', 'Sensitive file accessed without permission', 2),
('Phishing Attempt', 'Medium', 'Staff received suspicious email', 3);

-- ============================================================
-- SECTION 3: ROLES & RBAC 
-- ============================================================

-- Create Users
CREATE USER Alex WITH PASSWORD 'Alex@Sentinel123';
CREATE USER Amy WITH PASSWORD 'Amy@Sentinel123';
CREATE USER Noah WITH PASSWORD 'Noah@Sentinel123';

-- Grant Privileges 
-- Alex (Admin equivalent)
GRANT ALL PRIVILEGES ON SCHEMA public TO Alex;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO Alex;

-- Amy (Read/Write equivalent)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO Amy;
REVOKE DELETE ON INCIDENTS FROM Amy;

-- Noah (Read-Only equivalent)
GRANT SELECT ON ALL TABLES IN SCHEMA public TO Noah;

-- ============================================================
-- SECTION 4: ENCRYPTION & DATA MASKING NOTES
-- ============================================================
-- Note 1: SQL Server's ENCRYPTBYKEY and Symmetric Key logic has been removed. 
-- For the AWS migration, encryption at rest will be handled natively by 
-- enabling AWS KMS encryption on the Amazon RDS instance.
--
-- Note 2: Dynamic Data Masking (MASKED WITH) has been removed as it is not 
-- natively supported in standard open-source databases without extensions.

-- ============================================================
-- SECTION 5: VERIFICATION QUERIES
-- ============================================================

-- Check users and roles
SELECT u.UserID, u.Username, r.RoleName, u.ContactNumber
FROM USERS u
JOIN ROLES r ON u.RoleID = r.RoleID;

-- Check incidents
SELECT i.IncidentID, i.Type, i.Severity, u.Username, i.CreatedAt
FROM INCIDENTS i
JOIN USERS u ON i.ReporterID = u.UserID;