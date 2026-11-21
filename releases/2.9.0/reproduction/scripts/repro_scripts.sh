#!/bin/zsh
#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
# usage: repro_scripts.sh <tag> <folder-glob>   (runs tree then baseline per script, one at a time)
S=/private/tmp/claude-501/-Volumes-SSD-PROJETOS-pcb-thermal-lab/4c68d1f4-0ccc-466a-9ac6-5ee052402f79/scratchpad
R=/Volumes/SSD/PROJETOS/pcb-thermal-lab
TO=${TO:-180}; typeset -A e
cd $R; eval "$(pcb-library/scripts/link_env.sh)"
export QT_QPA_PLATFORM=offscreen MPLBACKEND=Agg
mkdir -p $S/slog/tree $S/slog/base
OUT=$S/repro_scripts_$1.tsv; : > $OUT
for sc in $(cd $S/tree; find research -path "research/$2/scripts/*.py" -maxdepth 3 | sort | grep -vE "/(make_figures|make_diagrams|_[a-z_]*)\.py$"); do
  f=${sc#research/}; f=${f%%/*}; n=$(basename $sc .py)
  py=$R/.venv/bin/python; case $f in gerber-*) py=$R/.venv-research/bin/python;; esac
  for v in tree base; do
    D=$S/$v; s=$(date +%s)
    (cd $D; PYTHONPATH=$D nice -n 10 timeout $TO $py $sc > $S/slog/$v/${f}__$n.log 2>&1); echo $? > $S/slog/$v/${f}__$n.rc
    e[$v]=$(( $(date +%s)-s ))
    [[ $v == tree && $(cat $S/slog/tree/${f}__$n.rc) == 124 ]] && { echo 124 > $S/slog/base/${f}__$n.rc; echo "(skipped)" > $S/slog/base/${f}__$n.log; break; }
  done
  echo "$f\t$n\t$(cat $S/slog/tree/${f}__$n.rc)\t$(cat $S/slog/base/${f}__$n.rc)\t${e[tree]}s\t${e[base]}s" >> $OUT
done
echo DONE >> $OUT
