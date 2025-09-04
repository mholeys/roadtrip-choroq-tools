# I think garage file is build up of a list of items, but the outer most list does not have a table
# List of the following:
# - Sub file list
# - each main sub file is as follows
# - Car [Subfiles]
# - - Model @ 16
# - - Model? @ Offset1
# - - Model? @ Offset2
# - Textures
# - - The textures may hold info after the last DMAtag, the one that causes the list to end?
# - - As sometimes it is followed by a palette, after a long set of the same number?
# - - This could be the method used to replace the flooring with a new palette/style?


import io
import os
import math
import sys

from choroq.amesh import AMesh
from choroq.texture import Texture
from choroq.car import CarModel, CarMesh
from choroq.car_hg3 import HG3CarModel, HG3CarMesh
import choroq.read_utils as U


class GarageModel:
    def __init__(self, entries):
        self.entries = entries

    @staticmethod
    def from_file(file, offset):
        entries = []
        position = offset
        file.seek(0, os.SEEK_END)
        end = file.tell()
        file.seek(offset, os.SEEK_SET)

        while position < end:
            entry, end_position = GarageEntry.from_file(file, position)
            print(f"Read garage entry up to {end_position + position}")
            GarageModel.read_until_next(file, end, end_position + position)
            position = file.tell()
            entries.append(entry)
            # break

        return GarageModel(entries)

    @staticmethod
    def read_until_next(file, end, last_position):
        file.seek(last_position, os.SEEK_SET)
        current = file.tell()
        if current + 2048 >= end:
            return
        # Check if we are already at the correct location
        test_valid = False
        next_try = current

        # Seek to next sector aligned area
        while not test_valid and file.tell() != end:
            file.seek(next_try, os.SEEK_SET)
            test = U.readLong(file)
            file.seek(-4, os.SEEK_CUR)
            test_valid = 0 < test < 32
            next_try = (math.floor(current / 2048) + 1) * 2048
            current = file.tell()
        print(f"Skipped until {file.tell()}")

class GarageEntry:

    def __init__(self, meshes=None, textures=None):
        self.meshes = meshes
        self.textures = textures

    @staticmethod
    def from_file(file, offset):
        print(f"Reading garage entry from {file.tell()}")

        file.seek(offset, os.SEEK_SET)
        # Read offset table
        offsets = [U.readLong(file)]
        while offsets[-1] != 0 and len(offsets) < 32:  # 32 check just for error prevention
            o = U.readLong(file)
            if o == 0 or o < offsets[-1]:
                break
            offsets.append(o)

        if offsets[0] > 32:
            print(f"Ended up at invalid location for garage entry (probably end) {file.tell()}")
            return None, offset+2048

        if len(offsets) > 3:
            print(f"Found different style of data @ {file.tell()}, has more than 2 subfiles [{len(offsets)}]")
            exit()

        # Read model
        meshes = CarMesh.from_file(file, offset+offsets[0], offset+offsets[1] - offset+offsets[0])
        # Read texture
        textures = []
        end_tag = False
        next_texture = offset+offsets[1]
        while not end_tag:
            texture, end_tag = Texture.read_texture(file, next_texture)
            next_texture = file.tell()
            textures.append(texture)

        print(f"Read garage entry up to {file.tell()}")
        # Seek to end
        file.seek(offsets[-1] + offset - 6)  # -6 to ensure other code works for finding next, no matter where we end reading

        return GarageEntry(meshes, textures), offsets[-1]





