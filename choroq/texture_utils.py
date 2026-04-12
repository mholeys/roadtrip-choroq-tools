from enum import Enum

from PIL import Image

class TextureUtil:

    # Used to reference which type of texture to create
    class PSM(Enum):
        PSMCT32 = 0b000000,
        PSMCT24 = 0b000001,
        PSMCT16 = 0b000010,
        PSMCT16S = 0b001010,
        PSMT8 = 0b010011,
        PSMT4 = 0b010100,
        PSMT8H = 0b011011,
        PSMT4HL = 0b100100,
        PSMT4HH = 0b101100,
        PSMZ32 = 0b110000,
        PSMZ24 = 0b110001,
        PSMZ16 = 0b110010,
        PSMZ16S = 0b111010,

    @staticmethod
    def unswizzle(palette, size):
        colours = []
        numParts = (int)(size / 32)
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
    def split_image(image):
        indexed_texture = image.convert('P', dither=Image.Dither.NONE, palette=Image.Palette.ADAPTIVE, colors=256)
        palette_image = indexed_texture.getpalette('RGBA')

        # Convert any alpha values into the required system
        # and build palette of colours
        palette = []
        for i in range(0, len(palette_image) >> 2):
            r, g, b, alpha = palette_image[i * 4: i * 4 + 4]

            # I think there is a rounding issue, between 254, and 255 so this fixes problems with this
            if alpha == 254:
                alpha = 255
            if alpha == 255:
                alpha = 0x80

            # It seems HG2's palette alpha is not just simple values, might have a map

            #if alpha != 0 and alpha != 255 and alpha != 0x80:
            #    alpha = 0
            #alpha = 100

            # if alpha < 255:
            #     # pixel = x + y * alpha_channel.width
            #     alpha = 0
            # else:
            #     alpha = 128
            palette.append((r, g, b, alpha))

        # convert palette to bytes
        swizzled = TextureUtil.unswizzle(palette, 256)
        palette_bytes = bytes()
        for i in range(0, len(palette_image) >> 2):
            palette_bytes += swizzled[i][0].to_bytes(1, 'little', signed=False)
            palette_bytes += swizzled[i][1].to_bytes(1, 'little', signed=False)
            palette_bytes += swizzled[i][2].to_bytes(1, 'little', signed=False)
            palette_bytes += swizzled[i][3].to_bytes(1, 'little', signed=False)

        # Save image
        texture = indexed_texture.convert('L')
        print(indexed_texture.getpixel((0, 0)))
        print(texture.getpixel((0, 0)))
        #texture.save(test_image_out, "PNG")

        return indexed_texture.tobytes(), palette_bytes