-- Q1. Is the data trustworthy? Check for orphans, bad timestamps and duplicates
-- before analyzing anything.
SELECT 'Incidents with unknown user' AS check_name, COUNT(*) AS issues
FROM incidents i LEFT JOIN users u ON u.user_id = i.user_id
WHERE u.user_id IS NULL
UNION ALL
SELECT 'Incidents with unknown agent', COUNT(*)
FROM incidents i LEFT JOIN agents a ON a.agent_id = i.agent_id
WHERE a.agent_id IS NULL
UNION ALL
SELECT 'Resolved before opened', COUNT(*)
FROM incidents WHERE resolved_at < opened_at
UNION ALL
SELECT 'Missing resolution time', COUNT(*)
FROM incidents WHERE resolved_at IS NULL
UNION ALL
SELECT 'Incident opened before user was hired', COUNT(*)
FROM incidents i JOIN users u ON u.user_id = i.user_id
WHERE DATE(i.opened_at) < u.hire_date
UNION ALL
SELECT 'Duplicate incident IDs', COUNT(*) - COUNT(DISTINCT incident_id)
FROM incidents;
