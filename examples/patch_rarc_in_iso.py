import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from wiithon.WiiIsoPatcher import WiiIsoPatcher
from wiithon.file_helper.transforms import auto_yaz0_transform, rarc_transform
from wiithon.file_helper.rarc import Rarc

SRC_ISO = "../assets/smg.iso"
DST_ISO = "../assets/dzdq.iso"
ARC_PATH = "StageData/AstroDome/AstroDomeScenario.arc"


def patch_scenario(rarc: Rarc) -> None:
    print("Files in RARC :")
    for entry in rarc.entries:
        if entry.file_id != 0xFFFF and entry.type != 0x02:
            print(f"  {entry.name}  ({len(entry.data)} bytes)")

    original = rarc.get_file("scenariodata.bcsv")
    print(f"\nOriginal size of scenariodata.bcsv : {len(original)} bytes")

    patched = b'bonjour'  # need to be replaced by a real bcsv byte thing stuff
    rarc.replace_file("scenariodata.bcsv", patched)


def main():
    with WiiIsoPatcher(SRC_ISO) as patcher:
        print(f"Jeu : {patcher.get_infos()['title']}")
        print(f"ID  : {patcher.get_infos()['game_id']}\n")

        patcher.transform_file(
            ARC_PATH,
            auto_yaz0_transform(rarc_transform(patch_scenario))
        )

        print(f"\nConstruct of {DST_ISO}...")
        patcher.build(DST_ISO, progress_cb=lambda p: print(f"\r  {p}%", end=""))
        print("\nDone.")


if __name__ == "__main__":
    main()
