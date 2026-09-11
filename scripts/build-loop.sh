#!/bin/bash
# Build the house loop (loop.mp4) from a list of source clips.
#
#   ./build-loop.sh out.mp4 "clip one.mp4" "clip two.mov" ...
#
# Run on the LOCAL machine — the VPS has 3 cores and no headroom for this.
#
# WHY the encode settings are not negotiable: start_loop.sh publishes loop.mp4 to
# Owncast with `-c copy`, so this file's specs ARE what the venue transmits.
# Off-spec clips do not get fixed downstream — they break the stream mid-play.
# Match the deployed loop: 1920x1080, 24fps, h264 ~1.25 Mbps, AAC 192k 48kHz stereo.
# Raising the bitrate raises egress for every concurrent viewer (150 x bitrate),
# which is the number the capacity tests were sized against — don't, casually.
#
# Sources are re-encoded rather than remuxed for two reasons: phone/camera exports
# carry data streams that break the concat demuxer, and the concat can only be a
# stream copy if every part shares identical encoder parameters.
#
# Square and vertical clips get a blurred-fill pillarbox. The blur is computed at
# 480x270 and scaled up — visually identical to a full-size gaussian, far cheaper.
#
# --for-resolve prepares clips for EDITING instead of building the loop. The free
# DaVinci Resolve on Linux ships no H.264/AAC licence and cannot read Matroska at
# all, so OBS captures are rejected twice over; DNxHR + PCM in a .mov is what it
# ingests happily:
#     ./build-loop.sh --for-resolve edit/ "clip one.mkv" ...
# Edit those, export from Resolve, then run the export back through the normal path
# above so the result still hits the transmit spec.
#
# The defaults are deliberately cheap. Everything here ends up 24fps at 1.25 Mbps,
# so an edit-grade 60fps intermediate is quality nothing downstream can carry: an
# 8-minute 1080p60 capture is 29 GB at DNXQ=hq and 1.3 GB at these defaults. Raise
# DNXQ to sq or hq only when the clip is going somewhere other than the stream.
#   DNXFPS=24  output frame rate   (source rate: DNXFPS=0)
#   DNXQ=lb    lb | sq | hq        (8-bit 422 profiles only)
#
# --for-web turns a finished Resolve export into the pitch-deck clip. Resolve on
# Linux cannot encode H.264 (same missing licence that blocks H.264/AAC import), so
# it exports ProRes/DNxHR and this does the web encode:
#     ./build-loop.sh --for-web pitch-clip.mp4 "Timeline 1.mov"
# yuv420p and +faststart are not optional: browsers cannot decode the 4:2:2 an NLE
# exports, and without faststart the video will not start until it has fully
# downloaded. Audio is dropped because the deck plays the clip muted. The clip loops,
# so it gets fades at both ends to hide the seam.
#   WEBCRF=26      ~760 kbps at 720p, matching the deployed clip (23 ~= 1.3 Mbps)
#   WEBSIZE=1280:720
#   FADEIN=0.4  FADEOUT=0.6      (set either to 0 to skip)
#
# Deploy (see also [[vspot-stream-scripts]]):
#   scp out.mp4 root@432bleu.com:/home/vspot/loop-new.mp4
#   ssh root@432bleu.com 'cp -a /home/vspot/loop.mp4 /home/vspot/loop-<date>.bak.mp4 \
#     && mv /home/vspot/loop-new.mp4 /home/vspot/loop.mp4 \
#     && chown vspot:vspot /home/vspot/loop.mp4 \
#     && sudo -u vspot -H bash -lc "/home/vspot/start_loop.sh --force"'
# Restarting drops the stream for ~15s, so do it when no show is running.
set -eu

# Sources come off phones and OBS as variable frame rate, which NLEs cut badly, so
# the intermediates are forced to CFR. This ffmpeg is 4.4 — -fps_mode does not exist
# here yet, -vsync is the spelling that works.
if [ "${1:-}" = "--for-resolve" ]; then
    shift
    DEST="${1:?usage: build-loop.sh --for-resolve <outdir> <clip> [clip ...]}"
    shift
    [ "$#" -gt 0 ] || { echo "no source clips given" >&2; exit 1; }
    # Only the 8-bit 422 profiles: hqx and 444 need a 10-bit pix_fmt instead.
    case "${DNXQ:=lb}" in hq|sq|lb) ;; *) echo "DNXQ must be hq, sq or lb" >&2; exit 1 ;; esac
    : "${DNXFPS:=24}"
    # DNxHR takes any resolution but insists both axes be even.
    vf='scale=trunc(iw/2)*2:trunc(ih/2)*2'
    [ "$DNXFPS" = "0" ] || vf="$vf,fps=$DNXFPS"
    mkdir -p "$DEST"
    i=0
    for src in "$@"; do
        i=$((i + 1))
        out="$DEST/$(basename "${src%.*}").mov"
        echo "[$i/$#] $(basename "$src") -> $(basename "$out")  (dnxhr_$DNXQ ${DNXFPS}fps)"
        ffmpeg -nostdin -y -v warning -nostats -i "$src" \
            -vf "$vf" -vsync cfr \
            -c:v dnxhd -profile:v "dnxhr_$DNXQ" -pix_fmt yuv422p \
            -c:a pcm_s16le -ar 48000 -ac 2 "$out"
        echo "      $(du -h "$out" | cut -f1)"
    done
    echo "done -> $DEST  (edit these, export, then build the loop from the export)"
    exit 0
fi


if [ "${1:-}" = "--for-web" ]; then
    shift
    WOUT="${1:?usage: build-loop.sh --for-web <output.mp4> <clip>}"
    shift
    WSRC="${1:?no source clip given}"
    : "${WEBCRF:=26}" "${WEBSIZE:=1280:720}" "${FADEIN:=0.4}" "${FADEOUT:=0.6}"
    wvf="scale=$WEBSIZE:force_original_aspect_ratio=decrease,pad=$WEBSIZE:(ow-iw)/2:(oh-ih)/2,setsar=1"
    # fade-out is placed from the end, so the real duration has to be measured first.
    wdur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$WSRC")
    [ "$FADEIN" = "0" ] || wvf="$wvf,fade=t=in:st=0:d=$FADEIN"
    [ "$FADEOUT" = "0" ] || wvf="$wvf,fade=t=out:st=$(echo "$wdur - $FADEOUT" | bc -l):d=$FADEOUT"
    echo "$(basename "$WSRC") -> $(basename "$WOUT")  (${WEBSIZE/:/x} crf$WEBCRF, ${wdur}s)"
    # Resolve stamps a timecode tag (01:00:00:00) on the video stream itself, and the
    # mp4 muxer turns that tag into a brand-new tmcd data track — so mapping only the
    # video stream is not enough; -write_tmcd 0 is what stops it. A stray data track
    # with no valid pts is the sort of thing Safari refuses to play.
    ffmpeg -nostdin -y -v warning -nostats -i "$WSRC" -map 0:v:0 -an -write_tmcd 0 \
        -vf "$wvf" \
        -c:v libx264 -profile:v high -level 4.0 -pix_fmt yuv420p \
        -crf "$WEBCRF" -preset slow -g 48 -movflags +faststart "$WOUT"
    # A clip that autoplays on a slide in front of investors is worth checking twice.
    ffmpeg -nostdin -v error -i "$WOUT" -f null - || { echo "DECODE ERRORS" >&2; exit 1; }
    python3 - "$WOUT" <<'PY'
import sys
d = open(sys.argv[1], 'rb').read(300000)
m, x = d.find(b'moov'), d.find(b'mdat')
print("  faststart: %s" % ("ok" if 0 <= m < x else "MISSING - will not stream"))
PY
    ffprobe -v error -show_entries stream=codec_name,profile,width,height,r_frame_rate,pix_fmt \
        -show_entries format=duration,size,bit_rate -of default=noprint_wrappers=1 "$WOUT"
    exit 0
fi

OUT="${1:?usage: build-loop.sh <output.mp4> <clip> [clip ...]}"
shift
[ "$#" -gt 0 ] || { echo "no source clips given" >&2; exit 1; }

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

VF='[0:v]scale=480:270:force_original_aspect_ratio=increase,crop=480:270,gblur=sigma=8,scale=1920:1080[bg];[0:v]scale=1920:1080:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,fps=24[v]'

i=0
: > "$WORK/concat.txt"
for src in "$@"; do
    i=$((i + 1))
    part=$(printf '%s/%03d.mp4' "$WORK" "$i")
    echo "[$i/$#] $(basename "$src")"
    ffmpeg -nostdin -y -v warning -nostats -i "$src" \
        -filter_complex "$VF" -map '[v]' -map 0:a:0 \
        -c:v libx264 -preset slow -profile:v high -level 4.0 -pix_fmt yuv420p \
        -b:v 1250k -maxrate 1400k -bufsize 2500k -g 48 -keyint_min 48 -sc_threshold 0 \
        -c:a aac -b:a 192k -ar 48000 -ac 2 \
        -movflags +faststart "$part"
    echo "file '$part'" >> "$WORK/concat.txt"
done

echo "concatenating -> $OUT"
ffmpeg -nostdin -y -v warning -nostats -f concat -safe 0 -i "$WORK/concat.txt" \
    -c copy -movflags +faststart "$OUT"

# A file that will loop forever on the public stream is worth decoding once.
echo "verifying"
ffmpeg -nostdin -v error -i "$OUT" -f null - || { echo "DECODE ERRORS — do not deploy" >&2; exit 1; }
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate \
    -show_entries format=duration,size,bit_rate -of default=noprint_wrappers=1 "$OUT"
