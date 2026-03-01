import os
import functools
from pathlib import Path

import re
import pycdlib
import customtkinter
from tkinter import filedialog, messagebox, Menu
from tkinter import ttk

from customtkinter import CTkFrame
# from elftools.elf.elffile import ELFFile

from choroq.egame.moddingui.common import *
from choroq.egame.moddingui.entries.game_entry import GameEntry, UnknownGameEntry
from choroq.egame.moddingui.entries.hg2_car_entry import HG2CarEntry, HG2ObjectEntry
from choroq.egame.moddingui.entries.hg2_course_entry import HG2CourseEntry
from choroq.egame.moddingui.entries.hg2_field_entry import HG2FieldEntry
from choroq.egame.moddingui.entries.hg2_shop_entry import HG2ShopEntry
from choroq.egame.moddingui.entries.hg3_car_entry import HG3CarEntry
from choroq.egame.moddingui.entries.hg3_course_entry import HG3CourseEntry
from egame_converter import EGameConverter

import choroq.egame.read_utils as U


class IsoTools:
    pass


class MessageBox(customtkinter.CTkToplevel):

    def __init__(self, master, buttons, message, title, callback=None, warn=False):
        super().__init__(master)
        self.wm_transient(master)
        self.wm_title(title)

        self.callback = callback

        message_label = customtkinter.CTkLabel(self, text=message, corner_radius=6)

        self.rowconfigure(0, weight=1)

        col = 0
        self.buttons = []
        for button_index, button_text in enumerate(buttons):
            button = customtkinter.CTkButton(self, text=button_text,
                                             command=functools.partial(self.callback_internal, button_index,
                                                                       button_text))
            if warn:
                # Colour button red
                button.configure(fg_color="Red")
                button.after(1, self.update())
            button.grid(row=1, column=col, sticky="nesw")
            self.buttons.append(button)
            col += 1
            self.columnconfigure(0, weight=1)
        message_label.grid(row=0, column=0, columnspan=col, sticky="nesw")

    def callback_internal(self, button_index, button_name):
        if self.callback is not None:
            self.callback(button_index, button_name)
            self.destroy()
        else:
            self.destroy()


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
        self.offsets = EntryMenu.find_offsets(self.original_data)

    def browse_part_cb(self):
        print("Asking for replacement part file path")
        self.part_path.set(filedialog.askopenfilename(defaultextension='.BIN'))

    def replace(self):
        # TODO: check if adding a new file works?
        print("Replacing file, checking everything")

        # Reopen the iso as read and write
        if not self.root.iso_writable:
            try:
                self.root.iso.close()
                self.root.iso.open(self.root.iso_path, 'r+b')
                self.root.iso_open = True
                self.root.iso_writable = True
            except Exception as e:
                print("failed to open iso")
                print(e)
                MessageBox(self.root, ["Close"],
                           "Failed reopen the ISO for writing\n" + str(e),
                           "Problem during replacement", warn=True)
                return False

        path = self.part_path.get()
        try:
            # write the replacement mesh at the correct location into the iso
            with open(path, "rb") as replacement_in:
                print("Replacing file, checking validity of given Part")
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


class ModdingUi(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        # Define on close
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.title("Choro-Q HG2 / HG3 modding tools")

        self.thread = None
        self.cancel_thread = None

        self.iso_path_var = customtkinter.StringVar()
        self.iso_path = None  # Path
        self.iso_open = False
        self.iso_writable = False  # Set to true if opened with r+b or wb
        self.iso = None  # CDlib iso

        self.entries = []

        self.game_version = None
        self.game_variant = None

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=10)

        self.button_frame = CTkFrame(self)
        self.button_frame.rowconfigure(0, weight=1)
        self.button_frame.columnconfigure(0, weight=1)
        self.button_frame.grid(row=0, column=0, padx=5, pady=5, sticky="new")
        button = customtkinter.CTkButton(self.button_frame, text="Open ISO", command=self.open_iso_cb)
        button.grid(row=0, column=0, padx=5, pady=5, sticky="nw")

        self.data_frame = CTkFrame(self)
        self.data_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nesw")
        self.data_frame.rowconfigure(0, weight=1)
        self.data_frame.columnconfigure(0, weight=20)
        self.data_frame.columnconfigure(1, weight=80)

        self.file_tree = FileEntryTree(self.data_frame)
        self.file_tree.grid(row=0, column=0, sticky="nesw")

        self.info_frame = FileInfoFrame(self.data_frame)
        self.info_frame.grid(row=0, column=1, sticky="nesw", padx=5)

        def on_file_item_clicked(event):
            file_id = self.file_tree.treeview.focus()
            # selected = self.treeview.selection() # multi select
            print(f"clicked {event} {file_id}")
            if file_id in self.file_tree.bound:
                self.info_frame.set_file(self.file_tree.bound[self.file_tree.treeview.focus()])

        self.bind('<<TreeviewSelect>>', on_file_item_clicked)

        self.entry_action_contextmenu = EntryMenu(self)

        def on_entry_file_right_clicked(event):
            file_id = self.file_tree.treeview.identify_row(event.y)
            # highlight the item on right click as well
            self.file_tree.treeview.focus(file_id)
            self.file_tree.treeview.selection_set(file_id)

            # selected = self.treeview.selection() # multi select
            print(f"right clicked {event} {file_id}")
            if file_id in self.file_tree.bound:
                self.entry_action_contextmenu.show(event.x_root, event.y_root, self.iso, self.file_tree.bound[file_id])

        self.file_tree.treeview.bind("<Button-3>", on_entry_file_right_clicked)

        # setup tree view
        bg_color = self._apply_appearance_mode(customtkinter.ThemeManager.theme["CTkFrame"]["fg_color"])
        text_color = self._apply_appearance_mode(customtkinter.ThemeManager.theme["CTkLabel"]["text_color"])
        selected_color = self._apply_appearance_mode(customtkinter.ThemeManager.theme["CTkButton"]["fg_color"])

        treestyle = ttk.Style()
        treestyle.theme_use('default')
        treestyle.configure("Treeview", background=bg_color, foreground=text_color, fieldbackground=bg_color,
                            borderwidth=0)
        treestyle.map('Treeview', background=[('selected', bg_color)], foreground=[('selected', selected_color)])
        treestyle.configure("Treeview.Heading",
                            foreground="white",
                            relief="flat")
        treestyle.map("Treeview.Heading",
                      background=[('active', '#3484F0')])

    def open_iso_cb(self):
        # Check if we already have an iso open
        if self.iso_open:
            MessageBox(self, ["Close application", "Cancel"],
                       "There is already an ISO open, please close the UI and reopen if you wish to switch ISOs",
                       "ISO open", callback=self.open_iso_discard_changes_cb,
                       warn=True)
            return

        # Warn user
        MessageBox(self, ["Understood"],
                   "Opening an iso is safe from modification, unless you press replace!",
                   "Warning", callback=self.ask_iso_path)

    def ask_iso_path(self, button_index, button_name):
        print("Asking for game iso path")
        self.iso_path_var.set(filedialog.askopenfilename(defaultextension="iso"))

        if self.iso_path_var.get() is None:
            MessageBox(self, ["Close"],
                       "The path supplied is either invalid or inaccessible",
                       "ISO not found", callback=None, warn=True)
            return

        # Check validity of the path/file
        self.iso_path = Path(self.iso_path_var.get())
        if not self.iso_path.exists() or not self.iso_path.is_file():
            self.iso_path = None
            MessageBox(self, ["Close"],
                       "The path supplied is either invalid or inaccessible",
                       "ISO not found", callback=None, warn=True)
            return

        if not self.check_and_load_iso():
            self.iso_path = None
            MessageBox(self, ["Close"],
                       "The given ISO path is invalid, or incompatible",
                       "ISO not valid", callback=None, warn=True)
            return

    def check_and_load_iso(self) -> bool:
        # Open iso using cdlib, and check what the disk is
        self.iso = pycdlib.PyCdlib()
        try:
            self.iso.open(self.iso_path, 'rb')
            self.iso_open = True
            # read only, as we do not want to edit unless the user says so
            self.iso_writable = False
        except Exception as e:
            print("failed to open iso")
            print(e)
            return False

        # Check for valid iso:
        hg2_required_folders = {
            "CAR0", "CAR1", "CAR2", "CAR3", "CAR4", "CARS",
            "ACTION", "COURSE", "FLD",
            "ITEM", "SHOP", "SOUND",
            "SYS"}
        hg3_required_folders = {"CARS", "COURSE", "ITEM", "SOUND", "SYS"}
        game_versions = {
            "SLES_513.56": (GameVersion.CHOROQ_HG_2, "EUR"),
            "SLPM_621.04": (GameVersion.CHOROQ_HG_2, "JP"),
            "SLKA_150.08": (GameVersion.CHOROQ_HG_2, "KOR"),
            "SLUS_203.98": (GameVersion.CHOROQ_HG_2, "US"),
            "SLPM 62355": (GameVersion.CHOROQ_HG_2, "JP"),  # Takara the Best Choro-Q HG2
            "SLPM 62761": (GameVersion.CHOROQ_HG_2, "JP"),  # Atlus Best Collection Choro-Q HG2

            "SLES_519.11": (GameVersion.CHOROQ_HG_3, "EUR"),
            "SLPM_622.44": (GameVersion.CHOROQ_HG_3, "JP"),
            "SLPM_625.95": (GameVersion.CHOROQ_HG_3, "JP"),  # Takara the Best Choro-Q HG3
            "SLPM_627.71": (GameVersion.CHOROQ_HG_3, "JP"),  # Atlus Best Collection Choro-Q HG3
        }

        folders = []
        subfolders = False

        for dirname, dirlist, filelist in self.iso.walk(iso_path='/'):
            folders.append(dirname)
            if dirlist:
                subfolders = True
            print("Dirname:", dirname, ", Dirlist:", dirlist, ", Filelist:", filelist)

        # Check for folder validity of some sort
        folders_valid = False
        folders_valid |= set(hg2_required_folders).issubset(set(folders))
        folders_valid |= set(hg3_required_folders).issubset(set(folders))

        # Check and read SYSTEM.CNF
        cnfdata = BytesIO()
        self.iso.get_file_from_iso_fp(cnfdata, iso_path='/SYSTEM.CNF;1')

        cnfdata.seek(0)
        cnf = PS2Cnf(cnfdata)
        # Check version
        self.game_version, self.game_variant = game_versions.get(cnf.elf_name, (GameVersion.UNSET, None))
        print(self.game_version)
        print(self.game_variant)

        self.populate_entry_table()
        self.file_tree.populate(self.entries)

        return True

    def open_iso_discard_changes_cb(self, button_index, button_name):
        if button_index == 0:
            # TODO: Clear changes, close iso, and recall function
            self.iso_open = False
            try:
                self.iso.close()
                self.iso_open = False
                self.destroy()
            except Exception as e:
                print(e)
            return
        # Otherwise user wishes to cancel the open request
        pass

    def populate_entry_table(self):
        # Work through each file in the iso,
        # creating the required GameEntry instances for each file,
        # and structure as needed

        if self.game_version == GameVersion.CHOROQ_HG_2:
            matches = [
                (re.compile("/CAR[0-4,S]/Q[0-9]([0-9]+).BIN"), HG2CarEntry),
                (re.compile("/CARS/TIRE.BIN"), HG2ObjectEntry),
                (re.compile("/CARS/WHEEL.BIN"), HG2ObjectEntry),
                (re.compile("/CARS/PARTS.BIN"), HG2ObjectEntry),
                (re.compile("/COURSE/C[0-9][0-9].BIN"), HG2CourseEntry),
                (re.compile("/ACTION/A[0-9][0-9].BIN"), HG2CourseEntry),
                (re.compile("/FIELD/[0-9][0-9][0-9].BIN"), HG2FieldEntry),
                (re.compile("/SHOP/T[0-9][0-9].BIN"), HG2ShopEntry),
            ]
            facade = self.iso.get_iso9660_facade()
            self.entries = {}

            for dirname, dirlist, filelist in self.iso.walk(iso_path='/'):
                folder_entries = {}
                for matcher, entry_type in matches:
                    for filename in filelist:
                        path = f"{dirname}/{filename}"
                        if matcher.match(path):
                            path = f"{dirname}/{filename}"
                            record = facade.get_record(path)
                            entry = entry_type(dirname, path, self.game_version, self.game_variant, record)
                            folder_entries[filename] = entry

                self.entries[dirname] = folder_entries
        elif self.game_version == GameVersion.CHOROQ_HG_3:
            matches = [
                (re.compile("/CARS/Q[0-9]([0-9]+).BIN"), HG3CarEntry),
                (re.compile("/COURSE/C[0-9][0-9](L|M|S|).BIN"), HG3CourseEntry),
                (re.compile("/COURSE/A[0-9][0-9].BIN"), HG3CourseEntry),
                # (re.compile("SYS/T[0-9][0-9].BIN"), HG3TownEntry),
                # (re.compile("SYS/T00S01.BIN"), HG3TownEntry),
            ]
            facade = self.iso.get_iso9660_facade()
            self.entries = {}

            for dirname, dirlist, filelist in self.iso.walk(iso_path='/'):
                folder_entries = {}
                for matcher, entry_type in matches:
                    for filename in filelist:
                        path = f"{dirname}/{filename}"
                        if matcher.match(path):
                            path = f"{dirname}/{filename}"
                            record = facade.get_record(path)
                            entry = entry_type(dirname, path, self.game_version, self.game_variant, record)
                            folder_entries[filename] = entry

                self.entries[dirname] = folder_entries

    def on_close(self):
        if self.iso_open:
            if messagebox.askokcancel("Quit", "Do you want to quit?"):
                try:
                    self.iso.close()
                finally:
                    self.iso_open = False
                    self.destroy()
        else:
            self.destroy()


class FileInfoFrame(CTkFrame):

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=100)
        # self.rowconfigure(3, weight=1)

        self.top_label = customtkinter.CTkLabel(self, text="File Info", corner_radius=6)
        self.top_label.grid(row=0, column=0, sticky="new")
        self.top_label.cget("font").configure(size=15)

        self.name_var = customtkinter.StringVar()
        self.name_label = customtkinter.CTkLabel(self, textvariable=self.name_var, corner_radius=6)
        self.name_label.grid(row=1, column=0, sticky="nesw")
        self.name_label.cget("font").configure(size=15)

        self.main_text = customtkinter.CTkTextbox(self, corner_radius=6)
        # self.main_text.configure(state="disabled")
        self.main_text.grid(row=2, column=0, padx=5, pady=5, sticky="nesw")

        # self.action_row = CTkFrame(self)
        #self.action_row.rowconfigure(3, weight=1)
        #self.action_row.columnconfigure(0, weight=1)
        # self.action_row.grid(row=3, column=0, padx=5, pady=5, sticky="sew")

    def set_file(self, selected):
        print(selected)
        dirname, filename, entry = selected

        # Clear out old text
        self.main_text.delete("0.0", "end")

        # Build file info string
        self.main_text.insert("end", "File info:\n")
        self.name_var.set(f"{entry.convert_name()} - {entry.get_type_string()}")
        self.main_text.insert("end", f"Filename: \t\t{filename}\t\t AKA: "
                                     f"{entry.convert_name()}\n")
        self.main_text.insert("end", f"Offset within iso:\t\tdecimal: "
                                     f"{entry.get_offset()}\t\thex: 0x{entry.get_offset():X}\t(bytes)\n")
        self.main_text.insert("end", f"Sector of file:\t\tdecimal: "
                                     f"{entry.get_sector()}\t\thex: 0x{entry.get_sector():X}\n")
        self.main_text.insert("end", f"File size:\t\tdecimal: "
                                     f"{entry.get_size()}\t\thex: 0x{entry.get_size():X}\t(bytes)\n")

        self.main_text.insert("end", "\n")

        # Put info on what is understood
        self.main_text.insert("end", f"File type: {entry.get_type_string()}\n")
        self.main_text.insert("end", entry.descriptor() + "\n")


class FileEntryTree(CTkFrame):

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.label = customtkinter.CTkLabel(self, text="Disk Contents", corner_radius=6)
        self.label.grid(row=0, sticky="nesw")

        self.treeview = ttk.Treeview(self, show=("tree", "headings"), selectmode="browse",
                                     columns=("pos-sector", "size", "pos-bytes"))
        self.treeview.grid(row=1, sticky="nesw")

        self.treeview.heading("#0", text="Filename")
        self.treeview.heading("pos-sector", text="Position (sector)")
        self.treeview.heading("size", text="Size (bytes)")
        self.treeview.heading("pos-bytes", text="Position (bytes)")
        self.treeview.column("#0", width=100, anchor='w')
        self.treeview.column("pos-sector", width=50, anchor='w')
        self.treeview.column("size", width=50, anchor='w')
        self.treeview.column("pos-bytes", width=50, anchor='w')

        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=100)
        self.columnconfigure(0, weight=1)
        self.bound = {}

    def populate(self, entries):
        self.bound = {}

        def item_opened(event):
            id = self.treeview.focus()
            print(f"opened {event} {self.treeview.focus()} {type({self.treeview.focus()})}")
            if id in self.bound:
                print(self.bound[self.treeview.focus()])

        def item_closed(event):
            id = self.treeview.focus()
            print(f"closed {event} {self.treeview.focus()} {type({self.treeview.focus()})}")
            if id in self.bound:
                print(self.bound[self.treeview.focus()])

        for dirname in entries:
            folder_entries = entries[dirname]
            # Add root for this dir
            self.treeview.insert('', 'end', dirname, text=dirname)
            for filename in reversed(folder_entries):
                entry = folder_entries[filename]
                id = self.treeview.insert(dirname, 'end', None,
                                          text=entry.get_file_name(),
                                          values=(entry.get_sector(), entry.get_size(), entry.get_offset()))
                self.bound[id] = (dirname, filename, entry)

        # self.treeview.bind('<<TreeviewSelect>>', item_clicked)
        # self.treeview.bind('<<TreeviewOpen>>', item_opened)
        # self.treeview.bind('<<TreeviewClose>>', item_closed)

        # self.treeview.insert('', '0', 'i1', text='Python')
        # self.treeview.insert('', '1', 'i2', text='Customtkinter')
        # self.treeview.insert('', '2', 'i3', text='Tkinter')
        # self.treeview.insert('i2', 'end', 'Frame', text='Frame')
        # self.treeview.insert('i2', 'end', 'Label', text='Label')
        # self.treeview.insert('i3', 'end', 'Treeview', text='Treeview')
        # self.treeview.move('i2', 'i1', 'end')
        # self.treeview.move('i3', 'i1', 'end')


class EntryMenu(Menu):

    def __init__(self, root):
        super().__init__(root)
        self.root = root

    def show(self, x, y, iso, entry):
        self.delete(0, "end")  # remove old options

        dirname, filename, entry = entry

        self.add_command(label="Dump", command=functools.partial(self.dump_cb, iso, entry))
        if entry.get_extractable():
            self.add_command(label="Extract", command=functools.partial(self.extract_cb, iso, entry))
        if entry.get_editable():
            with_str = "HG3"
            if entry.game_version == GameVersion.CHOROQ_HG_3:
                with_str = "HG2"
            if type(entry) is HG2CarEntry:
                self.add_command(label=f"Replace with {with_str}",
                                 command=functools.partial(self.import_replacement, iso, entry))
            if entry.game_version == GameVersion.CHOROQ_HG_2:
                self.add_command(label=f"Replace part",
                                 command=functools.partial(self.import_hg2_part, self.root, iso, entry))

        self.post(x, y)

    def dump_cb(self, iso: pycdlib.PyCdlib, entry: GameEntry):
        # Open save file dialog
        print("Asking for destination file, to save dump to")
        path = filedialog.asksaveasfilename(defaultextension=entry.extension, initialfile=entry.basename)
        try:
            with open(path, "wb") as fout:
                iso.get_file_from_iso_fp(fout, iso_path=entry.path)

                MessageBox(self.root, ["Close"], "Dump complete", "Completed")
        except Exception as e:
            MessageBox(self.root, ["Close"],
                       "Failed to dump the file from the ISO\n" + str(e),
                       "Problem dumping file", warn=True)

    def extract_cb(self, iso: pycdlib.PyCdlib, entry: GameEntry):
        # Open save file dialog
        print("Asking for destination folder, to save extracted data to")
        path = filedialog.askdirectory(title="Select the output folder")
        try:
            if entry.extract(iso, [], path):
                MessageBox(self.root, ["Close"], "Extraction complete", "Completed")
            else:
                MessageBox(self.root, ["Close"], "Extraction failed", "Failed to extract", warn=True)
        except Exception as e:
            MessageBox(self.root, ["Close"],
                       "Failed to extract from the ISO\n" + str(e),
                       "Problem extracting file", warn=True)

    def import_replacement(self, iso: pycdlib.PyCdlib, entry: GameEntry):
        # Warn user
        if self.root.iso_writable:
            return self.import_replacement_confirmed(iso, entry, 0, 0)
        MessageBox(self.root, ["Understood"],
                   "This method will attempt to edit your game iso, IN PLACE,\n"
                   "I recommend you make a clean copy before performing any modifications\n"
                   "such as replacements, as this cannot be undone using this tool\n"
                   "The first thing it will do is reopen the iso, as writable if allowed",
                   "Warning",
                   callback=functools.partial(self.import_replacement_confirmed, iso, entry),
                   warn=True)

    def import_hg2_part(self, root, iso: pycdlib.PyCdlib, entry: GameEntry):
        # Warn user
        if self.root.iso_writable:
            return self.import_part_hg2_confirmed(iso, entry, 0, 0)
        MessageBox(self.root, ["Understood"],
                   "This method will attempt to edit your game iso, IN PLACE,\n"
                   "I recommend you make a clean copy before performing any modifications\n"
                   "such as replacements, as this cannot be undone using this tool\n"
                   "The first thing it will do is reopen the iso, as writable if allowed",
                   "Warning",
                   callback=functools.partial(self.import_part_hg2_confirmed, root, iso, entry),
                   warn=True)

    def import_replacement_confirmed(self, iso: pycdlib.PyCdlib, entry: GameEntry, button_index, button_name):
        # Reopen the iso as read and write
        if not self.root.iso_writable:
            try:
                self.root.iso.close()
                self.root.iso.open(self.root.iso_path, 'r+b')
                self.root.iso_open = True
                self.root.iso_writable = True
            except Exception as e:
                print("failed to open iso")
                print(e)
                MessageBox(self.root, ["Close"],
                           "Failed reopen the ISO for writing\n" + str(e),
                           "Problem during replacement", warn=True)
                return False

        # TODO handle this in the entry class?
        # Open a bin file, extracted from HG2 or HG3, which ever is not the same
        # as the open game version, then convert the given bin into this iso's format
        # After we know the size, we can calculate if it will fit
        # If it will fit, copy out the texture transfer bytes (ensures addressing issues)
        # If not, tell user to try a different mesh
        print("Asking for replacement HG[2/3] BIN")
        path = filedialog.askopenfilename(defaultextension='.BIN')
        try:
            with open(path, "rb") as replacement_in:
                replacement_bytes = BytesIO()
                if entry.game_version == GameVersion.CHOROQ_HG_2:
                    EGameConverter.convert_hg3_to_hg2_stream(replacement_in, replacement_bytes)
                else:
                    EGameConverter.convert_hg2_to_hg3_stream(replacement_in, replacement_bytes)

                replacement_bytes.seek(0, os.SEEK_END)
                converted_size = replacement_bytes.tell()
                replacement_bytes.seek(0, os.SEEK_SET)

                if converted_size > entry.get_size():
                    MessageBox(self.root, ["Close"],
                               "Replacement unsuccessful, the car would be larger than "
                               f"the one you wish to replace, size {converted_size}",
                               "Not possible",
                               warn=True)
                else:
                    # replace texture header (+palette) with original to prevent clashes (addresses)
                    original_data = BytesIO()

                    iso.get_file_from_iso_fp(original_data, iso_path=entry.path)
                    # Find texture offset
                    original_data.seek(0, os.SEEK_SET)
                    offsets = EntryMenu.find_offsets(original_data)

                    texture_offset = offsets[-2]
                    original_data.seek(texture_offset, os.SEEK_SET)
                    original_texture_header = original_data.read(112)
                    # Skip original texture data
                    original_data.seek(texture_offset + 112 + 256 * 256, os.SEEK_SET)
                    original_palette_header = original_data.read(112)
                    # Skip original palette data
                    original_data.seek(texture_offset + 112 + 256 * 256 + 112 + 1024, os.SEEK_SET)
                    # read last bit + flush
                    original_flush = original_data.read(48)

                    # Find offsets again in this data and write it back, very similar code
                    replacement_bytes.seek(0, os.SEEK_SET)
                    offsets = EntryMenu.find_offsets(replacement_bytes)
                    texture_offset = offsets[-2]
                    # Jump to the texture subfile
                    replacement_bytes.seek(texture_offset, os.SEEK_SET)
                    replacement_bytes.write(original_texture_header)
                    # Skip past texture data, to palette header
                    replacement_bytes.seek(texture_offset + 112 + 256 * 256, os.SEEK_SET)
                    replacement_bytes.write(original_palette_header)
                    # Skip past palette data
                    replacement_bytes.seek(texture_offset + 112 + 256 * 256 + 112 + 1024, os.SEEK_SET)
                    # read last bit + flush
                    replacement_bytes.write(original_flush)

                    # Finally write back the replaced mesh

                    # Dirty, open file again then write where it should be
                    # without doing this the data positions change
                    with open(entry.record.data_fp.name, "r+b") as edited_out:
                        edited_out.seek(entry.record.fp_offset)
                        edited_out.write(replacement_bytes.getbuffer().tobytes())

                    # Do not use this function, it changes LBA and file positions
                    # This is here to remind me to not do this
                    # # Pad data until replacement is the same size, as required
                    # replacement_bytes.seek(0, os.SEEK_END)
                    # replacement_bytes.write(b'\x00' * (entry.get_size() - converted_size))
                    # converted_size = replacement_bytes.tell()
                    # replacement_bytes.seek(0, os.SEEK_SET)
                    # iso.modify_file_in_place(replacement_bytes, converted_size, entry.path)

                    MessageBox(self.root, ["Close"],
                               f"Replacement successful (replaced {converted_size} bytes)",
                               "Completed")
        except Exception as e:
            MessageBox(self.root, ["Close"],
                       "Failed to replace bytes in the ISO\n"
                       "If the following message makes no sense, assume\n"
                       "that I have not yet finished support for part of the given file\n\n" + str(e),
                       "Problem during replacement",
                       warn=True)

    def import_part_hg2_confirmed(self, root, iso: pycdlib.PyCdlib, entry: GameEntry, button_index, button_name):
        CarPartReplaceMenu(root, iso, entry)

    @staticmethod
    def find_offsets(stream):
        offsets = [U.readLong(stream)]
        read_more = True
        while read_more:
            offset = U.readLong(stream)
            if offset < offsets[-1] or offset == 0 or stream.tell() >= offsets[0]:
                read_more = False
                break
            offsets.append(offset)

        return offsets


if __name__ == '__main__':
    app = ModdingUi()
    app.mainloop()

    if app.thread is not None:
        app.thread.join()
