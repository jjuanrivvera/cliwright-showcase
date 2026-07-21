#!/usr/bin/env python3
"""Snapshot fleet download + traffic metrics into metrics/latest.json and append a dated row per
tool to metrics/history.csv, so trends accumulate (the GitHub API only exposes CUMULATIVE download
counts and 14-day-rolling traffic — there is no history unless you record it).

Cron-friendly. Usage:  python3 scripts/snapshot-metrics.py [--date YYYY-MM-DD]
Needs `gh` authenticated with push access to the repos (traffic endpoints require it).
"""
import subprocess, json, csv, os, re, argparse, datetime, collections, sys

ORG = "jjuanrivvera"
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MET = os.path.join(HERE, "metrics")


def load_tools():
    """repo -> binary, read from registry/*.yaml so the snapshot always covers exactly the
    showcased fleet. Adding a CLI to the registry is enough — there is no hand-maintained list
    to drift out of sync (which is how ms365/remoteok/torre were being missed)."""
    import glob

    import yaml

    tools = {}
    for path in sorted(glob.glob(os.path.join(HERE, "registry", "*.yaml"))):
        d = yaml.safe_load(open(path))
        repo = d["repo"].rstrip("/").split("/")[-1]
        tools[repo] = d["binary"]
    return tools


# repo -> binary
TOOLS = load_tools()


def gh(path, paginate=False):
    # Only paginate true arrays (releases). --paginate on the dict-shaped traffic endpoints
    # corrupts the payload, so those must be fetched without it.
    cmd = ["gh", "api"] + (["--paginate"] if paginate else []) + [path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return None
    out = r.stdout.strip()
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        merged = []
        for line in re.findall(r'\[.*?\]|\{.*\}', out, re.S):
            try:
                v = json.loads(line)
                merged.extend(v) if isinstance(v, list) else merged.append(v)
            except json.JSONDecodeError:
                pass
        return merged or None


def classify(name):
    n = name.lower()
    if n.endswith(".sbom.json") or "spdx" in n: t = "sbom"
    elif n == "checksums.txt": t = "checksum"
    elif n.endswith(".sig") or n.endswith(".pem"): t = "signature"
    elif n == "install.sh": t = "install.sh"
    elif n.endswith(".deb"): t = "deb"
    elif n.endswith(".rpm"): t = "rpm"
    elif n.endswith(".apk"): t = "apk"
    elif n.endswith((".tar.gz", ".zip", ".exe")) or re.search(r"-(darwin|linux|windows)-", n): t = "archive"
    else: t = "other"
    if "darwin" in n or "macos" in n: o = "macOS"
    elif "windows" in n: o = "Windows"
    elif "linux" in n or t in ("deb", "rpm", "apk"): o = "Linux"
    else: o = None
    if "arm64" in n or "aarch64" in n: a = "arm64"
    elif "amd64" in n or "x86_64" in n: a = "amd64"
    elif re.search(r"_(386|i386)", n): a = "386"
    else: a = None
    return t, o, a


def collect(repo):
    rel = gh(f"repos/{ORG}/{repo}/releases", paginate=True) or []
    by_os, by_arch, by_type = collections.Counter(), collections.Counter(), collections.Counter()
    dl_total = dl_install = 0
    versions = []
    for r in rel:
        tag, date = r.get("tag_name", "?"), (r.get("published_at") or "")[:10]
        v_install = 0
        for a in r.get("assets", []):
            dc = a.get("download_count", 0)
            t, o, ar = classify(a["name"])
            dl_total += dc
            by_type[t] += dc
            if t in ("archive", "deb", "rpm", "apk"):
                dl_install += dc
                v_install += dc
                if o: by_os[o] += dc
                if ar: by_arch[ar] += dc
        versions.append({"tag": tag, "date": date, "downloads": v_install})
    # traffic (needs push access; default to zeros if unavailable)
    views = gh(f"repos/{ORG}/{repo}/traffic/views") or {}
    clones = gh(f"repos/{ORG}/{repo}/traffic/clones") or {}
    referrers = gh(f"repos/{ORG}/{repo}/traffic/popular/referrers") or []
    paths = gh(f"repos/{ORG}/{repo}/traffic/popular/paths") or []
    meta = gh(f"repos/{ORG}/{repo}") or {}
    return {
        "name": repo, "binary": TOOLS[repo],
        "stars": meta.get("stargazers_count", 0), "forks": meta.get("forks_count", 0),
        "created_at": (meta.get("created_at") or "")[:10],
        "downloads_total": dl_total, "downloads_install": dl_install,
        "by_os": dict(by_os), "by_arch": dict(by_arch), "by_type": dict(by_type),
        "versions": sorted(versions, key=lambda v: v["date"]),
        "traffic": {
            "views_count": views.get("count", 0), "views_uniques": views.get("uniques", 0),
            "clones_count": clones.get("count", 0), "clones_uniques": clones.get("uniques", 0),
            "referrers": [{"referrer": x["referrer"], "count": x["count"], "uniques": x["uniques"]} for x in referrers[:6]],
            "paths": [{"path": x["path"], "count": x["count"], "uniques": x["uniques"]} for x in paths[:5]],
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    args = ap.parse_args()
    os.makedirs(MET, exist_ok=True)

    tools = [collect(r) for r in TOOLS]
    data = {"snapshot_date": args.date, "tools": tools}
    with open(os.path.join(MET, "latest.json"), "w") as f:
        json.dump(data, f, indent=2)

    # append per-tool history rows (create header once)
    hist = os.path.join(MET, "history.csv")
    # History tracks the CUMULATIVE, meaningful metrics (downloads accumulate → diff = per-period
    # installs). views_uniques is 14-day-rolling (kept as a rough interest signal); clones are
    # dropped (almost entirely CI/mirror/crawler noise).
    cols = ["date", "tool", "dl_total", "dl_install", "macOS", "Linux", "Windows",
            "amd64", "arm64", "archives", "linux_pkgs", "views_uniques_14d", "stars"]
    new = not os.path.exists(hist)
    with open(hist, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(cols)
        for t in tools:
            bt, bo, ba = t["by_type"], t["by_os"], t["by_arch"]
            w.writerow([args.date, t["binary"], t["downloads_total"], t["downloads_install"],
                        bo.get("macOS", 0), bo.get("Linux", 0), bo.get("Windows", 0),
                        ba.get("amd64", 0), ba.get("arm64", 0),
                        bt.get("archive", 0), bt.get("deb", 0) + bt.get("rpm", 0) + bt.get("apk", 0),
                        t["traffic"]["views_uniques"], t["stars"]])
    print(f"✓ wrote metrics/latest.json + appended {len(tools)} rows to metrics/history.csv ({args.date})")
    return data


if __name__ == "__main__":
    main()
