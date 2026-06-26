import os
from PIL import Image, ImagePalette, ImageOps
import choroq.read_utils as U
from choroq.egame.texture import Texture


class APTexture:
    STOP_ON_NEW = True
    PRINT_DEBUG = False

    def __init__(self, name, val_a, val_b, total_size, offset, extension=None):
        # Position of the definition (header under APT)
        self.offset = offset
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

        self.extension = extension

        # Position where texture data starts
        self.data_offset = 0

        # this should probably be split into a subclass
        self.rct = None

    def set_palette(self, data, palette_size=-1):
        if palette_size != -1:
            self.palette_size = palette_size
        # Unswizzle
        if palette_size > 16:
            self.palette = Texture._unswizzle(data, palette_size)
        else:
            self.palette = data

    def set_data(self, width, height, data, colour_format):
        self.width = width
        self.height = height
        self.data = data
        self.colour_format = colour_format

    def write_texture_to_png(self, path, flip_x=False, flip_y=False, use_palette=True):
        if self.data == [] or self.data is None:
            print("Skipping write, as texture has no data")
            return
        colour_list = []
        image = None

        if self.palette_size == 0:
            try:
                if APTexture.PRINT_DEBUG:
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
            except Exception as e:
                print(e)
                return
        else:
            if APTexture.PRINT_DEBUG:
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
        if APTexture.PRINT_DEBUG:
            print("Doing conversion")
        if use_palette:
            rgbd = image.convert("RGBA")
            if flip_x:
                rgbd = ImageOps.mirror(rgbd)
            if flip_y:
                rgbd = ImageOps.flip(rgbd)
            rgbd.save(path, "PNG")
        else:
            if flip_x:
                image = ImageOps.mirror(image)
            if flip_y:
                image = ImageOps.flip(image)
            image.save(path, "PNG")
        if APTexture.PRINT_DEBUG:
            print("Saved")

    def write_palette_to_ms_PAL(self, path):
        if self.palette == [] or self.palette is None:
            return

        with open(path, "wb") as fout:
            # Write PAL header
            fout.write("RIFF".encode("ascii"))
            expected_file_size = 24 + len(self.palette) * 4
            fout.write((expected_file_size - 8).to_bytes(4, 'little'))
            fout.write("PAL data".encode("ascii"))
            fout.write((expected_file_size - 20).to_bytes(4, 'little'))
            fout.write((0).to_bytes(1, 'little'))
            fout.write((3).to_bytes(1, 'little'))
            fout.write(len(self.palette).to_bytes(2, 'little'))
            for r, g, b, a in self.palette:
                fout.write(r.to_bytes(1, 'little'))
                fout.write(g.to_bytes(1, 'little'))
                fout.write(b.to_bytes(1, 'little'))
                # fout.write(a.to_bytes(1, 'little'))
                fout.write(b'\x00')

    def write_palette_to_png(self, path):
        if self.palette == [] or self.palette is None:
            return
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

    def get_image(self, use_palette=True):
        if self.rct is not None:
            return self.rct
        if self.data == [] or self.data is None:
            print("Texture has no data")
            return None
        colour_list = []
        image = None

        if self.palette_size == 0:
            try:
                if APTexture.PRINT_DEBUG:
                    print("Not using a palette, no palette")
                if self.colour_format == 32 or self.colour_format == 16:
                    image = Image.frombytes('RGBA', (self.width, self.height), self.data, 'raw')
                elif self.colour_format == 24:
                    image = Image.frombytes('RGB', (self.width, self.height), self.data, 'raw')
                    return image.convert("RGBA")
                elif self.colour_format == 4 or self.colour_format == 8:
                    image = Image.frombytes('L', (self.width, self.height), self.data, 'raw')
                    return image.convert("RGBA")
                else:
                    print(f"BAD BPP value {self.colour_format}")
                    exit()
            except Exception as e:
                print(e)
                return None
        else:
            if APTexture.PRINT_DEBUG:
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
        if APTexture.PRINT_DEBUG:
            print("Doing conversion")
        if use_palette:
            rgbd = image.convert("RGBA")
            return rgbd
        else:
            return image


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
        if APTexture.PRINT_DEBUG:
            print(f"U1: {unknown1}  U2: {unknown2}")

        # List of files start
        textures = []
        for i in range(texture_count):
            if APTexture.PRINT_DEBUG:
                print(file.tell())
            texture_offset = file.tell()
            val_a = U.readLong(file)
            val_b = U.readLong(file)
            size = U.readLong(file)  # Think this is the total size of the texture descriptor+palette+data
            zeros = U.readLong(file)
            texture_name = file.read(16)  # \0 terminated string, max 16 bytes
            try:
                first_0 = texture_name.index(0)
                texture_name = texture_name[0:first_0].decode("ascii").rstrip('\00')
            except Exception as e1:
                # Possible JP character in name, cannot really handle nicely, without custom d/encoding
                print(f"{texture_name} failed to convert to ascii")
                end_letter = 1
                for li in range(len(texture_name)):
                    if texture_name[li] > 0x7F:
                        end_letter = li-1
                try:
                    texture_name = texture_name[0:end_letter].decode("ascii").rstrip('\00')
                except Exception as e2:
                    print("Cannot parse name, other error occurred")
                    raise e2
            if texture_name == "RCT":
                # Decode? bits of RCT
                file.seek(-12, os.SEEK_CUR)
                rct_start_x = U.readShort(file)
                rct_start_y = U.readShort(file)
                rct_width = U.readShort(file)
                rct_height = U.readShort(file)
                rct_4 = U.readShort(file)
                rct_5 = U.readShort(file)
                print(f"RCT texture: start: {rct_start_x}, {rct_start_y}; size: {rct_width}, {rct_height}, unknown: 4:{rct_4} 6:{rct_5}")
            extension = None
            if "." in texture_name:
                # Remove extension, this is done as the mpc/mpd/pbls do not use the extension for referencing textures
                print(f"Found APT with name extension: {texture_name}")
                ext_start = texture_name.index(".")
                extension = texture_name[ext_start:]
                texture_name = texture_name[:ext_start]


            if APTexture.PRINT_DEBUG:
                print(f"Texture header: {texture_name}, {val_a}, {val_b}, {size}, {zeros:x}")
            #if zeros != 0:
            #    if APTexture.PRINT_DEBUG:
            #        print("Found non zero value in texture table data")
            #    if APTexture.STOP_ON_NEW:
            #        exit()
            new_texture = APTexture(texture_name, val_a, val_b, size, texture_offset, extension)

            if texture_name == "RCT":
                new_texture.rct_start_x = rct_start_x
                new_texture.rct_start_y = rct_start_y
                new_texture.rct_width = rct_width
                new_texture.rct_height = rct_height
                new_texture.rct_4 = rct_4  # seen 0, 9 and 8
                new_texture.rct_5 = rct_5  # seen 0 and 17

            textures.append(new_texture)

        def create_rct(reference_image, index):
            try:
                image = reference_image.get_image()
                rct = image.crop((
                    textures[index].rct_start_x, textures[index].rct_start_y,
                    textures[index].rct_start_x + textures[index].rct_width,
                    textures[index].rct_start_y + textures[index].rct_height
                ))
                textures[index].rct = rct
                sliced_data = rct.tobytes('raw')
                textures[index].set_data(textures[index].rct_width, textures[index].rct_height, sliced_data, 32)
                textures[index].set_palette(None, 0)
                textures[index].can_write = False
            except Exception as e:
                print(f"FAILED to create rct {textures[index].name} from {reference_image.name}")

        # After the header table, the texture data starts
        last_valid = None
        rct_in_progress = []
        for i in range(texture_count):
            if APTexture.PRINT_DEBUG:
                print(f"pos: {file.tell()} t: {i}")
            texture_start = file.tell()
            # Read texture descriptor
            max_length = texture_start + textures[i].total_size
            if textures[i].name == "RCT" and textures[i].total_size < 2128:  # based on 64x64 texture, might be save to have this at 0
                # Theory
                # ReCTangle (slice of texture)
                # so reuse previous data but with some adjustments?
                if last_valid is not None:
                    create_rct(textures[last_valid], i)
                else:
                    print("Visited RCT with no known image! probably means other (unknown) values used")
                    # Add this to a list, and when we hit a texture with data, process it
                    rct_in_progress.append(i)
                    continue
            else:
                width = U.readLong(file)
                height = U.readLong(file)
                colour_format = U.readLong(file)  # Might just be bytes per pixel (of texture, not palette)
                palette_size = U.readLong(file)  # Number of colours in palette

                # Also checking if the max_length is reasonable, 1 bit per pixel min
                if textures[i].total_size < int(width * height / 8) + palette_size * 4 + 16:
                    print(f"FAILED: total_size must be wrong, as even at 1bit pp texture would be this size {textures[i].total_size} vs {int(width * height * (colour_format/8)) + palette_size * 4 + 16}")
                    print(f"info: int({width} * {height} * ({colour_format}/8)) + {palette_size} * 4 + 16)")
                    # as we know it's wrong, might as well calculate a value
                    textures[i].total_size = int(width * height * (colour_format/8)) + palette_size * 4 + 16

                if APTexture.PRINT_DEBUG:
                    print(f"{width:x} {height:x} {colour_format:x} {palette_size:x}")

                if width == 0 or height == 0 or width > 2048 or height > 2048:
                    print(f"FAILED Cannot decode texture at @{file.tell()} size is {width}, {height}?")
                    return textures

                if palette_size > 2048:
                    print(f"FAILED Cannot decode texture at @{file.tell()} size is {width}, {height}, palette issues {palette_size}?")
                    return textures

                max_length = texture_start + textures[i].total_size

                # Read palette in
                palette = []
                for c in range(palette_size):
                    if file.tell() > max_length:
                        break
                    r = U.readByte(file)
                    g = U.readByte(file)
                    b = U.readByte(file)
                    a = U.readByte(file)
                    if a == 0x80:
                        a = 255
                    palette.append((r, g, b, a))
                # palette = file.read(palette_size * 4)
                if APTexture.PRINT_DEBUG:
                    print(f"pos: {file.tell()} t: {i}")

                # Check before reading, just in case.
                if file.tell() > max_length:
                    # Check if we are past the limit for this texture, seems to occur, which means
                    # the data given is not valid
                    # unsure why this happens, as the values I understand seem to still be right
                    file.seek(max_length, os.SEEK_SET)
                    continue

                texture_data = []
                # Read texture in
                for c in range(int(width * height * (colour_format/8))):
                    if file.tell() > max_length:
                        # Check if we are past the limit for this texture, seems to occur, which means
                        # the data given is not valid
                        # unsure why this happens, as the values I understand seem to still be right
                        file.seek(max_length, os.SEEK_SET)
                        break
                    if colour_format == 4:
                        val = U.readByte(file)
                        i1 = val & 0xF
                        i2 = (val >> 4) & 0xF
                        texture_data.append(i1)
                        texture_data.append(i2)
                    elif colour_format == 8:
                        val = U.readByte(file)
                        texture_data.append(val)
                    elif colour_format == 24:
                        val = U.readByte(file)
                        texture_data.append(val)
                    elif colour_format == 32:
                        val = U.readByte(file)
                        texture_data.append(val)
                    else:
                        print(f"new colour format found @ {file.tell()} value is: {colour_format}")
                        if APTexture.STOP_ON_NEW:
                            exit()
                        return

                # Might need some checks, to test if we were past max_length

                texture_data = bytes(texture_data)

                textures[i].set_data(width, height, texture_data, colour_format)
                textures[i].set_palette(palette, palette_size)
                textures[i].data_offset = texture_start
                last_valid = i

                if len(rct_in_progress) > 0:
                    for rct in rct_in_progress:
                        create_rct(textures[i], rct)
                    rct_in_progress = []

        return textures

