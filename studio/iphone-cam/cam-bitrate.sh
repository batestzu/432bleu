#!/bin/bash
# cam-bitrate.sh: what are the phones ACTUALLY sending?
#
# Measures each camera feed arriving at the iphone-cam receiver. It reads the
# receiver's byte counters twice and divides by the time between them, then
# asks ffprobe for the resolution and frame rate. The app's quality setting is
# a target. This is the real number, and the real number is what uses up WiFi.
#
#   ./cam-bitrate.sh        measure over 20 s
#   ./cam-bitrate.sh 60     measure over 60 s (steadier; use during a test set)
#
# The phones must be streaming, and the receiver must be up
# (`docker compose up -d` in this folder).
#
# On WiFi every phone feed crosses the air TWICE (phone -> router -> Zoltan),
# so the airtime it costs is about 2x the number printed here.

API=http://127.0.0.1:9997/v3/paths/list
SECS=${1:-20}

a=$(curl -s --max-time 3 "$API") || { echo "Receiver API not answering. Is iphone-cam up? Run: docker compose up -d (in $(dirname "$0"))"; exit 1; }
t0=$(date +%s.%N)

# Resolution/fps while we wait. ffprobe joins as a brief extra reader, which is harmless.
info=""
for cam in cam1 cam2; do
    line=$(timeout 8 ffprobe -v error -select_streams v:0 \
        -show_entries stream=codec_name,width,height,avg_frame_rate \
        -of csv=p=0 "rtmp://127.0.0.1:1936/live/$cam" 2>/dev/null | head -1)
    info+="$cam=$line;"
done

now=$(date +%s.%N)
left=$(python3 -c "print(max(0.0, $SECS - ($now - $t0)))")
sleep "$left"
b=$(curl -s --max-time 3 "$API")
t1=$(date +%s.%N)

python3 - "$t0" "$t1" "$a" "$b" "$info" <<'EOF'
import json, sys
t0, t1 = float(sys.argv[1]), float(sys.argv[2])
a, b = json.loads(sys.argv[3]), json.loads(sys.argv[4])
info = dict(kv.split("=", 1) for kv in sys.argv[5].split(";") if "=" in kv)

def counter(item):
    # MediaMTX renamed bytesReceived -> inboundBytes in later versions.
    for k in ("inboundBytes", "bytesReceived"):
        if k in item:
            return item[k]
    return None

before = {i["name"]: counter(i) for i in a.get("items", [])}
items = [i for i in b.get("items", []) if i.get("ready")]
if not items:
    print("No phone is streaming right now. Start cam1/cam2 in the Blackmagic app, then run this again.")
    sys.exit(0)

dt = t1 - t0
total = 0.0
print("Measured over %.0f s:" % dt)
for i in sorted(items, key=lambda x: x["name"]):
    name = i["name"]
    n0, n1 = before.get(name), counter(i)
    if n0 is None or n1 is None:
        print("  %-10s connected during the measurement, run again" % name)
        continue
    mbps = (n1 - n0) * 8 / dt / 1e6
    total += mbps
    cam = name.split("/")[-1]
    fmt = info.get(cam, "")
    if fmt:
        codec, w, h, fps = (fmt.split(",") + ["", "", "", ""])[:4]
        try:
            num, den = fps.split("/")
            fps = "%.0f fps" % (float(num) / float(den))
        except Exception:
            pass
        fmt = "%s %sx%s %s" % (codec, w, h, fps)
    print("  %-10s %6.1f Mbit/s   %s" % (name, mbps, fmt))
print("  %-10s %6.1f Mbit/s   (about %.0f Mbit/s of WiFi airtime, since each feed crosses the air twice)" % ("total", total, 2 * total))
print("For comparison, OBS sends the show to the VPS at about 4.2 Mbit/s.")
EOF
