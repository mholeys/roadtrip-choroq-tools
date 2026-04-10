import os
import functools

import re
import pycdlib
import customtkinter
from tkinter import filedialog, messagebox, Menu
from tkinter import ttk

from customtkinter import CTkFrame

# from elftools.elf.elffile import ELFFile

from choroq.egame.moddingui.modules.helper import Helper
from choroq.egame.moddingui.modules.hg2_car_replacement_ui import CarPartReplaceMenu
from choroq.egame.moddingui.modules.message_box import MessageBox

from choroq.egame.moddingui.common import *
from choroq.egame.moddingui.entries.game_entry import GameEntry
from egame_converter import EGameConverter

import choroq.read_utils as U


class HG2CarOptionHandler:

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

    @staticmethod
    def import_replacement(entrymenu, root, iso: pycdlib.PyCdlib, entry: GameEntry):
        # Warn user
        if root.config.has_warnings():
            MessageBox(root, ["Understood"],
                       "This method will attempt to edit your game iso, IN PLACE,\n"
                       "I recommend you make a clean copy before performing any modifications\n"
                       "such as replacements, as this cannot be undone using this tool\n"
                       "The first thing it will do is check the if iso can be written to",
                       "Warning",
                       callback=functools.partial(HG2CarOptionHandler.import_replacement_confirmed, root, iso, entry),
                       warn=True)
        else:
            return HG2CarOptionHandler.import_replacement_confirmed(entrymenu, root, iso, entry, 0, 0)

    @staticmethod
    def import_hg2_part(entrymenu, root, iso: pycdlib.PyCdlib, entry: GameEntry):
        # Warn user
        if root.config.has_warnings():
            MessageBox(root, ["Understood"],
                       "This method will attempt to edit your game iso, IN PLACE,\n"
                       "I recommend you make a clean copy before performing any modifications\n"
                       "such as replacements, as this cannot be undone using this tool\n"
                       "The first thing it will do is check the if iso can be written to",
                       "Warning",
                       callback=functools.partial(entrymenu.import_replacement_confirmed, iso, entry),
                       warn=True)
        else:
            return HG2CarOptionHandler.import_part_hg2_confirmed(entrymenu, root, iso, entry, 0, '')


    @staticmethod
    def import_replacement_confirmed(entrymenu, root, iso: pycdlib.PyCdlib, entry: GameEntry, button_index, button_name):
        # Reopen the iso as read and write
        try:
            write_test = open(entry.record.data_fp.name, "r+b")
            write_test.close()
        except Exception as e:
            print("failed to write to iso (test)")
            print(e)
            MessageBox(root, ["Close"],
                       "Failed to reopen the ISO for writing\n" + str(e),
                       "Problem during replacement", warn=True)
            return False

        # TODO handle this in the entry class?
        # Open a bin file, extracted from HG2 or HG3, which ever is not the same
        # as the open game version, then convert the given bin into this iso's format
        # After we know the size, we can calculate if it will fit
        # If it will fit, copy out the texture transfer bytes (ensures addressing issues)
        # If not, tell user to try a different mesh
        print("Asking for replacement HG[2/3] BIN")
        path = filedialog.askopenfilename(defaultextension='.BIN',
                                          initialdir=root.config.get_last_replacement_path(entry.game_version))
        if path == '':
            return
        try:
            with open(path, "rb") as replacement_in:
                root.config.update_replacement_path(path, entry.game_version)
                replacement_bytes = BytesIO()
                if entry.game_version == GameVersion.CHOROQ_HG_2:
                    EGameConverter.convert_hg3_to_hg2_stream(replacement_in, replacement_bytes)
                else:
                    EGameConverter.convert_hg2_to_hg3_stream(replacement_in, replacement_bytes)

                replacement_bytes.seek(0, os.SEEK_END)
                converted_size = replacement_bytes.tell()
                replacement_bytes.seek(0, os.SEEK_SET)

                if converted_size > entry.get_size():
                    MessageBox(root, ["Close"],
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
                    offsets = Helper.find_offsets(original_data)

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
                    offsets = Helper.find_offsets(replacement_bytes)
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

                    # Force closure, so other programs can use
                    fp = open(entry.record.data_fp.name, "r")
                    fp.close()

                    # Do not use this function, it changes LBA and file positions
                    # This is here to remind me to not do this
                    # # Pad data until replacement is the same size, as required
                    # replacement_bytes.seek(0, os.SEEK_END)
                    # replacement_bytes.write(b'\x00' * (entry.get_size() - converted_size))
                    # converted_size = replacement_bytes.tell()
                    # replacement_bytes.seek(0, os.SEEK_SET)
                    # iso.modify_file_in_place(replacement_bytes, converted_size, entry.path)

                    MessageBox(root, ["Close"],
                               f"Replacement successful (replaced {converted_size} bytes)",
                               "Completed")
        except Exception as e:
            MessageBox(root, ["Close"],
                       "Failed to replace bytes in the ISO\n"
                       "If the following message makes no sense, assume\n"
                       "that I have not yet finished support for part of the given file\n\n" + str(e),
                       "Problem during replacement",
                       warn=True)


    @staticmethod
    def import_part_hg2_confirmed(entrymenu, root, iso: pycdlib.PyCdlib, entry: GameEntry, button_index, button_name):
        CarPartReplaceMenu(root, iso, entry)