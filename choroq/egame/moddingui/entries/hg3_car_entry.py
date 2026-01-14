from io import BytesIO

from choroq.egame.moddingui.entries.game_entry import GameEntry
from choroq_extractor import process_file


class HG3CarEntry(GameEntry):

    def get_type_string(self) -> str:
        return "Car"

    def descriptor(self) -> str:
        return ("Contains different parts for each car body, Q00.bin -> Q01 in game"
                "Contents:\n"
                "[Body, something, brake-lights, front/back-lights, front/back-lights-black]\n"
                "[lp-body, null, null, lp-front/back-lights, lp-front/back-lights-black]\n"
                "[Spoiler 1]\n"
                "[F1 setup/Spoiler]\n"
                "[Boat cover]\n"
                "[Hovercraft cover]\n"
                "[Stickers]\n")

    def convert_name(self) -> str:
        q_number = int(self.basename[1:])
        q_number += 1
        q_number = str(q_number).zfill(2)
        q_file = "Q" + q_number
        return q_file

    def get_editable(self) -> bool:
        return True

    def get_extractable(self) -> bool:
        return True

    def extract(self, iso, options, destination) -> bool:
        try:
            # Get the fp, and read all the bytes of the file into memory
            in_file = BytesIO()
            iso.get_file_from_iso_fp(in_file, iso_path=self.path)
            in_file.seek(0)  # reset stream, to mimic a file
            process_file(in_file, self.basename, destination, ["obj+colour"], 3, True)
            return True
        except Exception as e:
            print(e)
        return False
