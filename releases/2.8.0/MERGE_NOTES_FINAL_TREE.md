# Merge notes, final tree of 2.8.0 (throwaway tmp/merge-final)

Order: development (b4ee3955), then fix/fem-interface-pad-film (6161b822, no conflict), then release/2.8.0-bump (533f8693).

Conflicts, both only "add at the same place" and resolved by keeping both sides (markers removed, the pad entry first):
* docs/decisions-log.md: the pad entry (HEAD) and the release-commit entry (bump).
* docs/versions.md: the two "How each version was tested" lines (pad fix, release commit).
CHANGELOG.md auto-merged: the pad correction text of the FEM entry sits in the [2.8.0] section. Added by hand: the finned_block |fem|1 and |2 +0.29..+0.30 K note in the frozen-numbers sentence of CHANGELOG [2.8.0] and RELEASE_NOTES.md, and a pad line in RELEASE_NOTES "What to know when upgrading".
