from io import BytesIO

from choroq.egame.moddingui.entries.game_entry import GameEntry
from choroq_extractor import process_file


class HG2CarEntry(GameEntry):

    def get_type_string(self) -> str:
        return "Car"

    def descriptor(self) -> str:
        return ("Contains different parts for each car body, Q00.bin -> Q01 in game"
                "Contents:\n"
                "[body, front/back-lights, brake-lights]\n"
                "[lp-body, lp-lights]\n"
                "[spoiler]\n"
                "[spoiler 2]\n"
                "[jets]\n"
                "[stickers]\n"
                "[texture]\n")

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
            process_file(in_file, self.basename, destination, ["obj+colour"], 2, True)
            return True
        except Exception as e:
            print(e)
        return False
