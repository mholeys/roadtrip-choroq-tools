from enum import Enum
from io import BytesIO


class GameVersion(Enum):
    UNSET = 0,
    CHOROQ_HG_2 = 1,
    CHOROQ_HG_3 = 2,


class PS2Cnf:

    def __init__(self, value):
        self.valid_cnf = False
        if type(value) is not str:
            if type(value) is BytesIO:
                value = value.read().decode('UTF-8')
            else:
                return
        found = 0
        self.elf_path = None
        self.elf_name = None
        self.elf_folder = None
        self.version = None
        self.video_mode = None

        lines = value.split('\r\n')
        for line in lines:
            if line.startswith("BOOT2") and self.elf_path is None:
                self.elf_path = line[line.index(" = ")+3:-2]
                self.elf_name = self.elf_path[self.elf_path.rfind("\\")+1:]
                self.elf_folder = self.elf_path[0:self.elf_path.rfind("\\")+1]
                found += 1
            elif line.startswith("VER") and self.version is None:
                self.version = line[line.index(" = ")+3:]
                found += 1
            elif line.startswith("VMODE") and self.video_mode is None:
                self.video_mode = line[line.index(" = ")+3:]
                found += 1

        if found == 3:
            self.valid_cnf = True

    def valid(self) -> bool:
        return self.valid_cnf

    def get_version(self) -> str:
        return self.version

    def get_elf_name(self) -> str:
        return self.elf_name

    def get_elf_folder(self) -> str:
        return self.elf_folder

    def get_elf_path(self) -> str:
        return self.elf_path

    def get_vmode(self) -> str:
        return self.video_mode
