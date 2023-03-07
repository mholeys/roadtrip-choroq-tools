# Class for extracting/holding all quick-pic (PUTI) activity images, found in cdrom0:/SYS/PUTI.BIN
# 
# Textures are 256x128 with a white border, 800 bytes of padding after the palette (usually 16x16 1024 byte palette)
# The images do not contain the car, as this is drawn on top for the current player config

import io
import os
import math
from choroq.texture import Texture
from choroq.car import CarMesh
import choroq.read_utils as U


class QuickPic:

    def __init__(self, textures = []):
        self.textures = textures

    @staticmethod
    def fromFile(file, offset, size):
        file.seek(offset, os.SEEK_SET)
        
        textures = []
        while file.tell() < size:
            textures.append(Texture._fromFile(file, file.tell()))
            file.seek(file.tell() + 800)
        return QuickPic(textures)