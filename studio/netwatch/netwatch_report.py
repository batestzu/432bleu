#!/usr/bin/env python3
"""Report for a netwatch.sh log: overall numbers per target, then every outage
and which link it was in.

    python3 netwatch_report.py logs/netwatch-....csv

An outage is 3 or more pings in a row with no reply. Each outage on the VPS
path is classified by what the router and internet targets did over the same
seconds:
    router also silent            -> WiFi (Zoltan <-> router)
    internet also silent          -> the building's internet connection
    only the VPS silent           -> the route to the VPS, or a firewall
"""
import csv
import statistics
import sys
import time

TARGETS = ["router", "internet", "vps"]
LABEL = {
    "router": "router (WiFi)",
    "internet": "internet (1.1.1.1)",
    "vps": "vps (stream path)",
}
MIN_RUN = 3          # consecutive misses that count as an outage
SLOW_MS = {"router": 200, "internet": 1000, "vps": 1000}


def hhmmss(t):
    return time.strftime("%H:%M:%S", time.localtime(t))


def load(path):
    """Per target: {seq: (time, rtt or None)}. A late reply beats a miss."""
    data = {t: {} for t in TARGETS}
    downs = {t: [] for t in TARGETS}
    with open(path) as f:
        for row in csv.DictReader(f):
            t = row["target"]
            if t not in data:
                continue
            ts = float(row["epoch"])
            if row["rtt_ms"] == "DOWN" or not row["seq"]:
                downs[t].append(ts)
                continue
            seq = int(row["seq"])
            rtt = None if row["rtt_ms"] == "LOST" else float(row["rtt_ms"])
            old = data[t].get(seq)
            if old is None or (old[1] is None and rtt is not None):
                # A miss is noticed about a second after its ping went out.
                data[t][seq] = (ts - 1.0 if rtt is None else ts - rtt / 1000.0, rtt)
    return data, downs


def runs_of_misses(series):
    """[(start, end, count)] for each run of >= MIN_RUN misses in a row."""
    out, run = [], []
    for seq in sorted(series):
        ts, rtt = series[seq]
        if rtt is None:
            run.append(ts)
        else:
            if len(run) >= MIN_RUN:
                out.append((run[0], run[-1] + 1.0, len(run)))
            run = []
    if len(run) >= MIN_RUN:
        out.append((run[0], run[-1] + 1.0, len(run)))
    return out


def miss_share(series, start, end):
    """Share of this target's pings in [start, end] that got no reply."""
    pts = [rtt for ts, rtt in series.values() if start - 0.5 <= ts <= end + 0.5]
    if not pts:
        return None
    return sum(1 for r in pts if r is None) / len(pts)


def pct(values, p):
    if not values:
        return None
    s = sorted(values)
    return s[min(len(s) - 1, int(round(p / 100.0 * (len(s) - 1))))]


def main(path):
    data, downs = load(path)
    allts = [ts for t in TARGETS for ts, _ in data[t].values()]
    if not allts:
        print("netwatch: the log has no pings in it yet.")
        return
    t0, t1 = min(allts), max(allts)
    print("netwatch report  %s -> %s  (%d min, times are %s)" % (
        hhmmss(t0), hhmmss(t1), round((t1 - t0) / 60), time.strftime("%Z")))
    print("log: %s" % path)
    print()
    print("  %-20s %6s %6s %7s %8s %8s %8s %6s" % (
        "target", "pings", "lost", "lost %", "median", "95%", "worst", "slow"))
    for t in TARGETS:
        rtts = [r for _, r in data[t].values() if r is not None]
        n, lost = len(data[t]), sum(1 for _, r in data[t].values() if r is None)
        slow = sum(1 for r in rtts if r > SLOW_MS[t])
        fmt = lambda v: "--" if v is None else "%.0f ms" % v
        print("  %-20s %6d %6d %6.1f%% %8s %8s %8s %6d" % (
            LABEL[t], n, lost, 100.0 * lost / n if n else 0,
            fmt(statistics.median(rtts) if rtts else None), fmt(pct(rtts, 95)),
            fmt(max(rtts) if rtts else None), slow))
    print("  (slow = replies over %d ms for the router, over %d ms elsewhere)" % (
        SLOW_MS["router"], SLOW_MS["vps"]))
    for t in TARGETS:
        if downs[t]:
            print("  %s: %d 'network unreachable' errors, first at %s" % (
                LABEL[t], len(downs[t]), hhmmss(downs[t][0])))
    print()

    outages = {t: runs_of_misses(data[t]) for t in TARGETS}
    if not any(outages.values()):
        print("No outages: no target ever missed %d pings in a row." % MIN_RUN)
        print("If OBS dropped during this window anyway, suspect a firewall that")
        print("treats the stream differently from pings.")
        return

    print("Outages (%d+ missed pings in a row):" % MIN_RUN)
    verdicts = []
    for start, end, count in outages["vps"]:
        r = miss_share(data["router"], start, end)
        i = miss_share(data["internet"], start, end)
        if r is not None and r >= 0.5:
            where = "WiFi (Zoltan <-> router)"
        elif i is not None and i >= 0.5:
            where = "the building's internet connection"
        else:
            where = "the route to the VPS only (or a firewall)"
        verdicts.append(where)
        print("  %s -> %s  %4ds  stream path down; router missed %s, internet missed %s  =>  %s" % (
            hhmmss(start), hhmmss(end), round(end - start),
            "--" if r is None else "%d%%" % round(100 * r),
            "--" if i is None else "%d%%" % round(100 * i), where))
    for t in ("router", "internet"):
        for start, end, count in outages[t]:
            v = miss_share(data["vps"], start, end)
            if v is not None and v >= 0.5:
                continue        # already listed above as a stream-path outage
            print("  %s -> %s  %4ds  %s down, but the stream path kept answering" % (
                hhmmss(start), hhmmss(end), round(end - start), LABEL[t]))
    if verdicts:
        print()
        top = max(set(verdicts), key=verdicts.count)
        print("Verdict: %d of %d stream-path outages were in %s." % (
            verdicts.count(top), len(verdicts), top))
        if top.startswith("WiFi"):
            print("  -> A wired cable for Zoltan should fix it.")
        elif top.startswith("the building"):
            print("  -> A cable on the same building network may NOT help. A separate uplink (e.g. a cellular hotspot for OBS) would.")
        else:
            print("  -> Talk to venue IT about the route or a firewall, or try a different way to send the stream.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: netwatch_report.py LOG.csv")
    main(sys.argv[1])
