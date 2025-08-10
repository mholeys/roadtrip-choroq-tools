print("Requires raylib")

from raylib import *
from pyray import Rectangle, Texture, Image, Color

import io
import os
from pathlib import Path
from abc import ABC, abstractmethod
import tkinter as tk
from tkinter import filedialog
import weakref

from choroq.texture import Texture as QTexture
from choroq.car import CarModel as QCar
from choroq.car_hg3 import HG3CarModel as QHG3Car

import choroq.read_utils as U

from enum import Enum


class GameVersions(Enum):
    UNSET = 0,
    CHOROQ_HG_2 = 1,
    CHOROQ_HG_3 = 2,

class HG3Tyres(Enum):
    UNSET = 0,


class ToolState:
    def __init__(self):
        self.selected_game_version = GameVersions.UNSET
        self.hg2_game_folder_path = ""
        self.hg3_game_folder_path = ""
        self.ready = False
        self.valid_path = False
        self.hg2_references = GameReferences()
        self.hg3_references = GameReferences()


class GameReferences:

    def __init__(self):
        self.cars = []
        self.courses = []
        self.fields = []


class ModelData:
    def __init__(self):
        self.meshes = []
        self.materials = []


class CarReference:
    def __init__(self, path, name, version):
        self.game_version = version
        self.path = path
        self.name = name
        self.loaded = False
        self.models = ModelData()


class CourseReference:
    def __init__(self, path, name):
        self.path = path
        self.name = name


class FieldReference:
    def __init__(self, path, name, coord):
        self.path = path
        self.name = name
        self.coord = coord


class ChoroQTools:
    def __init__(self):
        self.state = ToolState()
        self.screen_width = 1280
        self.screen_height = 768

        self.state_stack = []
        self.current_window = None

        self.camera = ffi.new("struct Camera3D *", [[18.0, 16.0, 18.0], [0.0, 0.0, 0.0], [0.0, 1.0, 0.0], 45.0, 0])

    def start_ui(self):
        SetConfigFlags(FLAG_WINDOW_RESIZABLE)
        InitWindow(self.screen_width, self.screen_height, b"ChoroQ HG 2 tool")

        SetTargetFPS(60)

        self.PushState(MenuTop())

        while not WindowShouldClose():
            UpdateCamera(self.camera, CAMERA_FREE)
            BeginDrawing()
            ClearBackground(GetColor(GuiGetStyle(DEFAULT, BACKGROUND_COLOR) & 0xffffffff))

            if not self.state.ready:
                DrawText("Please use setup to unlock features".encode('ascii'), 20, 150, 20, RED)

            for element in self.state_stack:
                element.OnDraw()

            if self.current_window is not None:
                self.current_window.OnDraw()

            EndDrawing()
        CloseWindow()

    def SetWindow(self, new_window):
        if self.current_window is not None:
            self.current_window.OnClose()
            self.current_window.OnInactive()
        self.current_window = new_window
        self.current_window.SetOwner(self)
        self.current_window.OnActive()

    def PushState(self, new_state):
        self.state_stack.append(new_state)
        new_state.SetOwner(self)
        new_state.OnActive()

    def SwitchToState(self, new_state):
        # TODO empty and add new as only
        pass

    def RemoveState(self, state):
        state.OnClose()
        state.OnInactive()
        self.state_stack.remove(state)

    def CloseWindow(self):
        if self.current_window is not None:
            self.current_window.OnClose()
            self.current_window.OnInactive()
            self.current_window = None


class RenderStackItem:

    def __init__(self):
        self.active = False

    @abstractmethod
    def OnDraw(self):
        pass

    @abstractmethod
    def OnUpdate(self):
        pass

    @abstractmethod
    def OnClose(self):
        pass

    @abstractmethod
    def OnActive(self):
        self.active = True

    @abstractmethod
    def OnInactive(self):
        self.active = False

    def SetOwner(self, owner):
        self.owner = owner


class MenuTop(RenderStackItem):

    def __init__(self):
        super().__init__()
        self.width = GetScreenWidth()
        self.height = 32

        DrawRectangle(2, 2, self.width - 2, self.height + 5, GetColor(0x22222222))

        self.buttons = 9
        self.button_width = self.width / self.buttons

        self.border = 5
        self.button = 0

        self.button1_rec = Rectangle(self.border * (self.button + 1) + self.button_width * self.button, self.border,
                                     self.button_width, self.height)
        self.button = 1
        self.button2_rec = Rectangle(self.border * (self.button + 1) + self.button_width * self.button, self.border,
                                     self.button_width, self.height)
        self.button = 2
        self.button3_rec = Rectangle(self.border * (self.button + 1) + self.button_width * self.button, self.border,
                                     self.button_width, self.height)
        self.button = 3
        self.button4_rec = Rectangle(self.border * (self.button + 1) + self.button_width * self.button, self.border,
                                     self.button_width, self.height)
        self.button = 4

    def OnDraw(self):
        if not self.active:
            return
        setup_pressed = GuiButton(self.button1_rec, "Setup".encode('ascii'))

        if setup_pressed:
            self.owner.SetWindow(SetupDialog())

        if self.owner.state.ready:
            if GuiButton(self.button2_rec, "Cars".encode('ascii')):
                if type(self.owner.current_window) != CarViewer:
                    self.owner.SetWindow(CarViewer(self.owner))
            if GuiButton(self.button3_rec, "Course".encode('ascii')):
                # if type(self.owner.current_window) != CourseViewer:
                pass
                # self.owner.SetWindow(CourseViewer())
            if GuiButton(self.button4_rec, "Field".encode('ascii')):
                # if type(self.owner.current_window) != FieldViewer:
                pass
                # self.owner.SetWindow(FieldViewer())



    def OnUpdate(self):
        pass

    def OnClose(self):
        pass

class FileOpenType(Enum):
    NONE = 0
    TEXTURE = 1
    CAR = 2
    COURSE = 3
    FIELD = 4
    SHOP = 5
    ACTION = 6

class SetupDialog(RenderStackItem):

    def __init__(self):
        super().__init__()
        self.visible = True
        self.selectedFileType = ffi.new("int *")

        self.selected_game_version = ffi.new("int *")
        self.selected_game_version[0] = 0

        # self.selected_folder = ffi.new("char[]",
        #                                 "I:\\Console\\PS2\\RoadTripAdventure_Data\\RoadTripAdventure\\SHOP\\T00.BIN".encode(
        #                                     'ascii'))
        self.selected_folder = ffi.new("char[]",
                                       os.path.dirname(os.path.realpath(__file__)).encode(
                                            'ascii'))

        self.editingHg2Path = False
        self.editingHg3Path = False

        self.offsetPosition = ffi.new("int *")
        self.editingOffsetPosition = False

        self.useOffsetTable = ffi.new("bool *")
        self.useOffsetTable[0] = False

        self.fileOpenType = FileOpenType.TEXTURE

        self.selectingType = False

        self.hg2_selected_folder = ffi.new("char[]", "I:\\Console\\PS2\\RoadTripAdventure_Data\\RoadTripAdventure".encode('ascii'))
        self.hg3_selected_folder = ffi.new("char[]", "I:\\Console\\PS2\\clean_CHQHG3".encode('ascii'))

    def OnDraw(self):
        if not self.active:
            return

        width = GetScreenWidth()
        height = GetScreenHeight()
        xborder = 64
        yborder = 64

        tl = (xborder, yborder)

        window = Rectangle(tl[0], tl[1], width - 2 * xborder, height - 2 * yborder)
        if GuiWindowBox(window, "Setup file paths".encode('ascii')):
            self.owner.RemoveState(self)

        line_position = 40

        GuiLabel(Rectangle(tl[0] + 25, tl[1] + line_position, 200, 16), "HG2 Game folder path (extracted ISO):".encode('ascii'))
        line_position += 16
        # Path of file
        if GuiTextBox(Rectangle(tl[0] + 25, tl[1] + line_position, 350, 24), self.hg2_selected_folder, 1024, self.editingHg2Path):
            self.editingHg2Path = not self.editingHg2Path

        # Browse file path button
        browsePressed = GuiButton(Rectangle(tl[0] + 380, tl[1] + line_position, 60, 24), "Browse".encode('ascii'))
        line_position += 24
        if browsePressed:
            root = tk.Tk()
            root.withdraw()

            # self.selected_folder = ffi.new("char[]", filedialog.askopenfilename().encode('ascii'))
            self.hg2_selected_folder = ffi.new("char[]", filedialog.askdirectory().encode('ascii'))

        GuiLabel(Rectangle(tl[0] + 25, tl[1] + line_position, 200, 16),
                 "HG3 Game folder path (extracted ISO):".encode('ascii'))
        line_position += 16
        # Path of file
        if GuiTextBox(Rectangle(tl[0] + 25, tl[1] + line_position, 350, 24), self.hg3_selected_folder, 1024, self.editingHg3Path):
            self.editingHg3Path = not self.editingHg3Path

        # Browse file path button
        browsePressed = GuiButton(Rectangle(tl[0] + 380, tl[1] + line_position, 60, 24), "Browse".encode('ascii'))
        line_position += 24
        if browsePressed:
            root = tk.Tk()
            root.withdraw()

            # self.selected_folder = ffi.new("char[]", filedialog.askopenfilename().encode('ascii'))
            self.hg3_selected_folder = ffi.new("char[]", filedialog.askdirectory().encode('ascii'))

        # Type of file to load (or how to treat loaded data)
        # Draw this last so its on top
        line_position += 16
        GuiLabel(Rectangle(tl[0] + 25, tl[1] + line_position, 280, 48),
                 "Game version \n"
                 "HG2 = (Everywhere) Road Trip (Adventure)\n"
                 "HG3 = Gadget Racers\n".encode('ascii'))

        # game_select_result = GuiDropdownBox(Rectangle(tl[0] + 320, tl[1] + line_position, 120, 24),
        #                "ChoroQ HG 2;ChoroQ HG 3".encode('ascii'), self.selected_game_version,
        #                self.selectingType)
        # line_position += 48

        # if game_select_result:
        #     self.selectingType = not self.selectingType

        line_position += 180
        # Open file button
        done_pressed = GuiButton(Rectangle(tl[0] + 25, tl[1] + line_position, 120, 24), "Done".encode('ascii'))
        if done_pressed:
            # Find selected output_type
            t = self.selected_game_version[0]

            self.owner.state.hg2_game_folder_path = ffi.string(self.hg2_selected_folder).decode('ascii')
            self.owner.state.hg3_game_folder_path = ffi.string(self.hg3_selected_folder).decode('ascii')
            self.owner.state.ready = self.CheckValidSetup()

            # Find all files we need
            self.FindResources()

            self.owner.CloseWindow()

    def CheckValidSetup(self):
        hg2_valid = False
        hg3_valid = False
        if self.owner.state.hg2_game_folder_path is not "":
            valid_path = os.path.isdir(os.path.join(self.owner.state.hg2_game_folder_path, "CAR0"))
            valid_path &= os.path.isdir(os.path.join(self.owner.state.hg2_game_folder_path, "CAR1"))
            valid_path &= os.path.isdir(os.path.join(self.owner.state.hg2_game_folder_path, "CAR2"))
            valid_path &= os.path.isdir(os.path.join(self.owner.state.hg2_game_folder_path, "CAR3"))
            valid_path &= os.path.isdir(os.path.join(self.owner.state.hg2_game_folder_path, "CAR4"))
            valid_path &= os.path.isdir(os.path.join(self.owner.state.hg2_game_folder_path, "CARS"))
            hg2_valid = valid_path
        if self.owner.state.hg3_game_folder_path is not "":
            valid_path = os.path.isdir(os.path.join(self.owner.state.hg3_game_folder_path, "CARS"))
            valid_path &= not os.path.isdir(os.path.join(self.owner.state.hg3_game_folder_path, "CAR1"))
            hg3_valid = valid_path

        if self.owner.state.hg2_game_folder_path is not "" and hg2_valid:
            # Has 2
            if self.owner.state.hg3_game_folder_path is not "":
                # Has 2 and 3
                self.owner.state.valid_path = hg2_valid and hg3_valid
            else:
                # Only has 2
                self.owner.state.valid_path = hg2_valid
        elif self.owner.state.hg3_game_folder_path is not "":
            # Only has 3
            self.owner.state.valid_path = hg3_valid
        return self.owner.state.valid_path

    def FindResources(self):
        # Find hg2 resources
        cars, courses, fields = SetupDialog._FindResources(self.owner.state.hg2_game_folder_path, GameVersions.CHOROQ_HG_2)

        self.owner.state.hg2_references.cars = cars
        self.owner.state.hg2_references.courses = courses
        self.owner.state.hg2_references.fields = fields

        # Find hg3 resources
        cars, courses, fields = SetupDialog._FindResources(self.owner.state.hg3_game_folder_path, GameVersions.CHOROQ_HG_3)

        self.owner.state.hg3_references.cars = cars
        self.owner.state.hg3_references.courses = courses
        self.owner.state.hg3_references.fields = fields

    @staticmethod
    def _FindResources(folder, version):
        cars = []
        courses = []
        fields = []
        # Find all cars
        for carFolder in [f"{folder}/CAR0", f"{folder}/CAR1", f"{folder}/CAR2", f"{folder}/CAR3", f"{folder}/CAR4",
                          f"{folder}/CARS"]:
            if Path(carFolder).is_dir():
                with os.scandir(carFolder) as it:
                    for entry in it:
                        if entry.name == "WHEEL.BIN":
                            continue
                        if entry.name == "FASHION.BIN":
                            continue
                        if entry.name == "FROG.BIN":
                            continue
                        if entry.name == "STICKER.BIN":
                            continue
                        if not entry.name.startswith('.') and entry.is_file():
                            cars.append(CarReference(entry, os.path.basename(entry.path), version))
        # Find all courses
        if Path(f"{folder}/COURSE").is_dir():
            with os.scandir(f"{folder}/COURSE") as it:
                for entry in it:
                    courses.append(entry)
        if Path(f"{folder}/FLD").is_dir():
            for fx in [0, 1, 2, 3]:
                for fy in [0, 1, 2, 3]:
                    for fz in [0, 1, 2, 3]:
                        field_number = f"{fx}{fy}{fz}"
                        field_file = f"{folder}/FLD/{field_number}.BIN"
                        fields.append(field_file)
        return cars, courses, fields
    def OnUpdate(self):
        pass

    def OnClose(self):
        pass


class CarViewerOption:
    def __init__(self, size=1):
        self.part_visible = []
        self.tire_selection = 0
        self.size = size
        self.set_size(size)

    def set_size(self, size):
        for i in range(0, size):
            self.part_visible.append(False)
        if size > 0:
            self.part_visible[0] = True
        self.size = size


class CarViewer(RenderStackItem):

    def __init__(self, owner):
        self.owner = owner
        self.panelScrollPos = ffi.new("struct Vector2 *", [0, 0])
        self.panelView = ffi.new("struct Rectangle *", [0, 0, 0, 0])

        self.options_panelScrollPos = ffi.new("struct Vector2 *", [0, 0])
        self.options_panelView = ffi.new("struct Rectangle *", [0, 0, 0, 0])
        self.options_numOptions = 20

        self.draw_pad_left = 150
        self.draw_pad_right = 250
        self.draw_width = GetScreenWidth() - self.draw_pad_left - self.draw_pad_right
        self.draw_height = GetScreenHeight() - 80
        self.renderTexture = LoadRenderTexture(self.draw_width, self.draw_height)

        self.loaded_cars = [None, None]
        self.current_slot = 0
        self.max_slots = 2

        self.car_options = [CarViewerOption(), CarViewerOption()]

        self.global_weakkeydict = weakref.WeakKeyDictionary()

        self.option_grid = True
        self.option_floor = True
        self.option_control_camera = True
        self.option_back_colour = WHITE
        self.option_draw_texture = False

        self.loaded_tyre = False
        self.loaded_parts = False

    def OnUpdate(self):
        pass

    def OnClose(self):
        pass

    def OnDraw(self):
        if not self.active:
            return

        if self.draw_width != GetScreenWidth() - self.draw_pad_left - self.draw_pad_right or self.draw_height != GetScreenHeight() - 80:
            UnloadRenderTexture(self.renderTexture)
            self.draw_width = GetScreenWidth() - self.draw_pad_left - self.draw_pad_right
            self.draw_height = GetScreenHeight() - 80
            self.renderTexture = LoadRenderTexture(self.draw_width, self.draw_height)

        width = GetScreenWidth()
        height = GetScreenHeight()
        xborder = 10
        yborder = 32 + 10

        tl = (xborder, yborder)

        window = Rectangle(tl[0], tl[1], width - 2 * xborder, height - yborder)
        if GuiWindowBox(window, "Car viewer".encode('ascii')):
            self.owner.CloseWindow()

        # Draw list of cars
        scrollWidth = 100
        carListRec = Rectangle(tl[0], tl[1] + 25, scrollWidth*2+10, height - yborder - 25)
        numCars = max(len(self.owner.state.hg2_references.cars), len(self.owner.state.hg3_references.cars))
        carListContentRec = Rectangle(0, 0, scrollWidth * 2, 24 * numCars)

        # Draw HG 2 cars
        GuiScrollPanel(carListRec, "Cars".encode('ascii'), carListContentRec, self.panelScrollPos, self.panelView)
        # Draw in scroll
        BeginScissorMode(int(self.panelView[0].x), int(self.panelView[0].y), int(self.panelView[0].width), int(self.panelView[0].height))
        # Draw each car button
        # gridRec = Rectangle(carListRec.x + self.panelScrollPos.x, carListRec.y + self.panelScrollPos.y, carListContentRec.width, carListContentRec.height)
        #
        # GuiGrid(gridRec, ffi.new("char *"), 16, 3, ffi.new("Vector2 * ", [0, 0]))
        text_height = 24
        position = carListRec.y + self.panelScrollPos.y + text_height

        leftButtonRec = Rectangle(15, position, scrollWidth - 10, text_height - 2)
        rightButtonRec = Rectangle(scrollWidth - 10 + 20, position, scrollWidth - 10, text_height - 2)

        position += text_height

        # Draw button to select slots
        defaultButtonColour = GuiGetStyle(BUTTON, BASE_COLOR_NORMAL)
        slot0_colour = 0x7FccaaFF if self.current_slot == 0 else defaultButtonColour
        slot1_colour = 0x7FccaaFF if self.current_slot == 1 else defaultButtonColour
        GuiSetStyle(BUTTON, BASE_COLOR_NORMAL, slot0_colour)
        if GuiButton(leftButtonRec, "Slot 0".encode('ascii')):
            self.current_slot = 0
        # restore normal button colour
        GuiSetStyle(BUTTON, BASE_COLOR_NORMAL, defaultButtonColour)

        position += text_height

        if self.loaded_tyre == False:
            self.LoadTyres()
        if self.loaded_parts == False:
            self.LoadParts()

        for car in self.owner.state.hg2_references.cars:
            leftButtonRec = Rectangle(15, position, scrollWidth - 10, text_height - 2)
            position += text_height
            carName = car.name.encode('ascii')
            if GuiButton(leftButtonRec, carName):
                self.loaded_cars[self.current_slot] = car
                if not self.loaded_cars[self.current_slot].loaded:
                    self.LoadCar(self.current_slot)

        # Set selected button colour
        GuiSetStyle(BUTTON, BASE_COLOR_NORMAL, slot1_colour)
        if GuiButton(rightButtonRec, "Slot 1".encode('ascii')):
            self.current_slot = 1
        # restore normal button colour
        GuiSetStyle(BUTTON, BASE_COLOR_NORMAL, defaultButtonColour)

        # Draw HG2 cars
        rightButtonRec = Rectangle(scrollWidth - 10 + 20, position, scrollWidth - 10, text_height - 2)
        position = carListRec.y + self.panelScrollPos.y + text_height + text_height
        for car in self.owner.state.hg3_references.cars:
            rightButtonRec = Rectangle(scrollWidth - 10 + 20, position, scrollWidth - 10, text_height - 2)
            position += text_height
            carName = car.name.encode('ascii')
            if GuiButton(rightButtonRec, carName):
                self.loaded_cars[self.current_slot] = car
                if not self.loaded_cars[self.current_slot].loaded:
                    self.LoadCar(self.current_slot)
        EndScissorMode()

        # Draw options menu (right)
        options_ListRec = Rectangle(GetScreenWidth() - tl[0] - (scrollWidth + 52), tl[1] + 25, scrollWidth + 52, height - yborder - 25)

        options_ListContentRec = Rectangle(0, 0, scrollWidth + 50, 24 * self.options_numOptions)

        # Draw options panel
        GuiScrollPanel(options_ListRec, "Options".encode('ascii'), options_ListContentRec, self.options_panelScrollPos, self.options_panelView)
        # Draw in scroll
        BeginScissorMode(int(self.options_panelView[0].x), int(self.options_panelView[0].y), int(self.options_panelView[0].width),
                         int(self.options_panelView[0].height))

        options_height = 24
        optionsRec = Rectangle(15, 0, scrollWidth + 52 - 10, text_height - 2)
        # GuiPanel(optionsRec, "Options".encode('ascii'))

        options_line = optionsRec.y + self.options_panelScrollPos.y + options_height
        option = ffi.new("bool *")
        option[0] = self.option_grid
        GuiCheckBox(Rectangle(optionsRec.x + 5, options_line, 24, 24), "Grid".encode('ascii'), option)
        self.option_grid = option[0]
        options_line += options_height
        option[0] = self.option_floor
        GuiCheckBox(Rectangle(optionsRec.x + 5, options_line, 24, 24), "Floor".encode('ascii'), option)
        self.option_floor = option[0]
        options_line += options_height
        option[0] = self.option_control_camera
        GuiCheckBox(Rectangle(optionsRec.x + 5, options_line, 24, 24), "Camera Control".encode('ascii'), option)
        self.option_control_camera = option[0]
        options_line += options_height
        self.option_back_colour = WHITE
        option[0] = self.option_draw_texture
        GuiCheckBox(Rectangle(optionsRec.x + 5, options_line, 24, 24), "Draw Texture".encode('ascii'), option)
        self.option_draw_texture = option[0]
        options_line += options_height

        for slot in range(self.max_slots):
            if self.loaded_cars[slot] is None:
                continue
            for i in range(self.car_options[slot].size):
                option[0] = self.car_options[slot].part_visible[i]
                GuiCheckBox(Rectangle(optionsRec.x + 5, options_line, 24, 24),
                            f"Part {i}".encode('ascii'), option)
                self.car_options[slot].part_visible[i] = option[0]
                options_line += options_height

            option[0] = self.car_options[slot].tire_selection == 0
            GuiCheckBox(Rectangle(optionsRec.x + 5, options_line, 24, 24),
                        "No tires".encode('ascii'), option)
            if option[0]:
                self.car_options[slot].tire_selection = 0
            options_line += options_height

            if self.owner.state.selected_game_version == GameVersions.CHOROQ_HG_2:
                option[0] = self.car_options[slot].tire_selection == 1
                GuiCheckBox(Rectangle(optionsRec.x + 5, options_line, 24, 24),
                            "Normal tires".encode('ascii'), option)
                if option[0]:
                    self.car_options[slot].tire_selection = 1
                options_line += options_height

                option[0] = self.car_options[slot].tire_selection == 2
                GuiCheckBox(Rectangle(optionsRec.x + 5, options_line, 24, 24),
                            "Big tires".encode('ascii'), option)
                if option[0]:
                    self.car_options[slot].tire_selection = 2
                options_line += options_height
            elif self.owner.state.selected_game_version == GameVersions.CHOROQ_HG_3:
                tyre_names = ["Normal ".encode('ascii')]
                if self.loaded_tyre is not None:
                    for tire in range(len(self.loaded_tyre.meshes)):
                        option[0] = self.car_options[slot].tire_selection == tire
                        GuiCheckBox(Rectangle(optionsRec.x + 5, options_line, 24, 24),
                                    "Big tires".encode('ascii'), option)
                        if option[0]:
                            self.car_options[slot].tire_selection = tire
                        options_line += options_height
        self.options_numOptions = int(options_line / options_height) + 1
        EndScissorMode()

        BeginTextureMode(self.renderTexture)
        ClearBackground(BLACK)
        BeginMode3D(self.owner.camera[0])
        # Draw 3d model
        if self.loaded_cars[0] is not None:
            if self.option_grid:
                DrawGrid(20, 1)
            if self.option_floor:
                DrawPlane([0, -0.002, 0], [100, 100], GRAY)

            for slot in range(self.max_slots):
                if self.loaded_cars[slot] is not None:
                    mat = MatrixIdentity()
                    mat = MatrixAdd(mat, MatrixTranslate(slot * 6, 0, 0))
                    car_offset = [0, 0, 0]
                    if self.car_options[slot].tire_selection != 0:
                        # Draw wheels
                        if self.owner.state.selected_game_version == GameVersions.CHOROQ_HG_2:
                            wheelMatrix = MatrixAdd(mat, MatrixIdentity())
                            # +x is left (looking from rear of car)
                            # -x is right (looking from rear of car)
                            # +z is forward (looking from rear of car)
                            # -z is backwards (looking from rear of car)
                            wheelMatrix = MatrixMultiply(wheelMatrix, MatrixTranslate(0, 0.38, 0))
                            wheelFLMatrix = MatrixMultiply(wheelMatrix, MatrixTranslate(0.75, -0.05, 0.66))
                            wheelFRMatrix = MatrixMultiply(wheelMatrix, MatrixTranslate(-0.75, -0.05, 0.66))
                            wheelRMatrix = MatrixMultiply(wheelMatrix, MatrixTranslate(0, 0, -0.66))

                            wheelBFLMatrix = MatrixMultiply(wheelMatrix, MatrixTranslate(0.45, 0.175, 0.675))
                            wheelBFRMatrix = MatrixMultiply(wheelMatrix, MatrixTranslate(-0.45, 0.175, 0.675))
                            wheelBRLMatrix = MatrixMultiply(wheelMatrix, MatrixTranslate(0.45, 0.175, -0.672))
                            wheelBRRMatrix = MatrixMultiply(wheelMatrix, MatrixTranslate(-0.45, 0.175, -0.672))

                            if self.car_options[slot].tire_selection == 1:
                                # Draw 4 normal tires
                                # 0/1 are Front left/right
                                DrawMesh(self.loaded_tyre.meshes[0][0], self.loaded_tyre.materials[0], wheelFLMatrix)
                                DrawMesh(self.loaded_tyre.meshes[1][0], self.loaded_tyre.materials[1], wheelFRMatrix)
                                # 2 is rear axle
                                DrawMesh(self.loaded_tyre.meshes[2][0], self.loaded_tyre.materials[2], wheelRMatrix)
                                #3 is lp tires
                                #DrawMesh(self.loaded_tyre.meshes[3][0], self.loaded_tyre.materials[3], wheelMatrix)

                            elif self.car_options[slot].tire_selection == 2:
                                # 4/5 is left/right big
                                # Draw 4 big tyres + axle + car
                                #front 2
                                DrawMesh(self.loaded_tyre.meshes[4][0], self.loaded_tyre.materials[0], wheelBFLMatrix)
                                DrawMesh(self.loaded_tyre.meshes[5][0], self.loaded_tyre.materials[1], wheelBFRMatrix)
                                # rear 2
                                DrawMesh(self.loaded_tyre.meshes[4][0], self.loaded_tyre.materials[0], wheelBRLMatrix)
                                DrawMesh(self.loaded_tyre.meshes[5][0], self.loaded_tyre.materials[1], wheelBRRMatrix)
                                # Axle
                                if self.loaded_parts is not None:
                                    DrawMesh(self.loaded_parts.meshes[12][0], self.loaded_parts.materials[12], mat)

                                car_offset[1] += 2.8

                        elif self.owner.state.selected_game_version == GameVersions.CHOROQ_HG_3:
                            pass

                    # Adjust car to needed spot, usually based on part/tyre selection
                    mat = MatrixAdd(mat, MatrixTranslate(car_offset[0], car_offset[1], car_offset[2]))
                    for i in range(self.car_options[slot].size):
                        # Check if user wants part drawing
                        if self.car_options[slot].part_visible[i]:
                            DrawMesh(self.loaded_cars[slot].models.meshes[i][0], self.loaded_cars[slot].models.materials[i], mat)



        EndMode3D()
        # Draw overlay
        if self.loaded_cars[0] is not None:
            DrawText(self.loaded_cars[0].name.encode('ascii'), 10, 10, 20, WHITE)
            # DrawText(self.loaded_cars[0].path.path.encode('ascii'), 10, 30, 20, WHITE)
            if self.option_draw_texture:
                tex0 = self.loaded_cars[0].models.materials[0].maps[0].texture
                DrawTexture(tex0, 0, self.draw_height - tex0.height, WHITE)
        if self.loaded_cars[1] is not None:
            name = self.loaded_cars[1].name
            DrawText(name.encode('ascii'), self.draw_width - (len(name)-1) * 15, 10, 20, WHITE)
            # DrawText(self.loaded_cars[1].path.path.encode('ascii'), 10, 30, 20, WHITE)
            if self.option_draw_texture:
                tex1 = self.loaded_cars[1].models.materials[0].maps[0].texture
                DrawTexture(tex1, self.draw_width - tex1.width, self.draw_height - tex1.height, WHITE)
        EndTextureMode()
        # DrawTexture(self.renderTexture.texture, , WHITE)
        rendRec = Rectangle(0, 0, int(self.renderTexture.texture.width), int(-self.renderTexture.texture.height))
        rendVec = [int(carListRec.x+carListRec.width+10), int(carListRec.y)]
        DrawTextureRec(self.renderTexture.texture, rendRec, rendVec, WHITE)

    def LoadCar(self, slot):
        car = self.loaded_cars[slot]
        with open(car.path, "rb") as f:
            f.seek(0, os.SEEK_END)
            file_size = f.tell()
            f.seek(0, os.SEEK_SET)

            if car.game_version == GameVersions.CHOROQ_HG_2:
                car = QCar.read_car(f, 0, file_size)
            elif car.game_version == GameVersions.CHOROQ_HG_3:
                car = QHG3Car.from_file(f, 0, file_size)

            # Convert to raylib models
            self.car_options[slot].set_size(len(car.meshes))
            for mesh in car.meshes:
                rMesh, material = self.ConvertCarModel(mesh, car.textures)
                self.loaded_cars[slot].models.meshes.append(rMesh)
                self.loaded_cars[slot].models.materials.append(material)

    def ConvertCarModel(self, mesh, textures):
        # Mesh is CarMesh obj
        # mesh.meshVertCount
        # mesh.meshVerts
        # mesh.meshNormals
        # mesh.meshUvs
        # mesh.meshFaces
        # mesh.meshColours
        # Mesh

        rMesh = ffi.new("struct Mesh*")
        vertices_c = ffi.new(f"float [{mesh.meshVertCount * 3}]")
        rMesh.vertices = vertices_c
        for i in range(0, mesh.meshVertCount):
            rMesh.vertices[i * 3] = -mesh.meshVerts[i][0]
            rMesh.vertices[i * 3 + 1] = mesh.meshVerts[i][1]
            rMesh.vertices[i * 3 + 2] = mesh.meshVerts[i][2]

        normals_c = ffi.new(f"float [{mesh.meshVertCount * 3}]")
        rMesh.normals = normals_c
        for i in range(0, mesh.meshVertCount):
            rMesh.normals[i * 3] = -mesh.meshNormals[i][0]
            rMesh.normals[i * 3 + 1] = -mesh.meshNormals[i][1]
            rMesh.normals[i * 3 + 2] = -mesh.meshNormals[i][2]

        uvs_c = ffi.new(f"float [{mesh.meshVertCount * 2}]")
        rMesh.texcoords = uvs_c
        for i in range(0, mesh.meshVertCount):
            rMesh.texcoords[i * 2] = mesh.meshUvs[i][0]
            rMesh.texcoords[i * 2 + 1] = -mesh.meshUvs[i][1]

        faces_c = ffi.new(f"unsigned short [{mesh.meshVertCount * 3}]")
        rMesh.indices = faces_c
        for i in range(0, len(mesh.meshFaces)):
            rMesh.indices[i * 3] = mesh.meshFaces[i][2] - 1
            rMesh.indices[i * 3 + 1] = mesh.meshFaces[i][1] - 1
            rMesh.indices[i * 3 + 2] = mesh.meshFaces[i][0] - 1

        colours_c = ffi.new(f"unsigned char [{mesh.meshVertCount * 4}]")
        rMesh.colors = colours_c
        for i in range(0, mesh.meshVertCount):
            rMesh.colors[i * 4] = int(mesh.meshColours[i][0])
            rMesh.colors[i * 4 + 1] = int(mesh.meshColours[i][1])
            rMesh.colors[i * 4 + 2] = int(mesh.meshColours[i][2])
            rMesh.colors[i * 4 + 3] = int(mesh.meshColours[i][3])

        rMesh.vertexCount = mesh.meshVertCount
        rMesh.triangleCount = len(mesh.meshFaces)

        self.global_weakkeydict[rMesh] = (vertices_c, normals_c, uvs_c, faces_c, colours_c)
        self.global_weakkeydict[mesh] = rMesh

        # Upload mesh
        UploadMesh(rMesh, False)
        # Set material + properties

        # Assemble texture
        tAddress, tex = textures[0]
        cAddress, clut = textures[1]
        tex.palette = clut.texture
        tex.palette_width = clut.width
        tex.palette_height = clut.height
        data = tex.get_texture_as_bytes()
        texture_c = ffi.new(f"char [{tex.width * tex.height * 3}]")
        for b in range(tex.width * tex.height):
            texture_c[b * 3 + 0] = data[b * 4 + 0].to_bytes(1, byteorder='little')
            texture_c[b * 3 + 1] = data[b * 4 + 1].to_bytes(1, byteorder='little')
            texture_c[b * 3 + 2] = data[b * 4 + 2].to_bytes(1, byteorder='little')
        # data = tex.texture
        # texture_c = ffi.new(f"char [{tex.width * tex.height}]")
        # for b in range(tex.width * tex.height):
        #     texture_c[b] = data[b].to_bytes(1, byteorder='little')
        image = Image(texture_c, tex.width, tex.height, 1, RL_PIXELFORMAT_UNCOMPRESSED_R8G8B8)
        rTexture = LoadTextureFromImage(image)
        material = LoadMaterialDefault()
        mat_ptr = ffi.new("struct Material*", material)
        SetMaterialTexture(mat_ptr, MATERIAL_MAP_ALBEDO, rTexture)

        self.global_weakkeydict[mesh] = (rMesh, texture_c, rTexture)
        return rMesh, material

    def LoadTyres(self):
        tyrePath = f"{self.owner.state.hg2_game_folder_path}/CARS/TIRE.BIN"
        if not Path(tyrePath).exists():
            self.loaded_tyre = None
            return

        with open(tyrePath, "rb") as f:
            f.seek(0, os.SEEK_END)
            file_size = f.tell()
            f.seek(0, os.SEEK_SET)

            self.loaded_tyre = ModelData()
            tyre = QCar.read_car(f, 0, file_size)
            for mesh in tyre.meshes:
                rMesh, material = self.ConvertCarModel(mesh, tyre.textures)
                self.loaded_tyre.meshes.append(rMesh)
                self.loaded_tyre.materials.append(material)

    def LoadParts(self):
        partsPath = f"{self.owner.state.hg2_game_folder_path}/CARS/PARTS.BIN"
        if not Path(partsPath).exists():
            self.loaded_parts = None
            return

        with open(partsPath, "rb") as f:
            f.seek(0, os.SEEK_END)
            file_size = f.tell()
            f.seek(0, os.SEEK_SET)

            self.loaded_parts = ModelData()
            parts = QCar.read_car(f, 0, file_size)
            for mesh in parts.meshes:
                rMesh, material = self.ConvertCarModel(mesh, parts.textures)
                self.loaded_parts.meshes.append(rMesh)
                self.loaded_parts.materials.append(material)


if __name__ == '__main__':
    tools = ChoroQTools()
    tools.start_ui()



## Parts notes
# HG2:
# PARTS.BIN:
# 0  Hood scoop
# 1  devil hood
# 2  devil eyes for 2
# 3  wing suit closed
# 4  wing suit open
# 5  Fog lights frame
# 6  Fog light bulb (for night)
# 7  Police bar
# 8  Propeller framex4
# 9  single prop for 8
# 10 Skiis
# 11 Advert sign on top
# 12 Big wheel axle
# 13 propeller lp

# HG3:
# TIRE.BIN
# 0  Front left
# 1  Front Right
# 2  Rear axle
# 3  LP 4 normal
# 4  Big tire Left
# 5  Big tire Right
# 6  Long wheel base LP
# 7  Wide Short wheel base big LP
# 8  Wide back big tire LPd
#
# PARTS.BIN
# 0  Roof rack? hover wheels?
# 1  Wheel front left
# 2  Wheel front right
# 3  Wheel axle wide, no tire
# 4  Tracked axle (rear?) wide
# 5  Helicopter blades
# 6  Sporty front + side pipes
# 7  Hovercraft + surround for rear prop
# 8  rear prop for 7
# 9  single jet turbine?
# 10 top, side turning jets
# 11 umbrella
# 12 twin prop mounts
# 13 prop for 12
# 14 boat bottom
# 15 two squares, should have a full texture on them?
# 16 single prop, possibly for 15?
# 17 rudder?
# 18 rear wing? jet plane style
# 19 left ski
# 20 right ski
# 21 boat with wings?
# 22 like 15
# 23 like 16, prop
# 24 periscope
# 25 axle/suspension
# 26 Coin holder?
# 27 coin for 26
# 28 same as 0 lp
# 29 two wheels lp
# 30 tank tracks lp
# 31 same as 6 lp sport front
# 32 same as 14 boat lp
# 33 single jet