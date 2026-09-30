-- IT Incident & User Analysis: database schema (SQLite)
DROP TABLE IF EXISTS incidents;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS agents;
DROP TABLE IF EXISTS departments;
DROP TABLE IF EXISTS sla_policy;

CREATE TABLE departments (
    department_id    INTEGER PRIMARY KEY,
    department_name  TEXT NOT NULL,
    headcount_budget INTEGER
);

CREATE TABLE users (
    user_id       INTEGER PRIMARY KEY,
    full_name     TEXT NOT NULL,
    department_id INTEGER NOT NULL REFERENCES departments(department_id),
    location      TEXT CHECK (location IN ('HQ Office','Branch Office','Remote')),
    device_os     TEXT,
    hire_date     DATE NOT NULL
);

CREATE TABLE agents (
    agent_id   INTEGER PRIMARY KEY,
    agent_name TEXT NOT NULL,
    team       TEXT NOT NULL
);

CREATE TABLE sla_policy (
    severity     TEXT PRIMARY KEY,
    target_hours REAL NOT NULL
);

CREATE TABLE incidents (
    incident_id INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(user_id),
    agent_id    INTEGER NOT NULL REFERENCES agents(agent_id),
    opened_at   DATETIME NOT NULL,
    resolved_at DATETIME,
    category    TEXT NOT NULL,
    severity    TEXT NOT NULL REFERENCES sla_policy(severity),
    reopened    INTEGER NOT NULL DEFAULT 0 CHECK (reopened IN (0,1))
);

CREATE INDEX idx_incidents_user  ON incidents(user_id);
CREATE INDEX idx_incidents_agent ON incidents(agent_id);
CREATE INDEX idx_incidents_open  ON incidents(opened_at);
