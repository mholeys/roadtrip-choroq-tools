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

    def get_file_name(self) -> str:
        return f"[{self.subfile_index}] {self.ap_texture.name}"

