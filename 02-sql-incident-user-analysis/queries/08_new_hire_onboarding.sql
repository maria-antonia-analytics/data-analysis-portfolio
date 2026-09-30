-- Q8. Do new hires need more IT help? Compare the incident rate in an employee's
-- first 30 days with the rate afterwards (incidents per user per 30 days).
-- Only users hired in 2026 are included, so both periods fall inside the data window.
WITH new_hires AS (
    SELECT user_id, hire_date
    FROM users
    WHERE hire_date BETWEEN '2026-01-01' AND '2026-05-31'
),
tagged AS (
    SELECT n.user_id,
           CASE WHEN JULIANDAY(DATE(i.opened_at)) - JULIANDAY(n.hire_date) <= 30
                THEN 'First 30 days' ELSE 'After day 30' END AS period,
           i.category
    FROM new_hires n
    JOIN incidents i ON i.user_id = n.user_id
),
exposure AS (   -- how many "30-day windows" each period covers across all new hires
    SELECT 'First 30 days' AS period,
           SUM(MIN(30, JULIANDAY('2026-06-30') - JULIANDAY(hire_date)) ) / 30.0 AS user_months
    FROM new_hires
    UNION ALL
    SELECT 'After day 30',
           SUM(MAX(0, JULIANDAY('2026-06-30') - JULIANDAY(hire_date) - 30)) / 30.0
    FROM new_hires
)
SELECT t.period,
       COUNT(*)                                                     AS incidents,
       ROUND(COUNT(*) / e.user_months, 2)                           AS incidents_per_user_month,
       ROUND(100.0 * SUM(t.category IN ('Login / MFA','Access Request')) / COUNT(*), 1)
                                                                    AS login_access_share_pct
FROM tagged t
JOIN exposure e ON e.period = t.period
GROUP BY t.period
ORDER BY t.period DESC;
