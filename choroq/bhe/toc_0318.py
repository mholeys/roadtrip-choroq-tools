import os
import choroq.read_utils as U
import pathlib


class Toc0318:
    CHAR_TABLE = None
    STOP_ON_NEW = False
    PRINT_DEBUG = False

    def __init__(self, toc_type, name, position, flag, data, length_read, text_length=0):
        self.type = toc_type
        self.name = name
        self.position = position
        self.flag = flag
        self.data = data
        self.length_read = length_read
        self.text_length = text_length

    @staticmethod
    def read_toc0318(file, offset):
        # Check for character table
        if Toc0318.CHAR_TABLE is None:
            # Load character table once to save IO
            Toc0318.CHAR_TABLE = load_character_table()

        file.seek(offset, os.SEEK_SET)

        magic = file.read(4)
        if magic != b'\x03\x18\x00\x00':
            if Toc0318.PRINT_DEBUG:
                print(f"TOC header invalid/different at @ {file.tell()}")
            return

        # Read subfile list
        if Toc0318.PRINT_DEBUG:
            print(f"Start of subfile list @ {file.tell()}")
        subfile_count = U.readLong(file)
        subfile_offsets = []
        for i in range(subfile_count+1):
            subfile_offsets.append(U.readLong(file))

        if Toc0318.PRINT_DEBUG:
            print(subfile_offsets)
            print(f"End of subfile list @ {file.tell()}")

        parts = []
        for o in subfile_offsets[:-1]:
            part = Toc0318.read_toc_part_header(file, offset + o)
            parts.append(part)

        # for o in subfile_offsets[:-1]:
        #     o = o + offset
        #     file.seek(o, os.SEEK_SET)
        #     if Toc0318.PRINT_DEBUG:
        #         print(f"Start of subfile[{o}] @ {file.tell()}")
        #     # Read part of TOC file/section
        #     part_type = file.read(4)
        #     print(f"TOC: part_type: {part_type}")
        #     if part_type != b'\x54\x4F\x43\x00':
        #         print(f"found different 'TOC' string in header @ {file.tell()}")
        #         if Toc0318.STOP_ON_NEW:
        #             exit(1)
        #     end_offset = U.readLong(file)  # 400
        #     size = U.readLong(file)
        #     value1 = U.readLong(file)
        #     # Read toc name
        #     name = file.read(12).decode('ascii').rstrip("\x00")
        #     print(f"TOC: name: {name}")
        #     value2 = U.readLong(file)
        #
        #     part_offsets = []
        #     if Toc0318.PRINT_DEBUG:
        #         print(f"Start of subfile[{o}] part list @ {file.tell()}")
        #     for pi in range(size):
        #         part_offsets.append(o + U.readLong(file))
        #
        #     part = [part_type, end_offset, size, value1, name, value2, part_offsets]
        #     parts.append(part)

        # Read all bits of the toc table
        part_data = []
        for part_index, part_description in enumerate(parts):
            part_data += Toc0318.read_toc_part(file, part_description)
        return part_data

    @staticmethod
    def read_toc_part_header(file, offset):
        # This is the bit with the TOC text at the beginning
        file.seek(offset, os.SEEK_SET)
        if Toc0318.PRINT_DEBUG:
            print(f"Start of subfile[{offset}] @ {file.tell()}")
        # Read part of TOC file/section
        part_type = file.read(4)
        print(f"TOC: part_type: {part_type}")
        if part_type != b'\x54\x4F\x43\x00':
            print(f"found different 'TOC' string in header @ {file.tell()}")
            if Toc0318.STOP_ON_NEW:
                exit(1)
        end_offset = U.readLong(file)  # 400
        size = U.readLong(file)
        value1 = U.readLong(file)
        # Read toc name
        name = file.read(12).decode('ascii').rstrip("\x00")
        print(f"TOC: name: {name}")
        value2 = U.readLong(file)

        part_offsets = []
        if Toc0318.PRINT_DEBUG:
            print(f"Start of subfile[{offset}] part list @ {file.tell()}")
        for pi in range(size):
            part_offsets.append(offset + U.readLong(file))

        part = [part_type, end_offset, size, value1, name, value2, part_offsets]
        return part


    @staticmethod
    def read_toc_part(file, part_description):
        part_data = []
        part_type, end_offset, size, value1, name, value2, part_offsets = part_description
        for part_bit_offset in part_offsets:
            file.seek(part_bit_offset, os.SEEK_SET)
            if Toc0318.PRINT_DEBUG:
                print(f"Reading part ({name}) from: {file.tell()}")
            head = U.readLong(file)  # unsure on use
            flag = head & 0xFF
            if flag == 0:
                continue
            # The flag must mean something, but for now ifs...
            text_after_4_flags = [0x39]
            text_flags = [0x32, 0x3F] + text_after_4_flags
            flags_4len = [0x2E, 0x03, 0x0F, 0x54, 0x56, 0xBB, 0x55, 0xF2, 0x75, 0x41, 0x15, 0x8D, 0x5B, 0x7C, 0x58,
                          0xF5, 0xF8, 0xF6, 0x1A]
            flags_8len = [0x2A, 0x2B, 0x26, 0x01, 0x02, 0x2F, 0xC4, 0x43, 0x25, 0x72, 0x0B, 0x06, 0x1F, 0xFF, 0xF4,
                          0xF9, 0x6F]
            flags_12len = [0xFD, 0x0E, 0x2C, 0x73, 0x0C, 0x17, 0x51, 0x4C, 0x08, 0x05, 0x04, 0x5E, 0x14, 0x12, 0x09,
                           0x53]
            flags_16len = [0x29, 0xBC, 0x33, 0x48, 0x07, 0x10, 0x0D, 0x3E]
            flags_20len = [0x52]
            flags_24len = [0x1C, 0x34]
            flags_36len = [0x1D]
            flags_0len = [0x2D, 0x11, 0x7D, 0x61, 0x30, 0x86, 0x70, 0xF3]
            if flag in text_flags:
                # Read null terminated string
                if flag in text_after_4_flags:
                    U.readLong(file)
                text_data = [file.read(1)]
                while text_data[-1] != b'\x00':
                    text_data.append(file.read(1))
                if Toc0318.PRINT_DEBUG:
                    print(text_data)

                # convert/decode text from bytes into custom encoding
                text = ""
                raw_data = ""
                t_positions = list(range(len(text_data)))
                for t in t_positions:
                    char = text_data[t]
                    raw_data += f"{char.hex().upper()} "
                    # Check if it is a normal char, or a special char
                    int_value = int.from_bytes(char, 'little')
                    if int_value < 0x7F:
                        # Regular ascii char
                        text += char.decode('ascii')
                    if int_value & 0xF0 >= 0xA0 and int_value < 0xFF:
                        # Using jp character, probably
                        char_2_index = t + 1
                        if char_2_index >= len(text_data):
                            continue
                        char2 = text_data[t + 1]
                        int_value_2 = int.from_bytes(char2, 'little')
                        if int_value_2 & 0xF0 >= 0xA0 and int_value < 0xFF:
                            pair = int.from_bytes(char + char2, 'big')
                            # print(pair)
                            if pair in Toc0318.CHAR_TABLE:
                                text += Toc0318.CHAR_TABLE[pair]
                                raw_data += f"{char2.hex().upper()} "
                                t_positions.remove(char_2_index) # Skip next char, as already used

                # Read end of message flag
                position = file.tell()
                if position % 4 != 0:
                    # Align to end of 4 bytes
                    required = 4 - position % 4
                    file.seek(required, os.SEEK_CUR)
                pp = file.tell()
                end_part = U.readLong(file)
                if end_part == 0:
                    if Toc0318.PRINT_DEBUG:
                        print(f"Possible wrong end of part message @ {file.tell() - 4} [{end_part}]")
                    end_part = U.readLong(file)
                if end_part != 0x80000000:
                    if Toc0318.PRINT_DEBUG:
                        print(f"Wrong end of part message @ {file.tell() - 4} [{end_part}]")
                    # exit()
                else:
                    part_data.append(Toc0318("text", name, part_bit_offset, head, [text, raw_data], file.tell() - part_bit_offset, len(text_data)))
            elif flag in flags_0len:
                data = []
                part_data.append(Toc0318("other", name, part_bit_offset, head, data, file.tell() - part_bit_offset))
            elif flag in flags_4len:
                data = []
                data.append(U.readLong(file))
                part_data.append(Toc0318("other", name, part_bit_offset, head, data, file.tell() - part_bit_offset))
            elif flag in flags_8len:
                data = []
                data.append(U.readLong(file))
                data.append(U.readLong(file))
                part_data.append(Toc0318("other", name, part_bit_offset, head, data, file.tell() - part_bit_offset))
            elif flag in flags_12len:
                data = []
                data.append(U.readLong(file))
                data.append(U.readLong(file))
                data.append(U.readLong(file))
                part_data.append(Toc0318("other", name, part_bit_offset, head, data, file.tell() - part_bit_offset))
            elif flag in flags_16len:
                data = []
                data.append(U.readLong(file))
                data.append(U.readLong(file))
                data.append(U.readLong(file))
                data.append(U.readLong(file))
                part_data.append(Toc0318("other", name, part_bit_offset, head, data, file.tell() - part_bit_offset))
            elif flag in flags_20len:
                data = []
                data.append(U.readLong(file))
                data.append(U.readLong(file))
                data.append(U.readLong(file))
                data.append(U.readLong(file))
                data.append(U.readLong(file))
                part_data.append(Toc0318("other", name, part_bit_offset, head, data, file.tell() - part_bit_offset))
            elif flag in flags_24len:
                data = []
                data.append(U.readLong(file))
                data.append(U.readLong(file))
                data.append(U.readLong(file))
                data.append(U.readLong(file))
                data.append(U.readLong(file))
                data.append(U.readLong(file))
                part_data.append(Toc0318("other", name, part_bit_offset, head, data, file.tell() - part_bit_offset))
            elif flag in flags_36len:
                data = []
                data.append(U.readLong(file))
                data.append(U.readLong(file))
                data.append(U.readLong(file))
                data.append(U.readLong(file))
                data.append(U.readLong(file))
                data.append(U.readLong(file))
                data.append(U.readLong(file))
                data.append(U.readLong(file))
                data.append(U.readLong(file))
                part_data.append(Toc0318("other", name, part_bit_offset, head, data, file.tell() - part_bit_offset))
            elif Toc0318.STOP_ON_NEW:
                print(f"Found new TOC part flag [0x{flag:X} {flag}] @ {file.tell()}")
                exit()
        return part_data

# http://www.rikai.com/library/kanjitables/kanji_codes.sjis.shtml
def load_character_table(path=None):
    # Load character table:
    char_table_path = pathlib.Path(__file__).parent / "choroq-encoding-full.tbl"
    if path is not None:
        char_table_path = path

    character_map = {}
    with open(char_table_path, "r", encoding="utf-8") as chr_file:
        for line in chr_file:
            stripped = line.strip()
            if len(stripped) == 0 or stripped[0] == "#":
                continue
            # print(line)
            value = ""
            character = ""
            if line.count("=") == 1:
                value, character = line.split("=")
            else:
                # Handle when we reference the = char
                if line[-2] == "=":
                    value, character = line[:-2].split("=")
                    if character == "":
                        character = "=\n"
                    else:
                        print("Failed to read char")
                        continue
                else:
                    print("Failed to read char")
                    continue

            if character == "\n":
                continue
            if type(character) is not str:
                print("Failed to read char")
                continue
            character = character[:-1]
            value = int(value, 16)
            character_map[value] = character
            # print(f"{value:X}={character}")

    return character_map




