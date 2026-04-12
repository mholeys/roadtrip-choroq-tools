import os
import functools

import re
import pycdlib
import customtkinter
from tkinter import filedialog, messagebox, Menu
from tkinter import ttk

from choroq.egame.moddingui.entries.hg2_car_entry import HG2CarEntry
from choroq.egame.moddingui.modules.message_box import MessageBox

from choroq.egame.moddingui.common import *
from choroq.egame.moddingui.entries.game_entry import GameEntry
from choroq.egame.moddingui.entries.hg2_object_entry import HG2ObjectEntry

import choroq.read_utils as U
from choroq.egame.moddingui.modules.helper import Helper


class FullCarReplaceMenu(customtkinter.CTkToplevel):

    def __init__(self, root, iso: pycdlib.PyCdlib, entry: GameEntry):
        super().__init__(root)
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

        self.part_count = 0
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

        if type(self.entry) == HG2CarEntry:
            self.part_count = 7

            self.columnconfigure(0, weight=20)
            self.columnconfigure(1, weight=20)
            self.columnconfigure(2, weight=20)
            self.columnconfigure(3, weight=20)

            for row in range(self.part_count):
                self.rowconfigure(row, weight=1)
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
                self.rowconfigure(part_i, weight=1)
                ui_part = CarPartSection(self, part_config[0], self.on_part_change_cb, part_config[1])
                ui_part.grid(row=part_i, column=0, columnspan=4, padx=5, pady=5, sticky="nesw")
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
        self.output_label.grid(row=self.part_count+1, column=0, padx=5, pady=5, sticky="nesw", columnspan=4)

        self.valid_var = customtkinter.StringVar()
        self.valid_var.set(f"")
        self.valid_label = customtkinter.CTkLabel(self, textvariable=self.valid_var, fg_color="gray30", corner_radius=6)
        self.valid_label.grid(row=self.part_count+2, column=0, padx=5, pady=5, sticky="nesw", columnspan=4)

        self.replace_btn = customtkinter.CTkButton(self, text="Replace", command=self.replace, state="disabled", fg_color="Red")
        self.close_btn = customtkinter.CTkButton(self, text="Close", command=self.close_cb)
        self.replace_btn.grid(row=self.part_count+3, column=0, columnspan=2, sticky="nesw")
        self.close_btn.grid(row=self.part_count+3, column=3, columnspan=2, sticky="nesw")

        self.columnconfigure(0, weight=1)

        self.check_size_valid()

    def check_size_valid(self):
        print("Checking if part will fit")

        all_valid_str = "All parts valid/selected"
        has_all_parts = True

        for i, part_ui in enumerate(self.parts_ui):
            if not part_ui.part_valid():
                has_all_parts = False
                break

        if not has_all_parts:
            all_valid_str = "Missing a required part"

        # Disable unless it fits
        self.replace_btn.configure(state="disabled")
        # Colour button red
        self.replace_btn.configure(fg_color="Red")
        if self.replacement_total_size != 0:
            if self.replacement_total_size <= self.offsets[-1]:
                # Enable replace button, as it fits
                self.replace_btn.configure(state="enabled")
                self.replace_btn.configure(fg_color="Blue")
                self.replace_btn.after(1, self.update())
                self.valid_var.set(f"Replacement will fit. {all_valid_str}")
            else:
                self.valid_var.set(f"Replacement too big! {all_valid_str}")
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
                  f"Tsize: {self.texture_tag_data[1]}\n"
                  f"Chead: {len(self.texture_tag_data[2])}\n"
                  f"Csize: {self.texture_tag_data[3]}\n"
                  f"Ctail: {len(self.texture_tag_data[4])}\n")


    def replace(self):
        # TODO: allow skipping of lp body, by making offsets the same as body when invalid aprt
        # TODO: write total replacement
        # TODO: write texture loading/selection (do I take this opportunity to do texture conversion from png too)
        # TODO: write out texture/clut header and tag bits, with replacement texture as well
        # Todo: have texture selection on ui (with option to leave as is)
        # TODO: refine size calculation, with texture size too
        # TODO: build new offset table from parts

        # TODO: check if adding a new file works?
        print("Replacing file, checking everything")

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

        path = self.part_path.get()
        try:
            # write the replacement mesh at the correct location into the iso
            with open(path, "rb") as replacement_in:
                print("Replacing file, checking validity of given Part")
                self.root.config.update_part_path(path)

                offset1 = U.readLong(replacement_in)
                offset2 = U.readLong(replacement_in)
                size1 = U.readLong(replacement_in)
                size2 = U.readLong(replacement_in)

                # Sanity check the given data
                invalid_data = False
                if offset1 > self.replacement_part_size:
                    invalid_data = True
                if offset2 > self.replacement_part_size:
                    invalid_data = True
                if size1 > 65535:
                    invalid_data = True
                if size2 > 65535:
                    invalid_data = True

                if invalid_data:
                    MessageBox(self.root, ["Close"], f"Issue with the given replacement part", "Problem", warn=True)
                    return
                else:
                    print("Replacing file, replacement seems valid")

                # Move back to the start after sanity check
                replacement_in.seek(0, os.SEEK_SET)

                # Find which offset we are replacing, and move to it
                part_value = self.part_chosen.get()
                if part_value in self.part_options:
                    index = self.part_options.index(part_value)

                    part_offset = self.offsets[index]

                    # Dirty, open file again then write where it should be,
                    # without doing this the data positions change
                    print(f"Replacing file, replacing {part_value}")
                    with open(self.entry.record.data_fp.name, "r+b") as edited_out:
                        # Move to the iso's file position, and move to the start of the part
                        part_offset = self.entry.record.fp_offset + part_offset
                        edited_out.seek(part_offset, os.SEEK_SET)

                        amount_written = edited_out.write(replacement_in.read())
                        if amount_written < self.replacement_part_size:
                            print(f"Failed to replace, did not write full size")

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
                else:
                    MessageBox(self.root, ["Close"],
                               f"Issue with destination part, probably a bug", "Problem", warn=True)
                    return
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