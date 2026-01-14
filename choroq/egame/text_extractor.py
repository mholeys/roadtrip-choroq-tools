# This is for getting out dialogue data from the game
# Notes: Escaped strings
# $R = last selected, possibly race only e.g "Peach Raceway"
# $T0 Time "time from the starting point to this\npoint is"
# $T1 Time "Your time from Sandpolis to this point is\n$T1"
# $T2 Time "Your time from Chestnut Canyon to this\npoint is $T2"
# $T3 Time "Your time from White Mountain to this\npoint is $T3"
# $T4 Time "Your time from Peach Town to this point\nis $T4"
# $T5 Time "Your time from Fuji City to this point is\n$T5"
# $T6 Time "Your total time from the starting point is\n$T6"
# $N
# $U user's entered currency
# $G Greeting? "Well then, come back if you want a\nhint.$G"

from PrettyPrint import PrettyPrintTree

import io
import os
import math
import choroq.egame.read_utils as U
from elftools.elf.elffile import ELFFile

class DialogueReader:
    HG2_TOWNS = [("MY GARAGE", 0),
                 ("Peach Town", 40),
                 ("Fuji City", 40),
                 ("Sandpolis", 33),
                 ("Chestnut Canyon", 29),
                 ("Mushroom Road", 12),
                 ("White Mountain", 38),
                 ("Papaya Island", 39),
                 ("Cloud Hill", 26),
                 ("My City", 30),
                 ("Laz-213", 5),
                 ("Bridge-220", 5),
                 ("UFO-", 5),
                 ("Ruins-012", 7),
                 ("Lighthouse-011", 5),
                 ("Junction-022", 7),
                 ("Tunnel-110", 3),
                 ("120", 2),
                 ("Temple-202", 5),
                 ("212", 5),
                 ("221", 2),
                 ("232", 2)]

    def __init__(self, file, offset, languages=None):
        self.file = file
        self.start_offset = offset
        self.languages = languages
        self.elf_file = None
        self.elf_sections = []

        self.parse_elf_sections()
        # Adjust offset to be file offset
        self.offset = self.get_section_offset(offset) + offset

    def parse_elf_sections(self):
        if self.elf_file is not None:
            return
        self.elf_file = ELFFile(self.file)

        sections = []
        for section in self.elf_file.iter_sections():
            sections.append(section)
        self.elf_sections = sections

    def get_section_offset(self, position):
        for section in self.elf_sections:
            section_addr = section.header.sh_addr
            section_offset = section.header.sh_offset
            section_size = section.header.sh_size

            if section_addr <= position < section_addr + section_size: # check in range
                # The ptr is in this section, so adjust ptr to position in file
                return -section_addr + section_offset
        else:
            print(f"FAILED TO FIND POSITION FOR GIVEN requested offset for [{position}]")

    def read_all_dialogue_hg2(self):

        print(f"Got section [{self.start_offset}]")
        self.file.seek(self.offset, os.SEEK_SET)

        languages_position = self.offset
        self.file.seek(languages_position, os.SEEK_SET)

        language_ptrs = []
        if self.languages is None or len(self.languages) == 0:
            # Read until 0 ptr
            languages = []
            languages.append(len(language_ptrs))
            language_ptrs.append(U.readLong(self.file))
            while language_ptrs[-1] != 0:
                language_ptrs.append(U.readLong(self.file))
                languages.append(len(language_ptrs))
        else:
            # Read until 0 ptr
            language_ptrs.append(U.readLong(self.file))
            while language_ptrs[-1] != 0:
                language_ptrs.append(U.readLong(self.file))
        language_ptrs = language_ptrs[:-1]

        dialogues = []

        for ptr in language_ptrs:
            offset = self.get_section_offset(ptr)
            dialogues.append(self.read_dialogue_hg2(ptr + offset, offset))

    def read_dialogue_hg2(self, offset, start_offset):
        # hg2 structure is nested ptrs
        # - Language ptr
        # -- [Town ptrs] # This one
        # --- [Shop ptrs]
        # ---- [Line ptrs]
        # ----- Line/text/precodes
        decoded = []
        print(f"Reading language from [{offset-start_offset:x}]")
        for i, (town, count) in enumerate(DialogueReader.HG2_TOWNS):
            print(f"Reading [{town}] with {count}")
            self.file.seek(offset + i * 4, os.SEEK_SET)
            town_ptr = U.readLong(self.file)
            town_ptr_offset = self.get_section_offset(town_ptr)
            if town_ptr == 0:
                continue
            decoded.append(self.read_town_hg2(town_ptr + town_ptr_offset, town_ptr_offset))
        return decoded

    def read_town_hg2(self, offset, start_offset):
        # hg2 structure is nested ptrs
        # - Language ptr # Done
        # -- [Town ptrs] # Done
        # --- [Shop ptrs] # This one
        # ---- [Line ptrs]
        # ----- Line/text/precodes
        print(f"Reading town from [{offset - start_offset:x}]")
        self.file.seek(offset, os.SEEK_SET)
        shops = [U.readLong(self.file)]
        while shops[-1] != 0:
            shops.append(U.readLong(self.file))

        for shop in shops:
            if shop == 0:
                continue
            shop_ptr_offset = self.get_section_offset(shop)
            shop_ptr = shop + shop_ptr_offset
            self.file.seek(shop_ptr, os.SEEK_SET)
            self.read_shop_hg2(shop_ptr, shop_ptr_offset)

    def read_shop_hg2(self, offset, start_offset):
        # hg2 structure is nested ptrs
        # - Language ptr # Done
        # -- [Town ptrs] # Done
        # --- [Shop ptrs] # Done
        # ---- [Line ptrs] # This one
        # ----- Line/text/precodes
        print(f"Reading shop from [{offset - start_offset:x}]")
        self.file.seek(offset, os.SEEK_SET)
        # TODO: read all, not first line
        name_ptr = U.readLong(self.file)
        if name_ptr == 0:
            return
        name_ptr_offset = self.get_section_offset(name_ptr)

        first_line_ptr = U.readLong(self.file)
        if first_line_ptr == 0:
            return
        first_line_ptr_offset = self.get_section_offset(first_line_ptr)

        self.file.seek(name_ptr + name_ptr_offset)
        name = self.read_string()
        print(f"Current shop: {name}")

        # Read first line of dialogue, and work through its jumps to find new dialogue that needs to be processed
        self.file.seek(first_line_ptr + first_line_ptr_offset)
        current_tree = DialogueTree(DialogueName(name))
        self.handle_line(current_tree, first_line_ptr + first_line_ptr_offset, offset - start_offset, 1, [0])
        ptdebug = PrettyPrintTree(
            lambda x: [] if x is None or x.children is None else x.children,
            lambda x: x.value if x else "   ",
            show_newline_literal=False
        )
        pt = PrettyPrintTree(
            lambda x: [] if x is None or x.children is None else x.children,
            # lambda x: x.value if isinstance(x, DialogueTree) else (x.value if x else "   "),
            lambda x: x.value if isinstance(x.value, DialogueText) else "",
            show_newline_literal=False
        )
        #ptdebug(current_tree)
        #pt(current_tree)
        # print(current_tree)
        print(current_tree.print())
        print(current_tree.print_dialogue())
        exit()

    def read_string(self):
        string = self.file.read(1)
        while True:
            next = self.file.read(1)
            if next[0] > 0x1F or next[0] == 0x0A:  # Handle new line chars as is
                string += next
            else:
                # Any values 1f or less are pre-codes, and define the flow of data
                # also handles \0 null terminator of the string, (not included/read in the string)
                self.file.seek(-1, os.SEEK_CUR)
                break
        return str(string, encoding='ascii')

    def handle_line(self, root, position, shop_position, current_line, parent_lines):
        tree = root
        if position == 0:
            # Null ptr, end
            tree.add_child(DialogueTree(DialogueEnd))
            return None
        while True:
            self.file.seek(position, os.SEEK_SET)
            character = self.file.read(1)
            if character[0] == 0:
                next_line = self.change_line(shop_position, current_line+1)
                if next_line == 0 or next_line == position and current_line != 0:  # Checks for cycles 1->1 or jumping back to 0, which should be exit
                    tree.add_child(DialogueTree(DialogueEnd))
                else:
                    right = tree.add_child(DialogueTree(DialogueChangeLine(current_line+1, "Finished, next line")))
                    self.handle_line(right, next_line, shop_position, current_line+1, parent_lines+[current_line])
                break
            if character[0] <= 0x1F:
                print(f"Got pre-code of {character[0]:x} at {self.file.tell()}")
            if character[0] > 0x1F or character[0] == 0x0A:
                # This is string data, read in until end of string
                self.file.seek(-1, os.SEEK_CUR)
                # Add string to tree, and move down the tree
                tree = tree.add_child(DialogueTree(DialogueText(self.read_string())))
                print(tree.value)
                # print(tree.value)
                position = self.file.tell()  # update position, as next branch will be where string began
                continue
            # We have a pre-control or control value
            elif character[0] == 0x01:
                # Checks flags
                # FUN_0023f2d8 = DAT_018254b8
                flag_index = self.file.read(1)[0] # + 1
                # TODO: possibly have table of flags once decoded all(/some?) of them
                # the check is is (bit != 0) == 0
                on_true = self.file.read(1)[0]  # + 2 # ChangeLine
                on_false = +3  # + 3 # HandleNextChar
                left = tree.add_child(DialogueTree(DialogueAdvance(on_false, f"FLAG check [0x01].{flag_index} on_false")))
                right = tree.add_child(DialogueTree(DialogueChangeLine(on_true, f"FLAG check [0x01].{flag_index} on_true")))
                next_line = self.change_line(shop_position, on_true)
                self.handle_line(left, position + on_false, shop_position, current_line, parent_lines+[current_line])
                if on_true != 0 and on_true != current_line and on_true not in parent_lines:
                    self.handle_line(right, next_line, shop_position, on_true, parent_lines+[current_line])
                else:
                    right.value.text += " !Nests/Loops self!"
                break
            elif character[0] == 0x02:
                # Checks flags, inverted version of 1
                # FUN_0023f2d8 = DAT_018254b8
                flag_index = self.file.read(1)[0] # + 1
                # TODO: possibly have table of flags once decoded all(/some?) of them
                # the check is is (bit != 0) != 0
                on_false = self.file.read(1)[0]  # + 2 # ChangeLine
                on_true = +3  # + 3 # HandleNextChar
                left = tree.add_child(DialogueTree(DialogueChangeLine(on_false, f"FLAG check [0x02].{flag_index} on_false")))
                right = tree.add_child(DialogueTree(DialogueAdvance(on_true, f"FLAG check [0x02].{flag_index} on_true")))
                next_line = self.change_line(shop_position, on_false)
                if on_false != 0 and on_false != current_line and on_false not in parent_lines:
                    self.handle_line(left, next_line, shop_position, on_false, parent_lines+[current_line])
                else:
                    left.value.text += " !Nests/Loops self!"
                self.handle_line(right, position + on_true, shop_position, current_line, parent_lines+[current_line])
                break
            elif character[0] == 0x03:
                # unsure, calls function which does some ORing based on next two bytes
                # FUN_0023efe8
                # if function returns 0 then moves to next, else jumps lines
                param1 = self.file.read(1)[0]
                param2 = self.file.read(1)[0]
                on_true = +4  # + 4 # HandleNextChar
                # Peek
                on_true_peek = self.file.read(1)[0]
                self.file.seek(-1, os.SEEK_CUR)
                on_false = self.file.read(1)[0]  # + 3 # ChangeLine
                left = tree.add_child(DialogueTree(DialogueAdvance(on_false, f"BITMASK check [0x03] ({param1}, {param2}) on_false")))
                right = tree.add_child(DialogueTree(DialogueChangeLine(on_true, f"BITMASK check [0x03] ({param1}, {param2}) on_true")))
                next_line = self.change_line(shop_position, on_false)
                if on_false != 0 and on_false != current_line and on_false not in parent_lines:
                    self.handle_line(left, next_line, shop_position, on_false, parent_lines+[current_line])
                else:
                    left.value.text += " !Nests/Loops self!"
                if on_true_peek != 0:
                    self.handle_line(right, position + on_true, shop_position, current_line, parent_lines+[current_line])
                break
            elif character[0] == 0x04:
                # Unsure, works with outer param2, which is a structure
                on_false = self.file.read(1)[0]  # + 2 # ChangeLine
                on_true = +2  # + 2 # HandleNextChar
                left = tree.add_child(DialogueTree(DialogueAdvance(on_false, f"FLAG check [0x04]  on_false")))
                right = tree.add_child(DialogueTree(DialogueChangeLine(on_true, f"FLAG check [0x04]  on_true")))
                next_line = self.change_line(shop_position, on_false)
                if on_false != 0 and on_false != current_line and on_false not in parent_lines:
                    self.handle_line(left, next_line, shop_position, on_false, parent_lines+[current_line],)
                else:
                    left.value.text += " !Nests/Loops self!"
                self.handle_line(right, position + on_true, shop_position, current_line, parent_lines+[current_line])
                break
            elif character[0] == 0x06:
                # Checks flags?
                # FUN_0023f188 = DAT_01825498/DAT_018254a0
                flag_index = self.file.read(1)[0] # + 1
                # TODO: possibly have table of flags once decoded all(/some?) of them
                # the check is is (bit != 0) == 0
                on_false = self.file.read(1)[0]  # + 2 # ChangeLine
                on_true = +3  # + 3 # HandleNextChar
                left = tree.add_child(DialogueTree(DialogueChangeLine(on_false, f"FLAG check [0x06].{flag_index} on_false")))
                right = tree.add_child(DialogueTree(DialogueAdvance(on_true, f"FLAG check [0x06].{flag_index} on_true")))
                next_line = self.change_line(shop_position, on_false)
                if on_false != 0 and on_false != current_line and on_false not in parent_lines:
                    self.handle_line(left, next_line, shop_position, on_false, parent_lines+[current_line])
                else:
                    left.value.text += " !Nests/Loops self!"
                self.handle_line(right, position + on_true, shop_position, current_line, parent_lines+[current_line])
                break
            elif character[0] == 0x07:
                # Checks flags?
                # FUN_0023f728 = DAT_018255f4/DAT_018255f6
                # TODO: possibly have table of flags once decoded all(/some?) of them
                # the check is is (bit != 0) == 0
                on_false = +2  # + 3 # HandleNextChar
                on_true = self.file.read(1)[0]  # + 1 # ChangeLine
                left = tree.add_child(DialogueTree(DialogueChangeLine(on_true, f"FN check [0x07] on_true")))
                right = tree.add_child(DialogueTree(DialogueAdvance(on_false, f"FN check [0x07]  on_false")))
                next_line = self.change_line(shop_position, on_false)
                if on_true != 0 and on_true != current_line and on_true not in parent_lines:
                    self.handle_line(left, next_line, shop_position, on_true, parent_lines+[current_line])
                else:
                    left.value.text += " !Nests/Loops self!"
                self.handle_line(right, position + on_false, shop_position, current_line, parent_lines+[current_line])
                break
            elif character[0] == 0x08:
                # Unsure, works with outer param2, which is a structure
                on_one = self.file.read(1)[0]  # FUN_0023f6e0 != 0
                on_two = +3  # FUN_0023f820 != 0
                on_three = self.file.read(1)[0]  # FUN_0023f6e0 == 0 and FUN_0023f820 == 0
                one = tree.add_child(DialogueTree(DialogueChangeLine(on_one, f"FN  check [0x08]  FUN_0023f6e0")))
                two = tree.add_child(DialogueTree(DialogueAdvance(on_two, f"FN check [0x08] FUN_0023f820")))
                three = tree.add_child(DialogueTree(DialogueChangeLine(on_three, f"FN check [0x08] other")))
                next_line = self.change_line(shop_position, on_one)
                if on_one != 0 and on_one != current_line and on_one not in parent_lines:
                    self.handle_line(one, next_line, shop_position, on_one, parent_lines+[current_line])
                else:
                    one.value.text += " !Nests/Loops self!"
                next_line = self.change_line(shop_position, on_three)
                if on_three != 0 and on_three != current_line and on_three not in parent_lines:
                    self.handle_line(three, next_line, shop_position, on_three, parent_lines+[current_line])
                else:
                    three.value.text += " !Nests/Loops self!"
                self.handle_line(two, position + on_two, shop_position, current_line, parent_lines+[current_line])
                break
            elif character[0] == 0x09:
                # I think this is draw options, such as "Yes"/"No"
                # I think it uses \t between the list of strings, e.g \tYes\0No\t \tYes\0Maybe\0No\t
                # Read string, repeat until we hit a \t, then follows a list of line jumps, for each option
                options = [self.read_string()]
                read = self.file.read(2)
                while read[1] != 0x09:
                    if read[0] == 0:
                        self.file.seek(-1, os.SEEK_CUR)
                    options.append(self.read_string())
                    read = self.file.read(2)
                print(read)
                print(options)

                for o in options:
                    on_option = self.file.read(1)[0]  # Which line to jump to when this option is selected
                    next = tree.add_child(DialogueTree(DialogueChangeLine(on_option, f"Option [0x09]: {o}")))
                    next_line = self.change_line(shop_position, on_option)
                    if on_option != 0 and on_option != current_line and on_option not in parent_lines:
                        print(f"Handling option [{o}] line {on_option} pos {next_line}")
                        # Set the in options so we don't loop
                        self.handle_line(next, next_line, shop_position, on_option, parent_lines+[current_line])
                    else:
                        next.value.text += " !Nests/Loops self!"
                break
            elif character[0] == 0x0c:
                # Unsure on this one, seems to do something different
                # I think it changes line
                jump = self.file.read(1)[0]  # + 2 # ChangeLine

                left = tree.add_child(
                    DialogueTree(DialogueChangeLine(jump, f"C changeLine? [0x0C] {jump}")))
                next_line = self.change_line(shop_position, jump)
                if jump != 0 and jump != current_line and jump not in parent_lines:
                    self.handle_line(left, next_line, shop_position, jump, parent_lines+[current_line])
                else:
                    left.value.text += " !Nests/Loops self!"
                break
            elif character[0] == 0x0e:
                # Checks flags
                flag_index = 0x50
                # On true moves by?, something like 0<->6*4 + other from a struct
                # a function is called, which returns 0 or 1/2/3/4/5 by comparing two values in memory
                # this returned value is then used
                on_true = -1  # TODO as complicated struct # HandleNextChar
                # On false + 7
                # self.file.seek(6, os.SEEK_CUR)
                on_false = +7 #self.file.read(1)[0]  # + 7 # HandleNextChar
                left = tree.add_child(DialogueTree(DialogueAdvance(on_false, f"FLAG check [0x0E].{flag_index} on_false")))
                right = tree.add_child(DialogueTree(DialogueAdvance(on_true, f"FLAG check [0x0E].{flag_index} on_true")))
                self.handle_line(left, position + on_false, shop_position, current_line, parent_lines+[current_line])
                # self.handle_line(tree.right, position + on_true, shop_position) # FIXME: after on_true is understood
                break
            elif character[0] == 0x0f:
                # Sets flags using next byte
                flag_index = self.file.read(1)[0]  # + 1
                # Moves to
                tree = tree.add_child(DialogueTree(DialogueAdvance(2, f"SETFLAG [0x0F].{flag_index}")))
                # self.handle_line(tree.right, position + 2, shop_position)
                position = self.file.tell()
                continue
            elif character[0] == 0x10:
                # Sets flags using next byte
                flag_index = self.file.read(1)[0]  # + 1
                # Moves to
                tree = tree.add_child(DialogueTree(DialogueAdvance(2, f"SETFLAG [0x10].{flag_index}")))
                # self.handle_line(tree.right, position + 2, shop_position)
                position = self.file.tell()
                continue
            elif character[0] == 0x11:
                # FUN_0023eef0
                param1 = self.file.read(1)[0]  # + 1
                param2 = self.file.read(1)[0]  # + 2
                # Moves to
                tree = tree.add_child(DialogueTree(DialogueAdvance(3, f"FN [0x11] P1 {param1} P2 {param2}")))
                position = self.file.tell()
                continue
            elif character[0] == 0x12:
                # FUN_0023f428 = Reads DAT_003d9984
                check = self.file.read(1)[0]  # + 1 # compares this byte to result of function
                jump = self.file.read(1)[0]  # + 1
                left = tree.add_child(DialogueTree(DialogueChangeLine(jump, f"FN check [0x12] {check} on_true")))
                right = tree.add_child(DialogueTree(DialogueEnd()))
                next_line = self.change_line(shop_position, jump)
                if jump != 0 and jump != current_line and jump not in parent_lines:
                    self.handle_line(left, next_line, shop_position, jump, parent_lines+[current_line])
                else:
                    left.value.text += " !Nests/Loops self!"
                break
            elif character[0] == 0x15:
                # Sets flags using next byte
                flag_index = self.file.read(1)[0]  # + 1
                # Moves to
                tree = tree.add_child(DialogueTree(DialogueAdvance(2, f"SETFLAG [0x15].{flag_index}")))
                # self.handle_line(tree.right, position + 2, shop_position)
                position = self.file.tell()
                continue
            elif character[0] == 0x1B:
                # I think this presents multiple options
                on_one = +2  # DAT_018255d1 != '\x03'
                on_two = self.file.read(1)[0]  # FUN_0023f188(100) != 0
                on_three = +2 # FUN_0023f2d8(87) != 0
                on_four = on_two  # FUN_0023f2d8(87) != 0

                one = tree.add_child(DialogueTree(DialogueAdvance(on_one, f"FN check [0x1B] DAT_018255d1")))
                two = tree.add_child(DialogueTree(DialogueChangeLine(on_two, f"FN check [0x1B] FUN_0023f188")))
                three = tree.add_child(DialogueTree(DialogueAdvance(on_three, f"FN check [0x1B] FUN_0023f2d8")))
                four = tree.add_child(DialogueTree(DialogueChangeLine(on_four, f"FN check [0x1B] other")))

                next_line = self.change_line(shop_position, on_two)
                if on_two != 0 and on_two != current_line and on_two not in parent_lines:
                    self.handle_line(two, next_line, shop_position, on_two, parent_lines+[current_line])
                else:
                    two.value.text += " !Nests/Loops self!"
                next_line = self.change_line(shop_position, on_four)
                if on_four != 0 and on_four != current_line and on_four not in parent_lines:
                    self.handle_line(four, next_line, shop_position, on_four, parent_lines+[current_line])
                else:
                    four.value.text += " !Nests/Loops self!"

                self.handle_line(one, position + on_one, shop_position, current_line, parent_lines+[current_line])
                self.handle_line(three, position + on_three, shop_position, current_line, parent_lines+[current_line])
                break
            else:
                tree = tree.add_child(DialogueTree(DialogueEvent(f"unimplemented pre-code of {character[0]:x}")))
                print(f"Got unimplemented pre-code of {character[0]:x}")
                # exit()
                break

        return tree

    def change_line(self, shop_offset, line_index):
        # Returns position in file (not elf address) to the requested line

        # Go to the first line, (array of shop lines)
        # move forward to the line requested, 4 bytes per ptr
        shop_ptr_offset = self.get_section_offset(shop_offset)
        self.file.seek((shop_offset + shop_ptr_offset) + line_index * 4, os.SEEK_SET)

        # Read and process the line's ptr to a file offset
        line_ptr = U.readLong(self.file)
        if line_ptr == 0:
            return 0
        line_ptr_offset = self.get_section_offset(line_ptr)
        return line_ptr + line_ptr_offset

# "abstract" class for when the dialogue line does something
class DialogueEvent:
    def __init__(self, text=""):
        self.text = text

    def __str__(self):
        return f"DialogueEvent [{self.text}]"


# This class is used for when the dialogue moves further into the current "line"
class DialogueAdvance(DialogueEvent):

    def __init__(self, position_adjust, text=""):
        super().__init__(text)
        self.position_adjust = position_adjust

    def __str__(self):
        return f"DialogueAdvance by +{self.position_adjust} [{self.text}]"


# This class is used for when the dialogue requests a change from the current "line" to different one by index
class DialogueChangeLine(DialogueEvent):

    def __init__(self, new_line_index, text=""):
        super().__init__(text)
        self.new_line_index = new_line_index

    def __str__(self):
        return f"DialogueChangeLine to {self.new_line_index} [{self.text}]"


class DialogueEnd(DialogueEvent):

    def __init__(self):
        super().__init__("<End>")

    def __str__(self):
        return "DialogueEnd"


class DialogueText(DialogueEvent):

    def __init__(self, text):
        super().__init__(text)

    def __str__(self):
        value = self.text.replace("\n", "\n              ")  # pad newlines to be inline
        return f"DialogueText [{value}]"


class DialogueName(DialogueText):

    def __init__(self, name):
        super().__init__(name)

    def __str__(self):
        value = self.text.replace("\n", "\n              ")  # pad newlines to be inline
        return f"DialogueName [{value}]"


class DialogueTree:

    def __init__(self, value=None):
        self.value = value
        self.children = []

    def add_child(self, child):
        self.children.append(child)
        return child

    def print(self, indent=None):
        if indent is None:
            indent = ""
        string = indent
        # if isinstance(self.value, DialogueText):
        value_str = str(self.value)
        value_str = value_str.replace("\n", "\n"+indent)
        string += f"{value_str}:\n"
        indent += "\t"
        for ci, child in enumerate(self.children):
            string += child.print(indent)
            if ci != len(self.children) - 1:
                string += indent+"or\n"
        return string

    def print_dialogue(self, indent=None):
        if indent is None:
            indent = ""
        string = indent
        if isinstance(self.value, DialogueText):
            value_str = str(self.value)
            value_str = value_str.replace("\n", "\n"+indent)
            string += f"{value_str}:\n"
            indent += "\t"
        for ci, child in enumerate(self.children):
            string += child.print_dialogue(indent)
            if ci != len(self.children) - 1:
                string += indent+"or\n"
        return string


    #
    # def __str__(self):
    #     return f"({self.left}) < {self.value} > ({self.right})"


HG2_TEXT_EUROPE = 0x002a4620
elf_path = "I:\\Console\\PS2\\RoadTripAdventure_Data\\RoadTripAdventure\\SLES_513.56"

with open(elf_path, "rb") as f:
    reader = DialogueReader(f, HG2_TEXT_EUROPE, ["English", "French", "German"])
    reader.read_all_dialogue_hg2()






