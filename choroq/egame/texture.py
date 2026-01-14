import io
import os
import choroq.egame.read_utils as U
import choroq.egame.ps2_utils as PS2
from PIL import Image, ImagePalette, ImageOps


class Texture:

    cc58 = [0x00,0x08,0x10,0x19, 0x21,0x29,0x31,0x3a, 0x42,0x4a,0x52,0x5a, 0x63,0x6b,0x73,0x7b,
            0x84,0x8c,0x94,0x9c, 0xa5,0xad,0xb5,0xbd, 0xc5,0xce,0xd6,0xde, 0xe6,0xef,0xf7,0xff]

    cc68 = [0x00,0x04,0x08,0x0c, 0x10,0x14,0x18,0x1c, 0x20,0x24,0x28,0x2d, 0x31,0x35,0x39,0x3d,
            0x41,0x45,0x49,0x4d, 0x51,0x55,0x59,0x5d, 0x61,0x65,0x69,0x6d, 0x71,0x75,0x79,0x7d,
            0x82,0x86,0x8a,0x8e, 0x92,0x96,0x9a,0x9e, 0xa2,0xa6,0xaa,0xae, 0xb2,0xb6,0xba,0xbe,
            0xc2,0xc6,0xca,0xce, 0xd2,0xd7,0xdb,0xdf, 0xe3,0xe7,0xeb,0xef, 0xf3,0xf7,0xfb,0xff]

    def __init__(self, texture=None, palette=None, size=(0, 0), palette_size=(0, 0), bpp=24, unswizzled=bytes(), fix_alpha=True):
        if texture is None:
            texture = []
        if palette is None:
            palette = []
        self.width = size[0]
        self.height = size[1]
        self.palette_width = palette_size[0]
        self.palette_height = palette_size[1]
        self.texture = texture
        self.palette = palette
        self.fixAlpha = fix_alpha
        self.unswizzled = unswizzled
        self.bpp = bpp

    @staticmethod
    def all_from_file(file, offset):
        textures = []
        texture, last = Texture.read_texture(file, offset)
        textures.append(texture)
        while not last:
            texture, last = Texture.read_texture(file, file.tell())
            textures.append(texture)
        return textures

    @staticmethod
    def read_texture(file, offset):
        gs_state = PS2.GsState()
        file.seek(offset, os.SEEK_SET)
        # Follows this pattern:
        # 1 DMA tag
        #  - GIF tag
        #  - GIF tag

        texture = (0, None)

        dma_start = file.tell()
        dma_tag = PS2.decode_DMATag(file)

        tag_id = PS2.decode_DMATagID_source(dma_tag)
        print(dma_tag)
        print(tag_id)
        chunk_byte_length = dma_tag['qwordCount'] * 16 + 16

        # if dma_tag["tag_id"] == 7:
        #     return {}
        # elif tag_id["tag_end"]:
        #     return {}

        data_count = 0
        while file.tell() < dma_start + chunk_byte_length:
            print(f"Data [{data_count}]: @ {file.tell()} out of {dma_start + chunk_byte_length}")
            # Read GIF
            gif_tag = int.from_bytes(file.read(16), 'little')

            nloop = PS2.gifGetNLoop(gif_tag)
            eop = PS2.gifGetEop(gif_tag)
            pre = PS2.gifGetPrimEnable(gif_tag)
            prim = PS2.gifGetPrim(gif_tag)
            mode = PS2.gifGetMode(gif_tag)
            nreg = PS2.gifGetNReg(gif_tag)
            descriptors = PS2.gifGetRegisterDescriptors(gif_tag)
            print(descriptors)

            registers = None
            if mode == PS2.GIF_MODE_PACKED:
                registers = []
                for i in range(0, 16):
                    registers.append(PS2.gifDecodePacked(descriptors[i]))
                print(registers)

                for loop in range(nloop):
                    for reg in range(nreg):
                        print(f"GsState change packet loop [{loop}] reg [{reg}]")
                        PS2.gifHandlePacked(file, gif_tag, reg, descriptors[reg], gs_state)
                change = False

            elif mode == PS2.GIF_MODE_REGLIST:
                print("RegList not implemented")
                exit(101)
            elif mode == PS2.GIF_MODE_IMAGE:
                destination = gs_state.BITBLTBUF["DBP"]  # Think this will be used by meshes to address the texture
                width = gs_state.TRXREG["RRW"]
                height = gs_state.TRXREG["RRH"]
                if gs_state.TRXPOS["DSAX"] != 0 or gs_state.TRXPOS["DSAY"] != 0:
                    # This texture's address is actually + some amount
                    # This must be handled by the next layer, as it does not have
                    # a way to append the data, so return different format
                    if gs_state.TRXPOS["DIR"] != 0:
                        # Only tested == 0 other values change how SAX and DSAX
                        exit(105)
                    destination = destination, (gs_state.TRXPOS['DSAX'] * width + gs_state.TRXPOS['DSAY']) >> 4

                image_type = gs_state.BITBLTBUF["DPSM"]
                length = nloop * 16
                in_bpp = PS2.gifPsmToBitsPP[gs_state.BITBLTBUF["SPSM"]]
                dest_bpp = PS2.gifPsmToBitsPP[gs_state.BITBLTBUF["DPSM"]]
                # So with others being right calculate it
                bpp = int((length / width / height) * 8)
                print(f"BPP should be {in_bpp} but is {bpp} dest_bpp {dest_bpp} using dest")
                bpp = dest_bpp

                print(
                    f"Parsing texture {width}x{height} {image_type} len({length}) bpp {bpp} -> {destination} from @ {file.tell()}")
                # print(vars(gs_state))
                # exit()

                texture, unswizzled = Texture._read_texture(file, length, bpp)
                print(file.tell())
                # print(texture)
                # if bpp <= 8:
                #     colours, psize = Texture._paletteFromFile(file, offset + length + headerLength, fixAlpha)
                # else:
                #     # No palette
                #     psize = (0, 0)
                #     colours = None
                texture = Texture(texture, None, (width, height), (0, 0), bpp, unswizzled)
                texture = (destination, texture)

                # gs_state.BITBLTBUF[]
                # gs_state.BITBLTBUF["SBP"]
                # gs_state.BITBLTBUF["SBW"]
                # gs_state.BITBLTBUF["SPSM"]
                # gs_state.BITBLTBUF["DBP"]
                # gs_state.BITBLTBUF["DBW"]
                # gs_state.BITBLTBUF["DPSM"]

                # gs_state.TRXPOS["SSAX"]
                # gs_state.TRXPOS["SSAY"]
                # gs_state.TRXPOS["DSAX"]
                # gs_state.TRXPOS["DSAY"]
                # gs_state.TRXPOS["DIR"]

                # gs_state.TRXDIR["XDIR"]

            else:
                print("GIF issue mode?")
                exit(103)

            print(registers)

        return texture, tag_id["tag_end"]

    @staticmethod
    def save_material_file_obj(fout, name, texture_path):
        fout.write(f"newmtl {name}\n")
        fout.write("Ka 1.000 1.000 1.000\n")  # ambient colour
        fout.write("Kd 1.000 1.000 1.000\n")  # diffused colour
        fout.write("Ks 0.000 0.000 0.000\n")  # Specular colour
        # fout.write("Ns 100") # specular exponent
        fout.write("d 1.0\n")
        fout.write(f"map_Ka {texture_path}\n")  # Path to ambient texture (relative)
        # the diffuse texture map (most of the time, it will be the same
        fout.write(f"map_Kd {texture_path}\n")  # Path to diffuse texture (relative)
        fout.write("\n")

    @staticmethod
    # Used for fixing clut when it has been parsed as a texture
    def unswizzle_bytes(texture):
        palette = texture.texture
        size = texture.width * texture.height
        bpp = texture.bpp

        if bpp == 16:
            colours = []


        # # if isinstance(palette, bytes): 
        # #     if size * 4 == len(palette):
        # #         # Convert into list of colours from bytes
        # print(f"Unswizzling {bpp} {palette}")
        # colours = []
        # if bpp == 32 or bpp == 24:
        #     for i in range(size):
        #         print(i)
        #         cr = palette[i * 4]
        #         cg = palette[i * 4 + 1]
        #         cb = palette[i * 4 + 2]
        #         ca = palette[i * 4 + 3]
        #         colours.append((int(cr), int(cg), int(cb), int(ca)))
        #     palette = colours
        # else:
        #     return palette
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
                        color = (0,0,0,0)
                        if bpp == 32:
                            color = (palette[rawInd * 4], palette[rawInd * 4 + 1], palette[rawInd * 4 + 2], palette[rawInd * 4+ 3])
                        elif bpp == 24:
                            color = (palette[rawInd * 3], palette[rawInd * 3 + 1], palette[rawInd * 3 + 2], 255)
                        elif bpp == 16:
                            color = (palette[rawInd * 4], palette[rawInd * 4 + 1], palette[rawInd * 4 + 2], palette[rawInd * 4 + 3])
                        # If the BPP is 8 or 4 then this is probably not a palette
                        # elif bpp == 4:
                        #     color = (palette[rawInd], palette[rawInd], palette[rawInd], palette[rawInd])
                        #     pass
                        else:
                            print("Probably not a palette as its B&W")
                            # color = palette[rawInd]
                        colours.append(color)
                        paletteIndex += 1
        return colours

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
    def _read_texture(file, length, bpp=8):
        texture = 0
        # read colours in
        if bpp == 32:
            # 32BBP ARGB
            texture = []
            for i in range(0, int(length / 4)):
                cr = U.readByte(file)
                cg = U.readByte(file)
                cb = U.readByte(file)
                ca = U.readByte(file)
                # Corrects transparency
                if ca == 0x80:
                    ca = 255
                # texture.append([cr, cg, cb, ca])
                texture.append(cr)
                texture.append(cg)
                texture.append(cb)
                texture.append(ca)
            # Unswizzle all, incase they are palettes, not found a better way yet
            if len(texture) != 0:
                unswizzled = bytes(Texture._unswizzle(texture, length))
            texture = bytes(texture)
            
        elif bpp == 24:
            print("Reading 24 bit image")
            # 24BPP RGB
            texture = []
            for i in range(0, int(length / 3)):
                cr = U.readByte(file)
                cg = U.readByte(file)
                cb = U.readByte(file)
                # texture.append([cr, cg, cb, 255])
                texture.append(cr)
                texture.append(cg)
                texture.append(cb)
                # Don't append A, as when we convert/save it will add A itself as 255 
            # Unswizzle all, incase they are palettes, not found a better way yet
            if len(texture) != 0:
                unswizzled = bytes(Texture._unswizzle(texture, length))
            texture = bytes(texture)
        elif bpp == 16:
            print("Reading 16 bit image (5551)")
            texture = []
            #16BIT Little Endian RGBA 5551 format
            for i in range(0, int(length / 2)):
                c = U.readShort(file)
                hex = f"{c:02X}"
                
                # cr = c & 0x1f
                # c = c >> 5
                # cg = c & 0x1f
                # c = c >> 5
                # cb = c & 0x1f
                # c = c >> 5
                # ca = 255 - 127 * c
                # texture.append(Texture.cc58[cr])
                # texture.append(Texture.cc58[cg])
                # texture.append(Texture.cc58[cb])
                # texture.append(ca)
                cr = (c & 0b11111) << 3
                cg = ((c >> 5) & 0b11111) << 3
                cb = ((c >> 10) & 0b11111) << 3
                ca = (1-((c >> 15) & 1)) * 255
                texture.append(cr)
                texture.append(cg)
                texture.append(cb)
                texture.append(ca)

            if len(texture) != 0:
                unswizzled = bytes(Texture._unswizzle(texture, length))
            # unswizzled = bytes(texture)
            texture = bytes(texture)
            #rawPalette.reverse()
            #isNonLinear = True
        # elif colourSize == 8:
        #     # This is not perfect
        #     # 32BBP RGBA
        #     for i in range(0, thisPaletteSize):
        #         cr = U.readByte(file)
        #         cg = U.readByte(file)
        #         cb = U.readByte(file)
        #         ca = U.readByte(file)
        #         if fix_alpha and ca == 0x80:
        #             ca = 255
        #         if fix_alpha and ca <= 0x80:
        #             ca = (ca + 0xF0) & 0xFF
        #         rawPalette.append([cr, cg, cb, ca])
            # isNonLinear = False
            # rawData = Texture._unswizzle(rawData, thisPaletteSize)
        # if bpp == 32:
        #     texture = U.read(file, length)
        # elif bpp == 24:
        #     texture = U.read(file, length)
        elif bpp == 8:
            texture = U.read(file, length)
            if len(texture) != 0:
                unswizzled = bytes(Texture._unswizzle(texture, length))
        elif bpp == 4:
            tex_data = []
            for i in range(0, int(length)):
                b = U.readByte(file)

                tex_data.append(b & 0xF)
                tex_data.append((b >> 4) & 0xF)
            if len(tex_data) != 0:
                unswizzled = bytes(Texture._unswizzle(tex_data, length))
            texture = bytes(tex_data)
        else:
            print(f"Failed to parse as BPP different {bpp}")
            exit()
        return texture, unswizzled

    def get_texture_as_bytes(self, flip_x=False, flip_y=False, usepalette=True):
        colour_list = []
        if self.palette_width == 0 and self.palette_height == 0: # bpp > 8
            image = Image.frombytes('RGB', (self.width, self.height), self.texture, 'raw')
            return bytes(image.tobytes())
        else:
            if type(self.palette) is bytes:
                if usepalette:
                    image = Image.frombytes('P', (self.width, self.height), self.texture, 'raw', 'P')
                    palette = ImagePalette.raw("RGBA", self.palette)
                    palette.mode = "RGBA"
                    image.palette = palette
                else:
                    image = Image.frombytes('L', (self.width, self.height), self.texture, 'raw')
            else:
                # Convert (R,G,B,A) TO [..., R,G,B,A,...]
                for colour in self.palette:
                    colour_list.append(colour[0])
                    colour_list.append(colour[1])
                    colour_list.append(colour[2])
                    colour_list.append(colour[3])
                if usepalette:
                    image = Image.frombytes('P', (self.width, self.height), self.texture, 'raw', 'P')
                    palette = ImagePalette.raw("RGBA", bytes(colour_list))
                    palette.mode = "RGBA"
                    image.palette = palette
                else:
                    image = Image.frombytes('L', (self.width, self.height), self.texture, 'raw')

            rgbd = image.convert("RGBA")
            if flip_x:
                rgbd = ImageOps.mirror(rgbd)
            if flip_y:
                rgbd = ImageOps.flip(rgbd)

            return rgbd.tobytes()

    def write_texture_to_png(self, path, flip_x=False, flip_y=False, use_palette=True, use_given_palette=False):
        colour_list = []
        # Use the palette stored in use_given_palette if set
        palette_width = self.palette_width
        palette_height = self.palette_height
        if use_given_palette != False:
            palette_width = use_given_palette.width
            palette_height = use_given_palette.height
            
        if palette_width == 0 and palette_height == 0:
            print("Not using a palette no palette")
            if self.bpp == 32 or self.bpp == 16:
                image = Image.frombytes('RGBA', (self.width, self.height), self.texture, 'raw')
            elif self.bpp == 24: 
                image = Image.frombytes('RGB', (self.width, self.height), self.texture, 'raw')
                image.convert("RGBA").save(path, "PNG")
            elif self.bpp == 4 or self.bpp == 8:
                image = Image.frombytes('L', (self.width, self.height), self.texture, 'raw')
                image.convert("RGBA").save(path, "PNG")
            else:
                print(f"BAD BPP value {self.bpp}")
                exit()
        else:
            if use_given_palette != False:
                print("Using given palette")
                image = Image.frombytes('P', (self.width, self.height), self.texture, 'raw', 'P')
                palette = ImagePalette.raw("RGBA", Texture.unswizzle_bytes(use_given_palette))
                palette.mode = "RGBA"
                image.palette = palette
            else:
                print("Using palette from texture")
                # Convert (R,G,B,A) TO [..., R,G,B,A,...]
                for colour in self.palette:
                    colour_list.append(colour[0])
                    colour_list.append(colour[1])
                    colour_list.append(colour[2])
                    colour_list.append(colour[3])
                if use_palette:
                    image = Image.frombytes('P', (self.width, self.height), self.texture, 'raw', 'P')
                    palette = ImagePalette.raw("RGBA", bytes(colour_list))
                    palette.mode = "RGBA"
                    image.palette = palette
                else:
                    image = Image.frombytes('L', (self.width, self.height), self.texture, 'raw')
        print("Doing conversion")
        rgbd = image.convert("RGBA")
        if flip_x:
            rgbd = ImageOps.mirror(rgbd)
        if flip_y:
            rgbd = ImageOps.flip(rgbd)
        rgbd.save(path, "PNG")
        print("Saved")

    def write_palette_to_png(self, path):
        colour_list = []
        # Convert (R,G,B,A) TO [..., R,G,B,A,...]
        for colour in self.palette:
            colour_list.append(colour[0])
            colour_list.append(colour[1])
            colour_list.append(colour[2])
            colour_list.append(colour[3])
        
        if self.palette_width * self.palette_height != len(self.palette):
            print(f"paletteLen = {len(colour_list)} should be {self.palette_width},{self.palette_height} {len(self.palette)} len {len(bytes(colour_list))}")

        image = Image.frombytes('RGBA', (self.palette_width, self.palette_height), bytes(colour_list), 'raw', 'RGBA')
        image.save(path, "PNG")
