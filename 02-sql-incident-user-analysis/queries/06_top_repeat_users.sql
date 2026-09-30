-- Q6. Who are the top 10 repeat users, and what keeps breaking?
-- Correlated subquery finds each user's most frequent category.
SELECT u.user_id,
       u.full_name,
       d.department_name,
       u.location,
       COUNT(*) AS incidents,
       (SELECT i2.category
        FROM incidents i2
        WHERE i2.user_id = u.user_id
        GROUP BY i2.category
        ORDER BY COUNT(*) DESC, i2.category
        LIMIT 1) AS top_category
FROM incidents i
JOIN users u       ON u.user_id = i.user_id
JOIN departments d ON d.department_id = u.department_id
GROUP BY u.user_id
ORDER BY incidents DESC
LIMIT 10;
