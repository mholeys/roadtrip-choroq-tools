from pycdlib.dr import DirectoryRecord
import pycdlib

from choroq.bhe.mpd_model import MPDModel
from choroq.bhe.moddingui.common import GameVersion
from choroq.bhe.moddingui.entries.game_entry import GameEntry


class MpdEntry(GameEntry):

    def __init__(self, model: MPDModel, folder, path, game_version: GameVersion, game_variant: str, record: DirectoryRecord, subtype: bytes, subfile_index, entry_position):
        super().__init__(folder, path, game_version, game_variant, record)
        self.model = model

        self.subtype = subtype
        self.subfile_index = subfile_index
        self.entry_position = entry_position

        self.can_write = False

    def descriptor(self) -> str:
        text = "MPD\n"
        text += f"Name: {self.model.name}\n"
        text += f"Apt references: \n"
        for ti, tex in enumerate(self.model.texture_references):
            try:
                text += f"\t[{ti}] Name: {tex[0]}\n"
                text += f"\t[{ti}] Size: {tex[1][0]} x {tex[1][1]}\n"
                text += f"\t[{ti}] Format: {tex[1][2]}\n"
                text += f"\t[{ti}] Palette size: {tex[1][3]}\n"
            except IndexError:
                text += f"\t[{ti}] Could not parse texture info\n"
            text += f"\t{tex}\n"

        return text

    def get_file_name(self) -> str:
        if self.model.name is not None:
            return f"[{self.subfile_index}] {self.model.name}"
        if len(self.model.texture_references) > 0:
            return f"[{self.subfile_index}] uses {self.model.texture_references[0][0]}"
        return f"[{self.subfile_index}] MPD"

    def get_position(self) -> int:
        return self.model.offset

    def get_position_in_parent(self) -> int:
        return self.entry_position

    def get_size(self) -> int:
        return self.model.size

    def get_offset(self) -> int:
        return self.record.orig_extent_loc * 2048 + self.model.offset

    def is_supported(self):
        # Returns true if the code can handle this format properly (no artifacts)
        #return self.ap_texture.colour_format
        return self.can_write

    def extract(self, iso, options, destination) -> bool:
        # self.model.write_mesh_to_obj(f"{destination}/{self.model.name}.png")
        with open(f"{destination}/mpd-{self.get_file_name()}.obj", "w") as file:
            self.model.write_mesh_to_obj(file)
        return True

