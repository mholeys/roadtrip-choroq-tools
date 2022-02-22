import io
import os
import choroq.read_utils as U
from PIL import Image, ImagePalette, ImageOps

class Texture:

    cc58 = [0x00,0x08,0x10,0x19, 0x21,0x29,0x31,0x3a, 0x42,0x4a,0x52,0x5a, 0x63,0x6b,0x73,0x7b,
            0x84,0x8c,0x94,0x9c, 0xa5,0xad,0xb5,0xbd, 0xc5,0xce,0xd6,0xde, 0xe6,0xef,0xf7,0xff]

    cc68 = [0x00,0x04,0x08,0x0c, 0x10,0x14,0x18,0x1c, 0x20,0x24,0x28,0x2d, 0x31,0x35,0x39,0x3d,
            0x41,0x45,0x49,0x4d, 0x51,0x55,0x59,0x5d, 0x61,0x65,0x69,0x6d, 0x71,0x75,0x79,0x7d,
            0x82,0x86,0x8a,0x8e, 0x92,0x96,0x9a,0x9e, 0xa2,0xa6,0xaa,0xae, 0xb2,0xb6,0xba,0xbe,
            0xc2,0xc6,0xca,0xce, 0xd2,0xd7,0xdb,0xdf, 0xe3,0xe7,0xeb,0xef, 0xf3,0xf7,0xfb,0xff]

    def __init__(self, texture = [], palette = [], size=(0,0), palettesize=(0,0), fixAlpha=True):
        self.width = size[0]
        self.height = size[1]
        self.pwidth = palettesize[0]
        self.pheight = palettesize[1]
        self.texture = texture
        self.palette = palette
        self.fixAlpha = fixAlpha

    @staticmethod
    def _parseTextureHeader(file, offset):
        unkn0 = U.readByte(file)
        length = U.readByte(file) * 4096 # Not always
        unkn1 = U.readByte(file)
        unkn2 = U.readByte(file)

        nullPad = U.readLong(file)
        unkn3 = U.readShort(file)

        # TODO: find way to determine size
        #length = width*height
        file.seek(offset+0x35, os.SEEK_SET)
        height = U.readByte(file) * 2
        #        file.seek(offset+0x20, os.SEEK_SET)
        width = (int) (length/height)       #= U.readByte(file) * 2
        file.seek(offset+0x70, os.SEEK_SET)
        #print(f"Texture size: {width}x{height}px {length}bytes")

        return width, height, length
    
    @staticmethod
    def _parsePaletteHeader(file, offset):
        # Skip header all values have unknown use atm
        #file.seek(112, os.SEEK_CUR)
        #header = file.read(112)
        
        fB = U.readByte(file) #  Often 0xX6 where x could be something
        colourSize = (fB & 0xF0) >> 4

        nullB = U.readByte(file)

        thisPaletteSize = U.readByte(file)+1 # This might not be really the number of colours
        #print(f"numC{thisPaletteSize} fp:{file.tell()}")
        # Assumed, as no information on the palette header yet
        numberOfPalettes = 1
        # So far all palettes have been nonlinear but need to find
        # if all files are non Linear before ruling out option
        isNonLinear = True
        psize = 16,16
        #print(f"Palette size: {psize[0]}x{psize[1]}px colourSize: {colourSize} numColours: {thisPaletteSize}")

        file.seek(offset+112, os.SEEK_SET)
        return isNonLinear, colourSize, thisPaletteSize, numberOfPalettes, psize

    @staticmethod
    def _fromFile(file, offset, fixAlpha=True):
        file.seek(offset, os.SEEK_SET)
        width, height, length = Texture._parseTextureHeader(file, offset)
        headerLength = 0x70

        # Read texture data in
        texture = file.read(length)

        isNonLinear, colourSize, thisPaletteSize, numberOfPalettes, psize = Texture._parsePaletteHeader(file, offset + length + headerLength)
        
        colours = []

        rawPalette = []

        # read colours in
        if colourSize == 4:
            # 32BBP ARGB
            for i in range(0, thisPaletteSize):
                cr = U.readByte(file)
                cg = U.readByte(file)
                cb = U.readByte(file)
                ca = U.readByte(file)
                if fixAlpha and ca == 0x80:
                    ca = 255
                rawPalette.append([cr, cg, cb, ca])
        elif colourSize == 3:
            #24BPP RGB
            for i in range(0, thisPaletteSize):
                cr = U.readByte(file)
                cg = U.readByte(file)
                cb = U.readByte(file)
                rawPalette.append([cr, cg, cb, 255])
        elif colourSize == 2:
            #16BIT Little Endian RGBA 5551 format
            for i in range(0, thisPaletteSize):
                c = U.readShort(file)
                hex = f"{c:02X}"
                
                cr = c & 0x1f
                c = c >> 5
                cg = c & 0x1f
                c = c >> 5
                cb = c & 0x1f
                c = c >> 5
                ca = 255 - 127 * c 
                rawPalette.append(
                    [Texture.cc58[cr],
                     Texture.cc58[cg], 
                     Texture.cc58[cb],
                     ca])
            #rawPalette.reverse()
            #isNonLinear = True


        if isNonLinear:            
            numParts = (int) (thisPaletteSize / 32)
            numBlocks = 2
            numStripes = 2
            numColours = 8

            paletteIndex = 0
            for part in range(0, numParts):
                for block in range(0, numBlocks):
                    for stripe in range(0, numStripes):
                        for c in range(0, numColours):
                            rawInd = part * numColours * numStripes * numBlocks + block * numColours + stripe * numStripes * numColours + c
                            colours.append(rawPalette[rawInd])
                            paletteIndex += 1
        else:
            colours = rawPalette
        #print(f"Number of colours read: {len(colours)}")
        return Texture(texture, colours, (width, height), psize, fixAlpha)
    
    def writeTextureToPNG(self, path, flipX=False, flipY=False, usepalette=True):
        cList = []
        for c in self.palette:
            cList.append(c[0])
            cList.append(c[1])
            cList.append(c[2])
            cList.append(c[3])
        if usepalette:
            image = Image.frombytes('P', (self.width, self.height), self.texture, 'raw', 'P')
            palette = ImagePalette.raw("RGBA", bytes(cList))
            palette.mode = "RGBA"
            image.palette = palette
        else:
            image = Image.frombytes('L', (self.width, self.height), self.texture, 'raw')
        
        rgbd = image.convert("RGBA")
        if flipX:
            rgbd = ImageOps.mirror(rgbd)
        if flipY:
            rgbd = ImageOps.flip(rgbd)
        rgbd.save(path, "PNG")

    def writePaletteToPNG(self, path):
        cList = []
        
        for c in self.palette:
            cList.append(c[0])
            cList.append(c[1])
            cList.append(c[2])
            cList.append(c[3])
        image = Image.frombytes('RGBA', (self.pwidth, self.pheight), bytes(cList), 'raw', 'RGBA')
        image.save(path, "PNG")



if __name__ == '__main__':
    with open("tests/T00.BIN", "rb") as f:
        f.seek(0, os.SEEK_END)
        fileSize = f.tell()
        print(f"Reading file of {fileSize} bytes")
        f.seek(0, os.SEEK_SET)
