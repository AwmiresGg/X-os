#!/usr/bin/env python3
"""Run Calamares' real fstab job code (from the image) with X-OS's fstab.conf, as if the root
disk were an SSD (a path the VM's virtual disk never takes), and print the generated fstab.

    python3 testing/installer/fstab_ssd_check.py \\
        build/work/desktop/chroot/usr/lib/x86_64-linux-gnu/calamares/modules/fstab/main.py \\
        installer/calamares/modules/fstab.conf
Exit status 0 = fstab written; 1 = the job raised (what users saw as "Bad main script file")."""
import importlib.util
import os
import sys
import tempfile
import traceback
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent / "calamares-stub"))
spec = importlib.util.spec_from_file_location("fstab_main", sys.argv[1])
F = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F)
F.is_ssd_disk = lambda name: True

conf = yaml.safe_load(Path(sys.argv[2]).read_text())
root = tempfile.mkdtemp()
os.makedirs(root + "/etc")
parts = [dict(device="/dev/nvme0n1p1", fs="fat32", mountPoint="/boot/efi", uuid="AAAA-BBBB", claimed=True),
         dict(device="/dev/nvme0n1p2", fs="ext4", mountPoint="/", uuid="1111-2222", claimed=True)]
opts = [dict(mountpoint="/", option_string="defaults,noatime"),
        dict(mountpoint="/boot/efi", option_string="defaults,umask=0077")]
gen = F.FstabGenerator(parts, root, opts, conf.get("crypttabOptions", "luks"), conf.get("tmpOptions", {}))
try:
    gen.run()
except Exception:
    traceback.print_exc()
    sys.exit(1)
print(Path(root, "etc/fstab").read_text())
