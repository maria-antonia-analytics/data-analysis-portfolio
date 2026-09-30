-- Q9. How does each agent perform against their own team's average?
-- Window AVG() ... OVER (PARTITION BY team) gives the team benchmark on every row.
WITH agent_stats AS (
    SELECT a.agent_name,
           a.team,
           COUNT(*)                                                           AS incidents,
           ROUND(AVG((JULIANDAY(i.resolved_at) - JULIANDAY(i.opened_at)) * 24), 1) AS avg_hours,
           ROUND(100.0 * AVG(i.reopened), 1)                                  AS reopen_rate_pct
    FROM incidents i
    JOIN agents a ON a.agent_id = i.agent_id
    GROUP BY a.agent_id
)
SELECT agent_name,
       team,
       incidents,
       avg_hours,
       reopen_rate_pct,
       ROUND(AVG(reopen_rate_pct) OVER (PARTITION BY team), 1) AS team_avg_reopen_pct,
       CASE WHEN reopen_rate_pct > 1.5 * AVG(reopen_rate_pct) OVER (PARTITION BY team)
            THEN 'Review' ELSE 'OK' END                          AS flag   -- 50%+ above team average
FROM agent_stats
ORDER BY team, reopen_rate_pct DESC;
