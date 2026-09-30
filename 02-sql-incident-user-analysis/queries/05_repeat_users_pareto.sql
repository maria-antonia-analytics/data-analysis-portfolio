-- Q5. Do a small group of users create most of the incidents? (Pareto analysis)
-- NTILE() splits users into 10 equal groups by incident count.
WITH user_counts AS (
    SELECT u.user_id,
           COUNT(i.incident_id) AS incidents
    FROM users u
    LEFT JOIN incidents i ON i.user_id = u.user_id
    GROUP BY u.user_id
),
deciles AS (
    SELECT user_id, incidents,
           NTILE(10) OVER (ORDER BY incidents DESC) AS decile
    FROM user_counts
)
SELECT decile,
       COUNT(*)                                                    AS users,
       SUM(incidents)                                              AS incidents,
       ROUND(100.0 * SUM(incidents) / (SELECT COUNT(*) FROM incidents), 1) AS share_pct,
       ROUND(100.0 * SUM(SUM(incidents)) OVER (ORDER BY decile)
             / (SELECT COUNT(*) FROM incidents), 1)                AS cumulative_share_pct
FROM deciles
GROUP BY decile
ORDER BY decile;
