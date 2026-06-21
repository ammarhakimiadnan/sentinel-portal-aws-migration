-- ============================================================
-- Security Test Suite
-- Run each section individually to verify specific security features
-- ============================================================

USE SentinelDB;
GO

-- ============================================================
-- TEST 1: PASSWORD POLICY VERIFICATION
-- Expected: Amy + Noah show is_expiration_checked=1, 
--           is_policy_checked=1. Alex shows 0,1
-- ============================================================
PRINT '=== TEST 1: Password Policy Verification ==='

USE master;
GO

SELECT 
    name,
    is_expiration_checked,
    is_policy_checked,
    is_disabled
FROM sys.sql_logins
WHERE name IN ('Alex', 'Amy', 'Noah');
GO

-- ============================================================
-- TEST 2: RBAC ROLE ASSIGNMENTS
-- Expected: Alex=db_owner, Amy=db_datareader+db_datawriter,
--           Noah=db_datareader only
-- ============================================================
PRINT '=== TEST 2: RBAC Role Assignments ==='

USE SentinelDB;
GO

SELECT 
    u.name AS UserName,
    r.name AS RoleName
FROM sys.database_role_members rm
JOIN sys.database_principals r 
    ON rm.role_principal_id = r.principal_id
JOIN sys.database_principals u 
    ON rm.member_principal_id = u.principal_id
WHERE u.name IN ('Alex', 'Amy', 'Noah')
ORDER BY u.name;
GO

-- ============================================================
-- TEST 3: DENY PERMISSIONS SUMMARY
-- Expected: Full list of all DENY permissions for Amy and Noah
-- ============================================================
PRINT '=== TEST 3: DENY Permissions Summary ==='

USE SentinelDB;
GO

SELECT 
    pr.name AS Principal,
    pe.permission_name AS Permission,
    ob.name AS TableName,
    pe.state_desc AS State
FROM sys.database_permissions pe
JOIN sys.database_principals pr 
    ON pe.grantee_principal_id = pr.principal_id
JOIN sys.objects ob 
    ON pe.major_id = ob.object_id
WHERE pr.name IN ('Amy', 'Noah')
  AND pe.state_desc = 'DENY'
ORDER BY pr.name, ob.name;
GO

-- ============================================================
-- TEST 4: NOAH CANNOT DELETE INCIDENTS
-- Expected: "DELETE permission was denied on object INCIDENTS"
-- ============================================================
PRINT '=== TEST 4: Noah DELETE Denied ==='

USE SentinelDB;
GO

EXECUTE AS USER = 'Noah';
    DELETE FROM INCIDENTS WHERE IncidentID = 1;
REVERT;
GO

-- ============================================================
-- TEST 5: AMY CANNOT DELETE INCIDENTS
-- Expected: "DELETE permission was denied on object INCIDENTS"
-- ============================================================
PRINT '=== TEST 5: Amy DELETE Denied ==='

USE SentinelDB;
GO

EXECUTE AS USER = 'Amy';
    DELETE FROM INCIDENTS WHERE IncidentID = 1;
REVERT;
GO

-- ============================================================
-- TEST 6: NOAH CANNOT INSERT INCIDENTS
-- Expected: "INSERT permission was denied on object INCIDENTS"
-- ============================================================
PRINT '=== TEST 6: Noah INSERT Denied ==='

USE SentinelDB;
GO

EXECUTE AS USER = 'Noah';
    INSERT INTO INCIDENTS (Type, Severity, Details, ReporterID, Status)
    VALUES ('Test', 'Low', 'Test insert by Noah', 3, 'Active');
REVERT;
GO

-- ============================================================
-- TEST 7: NOAH CANNOT ACCESS USER_LOGIN
-- Expected: "SELECT permission was denied on object USER_LOGIN"
-- ============================================================
PRINT '=== TEST 7: Noah Cannot Access USER_LOGIN ==='

USE SentinelDB;
GO

EXECUTE AS USER = 'Noah';
    SELECT * FROM USER_LOGIN;
REVERT;
GO

-- ============================================================
-- TEST 8: AMY CANNOT ACCESS USER_LOGIN
-- Expected: "SELECT permission was denied on object USER_LOGIN"
-- ============================================================
PRINT '=== TEST 8: Amy Cannot Access USER_LOGIN ==='

USE SentinelDB;
GO

EXECUTE AS USER = 'Amy';
    SELECT * FROM USER_LOGIN;
REVERT;
GO

-- ============================================================
-- TEST 9: COLUMN ENCRYPTION — RAW DATA WITHOUT KEY
-- Expected: Details = ***ENCRYPTED***, 
--           DetailsEncrypted = binary blob (0x0083B48F...)
-- ============================================================
PRINT '=== TEST 9: Column Encryption — Raw Data ==='

USE SentinelDB;
GO

SELECT TOP 5
    IncidentID,
    Type,
    Details,
    DetailsEncrypted
FROM INCIDENTS
ORDER BY IncidentID ASC;
GO

-- ============================================================
-- TEST 10: COLUMN ENCRYPTION — DECRYPT WITH KEY
-- Expected: Decrypted column shows original readable text
-- ============================================================
PRINT '=== TEST 10: Column Encryption — Decrypt With Key ==='

USE SentinelDB;
GO

OPEN SYMMETRIC KEY SentinelSymKey
    DECRYPTION BY CERTIFICATE SentinelCert;

SELECT TOP 5
    IncidentID,
    Type,
    DetailsEncrypted AS Encrypted,
    CONVERT(NVARCHAR(MAX), 
        DECRYPTBYKEY(DetailsEncrypted)) AS Decrypted
FROM INCIDENTS
ORDER BY IncidentID ASC;

CLOSE SYMMETRIC KEY SentinelSymKey;
GO

-- ============================================================
-- TEST 11: DYNAMIC DATA MASKING — NOAH SEES MASKED
-- Expected: ContactNumber = XXXXXXX001, XXXXXXX002, XXXXXXX003
-- ============================================================
PRINT '=== TEST 11: DDM — Noah Sees Masked ContactNumber ==='

USE SentinelDB;
GO

EXECUTE AS USER = 'Noah';
    SELECT 
        UserID, 
        Username, 
        ContactNumber 
    FROM USERS;
REVERT;
GO

-- ============================================================
-- TEST 12: DYNAMIC DATA MASKING — ALEX SEES FULL
-- Expected: ContactNumber = 0111000001, 0111000002, 0111000003
-- ============================================================
PRINT '=== TEST 12: DDM — Alex Sees Full ContactNumber ==='

USE SentinelDB;
GO

EXECUTE AS USER = 'Alex';
    SELECT 
        UserID, 
        Username, 
        ContactNumber 
    FROM USERS;
REVERT;
GO

-- ============================================================
-- TEST 13: ENCRYPTION KEYS EXIST
-- Expected: Master Key, SentinelCert, SentinelSymKey all present
--           algorithm_desc = AES_256, key_length = 256
-- ============================================================
PRINT '=== TEST 13: Encryption Keys Verification ==='

USE SentinelDB;
GO

-- Master Key
SELECT 
    'Master Key' AS KeyType,
    name,
    symmetric_key_id AS KeyID
FROM sys.symmetric_keys
WHERE name = '##MS_DatabaseMasterKey##';

-- Certificate
SELECT 
    'Certificate' AS KeyType,
    name,
    expiry_date,
    pvt_key_encryption_type_desc
FROM sys.certificates
WHERE name = 'SentinelCert';

-- Symmetric Key
SELECT 
    'Symmetric Key' AS KeyType,
    name,
    algorithm_desc,
    key_length
FROM sys.symmetric_keys
WHERE name = 'SentinelSymKey';
GO

-- ============================================================
-- TEST 14: SQL SERVER AUDIT IS RUNNING
-- Expected: is_state_enabled = 1, type_desc = FILE
-- ============================================================
PRINT '=== TEST 14: SQL Server Audit Status ==='

USE master;
GO

SELECT 
    name,
    is_state_enabled,
    type_desc
FROM sys.server_audits
WHERE name = 'SentinelAudit';
GO

-- ============================================================
-- TEST 15: DATABASE AUDIT SPECIFICATION IS ACTIVE
-- Expected: is_state_enabled = 1
-- ============================================================
PRINT '=== TEST 15: Database Audit Specification Status ==='

USE SentinelDB;
GO

SELECT 
    name,
    is_state_enabled
FROM sys.database_audit_specifications
WHERE name = 'SentinelDBAuditSpec';
GO

-- ============================================================
-- TEST 16: AMY'S ACCESS RECORDED IN AUDIT FILE
-- Expected: Amy's SELECT on INCIDENTS recorded
--           action_id = SL, succeeded = 1
-- ============================================================
PRINT '=== TEST 16: Amy Access Recorded in Audit File ==='

USE SentinelDB;
GO

-- Simulate Amy accessing incidents
EXECUTE AS USER = 'Amy';
    SELECT * FROM INCIDENTS;
REVERT;
GO

-- Check audit file for Amy's entry
SELECT TOP 10
    event_time,
    server_principal_name,
    object_name,
    action_id,
    succeeded
FROM sys.fn_get_audit_file(
    'C:\AuditLogs\*.sqlaudit', 
    DEFAULT, DEFAULT)
WHERE server_principal_name = 'Amy'
ORDER BY event_time DESC;
GO

-- ============================================================
-- TEST 17: APP AUDIT_LOGS TABLE
-- Expected: Shows LOGIN, INSERT_INCIDENT, RESOLVE_INCIDENT,
--           DELETE_INCIDENT entries with correct users + timestamps
-- ============================================================
PRINT '=== TEST 17: App AUDIT_LOGS Table ==='

USE SentinelDB;
GO

SELECT 
    a.AuditID,
    u.Username,
    a.ActionType,
    a.ActionTime,
    a.Status
FROM AUDIT_LOGS a
LEFT JOIN USERS u ON a.UserID = u.UserID
ORDER BY a.ActionTime DESC;
GO

-- ============================================================
-- TEST 18: BEFORE DELETE — run before deleting in app
-- Screenshot this, then delete in app, then run TEST 18B
-- ============================================================
PRINT '=== TEST 18A: BEFORE DELETE — Current Incidents ==='

USE SentinelDB;
GO

SELECT
    i.IncidentID,
    i.Type,
    i.Severity,
    i.Status,
    u.Username AS ReportedBy,
    i.CreatedAt
FROM INCIDENTS i
JOIN USERS u ON i.ReporterID = u.UserID
ORDER BY i.IncidentID ASC;
GO

-- ============================================================
-- TEST 18B: AFTER DELETE — run after deleting in app
-- Expected: Deleted incident no longer appears in results
-- ============================================================
PRINT '=== TEST 18B: AFTER DELETE — Incidents After Deletion ==='

USE SentinelDB;
GO

SELECT
    i.IncidentID,
    i.Type,
    i.Severity,
    i.Status,
    u.Username AS ReportedBy,
    i.CreatedAt
FROM INCIDENTS i
JOIN USERS u ON i.ReporterID = u.UserID
ORDER BY i.IncidentID ASC;

-- Confirm deletion logged in audit trail
SELECT TOP 3
    a.AuditID,
    u.Username,
    a.ActionType,
    a.ActionTime,
    a.Status
FROM AUDIT_LOGS a
LEFT JOIN USERS u ON a.UserID = u.UserID
WHERE a.ActionType = 'DELETE_INCIDENT'
ORDER BY a.ActionTime DESC;
GO

-- ============================================================
-- TEST 19: AFTER INSERT — run after inserting in app
-- Expected: Newest incident appears at top of results
-- ============================================================
PRINT '=== TEST 19: AFTER INSERT — Most Recent Incidents ==='

USE SentinelDB;
GO

SELECT TOP 5
    i.IncidentID,
    i.Type,
    i.Severity,
    i.Details,
    i.Status,
    u.Username AS ReportedBy,
    i.CreatedAt
FROM INCIDENTS i
JOIN USERS u ON i.ReporterID = u.UserID
ORDER BY i.CreatedAt DESC;
GO

-- ============================================================
-- TEST 20: FULL SECURITY SUMMARY
-- Expected: Clean table showing AUDIT, DENY, ENCRYPTION, 
--           RBAC all active in one view
-- ============================================================
PRINT '=== TEST 20: Full Security Summary ==='

USE SentinelDB;
GO

SELECT 'RBAC' AS Category,
    u.name AS Principal,
    r.name AS Detail
FROM sys.database_role_members rm
JOIN sys.database_principals r 
    ON rm.role_principal_id = r.principal_id
JOIN sys.database_principals u 
    ON rm.member_principal_id = u.principal_id
WHERE u.name IN ('Alex', 'Amy', 'Noah')

UNION ALL

SELECT 'DENY' AS Category,
    pr.name AS Principal,
    pe.permission_name COLLATE Latin1_General_CI_AS
        + ' ON '
        + ob.name COLLATE Latin1_General_CI_AS AS Detail
FROM sys.database_permissions pe
JOIN sys.database_principals pr 
    ON pe.grantee_principal_id = pr.principal_id
JOIN sys.objects ob 
    ON pe.major_id = ob.object_id
WHERE pr.name IN ('Amy', 'Noah')
  AND pe.state_desc = 'DENY'

UNION ALL

SELECT 'ENCRYPTION' AS Category,
    name AS Principal,
    algorithm_desc + 
        ' (' + CAST(key_length AS NVARCHAR) + ' bit)' AS Detail
FROM sys.symmetric_keys
WHERE name = 'SentinelSymKey'

UNION ALL

SELECT 'AUDIT' AS Category,
    name AS Principal,
    CASE is_state_enabled 
        WHEN 1 THEN 'RUNNING' 
        ELSE 'STOPPED' 
    END AS Detail
FROM sys.server_audits
WHERE name = 'SentinelAudit'

ORDER BY Category, Principal;
GO

-- ============================================================
-- END OF SECURITY TEST SUITE
-- Total: 20 tests covering Authentication, RBAC, Encryption,
--        DDM, Audit Trail, and Data Integrity
-- ============================================================
PRINT '=== All Security Tests Completed ==='