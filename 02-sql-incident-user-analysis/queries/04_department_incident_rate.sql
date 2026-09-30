-- Q4. Which departments generate the most incidents per employee?
-- Raw counts favor big departments, so normalize by headcount and rank.
WITH dept_users AS (
    SELECT department_id, COUNT(*) AS employees
    FROM users
    GROUP BY department_id
),
dept_incidents AS (
    SELECT u.department_id,
           COUNT(*)                                   AS incidents,
           SUM(i.category = 'Software')               AS software_incidents
    FROM incidents i
    JOIN users u ON u.user_id = i.user_id
    GROUP BY u.department_id
)
SELECT d.department_name,
       du.employees,
       di.incidents,
       ROUND(1.0 * di.incidents / du.employees, 2)          AS incidents_per_employee,
       ROUND(100.0 * di.software_incidents / di.incidents, 1) AS software_share_pct,
       RANK() OVER (ORDER BY 1.0 * di.incidents / du.employees DESC) AS rate_rank
FROM departments d
JOIN dept_users     du ON du.department_id = d.department_id
JOIN dept_incidents di ON di.department_id = d.department_id
ORDER BY rate_rank;
