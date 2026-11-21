#!/bin/zsh
#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
# Run the scripts of a subset list (select_scripts.py output: folder, script, class) one at a time: tree, then the v2.8.0 package,
# then (class T only) the tree with the old-stepping shim. A timeout on the tree skips the other runs (not reproduced).
# usage: run_subset.sh <scratch> <worktree> <subset.tsv> <out.tsv> [class ...]   (scratch holds tree/ and base/ copies and slog/)
S=$1; W=$2; LIST=$3; OUT=$4; shift 4
R=/Volumes/SSD/PROJETOS/pcb-thermal-lab
cd $R; eval "$(pcb-library/scripts/link_env.sh)"
export QT_QPA_PLATFORM=offscreen MPLBACKEND=Agg OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 VECLIB_MAXIMUM_THREADS=2 MKL_NUM_THREADS=2 NUMEXPR_NUM_THREADS=2
mkdir -p $S/slog/tree $S/slog/base $S/slog/shim
touch $OUT   # appended to: a script already in $OUT (or in $SKIP, a list of earlier tsv files) is not redone
SKIP=${SKIP:-$OUT}

# peak_mb: the expected peak of the study in MB, from a "peak RSS x GB" line of an earlier log of it, else 1.5 GB
peak_mb() { local v; v=$(grep -ho 'peak RSS [0-9.]*' $S/slog/tree/${f}__$b.log $S/slog_first_pass/tree/${f}__$b.log 2>/dev/null | awk '{print $3}' | sort -n | tail -1); [ -z "$v" ] && v=1.5; echo $v | awk '{printf "%d", $1*1000}'; }
# guard: before each script. Wait while swap used > 2500 MB, free+inactive+speculative (speculative pages are free pages that vm_stat lists apart) < 6 GB + the expected peak of the study, or the 1-minute load > 8 (the load counts other sessions);
# hard stop of the batch (exit 3, a STOPPED line in $OUT) at swap > 3000 MB; after 30 minutes of waiting it returns 1 (the caller defers the study to the end of the batch)
guard() { local w0=$(date +%s); local pk=$(peak_mb); while true; do
    local sw=$(sysctl -n vm.swapusage | sed 's/.*used = \([0-9]*\).*/\1/'); local ld=$(uptime | sed 's/.*averages: \([0-9]*\).*/\1/')
    local fi=$(vm_stat | awk '/Pages free|Pages inactive|Pages speculative/{gsub("\\.","",$3); s+=$3} END{printf "%d", s*16384/1000000}')
    if [ $sw -gt 3000 ]; then echo "STOPPED for memory before $f $b: swap=${sw}M" >> $OUT; exit 3; fi
    if [ $sw -gt 2500 ] || [ $fi -lt $((6000+pk)) ] || [ $ld -gt 8 ]; then
      if [ $(( $(date +%s)-w0 )) -gt 1800 ]; then return 1; fi
      sleep 30; else return 0; fi
  done; }
# tree_rss <pid>: resident memory in KB of a process and all its descendants (a study that forks workers, multiprocessing, is counted whole)
tree_rss() { local tot=0 r p; for p in $1 $(pgrep -P $1) $(for c in $(pgrep -P $1); do pgrep -P $c; done); do r=$(ps -o rss= -p $p 2>/dev/null | tr -d ' '); tot=$((tot + ${r:-0})); done; echo $tot; }
# run_capped <seconds> <cmd...>: wall-clock cap (exit 124), 4 GB cap on the whole process tree (exit 137), and the hard stop of the batch while it runs (swap > 3000 MB: kill, exit 138); load never kills a script
run_capped() { local cap=$1; shift; "$@" & local p=$!; local t0=$(date +%s); while kill -0 $p 2>/dev/null; do
    local rss=$(tree_rss $p); local sw=$(sysctl -n vm.swapusage | sed 's/.*used = \([0-9]*\).*/\1/'); local ld=$(uptime | sed 's/.*averages: \([0-9]*\).*/\1/')
    local code=0; [ $rss -gt 4000000 ] && code=137; [ $sw -gt 3000 ] && code=138; [ $(( $(date +%s)-t0 )) -gt $cap ] && code=124
    if [ $code -ne 0 ]; then pkill -P $p; for c in $(pgrep -P $p); do pkill -P $c; done; kill $p; wait $p 2>/dev/null; return $code; fi; sleep 2; done; wait $p; }

# process <f> <n> <c>: run one script (tree, v2.8.0, shim for class T) and append its line to $OUT; returns 1 if the guard gave up waiting (nothing run)
process() {
  local f=$1 n=$2 c=$3 b=${2%.py}
  local sc=research/$f/scripts/$n
  guard || return 1
  local py=$R/.venv/bin/python; case $f in gerber-*) py=$R/.venv-research/bin/python;; esac
  local TO=300; [[ $c == T || $c == F ]] && TO=600
  local s0=$(date +%s) v
  for v in tree base shim; do
    [[ $v == shim && $c != T ]] && continue
    D=$S/tree; PP=$S/tree; [[ $v == base ]] && { D=$S/base; PP=$S/base; }
    [[ $v == shim ]] && PP=$W/releases/2.9.0/reproduction/scripts/old_stepping:$S/tree
    (cd $D; PYTHONPATH=$PP run_capped $TO nice -n 10 $py $sc > $S/slog/$v/${f}__$b.log 2>&1); echo $? > $S/slog/$v/${f}__$b.rc
    if [[ $v == tree && ( $(cat $S/slog/tree/${f}__$b.rc) == 124 || $(cat $S/slog/tree/${f}__$b.rc) == 138 || $(cat $S/slog/tree/${f}__$b.rc) == 137 ) ]]; then
      cp $S/slog/tree/${f}__$b.rc $S/slog/base/${f}__$b.rc; echo "(skipped)" > $S/slog/base/${f}__$b.log; break
    fi
  done
  if [[ $(cat $S/slog/tree/${f}__$b.rc) == 138 ]]; then echo "STOPPED for memory during $f $b" >> $OUT; exit 3; fi
  echo "$f\t$b\t$c\t$(cat $S/slog/tree/${f}__$b.rc)\t$(cat $S/slog/base/${f}__$b.rc)\t$(( $(date +%s)-s0 ))s" >> $OUT
}
deferred=()
while IFS=$'\t' read -r f n c; do
  if [[ $# -gt 0 && " $* " != *" $c "* ]]; then continue; fi
  grep -qF "$f$(printf '\t')${n%.py}$(printf '\t')" $SKIP 2>/dev/null && continue
  process $f $n $c || { deferred+=("$f $n $c"); echo "deferred (waited 30 min for memory) $f $n" >> $OUT.deferred; }
done < $LIST
# the deferred studies get one more pass at the end; one that still waits 30 minutes is recorded as not run
for d in $deferred; do :; done
for d in "${deferred[@]}"; do
  set -- ${=d}
  process $1 $2 $3 || echo "NOT RUN (waited twice 30 min for memory): $1 ${2%.py} $3" >> $OUT
done
echo DONE >> $OUT
