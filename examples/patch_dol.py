import sys

from wiithon.WiiIsoPatcher import WiiIsoPatcher

sys.path.insert(0, "../src")

from wiithon.file_helper.dol import DOL
from wiithon.helpers import PowerPC as ppc

# Patch addresses
PATCH_ADDR_NOP   = 0x80258a0c
PATCH_ADDR_LI    = 0x80258a10
PATCH_ADDR_BL_FROM   = 0x80258a14
PATCH_ADDR_BL_TARGET = 0x80f58a14

CODE_VADDR = 0x806E0000
DATA_VADDR = 0x806F0000
DATA_SIZE  = 0x100

def apply_patches(dol: DOL) -> None:
    """All patches go here. Used for both the standalone DOL and the ISO DOL"""

    # Patch 1: write a nop at PATCH_ADDR_NOP
    dol.write_at(PATCH_ADDR_NOP, ppc.nop())
    print(f"  nop         @ {PATCH_ADDR_NOP:#010x}")

    # Patch 2: force li r3, 1 at PATCH_ADDR_LI
    dol.write_at(PATCH_ADDR_LI, ppc.li(3, 1))
    print(f"  li r3, 1    @ {PATCH_ADDR_LI:#010x}")

    # Patch 3: redirect a bl
    dol.write_at(PATCH_ADDR_BL_FROM, ppc.bl(PATCH_ADDR_BL_TARGET, PATCH_ADDR_BL_FROM))
    print(f"  bl {PATCH_ADDR_BL_TARGET:#010x} @ {PATCH_ADDR_BL_FROM:#010x}")

    dol.add_data_section(DATA_VADDR, b'\x00' * DATA_SIZE)

    hook_addr = 0x802e1860
    original = dol.read_at(hook_addr, 4)

    code = (
            original  # original instruction
            + ppc.li(3, 42)  # some logics
            + ppc.b(hook_addr + 4, CODE_VADDR + 8)  # return
    )
    dol.add_text_section(CODE_VADDR, code)

    # Branch when hooked
    dol.write_at(hook_addr, ppc.b(CODE_VADDR, hook_addr))


# A .dol file
def patch_standalone_dol(src: str, dst: str) -> None:
    print(f"\n--- Patching standalone DOL ---")
    print(f"  Source : {src}")
    print(f"  Output : {dst}")

    with open(src, "rb") as f:
        dol = DOL.read(f)

    apply_patches(dol)

    with open(dst, "wb") as f:
        f.write(dol.to_bytes())

    print("  Done.")


# Directly inside a Wii ISO
def patch_iso_dol(src_iso: str, dst_iso: str) -> None:
    with WiiIsoPatcher(src_iso) as patcher:
        patcher.patch_dol(apply_patches)

        patcher.add_file("file.arc", b"bonjour je suis un fichier")
        patcher.replace_file("LayoutData/AirMeter.arc", b"Bonjour, je suis de l'air meter .arc et voila :)")
        patcher.remove_file("AudioRes/SMR.szs")
        patcher.modify_title("Super Mario Galaxy AP Randomizer")
        patcher.modify_title_id("RMGE69")

        patcher.build(dst_iso)


# This file has been used to test if patching a real dol works (and it is !)
if __name__ == "__main__":
    # patch_standalone_dol("../assets/main.dol", "../assets/main_patched.dol")
    patch_iso_dol("../assets/smg.iso", "../assets/yes.iso")
