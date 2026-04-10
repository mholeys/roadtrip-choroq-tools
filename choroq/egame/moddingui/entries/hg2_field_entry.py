from choroq.egame.moddingui.entries.game_entry import GameEntry


class HG2FieldEntry(GameEntry):

    def get_type_string(self) -> str:
        return "Field"

    def descriptor(self) -> str:
        return "1 region of the world along with , e.g 223 is Peach Town"

    def convert_name(self) -> str:
        valid = [
            "011", "012", "013", "023",
            "103", "111", "113",
            "202", "203", "210", "211", "213", "220", "223", "233"
        ]
        names = {
            "011": "Lighthouse",
            "012": "Ruins",
            "013": "Sandpolis",
            "023": "My City",

            "103": "Chestnut Canyon",
            "111": "UFO",
            "113": "Fuji City",

            "202": "Underwater Temple",
            "203": "White Mountain",
            "210": "Mushroom Road",
            "213": "Windmills",
            "211": "Docks",
            "220": "Bridge",
            "223": "Peach Town",
            "233": "Papaya Island",
        }
        if self.basename in valid:
            return f"{names[self.basename]} ({self.basename})"

        ocean = [
            "000", "001", "002", "010", "031",
            "100", "101", "122", "123", "131", "132", "133",
            "231",
            "300", "302", "303", "311", "312", "313", "320", "322", "323", "331", "332", "333",
        ]
        if self.basename in ocean:
            return f"Ocean ({self.basename})"
        return self.basename

    def get_editable(self) -> bool:
        return False

    def extract(self, iso, options, destination) -> bool:
        return False
