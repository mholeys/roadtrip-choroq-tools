from choroq.egame.moddingui.entries.game_entry import GameEntry


class HG2FieldEntry(GameEntry):

    def get_type_string(self) -> str:
        return "Field"

    def descriptor(self) -> str:
        return "1 region of the world along with , e.g 223 is Peach Town"

    def get_editable(self) -> bool:
        return False

    def extract(self, iso, options, destination) -> bool:
        return False
