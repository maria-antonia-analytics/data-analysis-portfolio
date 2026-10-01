"""
parse_logs.py
Turn two raw server logs into clean, analysis-ready CSV files.

Input  (data/raw):   Linux.log   - syslog from a Linux server called "combo"
                     Apache.log  - Apache error log from the same server
Output (data/clean): linux_events.csv, apache_events.csv, parse_report.csv

Run from the project folder:
    python src/parse_logs.py
"""
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
CLEAN = ROOT / "data" / "clean"

MONTHS = {m: i + 1 for i, m in enumerate(
    "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}

# The syslog has no year. The Apache log from the same server starts on
# Thu Jun 09 2005, the same day and minute, so the syslog starts in 2005.
START_YEAR = 2005

# e.g. "Jun 14 15:16:01 combo sshd(pam_unix)[19939]: authentication failure; ..."
LINUX_LINE = re.compile(
    r"^(?P<mon>\w{3})\s+(?P<day>\d+) (?P<time>\d\d:\d\d:\d\d) (?P<host>\S+) "
    r"(?P<component>[^:\[]+?)(?:\[(?P<pid>\d+)\])?: (?P<message>.*)$")

# e.g. "[Thu Jun 09 06:07:04 2005] [notice] LDAP: Built with OpenLDAP LDAP SDK"
APACHE_LINE = re.compile(
    r"^\[(?P<ts>\w{3} \w{3} \d\d \d\d:\d\d:\d\d \d{4})\] \[(?P<level>\w+)\] (?P<message>.*)$")


def classify_linux(component: str, message: str) -> str:
    """Give every syslog line one event type."""
    if message.startswith("Out of Memory: Killed process"):
        return "oom_kill"
    if "authentication failure" in message or message.startswith("Authentication failed") \
            or message == "Kerberos authentication failed":
        return "auth_failure"
    if message.startswith("check pass; user unknown") or message.startswith("bad username"):
        return "unknown_user"
    if message.startswith("session opened"):
        return "session_opened"
    if message.startswith("session closed"):
        return "session_closed"
    if component == "ftpd" and message.startswith("connection from"):
        return "ftp_connection"
    if component == "kernel" and message.startswith("Linux version"):
        return "boot"
    if component == "logrotate" and "exited abnormally" in message:
        return "logrotate_failure"
    if component == "kernel":
        return "kernel_other"
    return "other"


def parse_linux(path: Path):
    rows, skipped = [], 0
    year, prev_month = START_YEAR, None
    for line in path.read_text(errors="replace").splitlines():
        month = MONTHS.get(line[:3])
        if month is None:
            skipped += 1
            continue
        if prev_month and month < prev_month:      # Dec -> Jan: a new year
            year += 1
        prev_month = month
        m = LINUX_LINE.match(line)
        if not m:                                  # e.g. "last message repeated 2 times"
            skipped += 1
            continue
        ts = pd.Timestamp(f"{year}-{month:02d}-{int(m['day']):02d} {m['time']}")
        rows.append((ts, m["component"].strip(), m["pid"], m["message"].strip()))

    df = pd.DataFrame(rows, columns=["timestamp", "component", "pid", "message"])
    df["event_type"] = [classify_linux(c, msg) for c, msg in zip(df.component, df.message)]
    # the service behind a PAM line, e.g. "sshd(pam_unix)" -> "sshd"
    df["service"] = df.component.str.replace(r"\(pam_unix\)", "", regex=True)
    df["killed_process"] = df.message.str.extract(r"^Out of Memory: Killed process \d+ \((\S+)\)\.")[0]
    df["remote_host"] = df.message.str.extract(r"rhost=(\S+)")[0]
    df["remote_host"] = df.remote_host.fillna(df.message.str.extract(r"^connection from (\S+)")[0])
    # "session opened for user root by (uid=0)" also contains "user", so match "user=" only
    df["target_user"] = df.message.str.extract(r"\buser=(\S+)")[0]
    df["session_user"] = df.message.str.extract(r"^session (?:opened|closed) for user (\S+)")[0]
    return df, skipped


def classify_apache(message: str) -> str:
    if message.startswith("File does not exist"):
        return "file_not_found"
    if message.startswith("Directory index forbidden"):
        return "directory_forbidden"
    if message.startswith("script not found"):
        return "script_not_found"
    if "workerEnv in error state" in message:
        return "jk_error_state"
    if message.startswith("jk2_init()") or message.startswith("mod_jk child init"):
        return "jk_child_init"
    if message.startswith("workerEnv.init() ok"):
        return "jk_worker_ok"
    if "Shutting down" in message:
        return "shutdown"
    if "resuming normal operations" in message:
        return "server_start"
    if "still did not exit" in message:
        return "child_sigterm"
    return "other"


def parse_apache(path: Path):
    rows, skipped = [], 0
    for line in path.read_text(errors="replace").splitlines():
        m = APACHE_LINE.match(line)
        if not m:                                  # fragments with no timestamp
            skipped += 1
            continue
        rows.append((m["ts"], m["level"], m["message"].strip()))

    df = pd.DataFrame(rows, columns=["timestamp", "level", "message"])
    df["timestamp"] = pd.to_datetime(df.timestamp, format="%a %b %d %H:%M:%S %Y")
    df["client_ip"] = df.message.str.extract(r"^\[client ([^\]]+)\]")[0]
    df["message"] = df.message.str.replace(r"^\[client [^\]]+\] ", "", regex=True)
    df["event_type"] = df.message.map(classify_apache)
    df["path"] = df.message.str.extract(r"(?:File does not exist|script not found or unable to stat|"
                                        r"Directory index forbidden by rule): (\S+)")[0]
    return df, skipped


def main():
    CLEAN.mkdir(parents=True, exist_ok=True)
    linux, linux_skipped = parse_linux(RAW / "Linux.log")
    apache, apache_skipped = parse_apache(RAW / "Apache.log")

    linux.to_csv(CLEAN / "linux_events.csv", index=False)
    apache.to_csv(CLEAN / "apache_events.csv", index=False)

    report = pd.DataFrame({
        "log": ["Linux.log", "Apache.log"],
        "raw_lines": [len(linux) + linux_skipped, len(apache) + apache_skipped],
        "parsed_rows": [len(linux), len(apache)],
        "skipped_lines": [linux_skipped, apache_skipped],
        "first_event": [linux.timestamp.min(), apache.timestamp.min()],
        "last_event": [linux.timestamp.max(), apache.timestamp.max()],
    })
    report["skipped_pct"] = (report.skipped_lines / report.raw_lines * 100).round(2)
    report.to_csv(CLEAN / "parse_report.csv", index=False)
    print(report.to_string(index=False))


if __name__ == "__main__":
    main()
