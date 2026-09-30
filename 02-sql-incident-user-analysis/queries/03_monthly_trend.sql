-- Q3. How is incident volume trending month over month?
-- Uses a CTE plus the LAG() window function.
WITH monthly AS (
    SELECT STRFTIME('%Y-%m', opened_at) AS month,
           COUNT(*)                     AS incidents
    FROM incidents
    GROUP BY month
)
SELECT month,
       incidents,
       LAG(incidents) OVER (ORDER BY month) AS prev_month,
       ROUND(100.0 * (incidents - LAG(incidents) OVER (ORDER BY month))
             / LAG(incidents) OVER (ORDER BY month), 1) AS mom_change_pct
FROM monthly
ORDER BY month;
