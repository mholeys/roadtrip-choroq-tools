from pycdlib.dr import DirectoryRecord

from choroq.bhe.aptexture import APTexture
from choroq.bhe.moddingui.common import GameVersion
from choroq.bhe.moddingui.entries.game_entry import GameEntry


class AptEntry(GameEntry):

    def __init__(self, ap_texture : APTexture, folder, path, game_version: GameVersion, game_variant: str, record: DirectoryRecord, subtype: bytes, subfile_index, entry_position):
        super().__init__(folder, path, game_version, game_variant, record)
        self.ap_texture = ap_texture

        self.subtype = subtype
        self.subfile_index = subfile_index
        self.entry_position = entry_position

    def descriptor(self) -> str:
        text = "AP texture\n"
        text += f"Format {self.ap_texture.colour_format}\n"
        text += f"Dimensions (W x H) {self.ap_texture.width}x{self.ap_texture.height}\n"
        text += f"Size (bytes) {self.ap_texture.total_size}\n"

        has_palette = self.ap_texture.palette_size > 0
        text += f"Palette? {has_palette}\n"
        if has_palette:
            text += f"Palette size: {self.ap_texture.palette_size} colours\n"

        return text


    def get_file_name(self) -> str:
        return f"[{self.subfile_index}] {self.ap_texture.name}"

    def get_position(self) -> int:
        return self.ap_texture.offset

    def get_size(self) -> int:
        return self.ap_texture.total_size

    def get_offset(self) -> int:
        return self.ap_texture.offset

    def is_supported(self):
        # Returns true if the code can handle this format properly (no artifacts)
        #return self.ap_texture.colour_format
        return False
