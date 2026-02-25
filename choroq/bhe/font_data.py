import os
from pathlib import Path

from PIL import Image, ImagePalette, ImageOps
import choroq.egame.read_utils as U
from choroq.egame.texture import Texture


class FontData:
    STOP_ON_NEW = False

    def __init__(self, char_width, char_height, characters, character_data, character_images):
        self.char_width = char_width
        self.char_height = char_height
        self.characters = characters
        self.character_data = character_data
        self.character_images = character_images

    @staticmethod
    def read_font(file, offset):
        file.seek(offset, os.SEEK_SET)
        font_label = file.read(16)
        char_width = U.readLong(file)
        char_height = U.readLong(file)
        header_size = U.readLong(file)
        char_size_bytes = U.readLong(file)
        font_table_value1 = U.readLong(file)
        characters_size = U.readLong(file)
        font_ref_start_pos = U.readLong(file)
        font_ref_size = U.readLong(file)
        val2 = U.readLong(file)
        val3 = U.readLong(file)  # Usually small, and often same as val2 e.g 0x14

        # file.seek(offset + font_table_value1, os.SEEK_SET)
        characters = []
        for i in range(int(characters_size/2)):
            char = U.readShort(file)  # Character code/value I think
            if char != 0xFFFF:
                characters.append(char)

        print(f"FONT| End of char table at {file.tell()}")
        # Padding
        file.seek((characters_size+8) % 16, os.SEEK_CUR)

        file.seek(offset + font_ref_start_pos, os.SEEK_SET)
        font_characters = {}
        print(f"FONT| Start of char values? at {file.tell()}")
        for i in range(int(font_ref_size/8)):
        # while file.tell() < offset + header_size:
            character = U.readShort(file)
            val1 = U.readShort(file)  # Might be draw width
            val2 = U.readShort(file)  # Might be draw height
            ffffs = U.readShort(file)
            font_characters[character] = (character, val1, val2, ffffs)

        file.seek(offset + header_size, os.SEEK_SET)
        print(f"FONT| Start of char texture at {file.tell()}")
        font_textures = {}
        for ci, char in enumerate(characters):
            data = bytes()
            # Have to read byte at a time, as need to split into nibbles
            for b in range(int(char_size_bytes)):
                byte = U.readByte(file)
                nibble_l = ((byte & 0xF) << 4).to_bytes(1, byteorder='little')
                nibble_u = (((byte & 0xF0) >> 4) << 4).to_bytes(1, byteorder='little')
                data += nibble_l
                data += nibble_u
            font_textures[ci] = data

        print(f"FONT| Finished char texture at {file.tell()}")

        return FontData(char_width, char_height, characters, font_characters, font_textures)

    def save_font_data(self, path, extra_name=""):
        Path(f"{path}").mkdir(parents=True, exist_ok=True)
        with open(f"{path}\\information-{extra_name}.data", "w") as file:
            file.write("Font data:\n")
            # Unsure on this data, and how it links to the other section, as they are not the same size?
            for ci, char in enumerate(self.character_data):
                file.write(f"Character[{ci}]:\n")
                file.write(f"-CH: {self.character_data[char][0]:x}\n")
                file.write(f"-V1: {self.character_data[char][1]}\n")
                file.write(f"-V2: {self.character_data[char][2]}\n")
                file.write(f"-FF: {self.character_data[char][3]:X}\n")

        for ci, char in enumerate(self.characters):
            image_dest = f"{path}\\character-{extra_name}-{ci}.png"
            image = Image.frombytes('L', (self.char_width, self.char_height), self.character_images[ci], 'raw')
            image.save(image_dest, "PNG")

