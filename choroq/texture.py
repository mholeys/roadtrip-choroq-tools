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
        typeF = U.readByte(file) - 0x6
        print(f"TextType: {typeF}")
        
        imageFormat = U.readByte(file)
        unkn1 = U.BreadByte(file) # Could be 64 = odd sizes
        if unkn1 == 0xFF:
            # This is a palette
            return 0,0,0,0
        print(f"Unknown1: {unkn1}")
        unkn2 = U.BreadByte(file)

        nullPad = U.BreadLong(file)
        unkn3 = U.BreadShort(file)

        if typeF == 0 or typeF == 128:
            # Usual file format
            pass

        bpp = 8
        
        oldWay = False
        if not oldWay:
            # 0x00  PSNCT32
            # 0x01  PSMCT24
            # 0x02  PSMCT16
            # 0x0A  PSMCT16S
            # 0x13  PSMT8
            # 0x20  PSMT4
            # 0x1B  PSMT8H
            # 0x24  PSM4HL
            # 0x2C  PSM4HH

            bpp = 0

            file.seek(offset+0x26, os.SEEK_SET)
            bppCheckRaw = U.readShort(file)

            if bppCheckRaw & 0xFF00 == 0x1300:
                bpp = 8
            elif bppCheckRaw & 0xFF00 == 0x1400:
                bpp = 4
            elif bppCheckRaw == 0x0101 or bppCheckRaw == 0x0102:
                bpp = 24
            else:
                print(f"Found new bpp check value {bppCheckRaw}")
                exit(1)
            print(f"BPP {bppCheckRaw}")

            file.seek(offset+0x44, os.SEEK_SET)
            height = U.readShort(file) & 0xFFF ## Think 12 bits for height of texture
            file.seek(offset+0x40, os.SEEK_SET)
            width = U.readShort(file) & 0xFFF ## Think 12 bits for width of texture
            
            file.seek(offset+0x34, os.SEEK_SET)
            length = U.readLong(file)
            print(f"reading texture w:{width} h:{height} l:{length} {bpp} from {bppCheckRaw >> 4}")
            if length == 0 and bpp != 0:
                length = int(width * height * (bpp/8))
                print(f"reading texture w:{width} h:{height} l:{length} {bpp}")
            if width * height != length * 8/bpp:
                # Unusual edge case: where length field is double
                if typeF == 0x40 and width * height * 2 == length:
                    length = width * height

                    print(f"FIXED ODD CASE reading texture w:{width} h:{height} l:{length} {bpp}")
                elif width == 640 and height == 384:
                    length = int(width * height * (bpp/8))
                    print(f"Image header has been read wrong, assuming full screen image")
                elif width == 640 and height == 448:
                    length = int(width * height * (bpp/8))
                    print(f"Image header has been read wrong, assuming full screen image")
                else:
                    # Image stats do not match what we would expect
                    print(f"Image header has been read wrong")

            print(f"reading texture w:{width} h:{height} l:{length} {bpp}")    
        else:
            # 0x35 is probably a long which is the length of the data in the file, no *4096 needed
            file.seek(offset+0x35, os.SEEK_SET)
            sizeTable = U.readByte(file)

            if typeF == 64:
                # File might not be usual size
                sizeTable = 0

            file.seek(offset+21, os.SEEK_SET)
            bitDepthFlag = U.readByte(file)
            print(f"BitDepthFlag {hex(bitDepthFlag)}")

            if bitDepthFlag == 0xB4:
                bpp = 4


            print(f"Sizetable is {sizeTable}")

            if sizeTable == 0:
                print("could mean 16x16 or anything?, will attempt to guess")

            if sizeTable == 8:
                print("assuming texture is 32x64")
                width = 32
                height = 64
                if bpp == 4:
                    width = int(width * 2)
            elif sizeTable == 16:
                print("assuming texture is 64x64")
                width = 64
                height = 64
                if bpp == 4:
                    width = int(width * 2)
            elif sizeTable == 32:
                print("assuming texture is 64x128")
                width = 64
                height = 128
                if bpp == 4:
                    width = int(width * 2)
            elif sizeTable == 64:
                print("assuming texture is 128x128")
                width = 128
                height = 128
            elif sizeTable == 128:
                # Example Meter0 Under ITEM
                print("assuming texture is 256x128")
                width = 256
                height = 128
                if bpp == 4:
                    width = 256
                    height = 256
            elif sizeTable == 192:
                print("assuming texture is 640x384")
                width = 640
                height = 384
            elif sizeTable == 184:
                print("assuming texture is 256x184 quickpic")
                width = 256
                height = 184
            else:
                print("Did not determine width/height by means above (see code)")
                file.seek(offset+0x44, os.SEEK_SET) 
                height = U.readByte(file)
                file.seek(offset+0x35, os.SEEK_SET)
                width = U.readByte(file)
                if bpp == 8:
                    width = width * 2
                print(f"1st {width}x{height}")

                if typeF == 64:
                    width = width * 2
                    print(f"2 {width}")
                elif typeF == 32:
                    width = height
                    height = 16
                    print(f"3 {width}x{height}")
                elif firstLength != 0 and width * height != firstLength:
                    if height == 0: # <- Temp fix
                        height = 32
                    width = (int) (firstLength / height)
                    print(f"4 {width}x{height}")
                if width == 0:
                    file.seek(offset+0x40, os.SEEK_SET)
                    width = U.readByte(file)
                    print(f"5 {width}x{height}")
            
            if typeF == 16:
                width = 16
                height = 16

            if typeF == 32:
                print(f"{width}x{height}")
                #height = (int)(height / 2 )

        # Skip to past header
        file.seek(offset+0x70, os.SEEK_SET)
        print(f"Texture size: {width}x{height}px {length}bytes {file.tell()}")

        return width, height, length, bpp
    
    @staticmethod
    def _parsePaletteHeader(file, offset):
        # Skip header all values have unknown use atm
        #file.seek(112, os.SEEK_CUR)
        #header = file.read(112)

        print(f"parse palette header at {offset} {file.tell()}")
        
        fB = U.readByte(file) #  Often 0xX6 where x could be something

        U.BreadByte(file)
        ffCheck = U.readByte(file)
        if ffCheck != 0xFF and ffCheck < 0x40:
            # This is not a palette, image probably doesn't use one
            return False, 0, 0, 0, (0, 0)
        
        # So far all palettes have been nonlinear but need to find
        # if all files are non Linear before ruling out option
        isNonLinear = True
        
        colourSize = fB - 6
        isNonLinear = True # Assuming all are swizzled
        file.seek(offset+0x40, os.SEEK_SET)
        pWidth = U.readShort(file) & 0xFFF
        file.seek(offset+0x44, os.SEEK_SET)
        pHeight = U.readShort(file) & 0xFFF
        psize = pWidth, pHeight
        thisPaletteSize = pWidth * pHeight
        numberOfPalettes = 1 # Assumption
        headerByteSize = 112

        file.seek(offset+0x6C, os.SEEK_SET)
        endLong = U.readLong(file)
        if endLong == 0x60:
            thisPaletteSize = thisPaletteSize >> 1

        nullB = U.BreadByte(file)

        print(f"Palette size: {psize[0]}x{psize[1]}px colourSize: {colourSize} numColours: {thisPaletteSize}")
        
        file.seek(offset+headerByteSize, os.SEEK_SET)
        return isNonLinear, colourSize, thisPaletteSize, numberOfPalettes, psize

    @staticmethod
    def _unswizzle(palette, size):
        colours = []
        numParts = (int) (size / 32)
        numBlocks = 2
        numStripes = 2
        numColours = 8

        paletteIndex = 0
        for part in range(0, numParts):
            for block in range(0, numBlocks):
                for stripe in range(0, numStripes):
                    for c in range(0, numColours):
                        rawInd = part * numColours * numStripes * numBlocks + block * numColours + stripe * numStripes * numColours + c
                        colours.append(palette[rawInd])
                        paletteIndex += 1
        return colours

    @staticmethod
    def _paletteFromFile(file, length, offset, fixAlpha=True):
        
        isNonLinear, colourSize, thisPaletteSize, numberOfPalettes, psize = Texture._parsePaletteHeader(file, offset)
        if (isNonLinear, colourSize, thisPaletteSize, numberOfPalettes, psize) == (False, 0, 0, 0, (0, 0)):
            # No palette
            print("!Missing palette flag!")
            file.seek(offset, os.SEEK_SET)
            return None, (0,0)

        print(f"Reading palette at {file.tell()}")

        colours = []

        rawPalette = []

        # read colours in
        if colourSize == 64:
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
            # Never been seen
            #24BPP RGB
            for i in range(0, thisPaletteSize):
                cr = U.readByte(file)
                cg = U.readByte(file)
                cb = U.readByte(file)
                rawPalette.append([cr, cg, cb, 255])
        elif colourSize == 32:
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
        elif colourSize == 8:
            # This is not perfect
            # 32BBP RGBA
            for i in range(0, thisPaletteSize):
                cr = U.readByte(file)
                cg = U.readByte(file)
                cb = U.readByte(file)
                ca = U.readByte(file)
                if fixAlpha and ca == 0x80:
                    ca = 255
                if fixAlpha and ca <= 0x80:
                    ca = (ca + 0xF0) & 0xFF
                rawPalette.append([cr, cg, cb, ca])
            # isNonLinear = False
            # rawData = Texture._unswizzle(rawData, thisPaletteSize)
        else:
            print(f"NO COLOUR SIZE, CANNOT GET PALETTE")


        colours = rawPalette
        if isNonLinear:           
            if len(rawPalette) != 0:
                colours = Texture._unswizzle(rawPalette, thisPaletteSize)
            
        #print(f"Number of colours read: {len(colours)}")
        return colours, psize

    @staticmethod
    def _readTexture(file, length, bpp=8):
        texture = 0
        if bpp == 24:
            texture = U.read(file, length)
        elif bpp == 8:
            texture = U.read(file, length)
        elif bpp == 4:
            texData = []
            for i in range(0, int(length)):
                b = U.readByte(file)

                texData.append(b & 0xF)
                texData.append((b >> 4) & 0xF)
            texture = bytes(texData)
        return texture

    @staticmethod
    def _fromFile(file, offset, fixAlpha=True):
        file.seek(offset, os.SEEK_SET)
        width, height, length, bpp = Texture._parseTextureHeader(file, offset)
        if (width, height, length, bpp) == (0,0,0,0):
            # This is probably a double palette image
            file.seek(offset, os.SEEK_SET)
            colours, psize = Texture._paletteFromFile(file, length, offset, fixAlpha)
            return None
        headerLength = 0x70


        # Read texture data in
        texture = Texture._readTexture(file, length, bpp)
        if bpp <= 8:
            colours, psize = Texture._paletteFromFile(file, length, offset + length + headerLength, fixAlpha)
        else:
            # No palette
            psize = (0, 0)
            colours = None
        return Texture(texture, colours, (width, height), psize, fixAlpha)
    
    def writeTextureToPNG(self, path, flipX=False, flipY=False, usepalette=True):
        cList = []
        if self.pwidth == 0 and self.pheight == 0: # bpp > 8
            image = Image.frombytes('RGB', (self.width, self.height), self.texture, 'raw')
            image.convert("RGBA").save(path, "PNG")
        else:
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
        
        if self.pwidth * self.pheight != len(self.palette):
            print(f"paletteLen = {len(cList)} should be {self.pwidth},{self.pheight} {len(self.palette)} len {len(bytes(cList))}")

        image = Image.frombytes('RGBA', (self.pwidth, self.pheight), bytes(cList), 'raw', 'RGBA')
        image.save(path, "PNG")



if __name__ == '__main__':
    with open("tests/T00.BIN", "rb") as f:
        f.seek(0, os.SEEK_END)
        fileSize = f.tell()
        print(f"Reading file of {fileSize} bytes")
        f.seek(0, os.SEEK_SET)
