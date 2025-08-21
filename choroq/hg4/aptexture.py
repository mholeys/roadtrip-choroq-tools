import os
from PIL import Image, ImagePalette, ImageOps
import choroq.read_utils as U


class APTexture:

    def __init__(self, name, val_a, val_b, total_size):
        self.name = name
        self.val_a = val_a
        self.height = val_b
        self.total_size = total_size

        self.width = 0
        self.height = 0
        self.data = None
        self.colour_format = 0

        self.palette_size = 0
        self.palette = None

    def set_palette(self, data, palette_size=-1):
        if palette_size != -1:
            self.palette_size = palette_size
        self.palette = data

    def set_data(self, width, height, data, colour_format):
        self.width = width
        self.height = height
        self.data = data
        self.colour_format = colour_format

    def write_texture_to_png(self, path, flip_x=False, flip_y=False, use_palette=True):
        colour_list = []

        if self.palette_size == 0:
            print("Not using a palette, no palette")
            if self.colour_format == 32 or self.colour_format == 16:
                image = Image.frombytes('RGBA', (self.width, self.height), self.data, 'raw')
            elif self.colour_format == 24:
                image = Image.frombytes('RGB', (self.width, self.height), self.data, 'raw')
                image.convert("RGBA").save(path, "PNG")
            elif self.colour_format == 4 or self.colour_format == 8:
                image = Image.frombytes('L', (self.width, self.height), self.data, 'raw')
                image.convert("RGBA").save(path, "PNG")
            else:
                print(f"BAD BPP value {self.colour_format}")
                exit()
        else:
            print("Using palette from texture")
            # Convert (R,G,B,A) TO [..., R,G,B,A,...]
            for colour in self.palette:
                colour_list.append(colour[0])
                colour_list.append(colour[1])
                colour_list.append(colour[2])
                colour_list.append(colour[3])
            if use_palette:
                image = Image.frombytes('P', (self.width, self.height), self.data, 'raw', 'P')
                palette = ImagePalette.raw("RGBA", bytes(colour_list))
                palette.mode = "RGBA"
                image.palette = palette
            else:
                image = Image.frombytes('L', (self.width, self.height), self.data, 'raw')
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

        if self.palette_size != len(self.palette):
            print(
                f"paletteLen = {len(colour_list)} should be {self.palette_size} {len(self.palette)} len {len(bytes(colour_list))}")

        image = Image.frombytes('RGBA', (4, int(self.palette_size / 4)), bytes(colour_list), 'raw', 'RGBA')
        image.save(path, "PNG")



    @staticmethod
    def read_apt(file, offset):
        file.seek(offset, os.SEEK_SET)
        # Read header
        magic = file.read(4)
        texture_count = U.readLong(file)
        unknown1 = U.readLong(file)  # Might be first texture size in bytes
        unknown2 = U.readLong(file)

        if magic != b"APT\0":
            print("No textures, incompatible file")
            return None

        print(f"U1: {unknown1}  U2: {unknown2}")

        # List of files start
        textures = []
        for i in range(texture_count):
            print(file.tell())
            val_a = U.readLong(file)
            val_b = U.readLong(file)
            size = U.readLong(file)  # Think this is the total size of the texture descriptor+palette+data
            zeros = U.readLong(file)
            texture_name = file.read(16).decode("ascii").rstrip('\00')  # \0 terminated string, max 16 bytes
            print(f"Texture header: {texture_name}, {val_a}, {val_b}, {size}, {zeros:x}")
            if zeros != 0:
                print("Found non zero value in texture table data")
            textures.append(APTexture(texture_name, val_a, val_b, size))

        # After the header table, the texture data starts
        for i in range(texture_count):
            print(f"pos: {file.tell()} t: {i}")
            # Read texture descriptor
            width = U.readLong(file)
            height = U.readLong(file)
            colour_format = U.readLong(file)  # Might just be bytes per pixel (of texture, not palette)
            palette_size = U.readLong(file)  # Number of colours in palette

            print(f"{width:x} {height:x} {colour_format:x} {palette_size:x}")

            # Read palette in
            palette = []
            for c in range(palette_size):
                r = U.readByte(file)
                g = U.readByte(file)
                b = U.readByte(file)
                a = U.readByte(file)
                palette.append((r, g, b, a))
            # palette = file.read(palette_size * 4)
            print(f"pos: {file.tell()} t: {i}")

            texture_data = []
            # Read texture in
            for c in range(int(width * height * (colour_format/8))):
                if colour_format == 4:
                    val = U.readByte(file)
                    i1 = val & 0xF
                    i2 = (val >> 4) & 0xF
                    texture_data.append(i1)
                    texture_data.append(i2)
                elif colour_format == 8:
                    val = U.readByte(file)
                    texture_data.append(val)
                else:
                    print(f"new colour format found @ {file.tell()} value is: {colour_format}")
                    exit(99)

            texture_data = bytes(texture_data)

            textures[i].set_data(width, height, texture_data, colour_format)
            textures[i].set_palette(palette, palette_size)

        return textures

