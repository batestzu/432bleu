# studio/: show-day tools for Zoltan (the broadcast machine)

These run on the studio machine, not the VPS. See `scripts/vps/` for the venue side.

| Folder | What | Use |
|---|---|---|
| `iphone-cam/` | MediaMTX receiver for the iPhone cameras (Blackmagic Camera app), port 1936. Includes the phone server profiles (`*.xml`). | After any reboot: log in, then `docker compose up -d --force-recreate` here. A plain `up -d` after the boot failure leaves it running with no logs. Then restart the stream on each phone: the app does not reconnect by itself after the receiver restarts. |
| `iphone-cam/cam-bitrate.sh` | Measures what each phone really sends: Mbit/s, resolution and fps. | `./cam-bitrate.sh 30` with both phones streaming. |
| `obs/cam-switch.lua` | Auto-switches between the two iPhone scenes and cuts away from a phone that drops. | OBS → Tools → Scripts. Set it before doors and don't touch it mid-show. |
| `netwatch/` | Pings the router, 1.1.1.1 and the VPS once a second. Its report says which link an outage was in (WiFi, building internet, or the route to the VPS). | Start `netwatch/netwatch.sh` before doors at a venue, and Ctrl-C it after the show. Logs go to `netwatch/logs/` (not in git). |

Zoltan's home directory is encrypted, which is why Docker can't start the receiver at boot.
