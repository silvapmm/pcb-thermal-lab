#!/bin/zsh
#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
# Run the scripts of a subset list (select_scripts.py output: folder, script, class) one at a time: tree, then the v2.8.0 package,
# then (class T only) the tree with the old-stepping shim. A timeout on the tree skips the other runs (not reproduced).
# usage: run_subset.sh <scratch> <worktree> <subset.tsv> <out.tsv> [class ...]   (scratch holds tree/ and base/ copies and slog/)
S=$1; W=$2; LIST=$3; OUT=$4; shift 4
R=/Volumes/SSD/PROJETOS/pcb-thermal-lab
cd $R; eval "$(pcb-library/scripts/link_env.sh)"
export QT_QPA_PLATFORM=offscreen MPLBACKEND=Agg OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 VECLIB_MAXIMUM_THREADS=2
mkdir -p $S/slog/tree $S/slog/base $S/slog/shim
touch $OUT   # appended to: a script already in $OUT (or in $SKIP, a list of earlier tsv files) is not redone
SKIP=${SKIP:-$OUT}

# guard: before each script. Pause while swap used > 2500 MB or free+inactive < 8 GB (6 GB + the job peak) or load > 5; HARD STOP of the whole batch (exit 3, a STOPPED line in $OUT) at swap > 3000 MB or load > 8 (CLAUDE.md A10, coordinator decision)
guard() { while true; do
    local sw=$(sysctl -n vm.swapusage | sed 's/.*used = \([0-9]*\).*/\1/'); local ld=$(uptime | sed 's/.*averages: \([0-9]*\).*/\1/')
    local fi=$(vm_stat | awk '/Pages free|Pages inactive/{gsub("\\.","",$3); s+=$3} END{printf "%d", s*16384/1000000}')
    if [ $sw -gt 3000 ] || [ $ld -gt 8 ]; then echo "STOPPED for memory or load before $f $b: swap=${sw}M load=$ld" >> $OUT; exit 3; fi
    if [ $sw -gt 2500 ] || [ $fi -lt 8000 ] || [ $ld -gt 5 ]; then sleep 30; else break; fi
  done; }
# run_capped <seconds> <v> <key> <cmd...>: run with a wall-clock cap and a 6 GB resident-memory cap (exit 124 time, 137 memory)
run_capped() { local cap=$1; shift; "$@" & local p=$!; local t0=$(date +%s); while kill -0 $p 2>/dev/null; do
    local rss=$(ps -o rss= -p $(pgrep -P $p | head -1) 2>/dev/null | tr -d ' '); [ -z "$rss" ] && rss=$(ps -o rss= -p $p | tr -d ' ')
    if [ -n "$rss" ] && [ "$rss" -gt 6000000 ]; then pkill -P $p; kill $p; wait $p 2>/dev/null; return 137; fi
    if [ $(( $(date +%s)-t0 )) -gt $cap ]; then pkill -P $p; kill $p; wait $p 2>/dev/null; return 124; fi; sleep 2; done; wait $p; }
while IFS=$'\t' read -r f n c; do
  if [[ $# -gt 0 && " $* " != *" $c "* ]]; then continue; fi
  b=${n%.py}; sc=research/$f/scripts/$n
  grep -qF "$f$(printf '\t')$b$(printf '\t')" $SKIP 2>/dev/null && continue
  guard
  py=$R/.venv/bin/python; case $f in gerber-*) py=$R/.venv-research/bin/python;; esac
  TO=300; [[ $c == T || $c == F ]] && TO=600
  s0=$(date +%s)
  for v in tree base shim; do
    [[ $v == shim && $c != T ]] && continue
    D=$S/tree; PP=$S/tree; [[ $v == base ]] && { D=$S/base; PP=$S/base; }
    [[ $v == shim ]] && PP=$W/releases/2.9.0/reproduction/scripts/old_stepping:$S/tree
    (cd $D; PYTHONPATH=$PP run_capped $TO nice -n 10 $py $sc > $S/slog/$v/${f}__$b.log 2>&1); echo $? > $S/slog/$v/${f}__$b.rc
    if [[ $v == tree && $(cat $S/slog/tree/${f}__$b.rc) == 124 || $(cat $S/slog/tree/${f}__$b.rc) == 137 ]]; then
      cp $S/slog/tree/${f}__$b.rc $S/slog/base/${f}__$b.rc; echo "(skipped)" > $S/slog/base/${f}__$b.log; break
    fi
  done
  echo "$f\t$b\t$c\t$(cat $S/slog/tree/${f}__$b.rc)\t$(cat $S/slog/base/${f}__$b.rc)\t$(( $(date +%s)-s0 ))s" >> $OUT
done < $LIST
echo DONE >> $OUT
