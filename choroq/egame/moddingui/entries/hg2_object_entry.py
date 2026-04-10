from choroq.egame.moddingui.entries.hg2_car_entry import HG2CarEntry

class HG2ObjectEntry(HG2CarEntry):

    def get_type_string(self) -> str:
        return "Object (like car)"

    def descriptor(self) -> str:
        return "Has multiple parts, depends on the file"

    def convert_name(self) -> str:
        return self.basename
