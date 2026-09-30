-- Q10. Where are SLAs being missed? SLA compliance by resolving team and severity.
SELECT a.team,
       i.severity,
       COUNT(*)                                                         AS incidents,
       ROUND(100.0 * SUM((JULIANDAY(i.resolved_at) - JULIANDAY(i.opened_at)) * 24
                         <= s.target_hours) / COUNT(*), 1)              AS sla_met_pct
FROM incidents i
JOIN agents a     ON a.agent_id = i.agent_id
JOIN sla_policy s ON s.severity = i.severity
GROUP BY a.team, i.severity
ORDER BY a.team, i.severity;
