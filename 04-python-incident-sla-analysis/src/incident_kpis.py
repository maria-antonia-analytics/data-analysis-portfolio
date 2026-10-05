"""
incident_kpis.py
Load the IT incident database from project 2 and turn it into one
analysis-ready table, plus the KPI functions the notebook uses.

Input:  ../02-sql-incident-user-analysis/it_incidents.db  (SQLite, 5 tables)
Output: one DataFrame with one row per incident

Run from the project folder to print a KPI summary:
    python src/incident_kpis.py
"""
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT.parent / "02-sql-incident-user-analysis" / "it_incidents.db"

# One query joins the five tables. Everything after that happens in Pandas.
QUERY = """
SELECT i.incident_id, i.opened_at, i.resolved_at, i.category, i.severity, i.reopened,
       i.user_id, u.location, u.device_os, u.hire_date,
       d.department_name AS department,
       i.agent_id, a.agent_name, a.team,
       s.target_hours
FROM incidents i
JOIN users u       ON u.user_id = i.user_id
JOIN departments d ON d.department_id = u.department_id
JOIN agents a      ON a.agent_id = i.agent_id
JOIN sla_policy s  ON s.severity = i.severity
ORDER BY i.incident_id
"""

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def load_incidents(db_path=DB_PATH) -> pd.DataFrame:
    """Read the database and add the columns every later step needs."""
    with sqlite3.connect(db_path) as con:
        df = pd.read_sql(QUERY, con, parse_dates=["opened_at", "resolved_at", "hire_date"])

    df["reopened"] = df["reopened"].astype(bool)
    df["resolution_hours"] = (df["resolved_at"] - df["opened_at"]).dt.total_seconds() / 3600
    df["sla_met"] = df["resolution_hours"] <= df["target_hours"]
    # 1.0 means the ticket used exactly its target; 1.5 means it ran 50% over.
    df["sla_ratio"] = df["resolution_hours"] / df["target_hours"]
    df["hours_over"] = (df["resolution_hours"] - df["target_hours"]).clip(lower=0)
    df["opened_date"] = df["opened_at"].dt.normalize()
    df["opened_weekday"] = pd.Categorical(df["opened_at"].dt.day_name(), WEEKDAYS[:5], ordered=True)
    df["resolved_weekday"] = pd.Categorical(df["resolved_at"].dt.day_name(), WEEKDAYS, ordered=True)
    return df


def quality_checks(df: pd.DataFrame) -> pd.Series:
    """Count rows that would make the analysis wrong. All should be zero."""
    return pd.Series({
        "missing values": int(df.isna().sum().sum()),
        "duplicate incident ids": int(df["incident_id"].duplicated().sum()),
        "resolved before opened": int((df["resolved_at"] < df["opened_at"]).sum()),
        "opened before hire date": int((df["opened_at"] < df["hire_date"]).sum()),
        "opened on a weekend": int((df["opened_at"].dt.dayofweek >= 5).sum()),
    }, name="rows")


def kpi_summary(df: pd.DataFrame) -> pd.Series:
    """Headline numbers for any slice of the incident table."""
    hours = df["resolution_hours"]
    return pd.Series({
        "incidents": len(df),
        "mean hours": round(hours.mean(), 1),
        "median hours": round(hours.median(), 1),
        "90th percentile hours": round(hours.quantile(0.90), 1),
        "SLA compliance %": round(df["sla_met"].mean() * 100, 1),
        "SLA breaches": int((~df["sla_met"]).sum()),
        "hours over target": round(df["hours_over"].sum()),
        "reopen rate %": round(df["reopened"].mean() * 100, 1),
    })


def sla_by(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """The same KPIs, one row per group, worst SLA compliance first."""
    out = df.groupby(column, observed=True).apply(kpi_summary, include_groups=False)
    return out.sort_values("SLA compliance %")


def standardised_compliance(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """SLA compliance each group would have with the company-wide severity mix.

    A group that gets more urgent tickets has tighter targets, so its raw
    compliance can look worse for a reason that is not its fault. This puts
    every group on the same mix so they can be compared fairly.
    """
    mix = df["severity"].value_counts(normalize=True)
    rates = df.pivot_table(index=column, columns="severity", values="sla_met", aggfunc="mean")
    return pd.DataFrame({
        "raw %": df.groupby(column)["sla_met"].mean() * 100,
        "same severity mix %": (rates * mix).sum(axis=1) * 100,
    }).round(1)


def open_backlog(df: pd.DataFrame, by: str = "team") -> pd.DataFrame:
    """Number of incidents open at the end of each day, one column per group.

    Every ticket adds 1 when it opens and removes 1 when it is resolved.
    The running total of those +1/-1 events is the open backlog.
    """
    events = pd.concat([
        pd.DataFrame({"time": df["opened_at"], by: df[by], "change": 1}),
        pd.DataFrame({"time": df["resolved_at"], by: df[by], "change": -1}),
    ]).sort_values("time")
    events["open"] = events.groupby(by)["change"].cumsum()
    daily = (events.set_index("time").groupby(by)["open"]
             .resample("D").last().unstack(by).ffill().fillna(0))
    return daily


def repeat_contacts(df: pd.DataFrame, window_days: int = 14) -> pd.Series:
    """True where the same user opened the same category again within the window."""
    ordered = df.sort_values(["user_id", "category", "opened_at"])
    previous = ordered.groupby(["user_id", "category"])["opened_at"].shift()
    gap_days = (ordered["opened_at"] - previous).dt.total_seconds() / 86400
    return (gap_days <= window_days).reindex(df.index)


def open_when_opened(df: pd.DataFrame, by: str = "team") -> pd.Series:
    """For each incident: how many tickets its group had open at the moment it arrived
    (counting the new ticket itself)."""
    events = pd.concat([
        pd.DataFrame({"time": df["opened_at"], by: df[by], "change": 1, "incident_id": df["incident_id"]}),
        pd.DataFrame({"time": df["resolved_at"], by: df[by], "change": -1, "incident_id": -1}),
    ]).sort_values(["time", "change"])            # at the same minute, count resolutions first
    events["open"] = events.groupby(by)["change"].cumsum()
    opened = events[events["change"] == 1].set_index("incident_id")["open"]
    return df["incident_id"].map(opened)


def _count_repeats(user, category, day, window_days):
    order = np.lexsort((day, category, user))
    u, c, d = user[order], category[order], day[order]
    return int(((u[1:] == u[:-1]) & (c[1:] == c[:-1]) & (d[1:] - d[:-1] <= window_days)).sum())


def repeat_contacts_by_chance(df: pd.DataFrame, window_days: int = 14,
                              n_shuffles: int = 2_000, seed: int = 42) -> dict:
    """How many repeat contacts would heavy users produce by chance alone?

    Keeps every user's ticket dates and their number of tickets per category,
    but shuffles which ticket got which category. If fixes fail and users come
    straight back, the real count will be clearly above the shuffled counts.
    """
    user = df["user_id"].to_numpy()
    category = pd.factorize(df["category"])[0]
    day = (df["opened_at"] - df["opened_at"].min()).dt.total_seconds().to_numpy() / 86400
    observed = _count_repeats(user, category, day, window_days)

    rng = np.random.default_rng(seed)
    by_user = np.argsort(user, kind="stable")
    shuffled = np.empty(n_shuffles)
    for i in range(n_shuffles):
        within_user = np.lexsort((rng.random(len(user)), user[by_user]))
        new_category = np.empty_like(category)
        new_category[by_user] = category[by_user][within_user]
        shuffled[i] = _count_repeats(user, new_category, day, window_days)
    low, high = np.percentile(shuffled, [2.5, 97.5])
    return {
        "observed repeat contacts": observed,
        "expected by chance": round(float(shuffled.mean()), 1),
        "chance range (95%)": f"{low:.0f} to {high:.0f}",
        "share of shuffles at or above observed": round(float((shuffled >= observed).mean()), 3),
    }


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple:
    """95% confidence interval for a proportion (Wilson score method)."""
    p = successes / n
    centre = (p + z**2 / (2 * n)) / (1 + z**2 / n)
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / (1 + z**2 / n)
    return centre - half, centre + half


def permutation_test(flag: pd.Series, in_group: pd.Series, n_shuffles: int = 10_000, seed: int = 42) -> dict:
    """How often would chance alone produce a gap this large?

    Shuffles the group labels many times and counts how often the shuffled
    difference in rates is at least as large as the real one (two-sided).
    """
    values = flag.to_numpy(dtype=float)
    mask = in_group.to_numpy(dtype=bool)
    observed = values[mask].mean() - values[~mask].mean()
    rng = np.random.default_rng(seed)
    shuffled = np.empty(n_shuffles)
    for i in range(n_shuffles):
        m = rng.permutation(mask)
        shuffled[i] = values[m].mean() - values[~m].mean()
    return {
        "group rate %": round(values[mask].mean() * 100, 1),
        "rest rate %": round(values[~mask].mean() * 100, 1),
        "difference (points)": round(observed * 100, 1),
        # +1 so the p-value is never exactly zero: the real data counts as one arrangement
        "p-value": round(float(((np.abs(shuffled) >= abs(observed)).sum() + 1) / (n_shuffles + 1)), 4),
    }


if __name__ == "__main__":
    incidents = load_incidents()
    print(f"Loaded {len(incidents):,} incidents from {DB_PATH.name}\n")
    print("Data quality checks (all should be 0)")
    print(quality_checks(incidents).to_string(), "\n")
    print("Overall KPIs")
    print(kpi_summary(incidents).to_string(), "\n")
    print("By team")
    print(sla_by(incidents, "team").to_string())
