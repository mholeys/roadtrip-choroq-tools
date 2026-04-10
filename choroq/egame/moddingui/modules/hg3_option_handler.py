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
from choroq.egame.moddingui.modules.hg2_option_handler import HG2CarOptionHandler
from choroq.egame.moddingui.modules.message_box import MessageBox

from choroq.egame.moddingui.common import *
from choroq.egame.moddingui.entries.game_entry import GameEntry
from egame_converter import EGameConverter

import choroq.read_utils as U


class HG3CarOptionHandler(HG2CarOptionHandler):

    pass