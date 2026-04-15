from io import BytesIO

from choroq.bhe.moddingui.entries.apt_entry import AptEntry
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

class AptOptionHandler:

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
                       callback=functools.partial(AptOptionHandler.import_replacement_confirmed, entrymenu, root,
                                                  iso, entry),
                       warn=True)
        else:
            return AptOptionHandler.import_replacement_confirmed(entrymenu, root, iso, entry, 0, 0)


    @staticmethod
    def import_replacement_confirmed(entrymenu, root, iso: pycdlib.PyCdlib, entry: AptEntry, button_index, button_name):

        if entry.ap_texture.colour_format not in [4, 8]:
            MessageBox(root, ["Close"],
                       f"Cannot convert this texture type {entry.ap_texture.colour_format}\n",
                       "Incompatible for now", warn=True)
            return False

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

        print("Asking for replacement PNG")
        path = filedialog.askopenfilename(defaultextension='.png',
                                          initialdir=root.config.get_last_replacement_path(entry.game_version))
        if path == '':
            return False
        try:
            # Load in the texture, and verify the formats are supported, and will be the right size
            with open(path, "rb") as replacement_in:
                root.config.update_replacement_path(path, entry.game_version)

                # As we are replacing 1 texture, this is 1 within one apt,
                # so we only want to change this one texture, not any of the
                # other apt textures, or the apt header
                replacement_bytes = BytesIO()

                texture_path_in = path
                selected_image = Image.open(texture_path_in)
                texture_bytes, clut_bytes = TextureUtil.split_image(selected_image, entry.ap_texture.colour_format, entry.ap_texture.palette_size, 32)

                texture_size = int(entry.ap_texture.width * entry.ap_texture.height * (entry.ap_texture.colour_format / 8))
                clut_size = entry.ap_texture.palette_size * 4 # palette_size is number of colours not bytes

                if len(texture_bytes) != texture_size:
                    print(f"Texture size mismatch: {texture_size} != {len(texture_bytes)}")
                    raise Exception("Texture not valid, or unsupported")
                if len(clut_bytes) != clut_size:
                    print(f"Clut size mismatch {clut_size} != {len(clut_bytes)}")
                    raise Exception("Texture not valid, or unsupported")

                replacement_bytes.seek(0, os.SEEK_SET)
                replacement_bytes.write(clut_bytes)
                replacement_bytes.write(texture_bytes)


                replacement_bytes.seek(0, os.SEEK_END)
                converted_size = replacement_bytes.tell()
                replacement_bytes.seek(0, os.SEEK_SET)

                # Calculate position to write new data to, this is +16 to move past
                # this APT entry's header/descriptor
                writing_offset = entry.get_offset() + 16
                print(writing_offset)

                if converted_size > entry.get_size():
                    MessageBox(root, ["Close"],
                               "Replacement unsuccessful, the car would be larger than "
                               f"the one you wish to replace, size {converted_size}",
                               "Not possible",
                               warn=True)
                else:
                    try:
                        # Dirty, open file again then write where it should be,
                        # without doing this the data positions change
                        print(f"Replacing texture {entry.basename} in {entry.record.data_fp.name}")
                        with open(entry.record.data_fp.name, "r+b") as edited_out:
                            # Move to the iso's file position, and move to the start of the part
                            edited_out.seek(writing_offset, os.SEEK_SET)

                            amount_written = edited_out.write(replacement_bytes.read())
                            if amount_written < clut_size + texture_size:
                                raise Exception(
                                    f"Failed to replace, did not write full size {amount_written} != {clut_size + texture_size}")

                        # Do not use this function, it changes LBA and file positions
                        # This is here to remind me to not do this
                        # # Pad data until replacement is the same size, as required
                        # replacement_bytes.seek(0, os.SEEK_END)
                        # replacement_bytes.write(b'\x00' * (entry.get_size() - converted_size))
                        # converted_size = replacement_bytes.tell()
                        # replacement_bytes.seek(0, os.SEEK_SET)
                        # iso.modify_file_in_place(replacement_bytes, converted_size, entry.path)
                        MessageBox(root, ["Close"],
                                   f"Replacement successful", "Completed")
                    except Exception as e:
                        MessageBox(root, ["Close"],
                                   "Failed to replace bytes in the ISO\n"
                                   "If the following message makes no sense, assume\n"
                                   "that I have not yet finished support for part of the given file\n\n" + str(e),
                                   "Problem during replacement",
                                   warn=True)

        except Exception as e:
            MessageBox(root, ["Close"],
                       "Failed to replace bytes in the ISO\n"
                       "If the following message makes no sense, assume\n"
                       "that I have not yet finished support for part of the given file\n\n" + str(e),
                       "Problem during replacement",
                       warn=True)