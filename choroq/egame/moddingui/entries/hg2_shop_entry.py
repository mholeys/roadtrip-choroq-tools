from choroq.egame.moddingui.entries.game_entry import GameEntry


class HG2ShopEntry(GameEntry):

    def get_type_string(self) -> str:
        return "Shop"

    def descriptor(self) -> str:
        return "Contains textures for each of the towns shops/interiors"

    def convert_name(self) -> str:
        town_map_eur = {
            "T00": "",
            "T01": "",
            "T02": "",
            "T03": "",
            "T04": "",
            "T05": "",
            "T06": "",
            "T07": "",
            "T08": "",
            "T09": "",
            "T10": "",
            "T11": "",
            "T12": "",
            "T13": "",
            "T14": "",
            "T15": "",
            "T16": "",
            "T17": "",
            "T18": "",
            "T19": "",
            "T20": ""
        }
        if self.game_variant == "EUR":
            return town_map_eur.get(self.basename, self.basename)
        return self.basename

    def get_editable(self) -> bool:
        return True

    def get_extractable(self) -> bool:
        return False

    def extract(self, iso, options, destination) -> bool:
        return False
