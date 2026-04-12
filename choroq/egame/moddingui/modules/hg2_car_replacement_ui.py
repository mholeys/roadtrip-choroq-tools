import os
import functools

import re
import pycdlib
import customtkinter
from tkinter import filedialog, messagebox, Menu
from tkinter import ttk

from choroq.egame.moddingui.modules.message_box import MessageBox

from choroq.egame.moddingui.common import *
from choroq.egame.moddingui.entries.game_entry import GameEntry
from choroq.egame.moddingui.entries.hg2_object_entry import HG2ObjectEntry

import choroq.read_utils as U
from choroq.egame.moddingui.modules.helper import Helper


class CarPartReplaceMenu(customtkinter.CTkToplevel):

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

        self.columnconfigure(0, weight=20)
        self.columnconfigure(1, weight=20)
        self.columnconfigure(2, weight=20)
        self.columnconfigure(3, weight=20)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)
        self.rowconfigure(3, weight=1)
        self.rowconfigure(4, weight=1)
        self.rowconfigure(5, weight=1)
        self.rowconfigure(6, weight=1)
        self.rowconfigure(7, weight=1)

        self.part_label = customtkinter.CTkLabel(self, text="Part path", fg_color="gray30", corner_radius=6)
        self.part_label.grid(row=0, column=0, padx=5, pady=5, sticky="nesw", columnspan=4)

        self.part_path = customtkinter.StringVar()
        self.part_path_entry = customtkinter.CTkEntry(self, textvariable=self.part_path)
        self.part_path_entry.grid(row=1, column=0, sticky="nesw", columnspan=3)

        self.browse_part_button = customtkinter.CTkButton(self, text="Browse", command=self.browse_part_cb)
        self.browse_part_button.grid(row=1, column=3, padx=5, pady=5, sticky="nesw")

        self.offsets_list = customtkinter.StringVar()
        self.offsets_list.set(f"Offset table: \n {str(self.offsets)}")
        self.offsets_list_label = customtkinter.CTkLabel(self, textvariable=self.offsets_list, fg_color="gray30", corner_radius=6)
        self.offsets_list_label.grid(row=2, column=0, padx=5, pady=5, sticky="nesw", columnspan=4)

        self.output_var = customtkinter.StringVar()
        self.output_var.set(f"")
        self.output_label = customtkinter.CTkLabel(self, textvariable=self.output_var, fg_color="gray30", corner_radius=6)
        self.output_label.grid(row=3, column=0, padx=5, pady=5, sticky="nesw", columnspan=4)

        self.valid_var = customtkinter.StringVar()
        self.valid_var.set(f"")
        self.valid_label = customtkinter.CTkLabel(self, textvariable=self.valid_var, fg_color="gray30", corner_radius=6)
        self.valid_label.grid(row=4, column=0, padx=5, pady=5, sticky="nesw", columnspan=4)

        parts_string = [
            "[0] Body & [1] Lights & [2] Brake-light",
            "[0] Low Poly Body & [1] Lights",
            "[0] Spoiler (default), [1] optional high level light",
            "[0] Spoiler (wing)",
            "[0] Jets",
            "[0] Stickers"]

        if type(entry) == HG2ObjectEntry:
            if entry.filename == "TIRE.BIN":
                parts_string = [
                    "[0] Front left wheel (world)",
                    "[0] Front right wheel (world)",
                    "[0] Pair wheels (rear) (world)",
                    "[0] 4 wheels (far away car) (world)",
                    "[0] Big tire left",
                    "[0] Big tire right",
                ]
            elif entry.filename == "WHEEL.BIN":
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
            elif entry.filename == "PARTS.BIN":
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

        if entry.filename == "WHEEL.BIN":
            car_part_count = len(self.offsets) - 1  # -1 for eof, no texture
        else:
            car_part_count = len(self.offsets) - 2  # -2 one for texture, and one for eof

        print(F"Car part count {car_part_count} vs {len(parts_string)}")
        self.part_options = []
        self.part_sizes = []

        self.replacement_part_size = 0

        for i in range(len(parts_string)):
            size = self.offsets[i+1] - self.offsets[i]
            self.part_sizes.append(size)

            if car_part_count == len(parts_string):
                part = parts_string[i]
            else:
                part = f"Part [{i}]"
            self.part_options.append(f"Part [{i}]: {part}: size: {size}")
            print(self.part_options[i])

        self.part_chosen = customtkinter.StringVar(value=self.part_options[0])

        # Dropdown menu
        self.drop_down_label = customtkinter.CTkLabel(self, text="Part to replace:", fg_color="gray30", corner_radius=6)
        self.drop_down_label.grid(row=5, column=0, padx=5, pady=5, sticky="nesw")
        self.part_drop_down = customtkinter.CTkOptionMenu(self, variable=self.part_chosen, values=self.part_options)
        self.part_drop_down.grid(row=5, column=1, padx=5, pady=5, columnspan=3, sticky="nesw")

        # Add callback for on change event, for the part chooser
        self.part_chosen.trace_add(['read', 'write', 'unset'], self.on_part_choice_change)
        # Add callback for when user selects a new file
        self.part_path.trace_add(['read', 'write', 'unset'], self.on_replacement_file_selected)

        # TODO: have checkbox to allow overwriting LP body, only do this on replace (and check and lock if o[0] == 0[1])

        self.replace_btn = customtkinter.CTkButton(self, text="Replace", command=self.replace, state="disabled", fg_color="Red")
        self.close_btn = customtkinter.CTkButton(self, text="Close", command=self.close_cb)
        self.replace_btn.grid(row=6, column=0, columnspan=2, sticky="nesw")
        self.close_btn.grid(row=6, column=3, columnspan=2, sticky="nesw")

        self.columnconfigure(0, weight=1)

        self.check_size_valid()

    def check_size_valid(self):
        print("Checking if part will fit")
        value = self.part_chosen.get()
        if value in self.part_options:
            index = self.part_options.index(value)
            #print(f"Does it ({self.replacement_part_size}) fit for part: {value}")
            # Disable unless it fits
            self.replace_btn.configure(state="disabled")
            # Colour button red
            self.replace_btn.configure(fg_color="Red")
            if self.replacement_part_size != 0:
                # TODO handle check for when we allow replacing/merging low poly
                if self.replacement_part_size <= self.part_sizes[index]:
                    # Enable replace button, as it fits
                    self.replace_btn.configure(state="enabled")
                    self.replace_btn.configure(fg_color="Blue")
                    self.replace_btn.after(1, self.update())
                    self.valid_var.set("Replacement part will fit")
                else:
                    self.valid_var.set("Replacement part too big!")
        else:
            self.valid_var.set("Invalid part choice")
            print(f"Invalid part choice {value}")
        self.replace_btn.after(1, self.update())

    def on_replacement_file_selected(self, variable, other, trace_mode):
        print(f"File: {variable} | {other} | {trace_mode}")
        value = self.root.getvar(variable)
        print(value)
        if trace_mode == 'write':
            print(f"New replacement part path {value}")
            try:
                with open(value, "rb") as file:
                    # Get size of the part they wish to
                    file.seek(0, os.SEEK_END)
                    self.replacement_part_size = file.tell()
                    file.seek(0, os.SEEK_SET)
                    self.output_var.set(f"Replacement file is {self.replacement_part_size} bytes")
                    self.check_size_valid()
            except Exception as e:
                self.output_var.set("Failed to read replacement part, check path\n {e}")
                print(e)

    def on_part_choice_change(self, variable, other, trace_mode):
        self.check_size_valid()

    def load_offsets(self):
        self.offsets = Helper.find_offsets(self.original_data)

    def browse_part_cb(self):
        print("Asking for replacement part file path")
        self.part_path.set(filedialog.askopenfilename(defaultextension='.BIN', initialdir=self.root.config.get_last_part_path()))

    def replace(self):
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
                            raise Exception(f"Failed to replace, did not write full size")

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