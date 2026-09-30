-- Q7. Are remote workers struggling with VPN? Compare VPN incidents per user by location.
WITH loc_users AS (
    SELECT location, COUNT(*) AS users FROM users GROUP BY location
)
SELECT u.location,
       lu.users,
       SUM(i.category = 'VPN')                                         AS vpn_incidents,
       ROUND(1.0 * SUM(i.category = 'VPN') / lu.users, 2)              AS vpn_per_user,
       ROUND(100.0 * SUM(i.category = 'VPN') / COUNT(*), 1)            AS vpn_share_of_incidents_pct
FROM incidents i
JOIN users u      ON u.user_id = i.user_id
JOIN loc_users lu ON lu.location = u.location
GROUP BY u.location
ORDER BY vpn_per_user DESC;
