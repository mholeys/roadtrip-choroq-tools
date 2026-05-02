from pycdlib.dr import DirectoryRecord
import pycdlib

from choroq.bhe.aptexture import APTexture
from choroq.bhe.moddingui.common import GameVersion
from choroq.bhe.moddingui.entries.game_entry import GameEntry


class AptEntry(GameEntry):

    def __init__(self, ap_texture: APTexture, folder, path, game_version: GameVersion, game_variant: str, record: DirectoryRecord, subtype: bytes, subfile_index, entry_position):
        super().__init__(folder, path, game_version, game_variant, record)
        self.ap_texture = ap_texture

        self.subtype = subtype
        self.subfile_index = subfile_index
        self.entry_position = entry_position

        self.can_write = True

    def descriptor(self) -> str:
        text = "AP texture\n"
        text += f"Format {self.ap_texture.colour_format}\n"
        text += f"Dimensions (W x H) {self.ap_texture.width}x{self.ap_texture.height}\n"
        text += f"Size (bytes) {self.ap_texture.total_size}\n"

        text += f"\nTexture started at {self.ap_texture.offset}\n"
        text += f"Have {len(self.ap_texture.data)} bytes for data\n"

        has_palette = self.ap_texture.palette_size > 0
        text += f"Palette? {has_palette}\n"
        if has_palette:
            text += f"Have {len(self.ap_texture.palette)} colours for clut\n"
            text += f"Palette size: {self.ap_texture.palette_size} colours\n"

        return text


    def get_file_name(self) -> str:
        return f"[{self.subfile_index}] {self.ap_texture.name}"

    def get_position(self) -> int:
        return self.ap_texture.offset

    def get_position_in_parent(self) -> int:
        return self.entry_position

    def get_size(self) -> int:
        return self.ap_texture.total_size

    def get_offset(self) -> int:
        return self.record.orig_extent_loc * 2048 + self.ap_texture.data_offset

    def is_supported(self):
        # Returns true if the code can handle this format properly (no artifacts)
        #return
        return self.can_write

    def extract(self, iso, options, destination) -> bool:
        self.ap_texture.write_texture_to_png(f"{destination}/{self.ap_texture.name}.png")
        return True

