from enum import Enum
from io import BytesIO

import configparser
from pathlib import Path


class GameVersion(Enum):
    UNSET = 0,
    COMBAT_Q = 1,
    SHIN_COMBAT_Q = 2,
    CHOROQ_HG_1 = 3,
    CHOROQ_HG_4 = 4,
    CHOROQ_WORKS = 5,


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


class UiConfig:
    # Paths section
    SECTION_PATHS = 'Paths'
    KEY_ISO_PATH = 'LastIsoPath'
    KEY_DUMP_PATH = 'LastDumpPath'
    KEY_EXTRACT_PATH = 'LastExtractPath'

    # Warning section
    SECTION_WARNINGS = 'Warnings'
    KEY_WARNINGS_DISABLED = 'WarningsDisabled'

    def __init__(self, config_name):
        if config_name == '' or config_name is None:
            config_name = 'config.txt'
        self.config_name = config_name
        self.config = configparser.ConfigParser()

    def parse_config(self):
        # Setup defaults
        self.config[UiConfig.SECTION_PATHS] = {
            UiConfig.KEY_ISO_PATH: 'None',
            UiConfig.KEY_DUMP_PATH: 'None',
            UiConfig.KEY_EXTRACT_PATH: 'None',
        }

        self.config[UiConfig.SECTION_WARNINGS] = {
            UiConfig.KEY_WARNINGS_DISABLED: 'False',
        }

        self.config.read(self.config_name)
        print(self.config[UiConfig.SECTION_PATHS][UiConfig.KEY_ISO_PATH])
        print(self.config[UiConfig.SECTION_WARNINGS][UiConfig.KEY_WARNINGS_DISABLED])

    def save_config(self):
        with open(self.config_name, 'w') as configfile:
            self.config.write(configfile)
        print("Saved ui config")

    def get_last_iso_path(self):
        if self.config is None:
            return None
        if UiConfig.SECTION_PATHS not in self.config:
            return None
        path = self.config[UiConfig.SECTION_PATHS][UiConfig.KEY_ISO_PATH]
        if path == 'None':
            return None
        return path

    def get_last_dump_path(self):
        if self.config is None:
            return None
        if UiConfig.SECTION_PATHS not in self.config:
            return None
        path = self.config[UiConfig.SECTION_PATHS][UiConfig.KEY_DUMP_PATH]
        if path == 'None':
            return None
        return path

    def get_last_extract_path(self):
        if self.config is None:
            return None
        if UiConfig.SECTION_PATHS not in self.config:
            return None
        path = self.config[UiConfig.SECTION_PATHS][UiConfig.KEY_EXTRACT_PATH]
        if path == 'None':
            return None
        return path

    def update_iso_path(self, path):
        # Get the path to the file, as we will reopen this
        self.config[UiConfig.SECTION_PATHS][UiConfig.KEY_ISO_PATH] = str(path)

    def update_dump_path(self, path):
        # Get the path to the folder, to make open file dialog faster
        folder_path = str(Path(path).parent)
        self.config[UiConfig.SECTION_PATHS][UiConfig.KEY_DUMP_PATH] = str(folder_path)

    def update_extract_path(self, path):
        # Get the path to the folder, to make open file dialog faster
        self.config[UiConfig.SECTION_PATHS][UiConfig.KEY_EXTRACT_PATH] = str(path)

    def has_warnings(self):
        if self.config is None:
            return True
        if UiConfig.SECTION_WARNINGS not in self.config:
            return True

        warnings_disabled = self.config[UiConfig.SECTION_WARNINGS][UiConfig.KEY_WARNINGS_DISABLED]
        if warnings_disabled == 'True':
            return False
        return True

