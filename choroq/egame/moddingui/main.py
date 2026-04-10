import os
import functools

import re
import pycdlib
import customtkinter
from tkinter import filedialog, messagebox, Menu
from tkinter import ttk

from customtkinter import CTkFrame
# from elftools.elf.elffile import ELFFile

from choroq.egame.moddingui.common import *
from choroq.egame.moddingui.entries.game_entry import GameEntry
from choroq.egame.moddingui.entries.hg2_car_entry import HG2CarEntry
from choroq.egame.moddingui.entries.hg2_object_entry import HG2ObjectEntry
from choroq.egame.moddingui.entries.hg2_course_entry import HG2CourseEntry
from choroq.egame.moddingui.entries.hg2_field_entry import HG2FieldEntry
from choroq.egame.moddingui.entries.hg2_shop_entry import HG2ShopEntry
from choroq.egame.moddingui.entries.hg3_car_entry import HG3CarEntry
from choroq.egame.moddingui.entries.hg3_course_entry import HG3CourseEntry
from choroq.egame.moddingui.modules.hg2_option_handler import HG2CarOptionHandler
from choroq.egame.moddingui.modules.hg3_option_handler import HG3CarOptionHandler
from egame_converter import EGameConverter

import choroq.read_utils as U

from modules.message_box import MessageBox
from modules.helper import Helper

class IsoTools:
    pass


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
        self.iso = None  # CDlib iso

        self.entries = []

        self.game_version = None
        self.game_variant = None

        # Setup/read config
        self.config = UiConfig('config.txt')
        self.config.parse_config()

        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=10)

        self.button_frame = CTkFrame(self)
        self.button_frame.rowconfigure(0, weight=1)
        self.button_frame.columnconfigure(0, weight=1)
        self.button_frame.grid(row=0, column=0, padx=5, pady=5, sticky="new")
        button = customtkinter.CTkButton(self.button_frame, text="Open ISO", command=self.open_iso_cb)
        button.grid(row=0, column=0, padx=5, pady=5, sticky="nw")

        button = customtkinter.CTkButton(self.button_frame, text="Reopen Last ISO", command=self.open_last_iso_cb)
        button.grid(row=0, column=1, padx=5, pady=5, sticky="nw")

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

        if self.config.has_warnings():
            # Warn user
            MessageBox(self, ["Understood"],
                       "Opening an iso is safe from modification, unless you press replace!",
                       "Warning", callback=self.ask_iso_path)
        else:
            self.ask_iso_path(0, '')

    def open_last_iso_cb(self):
        # Check if we already have an iso open, if os skip as not allowed for now
        if self.iso_open:
            return

        last_iso_path = self.config.get_last_iso_path()
        if last_iso_path is None:
            return
        self.iso_path_var.set(last_iso_path)
        if self.config.has_warnings():
            # Warn user
            MessageBox(self, ["Understood"],
                       "Opening an iso is safe from modification, unless you press replace!",
                       "Warning", callback=self.open_iso_from_path_var)
        else:
            self.open_iso_from_path_var()

    def ask_iso_path(self, button_index, button_name):
        print("Asking for game iso path")
        self.iso_path_var.set(filedialog.askopenfilename(defaultextension="iso", initialfile=self.config.get_last_iso_path()))
        self.open_iso_from_path_var()

    def open_iso_from_path_var(self, button_index=0, button_name=''):
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

            self.config.update_iso_path(self.iso_path)
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
                (re.compile("/FLD/[0-9][0-9][0-9].BIN"), HG2FieldEntry),
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
        self.config.save_config()
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
        # All entries can be dumped
        self.add_command(label="Dump", command=functools.partial(self.dump_cb, iso, entry))

        options = OptionsProvider.get_options(entry)
        for option, func in options:
            self.add_command(label=option, command=functools.partial(func, self, self.root, iso, entry))

        self.post(x, y)

    def dump_cb(self, iso: pycdlib.PyCdlib, entry: GameEntry):
        # Open save file dialog
        print("Asking for destination file, to save dump to")
        path = filedialog.asksaveasfilename(defaultextension=entry.extension, initialfile=entry.basename, initialdir=self.root.config.get_last_dump_path())
        if path == '':
            return
        try:
            with open(path, "wb") as fout:
                iso.get_file_from_iso_fp(fout, iso_path=entry.path)

                MessageBox(self.root, ["Close"], "Dump complete", "Completed")
            self.root.config.update_dump_path(path)
        except Exception as e:
            MessageBox(self.root, ["Close"],
                       "Failed to dump the file from the ISO\n" + str(e),
                       "Problem dumping file", warn=True)


class OptionsProvider:

    @staticmethod
    def get_options(object):
        if type(object) == HG2CarEntry:
            return [
                ("Extract", HG2CarOptionHandler.extract_cb),
                ("Replace With HG3", HG2CarOptionHandler.import_replacement),
                ("Replace part", HG2CarOptionHandler.import_hg2_part),
                # UI for all parts at once needed
                # ("Replace completely", HG2CarOptionHandler.import_hg2_all),
            ]
        if type(object) == HG3CarEntry:
            return [
                ("Extract", HG3CarOptionHandler.extract_cb),
                ("Replace With HG2", HG3CarOptionHandler.import_replacement),
                # ("Replace part", HG3CarOptionHandler.import_hg3_part),  # Tools not written yet
                # UI for all parts at once needed
                # ("Replace completely", HG2CarOptionHandler.import_hg2_all),
            ]
        if type(object) == HG2CourseEntry:
            return [
                #("Extract", HG2CourseOptionHandler.extract_cb),
            ]
        if type(object) == HG3CourseEntry:
            return [
                #("Extract", HG3CourseOptionHandler.extract_cb),
            ]
        if type(object) == HG2ShopEntry:
            return [
                #("Extract", HG2ShopOptionHandler.extract_cb),
            ]
        if type(object) == HG2FieldEntry:
            return [
                #("Extract", HG2FieldOptionHandler.extract_cb),
            ]
        return []


if __name__ == '__main__':
    app = ModdingUi()
    app.mainloop()

    if app.thread is not None:
        app.thread.join()
