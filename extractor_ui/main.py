import sys
import os
import threading
from enum import Enum

import customtkinter
from tkinter import filedialog

import choroq_extractor as extractor


class MessageBox(customtkinter.CTkToplevel):

    def __init__(self, master, buttons, message, title, callback=None):
        super().__init__()
        self.wm_transient(master)
        self.wm_title(title)

        self.callback = callback

        message_label = customtkinter.CTkLabel(self, text=message, fg_color="gray30", corner_radius=6)
        message_label.grid(row=0, column=0)

        col = 0
        self.buttons = []
        for button_text in buttons:
            button = customtkinter.CTkButton(self, text=button_text, command=self.callback_internal)
            button.grid(row=1, column=col)
            self.buttons.append(button)
            col += 1

    def callback_internal(self):
        if self.callback is not None:
            self.callback()
        else:
            self.destroy()


class PathFrame(customtkinter.CTkFrame):

    def __init__(self, master, on_path_change_cb):
        super().__init__(master)

        self.game_version = GameVersions.UNSET
        self.on_path_change_cb = on_path_change_cb

        self.grid_columnconfigure(0, weight=10)
        self.grid_columnconfigure(1, weight=1)

        self.game_label = customtkinter.CTkLabel(self, text="Game path", fg_color="gray30", corner_radius=6)
        self.game_label.grid(row=0, column=0, padx=5, pady=(2, 0), sticky="ew", columnspan=2)
        self.game_path = customtkinter.StringVar()
        self.game_path_entry = customtkinter.CTkEntry(self, textvariable=self.game_path).grid(row=1, column=0, sticky="ew")
        self.browse_game_button = customtkinter.CTkButton(self, text="Browse", command=self.browse_game_cb)
        self.browse_game_button.grid(row=1, column=1, padx=5, pady=5)

        self.export_label = customtkinter.CTkLabel(self, text="Export path", fg_color="gray30", corner_radius=6)
        self.export_label.grid(row=2, column=0, padx=5, pady=(2, 0), sticky="ew", columnspan=2)
        self.export_path = customtkinter.StringVar()
        self.export_path_entry = customtkinter.CTkEntry(self, textvariable=self.export_path).grid(row=3, column=0, sticky="ew")
        self.browse_export_button = customtkinter.CTkButton(self, text="Browse", command=self.browse_export_cb)
        self.browse_export_button.grid(row=3, column=1, padx=5, pady=5)

        self.game_text = customtkinter.StringVar()
        self.game_version_label = customtkinter.CTkLabel(self, textvariable=self.game_text, fg_color="gray30", corner_radius=6)
        self.game_version_label.grid(row=4, column=0, padx=5, pady=(2, 0), sticky="ew", columnspan=2)

        self.update_labels()

    def browse_game_cb(self):
        self.game_path.set(filedialog.askdirectory())
        # Check game version
        self.check_game_path_valid()
        self.update_labels()
        self.on_path_change_cb()

    def browse_export_cb(self):
        self.export_path.set(filedialog.askdirectory())
        self.on_path_change_cb()

    def check_game_path_valid(self):
        hg23_check = os.path.isdir(os.path.join(self.game_path.get(), "CARS"))
        hg2_check = os.path.isdir(os.path.join(self.game_path.get(), "CAR1"))

        if hg23_check and hg2_check:
            self.game_version = GameVersions.CHOROQ_HG_2
        elif hg23_check and not hg2_check:
            self.game_version = GameVersions.CHOROQ_HG_3
        else:
            self.game_version = GameVersions.UNSET

    def update_labels(self):
        if self.game_version == GameVersions.CHOROQ_HG_2:
            self.game_text.set("HG2 (Road Trip)")
        elif self.game_version == GameVersions.CHOROQ_HG_3:
            self.game_text.set("HG3 (Gadget Racers)")
        else:
            self.game_text.set("Unknown")



class GameVersions(Enum):
    UNSET = 0,
    CHOROQ_HG_2 = 1,
    CHOROQ_HG_3 = 2,


class OptionsFrame(customtkinter.CTkFrame):
    def __init__(self, master, game_version=GameVersions.CHOROQ_HG_2):
        super().__init__(master)
        self.game_version = game_version
        row = 0
        self.cars_checkbox = customtkinter.CTkCheckBox(self, text="Extract cars")
        self.cars_checkbox.grid(row=row, column=0, padx=10, pady=(10, 0), sticky="w")
        row += 1
        self.courses_checkbox = customtkinter.CTkCheckBox(self, text="Extract courses")
        self.courses_checkbox.grid(row=row, column=0, padx=10, pady=(10, 0), sticky="w")
        row += 1
        self.actions_checkbox = customtkinter.CTkCheckBox(self, text="Extract actions")
        self.actions_checkbox.grid(row=row, column=0, padx=10, pady=(10, 0), sticky="w")
        row += 1
        self.fields_checkbox = customtkinter.CTkCheckBox(self, text="Extract fields")
        self.fields_checkbox.grid(row=row, column=0, padx=10, pady=(10, 0), sticky="w")
        row += 1
        self.sys_checkbox = customtkinter.CTkCheckBox(self, text="Extract SYS files")
        self.sys_checkbox.grid(row=row, column=0, padx=10, pady=(10, 0), sticky="w")
        row += 1
        self.shops_checkbox = customtkinter.CTkCheckBox(self, text="Extract Shops")
        self.shops_checkbox.grid(row=row, column=0, padx=10, pady=(10, 0), sticky="w")
        row += 1
        self.items_checkbox = customtkinter.CTkCheckBox(self, text="Extract Items")
        self.items_checkbox.grid(row=row, column=0, padx=10, pady=(10, 0), sticky="w")
        row += 1
        self.obj_checkbox = customtkinter.CTkCheckBox(self, text="As OBJ")
        self.obj_checkbox.grid(row=row, column=0, padx=10, pady=(10, 0), sticky="w")
        row += 1
        self.ply_checkbox = customtkinter.CTkCheckBox(self, text="As PLY")
        self.ply_checkbox.grid(row=row, column=0, padx=10, pady=(10, 0), sticky="w")
        row += 1
        self.obj_c_checkbox = customtkinter.CTkCheckBox(self, text="As OBJ + colour vertices")
        self.obj_c_checkbox.grid(row=row, column=0, padx=10, pady=(10, 10), sticky="w")
        row += 1
        self.setup_checkboxes(game_version)

    def get(self):
        checked_checkboxes = []
        if self.cars_checkbox.get() == 1:
            checked_checkboxes.append("cars")
        if self.courses_checkbox.get() == 1:
            checked_checkboxes.append("courses")
        if self.actions_checkbox.get() == 1:
            checked_checkboxes.append("actions")
        if self.fields_checkbox.get() == 1:
            checked_checkboxes.append("fields")
        if self.sys_checkbox.get() == 1:
            checked_checkboxes.append("sys")
        if self.shops_checkbox.get() == 1:
            checked_checkboxes.append("shops")
        if self.items_checkbox.get() == 1:
            checked_checkboxes.append("items")
        if self.obj_checkbox.get() == 1:
            checked_checkboxes.append("obj")
        if self.ply_checkbox.get() == 1:
            checked_checkboxes.append("ply")
        if self.obj_c_checkbox.get() == 1:
            checked_checkboxes.append("obj_colour")
        return checked_checkboxes

    def setup_checkboxes(self, game_version):
        if game_version == GameVersions.CHOROQ_HG_3:
            self.actions_checkbox.configure(state=customtkinter.DISABLED)
            self.fields_checkbox.configure(state=customtkinter.DISABLED)
            self.items_checkbox.configure(state=customtkinter.DISABLED)
        else:
            self.actions_checkbox.configure(state=customtkinter.NORMAL)
            self.fields_checkbox.configure(state=customtkinter.NORMAL)
            self.items_checkbox.configure(state=customtkinter.NORMAL)


class StdHandler:
    def __init__(self, destination, progress_bar, max_progress):
        self.destination = destination
        self.progress_bar = progress_bar
        self.max_progress = max_progress
        self.progress = 0

    def __enter__(self):
        import sys
        self._sys = sys
        self._stdout = sys.stdout
        sys.stdout = self
        return self

    def __exit__(self, type, value, traceback):
        self._sys.stdout = self._stdout

    def write(self, txt):
        self.destination.insert("end", str(txt))
        self.destination.see("end")
        if self.progress_bar is not None and "\n" in txt:
            self.progress += self.max_progress
            self.progress_bar.set(self.progress)



class ChoroQHGExtractorApp(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.game_version = GameVersions.UNSET
        self.thread = None
        self.cancel_thread = None

        self.title("Choroq HG 2/3 Extractor")
        self.geometry("400x825")
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=5)
        self.grid_columnconfigure(2, weight=1)

        self.path_frame = PathFrame(self, self.path_change_cb)
        self.path_frame.grid(row=0, column=1, padx=0, pady=(10, 0), sticky="ew")

        self.options_frame = OptionsFrame(self)
        self.options_frame.grid(row=5, column=1, pady=(10, 0), sticky="ew")

        self.button = customtkinter.CTkButton(self, text="Extract", command=self.extract_callback)
        self.button.grid(row=10, column=1, padx=20, pady=(5, 5))
        self.cancel = customtkinter.CTkButton(self, text="Cancel", command=self.cancel_callback)
        self.cancel.grid(row=11, column=1, padx=20, pady=(5, 5))

        self.progress_label = customtkinter.CTkTextbox(self, activate_scrollbars=True)
        self.progress_label.insert("0.0", "Not started")
        self.progress_label.grid(row=13, column=0, padx=(5, 5), pady=0, columnspan=3, sticky="sew")

        self.progress_bar = customtkinter.CTkProgressBar(self, orientation="horizontal", mode="determinate")
        self.progress_bar.grid(row=12, column=0, padx=(5, 5), pady=0, columnspan=3, sticky="sew")
        self.progress_bar.set(0)

        self.protocol('WM_DELETE_WINDOW', self.attempt_close)

    def path_change_cb(self):
        self.game_version = self.path_frame.game_version
        self.options_frame.setup_checkboxes(self.game_version)

    def extract_callback(self):
        extractor.should_exit = False
        self.progress_label.delete("0.0", "end")
        self.progress_label.insert("0.0", "Starting")
        t = threading.Thread(target=self.start_extract, args=(), kwargs={})
        self.thread = t
        t.start()

    def cancel_callback(self):
        extractor.should_exit = True
        t = threading.Thread(target=self.await_cancel, args=(), kwargs={})
        self.cancel_thread = t
        t.start()


    def await_cancel(self):
        if self.thread is not None:
            self.thread.join()

    def attempt_close(self):
        extractor.should_exit = True
        self.await_cancel()
        self.destroy()

    def start_extract(self):
        selected_options = self.options_frame.get()

        obj = True if "obj" in selected_options else False
        ply = True if "ply" in selected_options else False
        obj_colours = True if "obj_colour" in selected_options else False

        if not obj and not ply and not obj_colours:
            MessageBox(self, ["Close"], "Failed please select an output format", "Error", callback=None)
            return

        folder_in = self.path_frame.game_path.get()
        folder_out = self.path_frame.export_path.get()
        game_version = self.game_version

        os.makedirs(folder_out, exist_ok=True)
        if not os.path.isdir(folder_out):
            MessageBox(self, ["Close"], "Failed to create or use output folder", "Error", callback=None)
            return

        if os.path.isfile(folder_in):
            MessageBox(self, ["Close"], "This tool is for extracting \"all\" game data, not just a single file", "Error",
                       callback=None)
            return

        output_formats = []
        if obj:
            output_formats.append("obj")
        if obj_colours:
            output_formats.append("obj+colour")
        if ply:
            output_formats.append("ply")
            MessageBox(self, ["Close"],
                       "Warning, PLY files are broken, they can be manually fixed, but for now please use OBJ/OBJ+Colours",
                       "Error", callback=None)

        if os.path.isdir(folder_in):
            max_progress = 0
            if "courses" in selected_options:
                max_progress += 1
                if game_version == GameVersions.CHOROQ_HG_3:
                    max_progress += 58
                else:
                    max_progress += 19
            if "cars" in selected_options:
                max_progress += 1
                max_progress += 154
            if "actions" in selected_options:
                max_progress += 1
                max_progress += 21
            if "fields" in selected_options:
                max_progress += 1
                max_progress += 64
            if "items" in selected_options:
                max_progress += 1
                if game_version == GameVersions.CHOROQ_HG_3:
                    max_progress += 11
                else:
                    max_progress += 12
            if "shops" in selected_options:
                max_progress += 1
                max_progress += 22
            if "sys" in selected_options:
                max_progress += 1
                if game_version == GameVersions.CHOROQ_HG_3:
                    max_progress += 30
                else:
                    max_progress += 42
            progress_step = 1 / max_progress
            print(max_progress)
            progress = 0
            out = StdHandler(self.progress_label, self.progress_bar, progress_step)
            errout = StdHandler(self.progress_label, None, None)
            with errout as sys.stderr:
                with out as sys.stdout:
                    if "courses" in selected_options:
                        extractor.process_courses(folder_in, folder_out, "COURSE", output_formats)
                    if "cars" in selected_options:
                        extractor.process_cars(folder_in, folder_out, output_formats)
                    if "actions" in selected_options:
                        extractor.process_courses(folder_in, folder_out, "ACTION", output_formats)
                    if "fields" in selected_options:
                        extractor.process_fields(folder_in, folder_out, output_formats)
                    # These are other bits from the game, might be useful for some
                    if "items" in selected_options:
                        extractor.process_items(folder_in, folder_out, output_formats)
                    if "shops" in selected_options:
                        extractor.process_shops(folder_in, folder_out, output_formats)
                    if "sys" in selected_options:
                        extractor.process_sys(folder_in, folder_out, output_formats)
                    print("Done")
            self.progress_bar.set(1.0)

        else:
            MessageBox(self, ["Close"], "Failed to read source folder", "Error",
                       callback=None)


app = ChoroQHGExtractorApp()
app.mainloop()

if app.thread is not None:
    app.thread.join()