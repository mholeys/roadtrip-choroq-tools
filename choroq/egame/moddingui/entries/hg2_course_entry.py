from choroq.egame.moddingui.entries.game_entry import GameEntry


class HG2CourseEntry(GameEntry):

    def get_type_string(self) -> str:
        return "Course"

    def descriptor(self) -> str:
        return ("Contains the track or event map with textures, mesh data,"
                " and usually a minimap, and objects used in the map/event.")

    def convert_name(self) -> str:
        name_map_eur = {
            "C00": "Peach Raceway",
            "C01": "Peach Raceway II",
            "C02": "Temple Raceway",
            "C03": "Ninja Temple Raceway",
            "C04": "Desert Raceway",
            "C05": "Night Glow Raceway",
            "C06": "Snow Mountain Raceway",
            "C07": "Miner 49er Raceway",
            "C08": "Slick Track",
            "C09": "Oval Raceway",
            "C10": "River Raceway",
            "C11": "Snow Mountain Raceway",
            "C12": "Lava Run Raceway",
            "C13": "Sunny Beach Raceway",
            "C14": "Lagoon Raceway",
            "C15": "No file - Not in game",
            "C16": "File, with oval/tunnel debug map?",
            "C17": "No file - Not in game",
            "C18": "Tin Raceway (Day)",
            "C19": "Tin Raceway (Night)",
            "C20": "Endurance Run",
            "A00": "Treasure Hunting Maze",
            "A01": "Sliding Door Race",
            "A02": "Highway Race",
            "A03": "Rock Climbing",
            "A04": "Drag Race",
            "A05": "Golf",
            "A06": "Roulette",
            "A07": "Figure 8",
            "A08": "Football",
            "A09": "Rainbow Jump",
            "A10": "Tunnel Race",
            "A11": "Obstacle Course",
            "A12": "Which-way? Race",
            "A13": "Volcano Course",
            "A14": "Curling",
            "A15": "Barrel Dodging",
            "A16": "Cloud Hill (Town)",
            "A17": "Ski Jumping",
            "A18": "Fishing",
            "A19": "Beach Flag",
            "A20": "Single Lap Race",
        }
        if self.game_variant == "EUR":
            return name_map_eur.get(self.basename, self.basename)
        return self.basename

    def get_editable(self) -> bool:
        return False

    def extract(self, iso, options, destination) -> bool:
        return False
