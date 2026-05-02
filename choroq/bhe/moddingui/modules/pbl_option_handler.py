from io import BytesIO

from choroq.bhe.moddingui.entries.pbl_entry import PblEntry
from choroq.bhe.moddingui.entries.game_entry import GameEntry
import os
import functools

import re
import pycdlib
import customtkinter
from tkinter import filedialog, messagebox, Menu
from tkinter import ttk

from PIL import Image

from customtkinter import CTkFrame

from choroq.bhe.moddingui.modules.message_box import MessageBox
from choroq.texture_utils import TextureUtil


# from elftools.elf.elffile import ELFFile

class PblOptionHandler:

    @staticmethod
    def extract_cb(entrymenu, root, iso: pycdlib.PyCdlib, entry: GameEntry):
        # Open save file dialog
        print("Asking for destination folder, to save extracted data to")
        path = filedialog.askdirectory(title="Select the output folder",
                                       initialdir=root.config.get_last_extract_path())
        if path == '':
            return
        try:
            if entry.extract(iso, [], path):
                root.config.update_extract_path(path)
                MessageBox(root, ["Close"], "Extraction complete", "Completed")
            else:
                MessageBox(root, ["Close"], "Extraction failed", "Failed to extract", warn=True)
        except Exception as e:
            MessageBox(root, ["Close"],
                       "Failed to extract from the ISO\n" + str(e),
                       "Problem extracting file", warn=True)
