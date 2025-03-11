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
from choroq.amesh import AMesh
from choroq.texture import Texture
from choroq.car import CarModel, CarMesh
from choroq.car_hg3 import HG3CarModel, HG3CarMesh
import choroq.read_utils as U

class GarageModel():
    def __init__(self, entries):
        self.entries = entries

    @staticmethod
    def fromFile(file, offset):
        file.seek(0, os.SEEK_END)
        maxLength = file.tell()
        file.seek(offset, os.SEEK_SET)
        entries = []

        currentIndex = 0
        while file.tell() < maxLength:
            test = U.BreadLong(file)
            if file.tell() % 4 == 0 and test != 0xFFFFFFFF and test != 0x00000000:
                file.seek(-4, os.SEEK_CUR)
                print(f"Trying to parse garage.[{currentIndex}] found start {file.tell()}")
                entries.append(GarageEntry.fromFile(file, file.tell()))
                currentIndex += 1

        if entries == []:
            print("No entries")
        return GarageModel(entries)


class GarageEntry():

    def __init__(self, meshes = [], textures = []):
        self.meshes = meshes
        self.textures = textures



    @staticmethod
    def _parseOffsets(file, offset):
        print(offset)
        file.seek(offset, os.SEEK_SET)
        subFileOffsets = [U.readLong(file), U.readLong(file), U.readLong(file), U.readLong(file)]
        return subFileOffsets

    @staticmethod
    def readAdditional(file, offset, maxLength):
        if offset + 100 > maxLength:
            return []
        textures = []
        file.seek(offset, os.SEEK_SET)
        check = U.readLong(file)
        # Check for next
        file.seek(offset, os.SEEK_SET)

        if check == 0x00000010:
            # Jump back to start of the next (probably) garage file 
            print(f"No additional texture, at next file 0x{check:X}")
            # give up, as we have not found a palette
            return []

        print(f"Reading garage additional @ {offset}")
        # Read texture data, as we don't know what the image dimentions are
        dataIn = U.readShort(file)
        data = []
        print(f"Reading until palette @ {file.tell()-2}")
        more = True
        count = 0
        while more and count < 0xFFFF:
            if dataIn == 0x0046:
                more = False
                break
            elif dataIn == 0x0010:
                more = False
                break
            # Read 4 as the headers are aligned by 16 bytes
            data.append(dataIn)
            dataIn = U.readShort(file)
            data.append(dataIn)
            dataIn = U.readShort(file)
            data.append(dataIn)
            dataIn = U.readShort(file)
            data.append(dataIn)
            dataIn = U.readShort(file)
            count += 16
        if len(data) < 16:
            if data[3] == 0 and data[4] == 0x51: #this is midway between a header
                file.seek(offset+64, os.SEEK_SET)
                return GarageEntry.readAdditional(file, file.tell(), maxLength)
            if data[3] == 0 and data[4] == 0x52: #this is midway between a header
                file.seek(offset+48, os.SEEK_SET)
                return GarageEntry.readAdditional(file, file.tell(), maxLength)
            if data[3] == 0 and data[4] == 0x53: #this is midway between a header
                file.seek(offset+32, os.SEEK_SET)
                return GarageEntry.readAdditional(file, file.tell(), maxLength)
        print(data)
        print(f"Read up to ?palette @ {file.tell()-2}")
        # Check of the 3/4 byte of the palette, should me FF to be a palette
        # if not we are probably at bad data, give up
        check = U.readShort(file)
        # Check for the start of the next garage entry
        if dataIn == 0x0010 and check == 0x0000:
            # Now check that there are only 3 offsets
            offset1 = U.readLong(file)
            offset2 = U.readLong(file)
            offset3 = U.readLong(file)
            print(f"offsets? {[(dataIn << 8) | check, offset1, offset2, offset3]}")
            if offset2 > offset1: # Sanity check
                if offset3 == 0:        
                    # Jump back to start of the next (probably) garage file 
                    file.seek(-16, os.SEEK_CUR)
                    print(f"Offsets valid")
                    print(f"No texture, at next file 0x{check:X}")
                    # give up, as we have not found a palette
                    return []
            # This is probably data we want to parse, not a new entry
            print("Offsets not valid trying as texture")
            file.seek(-16, os.SEEK_CUR)
        # Check for the start of a Palette
        palette = True
        if (check & 0xFFFF) != 0x10FF:
            print(f"No palette, check 0x{check:X}")
            # give up, as we have not found a palette
            palette = False
        print(f"Probably palette? {palette}")
        # Move to palette/start of next section
        file.seek(-4, os.SEEK_CUR)
        # Read palette and create image
        texture = []
        for v in data:
            texture.append(v & 0xFF)
            texture.append((v & 0xFF00) > 8)
        
        texture = bytes(texture)
        # Just make up width/height
        width = int(len(texture) / 16)
        height = int(len(texture) / width)
        if palette:
            bpp = 8
            colours, psize = Texture._paletteFromFile(file, file.tell(), fixAlpha=True)
        else:
            bpp = 24
            psize = (0, 0)
            colours = None
            
        textures.append(Texture(texture, colours, (width, height), psize, bpp, fixAlpha=True))
        print(f"Read texture {texture}")

        # Check for extra dma tag, which would end the last image/palette data
        dmaTagCheck = U.readLong(file)
        file.seek(-4, os.SEEK_CUR)
        if dmaTagCheck & 0xFF00FFFF == 0x70000002:
            # Skip past dma tag, ignoring value
            print("Skipping ending dmatag")
            file.seek((dmaTagCheck & 0xFFFF) * 16 + 16, os.SEEK_CUR)
        # Check for more
        textures += GarageEntry.readAdditional(file, file.tell(), maxLength)
        return textures

    @staticmethod
    def fromFile(file, offset):
        file.seek(0, os.SEEK_END)
        maxLength = file.tell()
        file.seek(offset, os.SEEK_SET)
        print(offset)
        offsets = GarageEntry._parseOffsets(file, offset)
        meshes = []
        textures = []
        for oi, o, in enumerate(offsets):
            if o == 0:
                break
            file.seek(offset+o, os.SEEK_SET)
            if oi == 0:
                # Car style meshes
                print(f"Reading garage mesh {file.tell()}")
                meshes += CarMesh._fromFile(file, offset+o, offsets[1])
            elif oi == 1:
                # Textures
                print(f"Reading garage textures {file.tell()}")
                textures += Texture.allFromFile(file, offset+o, maxLength, returnToStart=False)
            elif oi == 2:
                # Extra textures?                
                textures += GarageEntry.readAdditional(file, offset+o, maxLength)

            
        return GarageEntry(meshes, textures)

    