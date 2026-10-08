# Smart Environment Monitor

University personal project (local version): collect temperature, humidity and pressure from a Sense HAT emulator, store measurements in SQLite, and display live readings, trends and threshold alerts through Flask.

This repository contains a cleaned copy of the local source only. The original database, report, video and cloud-account screenshots are intentionally omitted. The separate AWS prototype is not included because its service endpoints and account-specific settings need a further review.

## Run locally

Use Python and a compatible Sense HAT emulator environment. Install `requirements.txt`, run `python "creatdatabase sensor_data.py"`, then start `python work.py` to collect readings and `python app.py` to view the dashboard at `http://127.0.0.1:5000`. `ENV_MONITOR_DB` can override the default local database path for all three scripts.

The collector depends on the emulator and may need adaptation for a different operating system. This is a portfolio project, not a production deployment.
