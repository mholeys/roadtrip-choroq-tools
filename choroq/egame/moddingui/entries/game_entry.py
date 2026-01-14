from abc import abstractmethod

from pycdlib.dr import DirectoryRecord

from choroq.egame.moddingui.common import *


class GameEntry(object):
    """
    For things like car/course/field/binary
    so we can store how it can be edited
    """

    def __init__(self, folder, path, game_version: GameVersion, game_variant: str, record: DirectoryRecord):
        self.folder = folder
        self.path = path
        self.filename = self.path[self.path.rfind("/") + 1:self.path.rfind(";")]
        if '.' in self.filename:
            self.extension = self.filename[self.filename.rfind(".")+1:]
        else:
            self.extension = ""
        self.basename = self.path[self.path.rfind("/") + 1:self.path.rfind(".")]
        self.game_version = game_version
        self.game_variant = game_variant
        self.record = record

    def get_game_version(self) -> GameVersion:
        """
        @return: Returns which game this file is from, probably internal use only
        """
        return self.game_version

    def get_game_variant(self) -> str:
        """
        @return: Returns which game this file is from, probably internal use only
        """
        return self.game_variant

    def get_type_string(self) -> str:
        """
        @return: Short string to describe the type such as 'Course'
        """
        return "Unknown"

    def descriptor(self) -> str:
        """
        Short description of this file type

        @return A short descriptive string of this entry and what it does in the game or on the disk
        """
        return "Unknown"

    def convert_name(self) -> str:
        """
        Take the given file name, and converts it into the localised version used in the game
        e.g. Q00 -> Q01 (car name here)
        e.g. C00 -> Peach Raceway C00-> jp name

        @return: string containing the known name of this file's contents
        """
        return self.basename

    def get_editable(self) -> bool:
        """
        Used to see if the entry for this game is well known,
        and there are editing tools available.
        This will only be possible if the file format it well understood

        @return: bool on availability of editing tools
        """
        return False

    def get_sector(self) -> int:
        """
        @return: Returns the sector number of this file entry (2048 size for cd/dvd)
        """
        if self.record is None:
            return -1
        return self.record.orig_extent_loc

    def get_offset(self) -> int:
        """
        @return: Returns the byte offset of this file entry
        """
        if self.record is None:
            return -1
        return self.record.fp_offset

    def get_size(self) -> int:
        """
        @return: The number of bytes this file takes up on the disk
        """
        if self.record is None:
            return -1
        return self.record.data_length

    def get_file_name(self) -> str | None:
        """
        @return: The file name as is on the disk
        """
        return self.filename

    def get_file_extension(self) -> str | None:
        """
        @return: The extension of the file, e.g "BIN" "CPK"
        """
        return self.extension

    def get_file_folder(self) -> str | None:
        """
        @return: The path to the folder that this is in, e.g "/FLD/"
        """
        return self.folder

    def get_extractable(self) -> bool:
        """
        This can be used to check the availablity of extraction tools for this type

        @return: True if the file can be extracted into another format
        """
        return False

    @abstractmethod
    def extract(self, iso, options, destination) -> bool:
        """
        Extract this entry into the destination given, with
        the ability to pass options to the extractor

        @param iso: the open iso to extract data from
        @param options: Options for extraction (varies by entry type)
        @param destination: Path/str to where the file should be extracted to
        @return: successfulness of the extraction
        """
        return False

    def get_extraction_options(self) -> dict | None:
        """
        Used to get all the options available for this extractor
        # TBD on format

        @return: the options # TBD
        """
        return None


class UnknownGameEntry(GameEntry):

    def extract(self, iso, options, destination) -> bool:
        return False
