-- Q2. Headline KPIs for Jan–Jun 2026.
WITH inc AS (
    SELECT i.*,
           (JULIANDAY(i.resolved_at) - JULIANDAY(i.opened_at)) * 24 AS resolution_hours,
           s.target_hours
    FROM incidents i
    JOIN sla_policy s ON s.severity = i.severity
)
SELECT COUNT(*)                                                    AS total_incidents,
       COUNT(DISTINCT user_id)                                     AS users_affected,
       (SELECT COUNT(*) FROM users)                                AS total_users,
       ROUND(AVG(resolution_hours), 1)                             AS avg_resolution_hours,
       ROUND(100.0 * SUM(resolution_hours <= target_hours) / COUNT(*), 1) AS sla_met_pct,
       ROUND(100.0 * AVG(reopened), 1)                             AS reopen_rate_pct
FROM inc;
