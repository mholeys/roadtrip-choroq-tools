import os
from pathlib import Path

import choroq.read_utils as U
from choroq.bhe.aptexture import APTexture
from choroq.bhe.mpd_model import MPDModel
from choroq.bhe.pbl_model import PBLModel
from choroq.bhe.toc_0318 import Toc0318

# import lzstring


class CPK:

    def __init__(self, entry_count, entry_positions, eof_position, subfile_types):
        self.entry_count = entry_count
        self.entry_positions = entry_positions
        self.eof_position = eof_position
        self.subfile_types = subfile_types
        self.subfiles = {}

    def read_subfiles(self, file):
        # TODO: support LZS compression/decompression for works
        # TODO: cnt https://en.wikipedia.org/wiki/Lempel%E2%80%93Ziv%E2%80%93Stac
        for i, position in enumerate(self.entry_positions):
            self.read_subfile(file, i)


    def read_subfile(self, file, index):
        position = self.entry_positions[index]
        i = index
        print(f"Reading subfile @ {position}, type should be {self.subfile_types[i]} ")
        read_from = file

        # Need to handle LZS compression
        # Then read as another type
        # if self.subfile_types[i] == b'LZS\x00':
        #     file.seek(position)
        #     U.readLong(file)
        #     size_maybe = U.readLong(file)
        #     string_in = file.read(8618)
        #     # LZS compression
        #     result = lzstring._decompress(len(string_in), 255, lambda index: string_in[index])
        #     # result = lzstring.decompressFromUint8Array(string_in)
        #     print(result)
        #     print(result[0:5])

        if self.subfile_types[i] == b'PBL\x00':
            # Model format
            pbl_data = PBLModel.read_pbl(read_from, position)
            self.subfiles[i] = ("PBL", pbl_data)
        elif self.subfile_types[i] == b'MPD\x00':
            # Model format
            mpd_data = MPDModel.read_mpd(read_from, position)
            self.subfiles[i] = ("MPD", mpd_data)
        elif self.subfile_types[i] == b'APT\x00':
            # Texture file
            apt_data = APTexture.read_apt(read_from, position)
            self.subfiles[i] = ("APT", apt_data)
        elif self.subfile_types[i] == b'\x03\x18\x00\x00':
            # toc/0318 file
            toc_data = Toc0318.read_toc0318(read_from, position)
            self.subfiles[i] = (b'TOC\x00', toc_data)
        elif self.subfile_types[i] == b'TOC\x00':  # This is odd, but its same as 0318, but just one toc
            # toc/TOC file
            toc_header = Toc0318.read_toc_part_header(read_from, position)
            toc_data = Toc0318.read_toc_part(read_from, toc_header)
            self.subfiles[i] = (b'TOC\x00', toc_data)  # Convert to list, as this is required for other type
        else:
            print(f"Unknown subfile type: {self.subfile_types[i]} @ {position}")
        pass

    pass

    @staticmethod
    def read_cpk(file, offset):
        file.seek(offset, os.SEEK_SET)

        # CPK format is as follows:
        # 0x00 00 00 04 magic
        # entry_count (long)
        # Then a table of entries,
        # with a number indicating the position in the file, / 2048 1= 2048 4 = 8192 for that section

        # Read CPK header
        magic = U.readLong(file)
        if magic != 0x40000000:  # flipped but worth checking
            print(f"Invalid CPk file, does not contain BHE CPK magic")
            exit(1)

        entry_count = U.readLong(file)
        print(f"CPK has {entry_count} entries")
        entry_positions = []
        for i in range(entry_count):
            entry_positions.append(U.readShort(file) * 2048)

        past_eof = U.readShort(file)  # Not sure why, but the last one is after the end of the file?

        # Remove duplicates, and bad offsets
        entry_positions_2 = []
        for i in range(len(entry_positions)):
            pos = entry_positions[i]
            if not (pos in entry_positions[0:i] or pos >= past_eof * 2048):
                entry_positions_2.append(pos)

        # Now parse each section as their own formats
        # Read all formats
        subfile_types = []
        for pos in entry_positions_2:
            # Check if we have past the end
            # Jump to position, and find its magic/header
            file.seek(pos, os.SEEK_SET)
            file_magic = file.read(4)
            if file_magic == b'':
                print(f"Bad position @ {pos}")
            subfile_types.append(file_magic)
            try:
                name = file_magic.decode('ascii').rstrip("\x00")
                print(f"{name} @ {pos}")
            except:
                print(f"Possible bad position @ {pos} {file_magic}")
                # exit()
                pass

        if len(entry_positions_2) != len(subfile_types):
            print("Different lengths")
            exit()

        cpk = CPK(entry_count, entry_positions_2, past_eof, subfile_types)

        return cpk




