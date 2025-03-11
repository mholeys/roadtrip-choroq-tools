# I think shop file is build up of a list of textures, but the outer most list does not have a table
# List of the following:
# - Textures
# - - Textures have spaces afterwards, void of real data, before next texture starts


import io
import os
import math
from choroq.amesh import AMesh
from choroq.texture import Texture
from choroq.car import CarModel, CarMesh
from choroq.car_hg3 import HG3CarModel, HG3CarMesh
import choroq.ps2_utils as PS2
import choroq.read_utils as U

class Shop():
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
                print(f"Trying to parse shop.[{currentIndex}] found start {file.tell()}")
                t = Texture.allFromFile(file, file.tell(), maxLength, returnToStart=False)
                print(t)
                entries.append(t)
                currentIndex += 1
                
                # Check for oddness after last texture dma tag
                afterTexturePos = file.tell()
                print(f"Checking for skip {afterTexturePos}")
                file.seek(-48, os.SEEK_CUR)
                print(f"Checking for skip dmaTag @{file.tell()}")

                dmaTag = PS2.decode_DMATag(file)
                tagId = PS2.decode_DMATagID_source(dmaTag)
                print(dmaTag)
                print(tagId)

                # Check prev dmaTag, to look for the skip field
                dataSkipField = (dmaTag['data'] & 0xFFF0) >> 4
                print(dataSkipField)
                # Shift order
                dataSkipField = (((dataSkipField & 0xF) << 8) | (dataSkipField & 0xF0) | ((dataSkipField & 0xF00) >> 8)) << 4
                print(f"Does tag have skip? {dmaTag['data']} {dmaTag['data'] & 0xFFF0} {dataSkipField}")
                
                # This field holds the length of data, ignoring the header in QW
                file.seek(afterTexturePos+96, os.SEEK_SET)
                dataLength = U.readShort(file)

                if dmaTag['unused'] != 135: # Case in shops where there is another image within this end tag
                    postTag = dmaTag['taddr']+dmaTag['qwordCount']*16+16
                    # Try and see if skip is valid
                    file.seek(postTag+dataSkipField, os.SEEK_SET)
                    if file.tell() % 16 == 0:
                        U.BreadByte(file)
                        U.BreadByte(file)
                        test = U.BreadByte(file)
                        if test == 0x10 or test == 0xFF:
                            # This is probably the next shop, so setup next
                            file.seek(postTag+dataSkipField, os.SEEK_SET)
                        else:
                            file.seek(afterTexturePos, os.SEEK_SET)
                    # elif dataLength % 4 == 0 and dataLength > 16 and dataLength < 1228800: # 640x480 image
                    #     # This check should probably be a part of texture
                    else:
                        file.seek(afterTexturePos, os.SEEK_SET)
                else:
                    file.seek(afterTexturePos, os.SEEK_SET)

        if entries == []:
            print("No entries")
        return Shop(entries)
