# Fleet metrics

`snapshot-metrics.py` records GitHub release downloads + 14-day traffic for every fleet CLI.
The GitHub API only exposes *cumulative* download counts and *14-day-rolling* traffic — there is
no history unless you record it, which is what this does.

- `latest.json` — the most recent full snapshot (per-tool downloads by OS/arch/version + traffic/referrers).
- `history.csv` — one row per tool per run; downloads accumulate, so diffing dates gives per-period installs.

Run (needs `gh` authed with push access — traffic endpoints require it):

    python3 scripts/snapshot-metrics.py

Cron weekly on the VPS (Monday 08:00), committing the append:

    0 8 * * 1  cd /path/to/cliwright-showcase && python3 scripts/snapshot-metrics.py && \
               git commit -am "metrics: weekly snapshot" && git push
