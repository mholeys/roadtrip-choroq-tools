import os
from io import BytesIO

import choroq.read_utils as U
import choroq.external_lib.ff7.lzss as lzss
from choroq.bhe.aptexture import APTexture


class LZSContainer:

    def __init__(self, contained_file=None):
        if contained_file is None:
            contained_file = []
        self.contained_file = contained_file

    @staticmethod
    def read_lzs(file, offset, compressed_length):
        file.seek(offset, os.SEEK_SET)
        magic = file.read(4)
        if magic != b'LZS\0':
            return LZSContainer()

        decompressed_length = U.readLong(file)
        header_length = 8
        compressed_data = file.read(compressed_length - header_length)
        compressed_data += b'\0' * 1024 # pad to help with oob errors

        try:
            decompressed_data = lzss.decompress(compressed_data)
        except Exception as e:
            print("Failed to decompress LZS")
            return LZSContainer()

        decompressed = BytesIO(decompressed_data)
        decompressed.seek(0, os.SEEK_SET)
        subfile_magic = decompressed.read(4)

        if len(decompressed_data) != decompressed_length:
            print(f"LZS decompression resulted in a different size {len(decompressed_data)} != {decompressed_length}")

        contained_file = None
        if subfile_magic == b'APT\0':
            apt_data = APTexture.read_apt(decompressed, 0)
            contained_file = apt_data

        elif subfile_magic == b'\0\0\0\0':
            print(f"Failed to extract file from LZS, bad decompression magic: {subfile_magic}")
        else:
            print(f"Failed to extract file from LZS, unknown subfile {subfile_magic}")

        return LZSContainer(contained_file)