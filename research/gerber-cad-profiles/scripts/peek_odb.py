#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file peek_odb.py
@brief Print the identification files of an ODB++ archive (misc/info, matrix header) without extracting it.

Question answered: which fields of an ODB++ job name the generating program?  Reads only the
text members `*/misc/info` and `*/matrix/matrix` (first lines) of a .tgz, in memory.
Run: .venv/bin/python -I peek_odb.py FILE.tgz
"""
import sys
import tarfile


def main(argv):
    """!
    @brief Print the head of the identification members.

    @param argv  Command line with the archive path.

    @return int Exit code.
    """
    with tarfile.open(argv[1]) as tf:
        names = tf.getnames()
        print(len(names), "members; first:", names[:3])
        for n in names:
            if n.endswith("misc/info") or n.endswith("misc/sysattr") or n.endswith("/matrix/matrix"):
                data = tf.extractfile(n).read(1200).decode("latin-1")
                print("--", n)
                print(data[:900])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
