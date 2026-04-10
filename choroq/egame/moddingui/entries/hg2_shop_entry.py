from choroq.egame.moddingui.entries.game_entry import GameEntry


class HG2ShopEntry(GameEntry):

    def get_type_string(self) -> str:
        return "Shop"

    def descriptor(self) -> str:
        return "Contains textures for each of the towns shops/interiors"

    def convert_name(self) -> str:
        town_map_eur = {
            "T00": "Peach Town",
            "T01": "Fuji City",
            "T02": "Sandpolis",
            "T03": "Chestnut Canyon",
            "T04": "Mushroom Road",
            "T05": "White Mountain",
            "T06": "Papaya Island",
            "T07": "Cloud Hill",
            "T08": "My City",
            "T09": "Windmills",
            "T10": "Bridge",
            "T11": "UFO",
            "T12": "Ruins",
            "T13": "Lighthouse",
            "T14": "022",
            "T15": "110",
            "T16": "120",
            "T17": "202",
            "T18": "212",
            "T19": "221",
            "T20": "232"
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
