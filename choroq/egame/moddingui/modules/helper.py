import os

import choroq.read_utils as U
from choroq.egame.texture import Texture


class Helper:
    @staticmethod
    def find_offsets(stream):
        offsets = [U.readLong(stream)]
        read_more = True
        while read_more:
            offset = U.readLong(stream)
            if offset < offsets[-1] or offset == 0 or stream.tell() >= offsets[0]:
                read_more = False
                break
            offsets.append(offset)

        return offsets

    @staticmethod
    def find_texture_addresses(stream):
        offsets = Helper.find_offsets(stream)
        eof_offset = offsets[-1]
        texture_offset = offsets[-2]

        textures = Texture.all_from_file(stream, texture_offset)
        if textures.size == 2:
            raise Exception("Cannot find texture addresses")

        return textures[0][0], textures[1][0]

    @staticmethod
    def find_texture_tags(stream):
        stream.seek(0, os.SEEK_SET)
        offsets = Helper.find_offsets(stream)
        eof_offset = offsets[-1]
        texture_offset = offsets[-2]

        textures = Texture.all_from_file(stream, texture_offset)
        if len(textures) == 2:
            raise Exception("Cannot find texture addresses")

        # Move to start of the texture, and copy the tag bytes
        stream.seek(0, os.SEEK_SET)
        stream.seek(texture_offset, os.SEEK_CUR)
        texture_header = stream.read(112) # 112 is texture header for hg2

        # Move to start of the clut
        texture_size = int(textures[0][1].width * textures[0][1].height * textures[0][1].bpp / 8)
        texture_data = stream.read(texture_size)
        # Read/copy in the tag bytes
        clut_header = stream.read(112)  # 112 is texture header for hg2

        # Move to end of the clut
        clut_size = int(textures[1][1].width * textures[1][1].height * textures[1][1].bpp / 8)
        clut_data = stream.read(clut_size)

        # Read/copy in the end bytes
        # 48 is texture/clut tail for hg2
        # has commands to flush and end dma
        clut_tail = stream.read(48)
        if stream.tell() != eof_offset:
            raise Exception("end of texture != EOF, invalid original car file, cannot reuse data")

        return texture_header, texture_data, texture_size, clut_header, clut_data, clut_size, clut_tail

