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
        firstLength = U.readByte(file) * 4096
        print(f"Initial length {firstLength}")
        unkn1 = U.readByte(file) # Could be 64 = odd sizes
        print(f"Unknown1: {unkn1}")
        unkn2 = U.readByte(file)

        nullPad = U.readLong(file)
        unkn3 = U.readShort(file)
        
        #This block is old block
        # # byte 0x44(68) seems to hold height directly, but would not be enough for 640
        # # Height also spills into next byte when 640 but second byte is uselss for rest?
        # file.seek(offset+0x44, os.SEEK_SET)
        # height = U.readByte(file)
        # print(f"Initial Height: {height}")
        # if height == 0:
        #     print("file has no height at 0x44")

        # # byte 0x35(53) might hold the width/2 for some files, may depend on the 0xX6 bit of the header
        # # or the byte proceeding it, 
        # # NOT TRUE this is probably a lookup table or dependent on value not the value
        # file.seek(offset+0x35, os.SEEK_SET)
        # widthF = U.readByte(file) * 2        #(int) (length/height)       #= 
        # print(f"Initial Width: {widthF}")
        # if widthF == 0:
        #     print("file has no width at 0x35")
        # width = widthF
        # # 0x40(64) seems to be width ?
        # file.seek(offset+0x40, os.SEEK_SET)
        # width2 = U.readByte(file)
        # print(f"Second width: {width2}")
        # if width2 == 0:
        #     print("file has no width at 0x40")
        # if widthF < width2:
        #     print(f"0x40 width {width2} different from 0x35 width {widthF}")
        #     if width2 != 0:
        #         width = width2
        # print(f"Set Width: {width}")
        # print(f"Set Height: {height}")
        #This block is old block

        if typeF == 0 or typeF == 128:
            # Usual file format?
            pass
        
        file.seek(offset+0x35, os.SEEK_SET)
        sizeTable = U.readByte(file)

        if typeF == 64:
            # File might not be usual size
            sizeTable = 0


        print(f"Sizetable is {sizeTable}")

        if sizeTable == 0:
            print("could mean 16x16 or anything?, will attempt to guess")

        if sizeTable == 8:
            print("assuming texture is 32x64")
            width = 32
            height = 64
        elif sizeTable == 16:
            print("assuming texture is 64x64")
            width = 64
            height = 64
        elif sizeTable == 32:
            print("assuming texture is 64x128")
            width = 64
            height = 128
            # Some of these are actually 128x64 so perhaps there is a flag to swap them?
        elif sizeTable == 64:
            print("assuming texture is 128x128")
            width = 128
            height = 128
        elif sizeTable == 192:
            print("assuming texture is 640x384")
            width = 640
            height = 384
        else:
            print("Did not determine width/height by means above (see code)")
            file.seek(offset+0x44, os.SEEK_SET)
            height = U.readByte(file)
            file.seek(offset+0x35, os.SEEK_SET)
            width = U.readByte(file) * 2

            
            if typeF == 64:
                width = width * 2
            elif firstLength != 0 and width * height != firstLength:
                width = (int) (firstLength / height)
            if width == 0:
                file.seek(offset+0x40, os.SEEK_SET)
                width = U.readByte(file)
        
        if typeF == 16:
            width = 16
            height = 16

        if typeF == 32:
            print(f"{width}x{height}")
            #height = (int)(height / 2 )
            

        # typeF could be bit depth?
        # 0  = 8bpp
        # 32 = 4bpp
        # 64 = 4bypp
        # 128 = ?
        bpp = 8
        #if typeF == 32:
        #    print("File is 4 bpp")
        #    bpp = 4
        #    width = width * 2
        
        # #This block is part of old block
        # # byte 0x61(97) holds the length/4096, but is (so far) the same as byte 0x1(1)
        # # This may be a fall back or, allocation size for 0x1, and read length for 0x61 (same for now)
        # file.seek(offset+0x61, os.SEEK_SET)
        # length = U.readByte(file) * 4096 # Smallest texture might be 64x64 hence 4096 or in 4k chunks?
        # if firstLength != length:
        #     print(f"FirstTexLen({firstLength}) vs {length}")
        #     length = firstLength
        
        # if width * height != length:
        #     if width == width2 or width == widthF:
        #         # Then adjust height
        #         print(f"Adjusted height")
        #         height = (int) (length / width)
        #     else:
        #         # Adjust width
        #         print(f"Adjusted width")
        #         width = (int)(length / height)
        # #This block is part of old block
        # #try:
        # #    width = (int)(length / height)
        # #    print(f"calculated width as {width} from {height}/{length}")
        # #except:
        # #    width = 128
        # #    height = 128
        # #    length = width * height
        #This block is part of old block

        # Some files have multiple palettes!!
        # After first palette there is 02 00 87 70 
        # and sometimes this is followed by 00s
        # But the header of 02 00 87 70 is only short, maybe 48 bytes
        # 

        length = width * height


        # Skip to past header
        file.seek(offset+0x70, os.SEEK_SET)
        print(f"Texture size: {width}x{height}px {length}bytes")

        return width, height, length, bpp
    
    @staticmethod
    def _parsePaletteHeader(file, offset):
        # Skip header all values have unknown use atm
        #file.seek(112, os.SEEK_CUR)
        #header = file.read(112)
        
        fB = U.readByte(file) #  Often 0xX6 where x could be something
        
        # So far all palettes have been nonlinear but need to find
        # if all files are non Linear before ruling out option
        isNonLinear = True
        
        # This is old block
        # colourSize = (fB & 0xF0) >> 4
        # if colourSize == 0:
        #     print(f"ColourSize = {colourSize} perhaps should be {fB - 6}")
        #     if fB - 6 == 8 or fB - 6 == 16:
        #         colourSize = fB - 6
        #     if colourSize <= 0:
        #         print(f"ColourSize is unknown @ fB:{fB}")

        # thisPaletteSize = 256
        # psize = 16,16
        # numberOfPalettes = 1

        # # If ARGB 1555 then:
        # if colourSize == 2:
        #     thisPaletteSize = 16
        #     psize = 4,4
        #     isNonLinear = False
        # This is old block



        thisPaletteSize = 256
        psize = 16,16
        # This is unknown, for now:
        numberOfPalettes = 1
        isNonLinear = False

        colourSize = fB - 6
        headerByteSize = 112 #  Usual header size

        if colourSize == 64:
            # ARGB 888 format
            thisPaletteSize = 256
            psize = 16,16
            numberOfPalettes = 1
            isNonLinear = True
            pass
        elif colourSize == 32:
            # BGRA 5551 format
            thisPaletteSize = 16
            psize = 4,4
            numberOfPalettes = 1
            isNonLinear = True
            pass
        elif colourSize == 16:
            print(f"found a palette that is of type 16 @ {file.tell()} stopping")
            exit(1)
            pass
        elif colourSize == 8:
            # 128 bytes, format unknown
            print("Decoding as small 5551 file")
            # Override colour size for now
            colourSize = 32 
            thisPaletteSize = 64
            psize = 8,8
            numberOfPalettes = 1
            isNonLinear = True
        elif colourSize == -4:
            # Header is 02 00 87 70 and is only 48 bytes long?
            # or        02 00 40 70
            # no idea what this is, unless its an extra palette, or lighting info
            # so going to skip
            colourSize = 64
            psize = 32,32
            thisPaletteSize = 1028 # This is just a guess, just to move to next
            numberOfPalettes = 1
            isNonLinear = True
            headerByteSize = 48



        nullB = U.readByte(file)

        #print(f"numC{thisPaletteSize} fp:{file.tell()}")
        # Assumed, as no information on the palette header yet
        
        
        
        
        print(f"Palette size: {psize[0]}x{psize[1]}px colourSize: {colourSize} numColours: {thisPaletteSize}")

        
        file.seek(offset+headerByteSize, os.SEEK_SET)
        return isNonLinear, colourSize, thisPaletteSize, numberOfPalettes, psize

    def _paletteFromFile(file, length, offset, fixAlpha=True):
        isNonLinear, colourSize, thisPaletteSize, numberOfPalettes, psize = Texture._parsePaletteHeader(file, offset)

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
        return colours, psize

    @staticmethod
    def _readTexture(file, length, bpp=8):
        texture = 0
        if bpp == 8:
            texture = file.read(length)
        elif bpp == 4:
            textData = []
            for i in range(0, length):
                b = file.read(length)

                texData.append(b & 0xF)
                texData.append((b >> 4) & 0xF)
            texture = bytes(texData)
        return texture

    @staticmethod
    def _fromFile(file, offset, fixAlpha=True):
        file.seek(offset, os.SEEK_SET)
        width, height, length, bpp = Texture._parseTextureHeader(file, offset)
        headerLength = 0x70

        # Read texture data in
        texture = Texture._readTexture(file, length, bpp)


        colours, psize = Texture._paletteFromFile(file, length, offset + length + headerLength, fixAlpha)
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
        print(f"paletteLen = {len(cList)} should be {self.pwidth},{self.pheight} {len(self.palette)} len {len(bytes(cList))}")

        image = Image.frombytes('RGBA', (self.pwidth, self.pheight), bytes(cList), 'raw', 'RGBA')
        image.save(path, "PNG")



if __name__ == '__main__':
    with open("tests/T00.BIN", "rb") as f:
        f.seek(0, os.SEEK_END)
        fileSize = f.tell()
        print(f"Reading file of {fileSize} bytes")
        f.seek(0, os.SEEK_SET)
