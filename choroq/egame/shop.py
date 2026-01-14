# I think shop file is build up of a list of textures, but the outer most list does not have a table
# List of the following:
# - Textures
# - - Textures have spaces afterwards, void of real data, before next texture starts


import io
import os
from choroq.egame.amesh import AMesh
from choroq.egame.texture import Texture
import choroq.egame.ps2_utils as PS2
import choroq.egame.read_utils as U


class Shop():
    def __init__(self, textures):
        self.textures = textures

    @staticmethod
    def from_file(file, offset):
        file.seek(0, os.SEEK_END)
        max_length = file.tell()
        file.seek(offset, os.SEEK_SET)
        textures = []

        while file.tell() + 64 < max_length:
            test = U.BreadLong(file)
            # This currently misses some, as DMA tag being "end" also somehow means load next texture for some
            if (file.tell()-4) % 2048 == 0 and test & 0xFF000000 == 0x10000000:
                file.seek(-4, os.SEEK_CUR)
                print(f"Next texture at @ {file.tell()}")

                last = False
                while not last:
                    test = U.BreadLong(file)
                    if (file.tell() - 4) % 2048 == 0 and test & 0xFF000000 == 0x10000000:
                        file.seek(-4, os.SEEK_CUR)  # Seek back for next read
                    else:
                        break  # No more textures
                    # Read texture
                    (address, texture), last = Texture.read_texture(file, file.tell())

                    # AFAIK all addresses are 0 for textures for shops
                    if address != 0:
                        exit(910)

                    textures.append(texture)

                    if not last:
                        # Check for FF which should mark the next texture as being a palette (CLUT)
                        # if this is FF then assume it is for the pre texture, if not just try and
                        # read more textures
                        test2 = U.readLong(file)  # Peek
                        file.seek(-4, os.SEEK_CUR)
                        print(f"Checking for clut at @ {file.tell()} {test2:x}")
                        if test2 & 0xFF000000 == 0x10000000 and test2 & 0x00FF0000 == 0x00FF0000:
                            print(f"Has clut at @ {file.tell()}")
                            # Probably a clut
                            (clut_address, clut), last = Texture.read_texture(file, file.tell())
                            unswizzled = Texture.unswizzle_bytes(clut)
                            texture.palette = unswizzled  # Set the texture's palette accordingly
                            texture.palette_width = clut.width
                            texture.palette_height = clut.height


                print(f"Done texture at @ {file.tell()}")
                print(f"{len(textures)}")

        return Shop(textures)

    @staticmethod
    def fromFile(file, offset):
        file.seek(0, os.SEEK_END)
        max_length = file.tell()
        file.seek(offset, os.SEEK_SET)
        entries = []

        current_index = 0
        while file.tell() < max_length:
            test = U.BreadLong(file)
            if file.tell() % 4 == 0 and test != 0xFFFFFFFF and test != 0x00000000:
                file.seek(-4, os.SEEK_CUR)
                print(f"Trying to parse shop.[{current_index}] found start {file.tell()}")
                t = Texture.all_from_file(file, file.tell())
                print(t)
                entries.append(t)
                current_index += 1
                
                # Check for oddness after last texture dma tag
                after_texture_pos = file.tell()
                print(f"Checking for skip {after_texture_pos}")
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
                file.seek(after_texture_pos+96, os.SEEK_SET)
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
                            file.seek(after_texture_pos, os.SEEK_SET)
                    # elif dataLength % 4 == 0 and dataLength > 16 and dataLength < 1228800: # 640x480 image
                    #     # This check should probably be a part of texture
                    else:
                        file.seek(after_texture_pos, os.SEEK_SET)
                else:
                    file.seek(after_texture_pos, os.SEEK_SET)

        if entries == []:
            print("No textures")
        return Shop(entries)
