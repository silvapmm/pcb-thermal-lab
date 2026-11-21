#!/bin/zsh
cd /Volumes/SSD/PROJETOS/pcb-thermal-lab
eval "$(pcb-library/scripts/link_env.sh)"
export QT_QPA_PLATFORM=offscreen
S=/private/tmp/claude-501/-Volumes-SSD-PROJETOS-pcb-thermal-lab/4c68d1f4-0ccc-466a-9ac6-5ee052402f79/scratchpad
T=$S/tree
cd $T
OUT=$S/repro_tests_results.tsv; : > $OUT
for d in research/*/tests research/theory/tests; do
  f=${d%/tests}; f=${f#research/}
  py=/Volumes/SSD/PROJETOS/pcb-thermal-lab/.venv/bin/python
  case $f in gerber-*) py=/Volumes/SSD/PROJETOS/pcb-thermal-lab/.venv-research/bin/python;; esac
  s=$(date +%s)
  PYTHONPATH=$T timeout 1500 $py -m pytest -q -rs -p no:cacheprovider --timeout=900 --timeout-method=thread $d > $S/repro_t_$f.log 2>&1
  rc=$?
  echo "$f\t$rc\t$(( $(date +%s)-s ))s\t$(tail -1 $S/repro_t_$f.log)" >> $OUT
done
for t in tests/test_docs.py tests/test_license_header.py; do
  s=$(date +%s); PYTHONPATH=$T timeout 900 /Volumes/SSD/PROJETOS/pcb-thermal-lab/.venv/bin/python -m pytest -q -p no:cacheprovider $t > $S/repro_t_$(basename $t).log 2>&1; rc=$?
  echo "$t\t$rc\t$(( $(date +%s)-s ))s\t$(tail -1 $S/repro_t_$(basename $t).log)" >> $OUT
done
echo DONE >> $OUT
