from pycdlib.dr import DirectoryRecord

from choroq.bhe.moddingui.common import GameVersion
from choroq.bhe.moddingui.entries.game_entry import GameEntry


class CpkSubfileEntry(GameEntry):

    def __init__(self, folder, path, game_version: GameVersion, game_variant: str, record: DirectoryRecord, subtype: bytes, subfile_index, entry_position):
        super().__init__(folder, path, game_version, game_variant, record)
        self.subtype = subtype
        self.subfile_index = subfile_index
        self.entry_position = entry_position

    def get_type_string(self) -> str:
        if self.subtype == b"TOC\0" or self.subtype == b"\x03\x18\x00\x00":
            return "TOC"
        elif self.subtype == b"APT\0":
            return "Texture"
        elif self.subtype == b"PBL\0":
            return "PBL"
        elif self.subtype == b"MPD\0":
            return "MPD"
        elif self.subtype == b"HPD\0":
            return "HitPoly"
        elif self.subtype == b"FONT":
            return "Font data"
        elif self.subtype == b"LZS\0":
            return "Compressed data"
        return f"Unknown {str(self.subtype)}"

    def descriptor(self) -> str:
        return ""

    def convert_name(self) -> str:
        return "Unknown"

    def get_file_name(self) -> str:
        return f"[{self.subfile_index}] {self.get_type_string()}"

    def get_position_in_parent(self) -> int:
        return self.entry_position

    def get_offset(self) -> int:
        return self.get_sector() * 2048 + self.get_position_in_parent()

    def get_editable(self) -> bool:
        return False

    def get_extractable(self) -> bool:
        return True

    def extract(self, iso, options, destination) -> bool:
        # try:
        #     # Get the fp, and read all the bytes of the file into memory
        #     in_file = BytesIO()
        #     iso.get_file_from_iso_fp(in_file, iso_path=self.path)
        #     in_file.seek(0)  # reset stream, to mimic a file
        #     process_file(in_file, self.basename, destination, ["obj+colour"], 2, True)
        #     return True
        # except Exception as e:
        #     print(e)
        return False

    def has_children(self):
        return self.children is not None and len(self.children) > 0

    def get_children(self):
        return self.children







