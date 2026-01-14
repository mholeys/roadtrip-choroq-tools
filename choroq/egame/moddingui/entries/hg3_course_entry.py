from choroq.egame.moddingui.entries.game_entry import GameEntry


class HG3CourseEntry(GameEntry):

    def get_type_string(self) -> str:
        return "Course"

    def descriptor(self) -> str:
        return ("Contains the track or event map with textures, mesh data,"
                " and usually a minimap, and objects used in the map/event.")

    def convert_name(self) -> str:
        name_map_eur = {
            "C00": "Lake Side Castle",
            "C01": "Sunset Volcano",
            "C02": "Hot Sand Ruin",
            "C03": "Asian Miracle",
            "C04": "Jungle Beat",
            "C05": "Rainy Mansion",
            "C06": "Snow Palace Mountain",
            "C07": "Splash Highway",
            "C08": "Disco King's Cave",
            "C09": "Two-Tone Factory",
            "C10": "Heaven's Rainbow",
            "C11": "Space Trip",
            "C12": "Grunge Garden",
            "C13": "Scratch Mountain",
            "C14": "Echo Forest",
            "C15": "Noice City",
            "C16": "Live House",
            "C17": "Ending",
            "A00": "Beginners",
            "A01": "Speed Boat",
            "A02": "Balloon Hover",
            "A03": "The Fisher",
            "A04": "Jungle Heli",
            "A05": "Let's Side Jet",
            "A06": "Drag",
            "A07": "Water Drag",
            "A08": "Aqua Drag",
            "A09": "Soccer",
        }
        if self.game_variant == "EUR":
            return name_map_eur.get(self.basename, self.basename)
        return self.basename

    def get_editable(self) -> bool:
        return False

    def extract(self, iso, options, destination) -> bool:
        return False
