import os
import functools

import re
import pycdlib
import customtkinter
from tkinter import filedialog, messagebox, Menu
from tkinter import ttk
from PIL import Image

from choroq.egame.moddingui.entries.hg2_car_entry import HG2CarEntry
from choroq.egame.moddingui.modules.message_box import MessageBox

from choroq.egame.moddingui.common import *
from choroq.egame.moddingui.entries.game_entry import GameEntry
from choroq.egame.moddingui.entries.hg2_object_entry import HG2ObjectEntry

import choroq.read_utils as U
from choroq.egame.moddingui.modules.helper import Helper
from choroq.texture_utils import TextureUtil


class FullCarReplaceMenu(customtkinter.CTkToplevel):

    def __init__(self, root, iso: pycdlib.PyCdlib, entry: GameEntry):
        super().__init__(root)
        self.output_var = None
        self.output_label = None
        self.valid_var = None
        self.valid_label = None
        self.close_btn = None
        self.replace_btn = None
        self.wm_transient(root)
        self.root = root

        self.title("Car/Part replacement UI")

        self.iso = iso
        self.entry = entry

        self.original_data = BytesIO()
        iso.get_file_from_iso_fp(self.original_data, iso_path=entry.path)
        # Find texture offset
        self.original_data.seek(0, os.SEEK_SET)

        self.offsets = []
        self.load_offsets()

        # texture_header, texture_size, clut_header, clut_size, clut_tail
        self.texture_tag_data = None
        self.load_texture_data()

        self.part_count = 0
        self.parts_ui = []

        self.replacement_total_size = 0 # size in bytes of all parts together + offset table
        self.replacement_part_sizes = []  # size in bytes of each parts

        self.build_ui()

    def on_part_change_cb(self):
        # User has changed one or more parts, recalculate total replacement size
        self.recalculate_size()

    def recalculate_size(self):
        self.replacement_total_size = 0

        if type(self.entry) == HG2CarEntry:
            # offset table for a car is 48 bytes (32 + 16 pad)
            self.replacement_total_size = 48
        # TODO: handle other object types like wheel/tire/etc

        for part_i, part in enumerate(self.parts_ui):
            part_size = part.replacement_part_size

            self.replacement_part_sizes[part_i] = part_size
            self.replacement_total_size += part_size
        self.check_size_valid()

    def build_ui(self):
        # build a table of part selection settings based on the max allowed for this obj type
        # For title/head
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)
        title_size = 3

        header_label = customtkinter.CTkLabel(self, text="Select parts", fg_color="gray30", corner_radius=6)
        header_label.grid(row=0, column=0, padx=5, pady=5, sticky="nesw", columnspan=4)

        header_desc = customtkinter.CTkLabel(self,
                                             text="Select/browse for each part you wish to use (.BIN from blender). "
                                                  "The texture option supports multiple formats, as long as it is 128x128 "
                                                  "with RGB or RGBA e.g PNG. For cars you may skip the low poly part, and leave it "
                                                  "blank, this will save space, and cause the full model to be drawn for both in game.\n\n"
                                                  "I have provided an \"Empty\" part, which can be used for any parts do draw nothing."
                                             , fg_color="gray30", corner_radius=6, wraplength=500)
        header_desc.grid(row=1, column=0, padx=5, pady=5, ipady=10, sticky="nesw", columnspan=4, rowspan=2)

        if type(self.entry) == HG2CarEntry:
            self.part_count = 6

            self.columnconfigure(0, weight=20)
            self.columnconfigure(1, weight=20)
            self.columnconfigure(2, weight=20)
            self.columnconfigure(3, weight=20)



            for row in range(self.part_count):
                self.rowconfigure(title_size+row, weight=1)
                self.replacement_part_sizes.append(0)

            part_configs = [
                ("[0] Body & [1] Lights & [2] Brake-light", False),
                ("[0] Low Poly Body & [1] Lights", True),
                ("[0] Spoiler (default), [1] optional high level light", False),
                ("[0] Spoiler (wing)", False),
                ("[0] Jets", False),
                ("[0] Stickers", False),
            ]

            for part_i, part_config in enumerate(part_configs):
                self.rowconfigure(title_size+part_i, weight=1)
                ui_part = CarPartSection(self, part_config[0], self.on_part_change_cb, part_config[1])
                ui_part.grid(row=title_size+part_i, column=0, columnspan=4, padx=5, pady=5, sticky="nesw")
                self.parts_ui.append(ui_part)

            self.rowconfigure(title_size+self.part_count, weight=1)
            self.replacement_part_sizes.append(0)
            ui_part = TextureSection(self, (128, 128), "Texture", self.on_part_change_cb, True)
            ui_part.grid(row=title_size+self.part_count, column=0, columnspan=4, padx=5, pady=5, sticky="nesw")
            self.parts_ui.append(ui_part)


        elif type(self.entry) == HG2ObjectEntry:
            if self.entry.filename == "TIRE.BIN":
                car_part_count = len(self.offsets) - 2  # -2 one for texture, and one for eof
                parts_string = [
                    "[0] Front left wheel (world)",
                    "[0] Front right wheel (world)",
                    "[0] Pair wheels (rear) (world)",
                    "[0] 4 wheels (far away car) (world)",
                    "[0] Big tire left",
                    "[0] Big tire right",
                ]
            elif self.entry.filename == "WHEEL.BIN":
                car_part_count = len(self.offsets) - 1  # -1 for eof, no texture
                parts_string = [
                    "[0] Outer tire",
                    "[0] Normal Wheel 3D",
                    "[0] Mesh Wheel 3D",
                    "[0] Spoke 1 Wheel 3D",
                    "[0] Spoke 2 Wheel 3D",
                    "[0] Flush 1 Wheel 3D",
                    "[0] Spoke 3 Wheel 3D",
                    "[0] Flush 2 Wheel 3D",
                    "[0] Spoke 4 Wheel 3D",
                    "[0] Spoke 5 Wheel 3D",
                    "[0] Spoke 6 Wheel 3D",
                    "[0] Flush 3 Wheel 3D",
                    "[0] Flush 4 Wheel 3D",
                    "[0] Flush 5 Wheel 3D",
                    "[0] Spoke 7 Wheel 3D",
                    "[0] Spoke 666 Wheel 3D",
                ]
            elif self.entry.filename == "PARTS.BIN":
                car_part_count = len(self.offsets) - 2  # -2 one for texture, and one for eof
                parts_string = [
                    "[0] Hood scoop",
                    "[0] Devil hood \"scoop\" & [1] Devil light covers",
                    "[0] Flight wing (closed)",
                    "[0] Flight wing (open)",
                    "[0] Light frame & [1] Light lens",
                    "[0] Police sign",
                    "[0] Propeller frame",
                    "[0] Propeller blade",
                    "[0] Water Skii",
                    "[0] Advert roof sign",
                    "[0] Big wheel axles/subframe",
                    "[0] Propeller special part unknown",
                ]


        self.output_var = customtkinter.StringVar()
        self.output_var.set(f"")
        self.output_label = customtkinter.CTkLabel(self, textvariable=self.output_var, fg_color="gray30", corner_radius=6)
        self.output_label.grid(row=title_size+self.part_count+1, column=0, padx=5, pady=5, sticky="nesw", columnspan=4)

        self.valid_var = customtkinter.StringVar()
        self.valid_var.set(f"")
        self.valid_label = customtkinter.CTkLabel(self, textvariable=self.valid_var, fg_color="gray30", corner_radius=6)
        self.valid_label.grid(row=title_size+self.part_count+2, column=0, padx=5, pady=5, sticky="nesw", columnspan=4)

        self.replace_btn = customtkinter.CTkButton(self, text="Replace", command=self.replace, state="disabled", fg_color="Red")
        self.close_btn = customtkinter.CTkButton(self, text="Close", command=self.close_cb)
        self.replace_btn.grid(row=title_size+self.part_count+3, column=0, columnspan=2, sticky="nesw")
        self.close_btn.grid(row=title_size+self.part_count+3, column=3, columnspan=2, sticky="nesw")

        self.columnconfigure(0, weight=1)

        self.check_size_valid()

    def check_size_valid(self):
        print("Checking if part will fit")

        all_valid_str = "All parts valid/selected"
        has_all_parts = True

        for i, part_ui in enumerate(self.parts_ui):
            if not part_ui.part_valid():
                has_all_parts = False
                print(f"Part invalid: {i}")
                break

        if not has_all_parts:
            all_valid_str = "Missing a required part"

        # Disable unless it fits
        self.replace_btn.configure(state="disabled")
        # Colour button red
        self.replace_btn.configure(fg_color="Red")

        if has_all_parts and self.replacement_total_size != 0:
            if self.replacement_total_size <= self.entry.get_size():
                # Enable replace button, as it fits
                self.replace_btn.configure(state="enabled")
                self.replace_btn.configure(fg_color="Blue")
                self.valid_var.set(f"Replacement will fit. {all_valid_str}")
            else:
                self.valid_var.set(f"Replacement too big! {all_valid_str}")
        self.replace_btn.after(1, self.update())
        self.valid_var.set(all_valid_str)

    def load_offsets(self):
        self.offsets = Helper.find_offsets(self.original_data)

    def load_texture_data(self):
        # texture_header, texture_size, clut_header, clut_size, clut_tail
        self.texture_tag_data = Helper.find_texture_tags(self.original_data)
        if self.texture_tag_data is None:
            print("Failed to decode texture tags/data, cannot copy")
        else:
            print(f"Got texture tags,\n"
                  f"Thead: {len(self.texture_tag_data[0])}\n"
                  f"Tsize: {self.texture_tag_data[2]}\n"
                  f"Chead: {len(self.texture_tag_data[3])}\n"
                  f"Csize: {self.texture_tag_data[5]}\n"
                  f"Ctail: {len(self.texture_tag_data[6])}\n")


    def replace(self):
        # Reopen the iso as read and write
        try:
            write_test = open(self.entry.record.data_fp.name, "r+b")
            write_test.close()
        except Exception as e:
            print("failed to write to iso (test)")
            print(e)
            MessageBox(self.root, ["Close"],
                       "Failed to reopen the ISO for writing\n" + str(e),
                       "Problem during replacement", warn=True)
            return False

        # Build replacement car/object in memory
        replacement_bytes = BytesIO()

        # Slip past position of offset table, and build this at the end
        offset_table = []
        # TODO: handle other objects, with different offset table size
        replacement_bytes.seek(48, os.SEEK_SET)

        # Go through all parts, loading their data, and writing into memory buffer
        for part_index in range(self.part_count):
            is_skipped_lp_body = (
                    part_index == 1
                    and self.parts_ui[part_index].optional
                    and not self.parts_ui[part_index].valid_path)

            # Handle skipping LP, as just draw full
            if is_skipped_lp_body:
                offset_table.append(offset_table[0])
            else:
                # Add this part's offset to the table
                offset_table.append(replacement_bytes.tell())

                path = self.parts_ui[part_index].part_path.get()
                try:
                    with open(path, "rb") as part_in:
                        replacement_bytes.write(part_in.read())

                    # Get the position after writing, and pad to be 16 byte aligned for the next section
                    next_position = replacement_bytes.tell()
                    if next_position % 16 != 0:
                        next_position += 16 - (next_position % 16)

                    replacement_bytes.seek(next_position, os.SEEK_SET)

                except Exception as e:
                    MessageBox(self.root, ["Close"],
                               "Failed to replace data\n"
                               "There was an issue with reading data from the supplied parts\n"
                               f"[{part_index}/{path}]:\n{str(e)}",
                               "Problem during replacement",
                               warn=True)

        # Once all parts have been written, write out the texture
        offset_table.append(replacement_bytes.tell())

        texture_header, texture_data, texture_size, clut_header, clut_data, clut_size, clut_tail = self.texture_tag_data

        # Load, and convert texture
        if self.parts_ui[-1].valid_path:
            texture_path_in = self.parts_ui[-1].part_path.get()
            selected_image = Image.open(texture_path_in)
            texture_bytes, clut_bytes = TextureUtil.split_image(selected_image)
        else:
            # Reuse current car texture (unlikely but nice to have)
            texture_bytes = texture_data
            clut_bytes = clut_data

        if len(texture_bytes) != texture_size:
            print(f"Texture size mismatch: {texture_size} != {len(texture_bytes)}")
            raise Exception("Texture not valid, or unsupported")
        if len(clut_bytes) != clut_size:
            print(f"Clut size mismatch {clut_size} != {len(clut_bytes)}")
            raise Exception("Texture not valid, or unsupported")

        replacement_bytes.write(texture_header)
        replacement_bytes.write(texture_bytes)

        replacement_bytes.write(clut_header)
        replacement_bytes.write(clut_bytes)
        replacement_bytes.write(clut_tail)

        # Once all parts, and texture have been written, write out offset table
        eof = replacement_bytes.tell()
        offset_table.append(eof)
        replacement_bytes.seek(0, os.SEEK_SET)
        for offset in offset_table:
            replacement_bytes.write(offset.to_bytes(4, byteorder="little"))

        replacement_bytes.seek(0, os.SEEK_SET)

        try:

            # Dirty, open file again then write where it should be,
            # without doing this the data positions change
            print(f"Replacing all parts of car {self.entry.basename}")
            with open(self.entry.record.data_fp.name, "r+b") as edited_out:
                # Move to the iso's file position, and move to the start of the part
                edited_out.seek(self.entry.record.fp_offset, os.SEEK_SET)

                amount_written = edited_out.write(replacement_bytes.read())
                if amount_written < self.replacement_total_size:
                    raise Exception(f"Failed to replace, did not write full size {amount_written} != {self.replacement_total_size}")

            # Do not use this function, it changes LBA and file positions
            # This is here to remind me to not do this
            # # Pad data until replacement is the same size, as required
            # replacement_bytes.seek(0, os.SEEK_END)
            # replacement_bytes.write(b'\x00' * (entry.get_size() - converted_size))
            # converted_size = replacement_bytes.tell()
            # replacement_bytes.seek(0, os.SEEK_SET)
            # iso.modify_file_in_place(replacement_bytes, converted_size, entry.path)
            MessageBox(self.root, ["Close"],
                       f"Replacement successful","Completed")
        except Exception as e:
            MessageBox(self.root, ["Close"],
                       "Failed to replace bytes in the ISO\n"
                       "If the following message makes no sense, assume\n"
                       "that I have not yet finished support for part of the given file\n\n" + str(e),
                       "Problem during replacement",
                       warn=True)

    def close_cb(self):
        self.destroy()


class CarPartSection(customtkinter.CTkFrame):

    def __init__(self, parent, part_name="", on_change_cb=None, optional=False):
        super().__init__(parent)
        self.root = parent.root
        self.part_name = part_name
        self.on_change_cb = on_change_cb
        self.valid_path = False
        self.optional = optional

        self.replacement_part_size = 0

        self.columnconfigure(0, weight=20)
        self.columnconfigure(1, weight=20)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)

        self.part_label = customtkinter.CTkLabel(self, text=part_name, fg_color="gray30", corner_radius=6)
        self.part_label.grid(row=0, column=0, sticky="nesw", columnspan=4)

        self.part_path = customtkinter.StringVar()
        self.part_path_entry = customtkinter.CTkEntry(self, textvariable=self.part_path)
        self.part_path_entry.grid(row=1, column=0, padx=[0, 5], pady=5, sticky="nesw", columnspan=3)

        self.browse_part_button = customtkinter.CTkButton(self, text="Browse", command=self.browse_part_cb)
        self.browse_part_button.grid(row=1, column=3, pady=5, sticky="nesw")

        self.output_var = customtkinter.StringVar()
        self.output_var.set(f"")
        self.output_label = customtkinter.CTkLabel(self, textvariable=self.output_var, fg_color="gray30",
                                                   corner_radius=6)
        self.output_label.grid(row=2, column=0, sticky="nesw", columnspan=4)

    def browse_part_cb(self):
        print("Asking for replacement part file path")
        self.part_path.set(filedialog.askopenfilename(defaultextension='.BIN', initialdir=self.root.config.get_last_part_path()))
        value = self.part_path.get()
        try:
            with open(value, "rb") as file:
                # Get size of the part they wish to
                file.seek(0, os.SEEK_END)
                self.replacement_part_size = file.tell()
                self.output_var.set(f"Part is {self.replacement_part_size} bytes")
                if self.replacement_part_size % 16 != 0:
                    raise Exception("Part is not 16 byte aligned")
                file.seek(0, os.SEEK_SET)
                self.valid_path = self.replacement_part_size > 16
        except Exception as e:
            self.output_var.set(f"Failed to read replacement part, check path\n {e}")
            self.valid_path = False
            print(e)
        self.on_change_cb()

    def part_valid(self):
        if self.optional and not self.valid_path:
            return True

        return self.valid_path

class TextureSection(CarPartSection):

    def __init__(self, parent, required_size=(128, 128), part_name="", on_change_cb=None, optional=True):
        super().__init__(parent, part_name, on_change_cb, optional)
        self.required_size = required_size

    def browse_part_cb(self):
        self.part_path.set(filedialog.askopenfilename(defaultextension='.PNG', initialdir=self.root.config.get_last_part_path()))
        value = self.part_path.get()
        try:
            selected_image = Image.open(value)

            # Get the "part" size
            with open(value, "rb") as file:
                file.seek(0, os.SEEK_END)
                self.replacement_part_size = file.tell()

            if selected_image.size != self.required_size:
                self.valid_path = False
                self.output_var.set(f"Image size is incorrect must be {self.required_size}")
            else:
                self.valid_path = True
                self.output_var.set(f"Loaded texture, size {selected_image.size}\n")
        except Exception as e:
            self.output_var.set(f"Failed to read texture, check path\n {e}")
            self.valid_path = False
            print(e)
        self.on_change_cb()

    def part_valid(self):
        if self.optional and not self.valid_path:
            return True

        return self.valid_path