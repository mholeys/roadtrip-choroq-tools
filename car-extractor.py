from choroq.texture import Texture
from choroq.car import CarModel, CarMesh
from choroq.car_hg3 import HG3CarModel, HG3CarMesh

import io
import os
import sys
import pathlib
import colorama
from colorama import Fore, Back, Style

def show_help():
    print("##############################################################################################")
    print("ChoroQ car extractor by Matthew Holey")
    print("##############################################################################################")
    print("")
    print("Extracts RoadTrip Adventure car model/textures and accessories from Qxx.BIN files")
    print("Works on the UK/EU version of the game aka ChoroQ 2 HG")
    print("Textures are in PNG format, and the texture palette is also exported as PNG marked \"-p\"")
    print("Models will be exported as OBJ and PLY unless stated otherwise, OBJ does not contain colours")
    print("")
    print("Options: <REQUIRED> [OPTIONAL]")
    print("<folder/file to open>")
    print("<output folder>")
    print("[makefolders]             : whether to create sub folders for each car : 1 = Yes")
    print("[type]                    : model output format (requires [makefolders])")
    print("                            -- 1 = OBJ only")
    print("                            -- 2 = PLY only")
    print("                            --  <other> = BOTH ")
    print("[gameVersion]             : default = 2, ChoroQ HG 2 or other (requires [type])")
    print("                            -- 2 = HG 2")
    print("                            -- 3 = HG 3")

def process_file(entry, folder_out, obj = True, ply = True, gameVersion = 2):
    if type(entry) is str:
        entry = pathlib.Path(entry)
    basename = entry.name[0 : entry.name.find('.')]
    with open(entry, "rb") as f:
        out_folder = f"{folder_out}/{basename}/"
        os.makedirs(out_folder, exist_ok=True)
        f.seek(0, os.SEEK_END)
        file_size = f.tell()
        f.seek(0, os.SEEK_SET)
        if gameVersion == 2:
            car = CarModel.read_car(f, 0, file_size)
        elif gameVersion == 3:
            car = HG3CarModel.from_file(f, 0, file_size)

        # Get texture, and fix clut/palette
        address, texture = car.textures[0]
        clut_address, clut = car.textures[1]
        # assign palette
        unswizzled = Texture.unswizzle_bytes(clut)
        texture.palette = unswizzled  # Set the texture's palette accordingly
        texture.palette_width = clut.width
        texture.palette_height = clut.height

        # Save texture and material for use in mesh
        texture.write_texture_to_png(f"{out_folder}{basename}.png")
        # texture.writePaletteToPNG(f"{out_folder}/{basename}-{i}-p.png")
        texture_path = f"{basename}.png"
        with open(f"{out_folder}{basename}.mtl", "w") as fout:
            Texture.save_material_file_obj(fout, basename, texture_path)

        for i, mesh in enumerate(car.meshes):
            if obj:
                with open(f"{out_folder}{basename}-{i}.obj", "w") as fout:
                    mesh.write_mesh_to_obj(fout, material=basename)
            if ply:
                with open(f"{out_folder}{basename}-{i}.obj", "w") as fout:
                    mesh.write_mesh_to_ply(fout)


if __name__ == '__main__':
    colorama.init()
    if len(sys.argv) >= 3:
        folder_in = sys.argv[1]
        folderOut = sys.argv[2]
    else:
        show_help()
        print(Fore.RED +"ERROR: " + Style.RESET_ALL + "Not enough args")
        exit(1)
    
    makeFolders = False
    obj = True
    ply = True
    gameVersion = 2
    if len(sys.argv) == 4: 
        makeFolders = True if sys.argv[3] == "1" else False
    elif len(sys.argv) == 5:
        makeFolders = True if sys.argv[3] == "1" else False
        obj = True if sys.argv[4] == "1" else False
        ply = True if sys.argv[4] == "2" else False
    elif len(sys.argv) == 6:
        makeFolders = True if sys.argv[3] == "1" else False
        obj = True if sys.argv[4] == "1" else False
        ply = True if sys.argv[4] == "2" else False
        gameVersion = int(sys.argv[5])
    elif len(sys.argv) > 6:
        show_help()
        print(Fore.RED +"ERROR: " +Style.RESET_ALL+ "Too many args")
        exit(1)

    if gameVersion != 2 and gameVersion != 3:
        show_help()
        print(Fore.RED +"ERROR: " +Style.RESET_ALL+ "Unknown game version")
        exit(1)

    os.makedirs(folderOut, exist_ok=True)
    if not os.path.isdir(folderOut):
        print(Fore.RED +"ERROR: " +Style.RESET_ALL+ "Failed to create or use output folder")
        exit(1)

    if os.path.isdir(folder_in):
        with os.scandir(folder_in) as it:
            for entry in it:
                if not entry.name.startswith('.') and entry.is_file():
                    process_file(entry, folderOut, obj, ply, gameVersion)
    
    elif os.path.isfile(folder_in):
        process_file(folder_in, folderOut, obj, ply, gameVersion)
    else:
        print(Fore.RED + "ERROR: " + Style.RESET_ALL + "Failed to read file/folder " + folder_in)
        exit(1)
    
