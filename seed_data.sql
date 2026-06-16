-- ============================================================
-- CLEAN DATA & RESET IDENTITY COUNTERS
-- PostgreSQL uses TRUNCATE with RESTART IDENTITY to wipe data 
-- and reset the SERIAL counters back to 1 in a single command.
-- ============================================================

TRUNCATE TABLE AUDIT_LOGS, INCIDENTS, USER_LOGIN, USERS, ROLES RESTART IDENTITY CASCADE;

-- ============================================================
-- INSERT ROLES, USERS, & LOGINS
-- ============================================================

INSERT INTO ROLES (RoleName, PermissionLevel) VALUES
('Admin',   'Full'),
('Analyst', 'ReadWrite'),
('Viewer',  'ReadOnly');

INSERT INTO USERS (Username, RoleID, ContactNumber) VALUES
('alex', 1, '0111000001'),
('amy',  2, '0111000002'),
('noah', 3, '0111000003');

INSERT INTO USER_LOGIN (UserID, PasswordHash, LastLogin) VALUES
(1, '$2b$12$qh7tHbvAyrIg2.wXjIEiwOBDAvbzq2l.wPs/GnwEa4ziHDpXzHarS', NOW()),
(2, '$2b$12$qh7tHbvAyrIg2.wXjIEiwOBDAvbzq2l.wPs/GnwEa4ziHDpXzHarS', NOW()),
(3, '$2b$12$qh7tHbvAyrIg2.wXjIEiwOBDAvbzq2l.wPs/GnwEa4ziHDpXzHarS', NOW());

-- ============================================================
-- INSERT 3 FIXED & 100 RANDOM INCIDENTS
-- PostgreSQL uses DO $$ ... END $$; for procedural logic.
-- random() is used instead of NEWID().
-- ============================================================

DO $$
DECLARE 
    i INT := 1;
    v_type VARCHAR(100);
    v_severity VARCHAR(20);
    v_details TEXT;
    v_reporter INT;
    v_status VARCHAR(20);
    v_created TIMESTAMP;
BEGIN
    -- Insert 3 fixed examples first
    INSERT INTO INCIDENTS (Type, Severity, Details, DetailsEncrypted, ReporterID, Status, CreatedAt) VALUES
    ('Unauthorised Access', 'High', '***ENCRYPTED***', convert_to('Detected login from unknown IP 192.168.99.1 at 2AM outside business hours', 'UTF8'), 1, 'Active', NOW() - INTERVAL '5 days'),
    ('Data Leak', 'Critical', '***ENCRYPTED***', convert_to('Sensitive customer file accessed and downloaded without authorisation', 'UTF8'), 2, 'Active', NOW() - INTERVAL '3 days'),
    ('Phishing Attempt', 'Medium', '***ENCRYPTED***', convert_to('Staff member received suspicious email impersonating IT department', 'UTF8'), 3, 'Resolved', NOW() - INTERVAL '10 days');

    -- Generate 100 random incidents
    WHILE i <= 100 LOOP
        -- Random Type
        v_type := CASE floor(random() * 9)::int
            WHEN 0 THEN 'Phishing'
            WHEN 1 THEN 'Unauthorised Access'
            WHEN 2 THEN 'Data Leak'
            WHEN 3 THEN 'Malware'
            WHEN 4 THEN 'Ransomware'
            WHEN 5 THEN 'Brute Force'
            WHEN 6 THEN 'DDoS'
            WHEN 7 THEN 'Insider Threat'
            ELSE        'Social Engineering'
        END;

        -- Random Severity
        v_severity := CASE floor(random() * 4)::int
            WHEN 0 THEN 'Low'
            WHEN 1 THEN 'Medium'
            WHEN 2 THEN 'High'
            ELSE        'Critical'
        END;

        -- Random Reporter (1-3)
        v_reporter := floor(random() * 3)::int + 1;

        -- Random Status (80% Active)
        v_status := CASE floor(random() * 5)::int
            WHEN 0 THEN 'Resolved'
            ELSE        'Active'
        END;

        -- Random Timestamp (up to 90 days ago / 129600 minutes)
        v_created := NOW() - (floor(random() * 129600)::int || ' minutes')::INTERVAL;

        -- Unique details based on type
        IF v_type = 'Phishing' THEN
            v_details := 'Phishing variant detected. Case #' || i::VARCHAR;
        ELSIF v_type = 'Unauthorised Access' THEN
            v_details := 'Unauthorised access from IP 192.168.' || floor(random() * 255)::int::VARCHAR || '.1. Case #' || i::VARCHAR;
        ELSIF v_type = 'Data Leak' THEN
            v_details := 'Potential data exfiltration detected on endpoint. Case #' || i::VARCHAR;
        ELSIF v_type = 'Malware' THEN
            v_details := 'Malicious payload isolated on WS-' || i::VARCHAR;
        ELSIF v_type = 'Ransomware' THEN
            v_details := 'Ransomware indicators found on ' || (floor(random() * 10)::int + 1)::VARCHAR || ' endpoints. Case #' || i::VARCHAR;
        ELSIF v_type = 'Brute Force' THEN
            v_details := (floor(random() * 900)::int + 100)::VARCHAR || ' failed login attempts blocked. Case #' || i::VARCHAR;
        ELSIF v_type = 'DDoS' THEN
            v_details := 'Volumetric attack mitigated. Traffic spiked to ' || (floor(random() * 900)::int + 100)::VARCHAR || 'Gbps.';
        ELSIF v_type = 'Insider Threat' THEN
            v_details := 'Anomalous internal data movement flagged. Case #' || i::VARCHAR;
        ELSE
            v_details := 'Social engineering attempt reported by staff. Case #' || i::VARCHAR;
        END IF;

        -- Insert the record
        INSERT INTO INCIDENTS (Type, Severity, Details, DetailsEncrypted, ReporterID, Status, CreatedAt)
        VALUES (v_type, v_severity, '***ENCRYPTED***', convert_to(v_details, 'UTF8'), v_reporter, v_status, v_created);

        i := i + 1;
    END LOOP;
END $$;

-- ============================================================
-- VERIFICATION
-- ============================================================

SELECT 
    COUNT(*) AS TotalIncidents,
    SUM(CASE WHEN Status = 'Active' THEN 1 ELSE 0 END) AS Active,
    SUM(CASE WHEN Status = 'Resolved' THEN 1 ELSE 0 END) AS Resolved
FROM INCIDENTS;