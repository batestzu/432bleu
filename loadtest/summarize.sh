#!/usr/bin/env bash
# Summarize the most recent loadtest CSV for a label: peaks + the worst-moment row.
# Usage: bash loadtest/summarize.sh <label>   (e.g. t1)
set -u
LABEL="${1:-t1}"
FILE=$(ls -t "$HOME"/loadtest-"$LABEL"-*.csv 2>/dev/null | head -1)
if [ -z "$FILE" ]; then echo "no CSV found for label '$LABEL' in $HOME"; exit 1; fi
echo "file: $FILE ($(($(wc -l < "$FILE") - 1)) samples)"
awk -F, 'NR>1{
  if($2+0>L){L=$2; peakrow=$0}
  if(A==""||$4+0<A+0)A=$4
  if($5+0>SW)SW=$5
  if($6+0>SI)SI=$6
  if($7+0>SO)SO=$7
  if($8+0>RX)RX=$8
  if($9+0>TX)TX=$9
} END{
  print "peak_load1        = " L
  print "min_mem_avail_mb  = " A
  print "max_swap_used_mb  = " SW
  print "max_swap_in_kb/s  = " SI
  print "max_swap_out_kb/s = " SO
  print "peak_rx_mbps      = " RX
  print "peak_tx_mbps      = " TX
  print ""
  print "row at peak load (ts,load1,mem_used,mem_avail,swap_used,swap_in,swap_out,rx,tx,containers):"
  print peakrow
}' "$FILE"
