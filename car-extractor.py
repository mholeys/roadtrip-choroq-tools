from choroq.texture import Texture
from choroq.car import CarModel, CarMesh

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

def process_file(entry, folderOut, obj = True, ply = True):
    if type(entry) is str:
        entry = pathlib.Path(entry)
    basename = entry.name[0 : entry.name.find('.')]
    with open(entry, "rb") as f:
        outfolder = f"{folderOut}/{basename}/"
        os.makedirs(outfolder, exist_ok=True)
        f.seek(0, os.SEEK_END)
        fileSize = f.tell()
        f.seek(0, os.SEEK_SET)
        car = CarModel.fromFile(f, 0, fileSize)
        for i,mesh in enumerate(car.meshes):
            if obj:
                with open(f"{outfolder}{basename}-{i}.obj", "w") as fout:
                    mesh.writeMeshToObj(fout)
            if ply:
                with open(f"{outfolder}{basename}-{i}.ply", "w") as fout:
                    mesh.writeMeshToPly(fout)
        for i,tex in enumerate(car.textures):
            tex.writeTextureToPNG(f"{outfolder}{basename}-{i}.png")
            tex.writePaletteToPNG(f"{outfolder}{basename}-{i}-p.png")

if __name__ == '__main__':
    colorama.init()
    if len(sys.argv) >= 3:
        folderIn = sys.argv[1]
        folderOut = sys.argv[2]
    else:
        show_help()
        print(Fore.RED +"ERROR: " + Style.RESET_ALL + "Not enough args")
        exit(1)
    
    makeFolders = False
    obj = True
    ply = True
    if len(sys.argv) == 4: 
        makeFolders = True if sys.argv[3] == "1" else False
    elif len(sys.argv) == 5:
        makeFolders = True if sys.argv[3] == "1" else False
        obj = True if sys.argv[4] == "1" else False
        ply = True if sys.argv[4] == "2" else False
    elif len(sys.argv) > 4:
        show_help()
        print(Fore.RED +"ERROR: " +Style.RESET_ALL+ "Too many args")
        exit(1)

    os.makedirs(folderOut, exist_ok=True)
    if not os.path.isdir(folderOut):
        print(Fore.RED +"ERROR: " +Style.RESET_ALL+ "Failed to create or use output folder")
        exit(1)

    if os.path.isdir(folderIn):
        with os.scandir(folderIn) as it:
            for entry in it:
                if not entry.name.startswith('.') and entry.is_file():
                    process_file(entry, folderOut, obj, ply)
    
    elif os.path.isfile(folderIn):
        process_file(folderIn, folderOut, obj, ply)
    else:
        print(Fore.RED + "ERROR: " +Style.RESET_ALL+ "Failed to read file/folder")
        exit(1)
    

    



    
    