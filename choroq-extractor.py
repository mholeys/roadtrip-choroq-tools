from choroq.texture import Texture
from choroq.car import CarModel, CarMesh
from choroq.course import CourseModel
from choroq.quickpic import QuickPic

import io
import os
import sys
from pathlib import Path
import colorama
from colorama import Fore, Back, Style

def show_help():
    print(Fore.BLUE+"##############################################################################################")
    print(Fore.BLUE+"ChoroQ HG 2 extractor by Matthew Holey")
    print(Fore.BLUE+"##############################################################################################")
    print(Style.RESET_ALL+"")
    print("Extracts Road Trip Adventure model/textures")
    print("Works on the UK/EU version of the game aka ChoroQ 2 HG")
    print("Textures are exported in PNG format") #, and the texture palette is marked \"-p\"")
    print("Models will be exported as PLY by default, OBJ does not contain colours")
    print("")
    print("Currently this will only work when given the path to the game root")
    print("")
    print("Options: <REQUIRED> [OPTIONAL]")
    print("<source path>")
    print("<output folder>")
    # print("[makefolders]             : whether to create sub folders for each car : 1 = Yes")
    print("[type]                    : model output format (requires [makefolders])")
    print("                            -- 1 = OBJ only")
    print("                            -- 2 = PLY only")
    print("                            --  <other> = BOTH ")

    print("The output folder structure will be as follows:")
    print("<output dir>/")
    print(" - COURSES/")
    print("   - Cxx{obj/ply}/ # where xx is the course number")
    print("     - colliders/ # Colliders/other mesh data")
    print("     - tex/ # All textures ")
    print("     - Cxx-{zIndex}-{xIndex}-{meshIndex}.{obj/ply}")
    print(" - ACTIONS/")
    print("   - Axx{obj/ply}/ # where xx is the action number")
    print("     - colliders/ # Colliders/other mesh data")
    print("     - tex/ # All textures ")
    print("     - Axx-{zIndex}-{xIndex}-{meshIndex}.{obj/ply}")
    print(" - FIELDS/")
    print("   - xxx{obj/ply}/ # where xxx is the field number")
    print("     - colliders/ # Folder for colliders/other mesh data")
    print("     - tex/ # Folder for all textures ")
    print("     - Cxx-{zIndex}-{xIndex}-{meshIndex}.{obj/ply}")
    print(" - CARS/")
    print("   - PARTS/ # Folder with models/textures for the extra parts")
    print("   - Qxx/ # Folders with model and textures for car Qxx")
    print("   - TIRE/ # Folder with models/textures for the tires")
    print("   - WHEEL/ # Folder with models/textures for the wheels")

    print(Fore.YELLOW+" WARNING: This may produce a large number of files, and take some time,")
    print(Fore.YELLOW+"          with all data currently supported this will be around 2GB")
    print(Fore.YELLOW+"          Courses (obj): ~100k files ~140 MB")
    print(Fore.YELLOW+"          Courses (ply): ~100k files ~190 MB")
    print(Fore.YELLOW+"          Fields  (obj): ~430k files ~700 MB")
    print(Fore.YELLOW+"          Fields  (ply): ~430K files ~900 MB")
    print(Fore.YELLOW+"          Cars    (obj): ~1.5k files ~120 MB")
    print(Fore.YELLOW+"          Cars    (ply): ~1.5k files ~100 MB")


def process_courses(source, dest, outputFormats):
    print("Processing courses")
    for cNumber in ['00', '01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12', '13', '14', '16', '18', '19', '20']:
        courseFile = f"{source}/COURSE/C{cNumber}.BIN"

        print(f"Processing {courseFile}")
        for outType in outputFormats:
            courseOutputFolder = f"{dest}/COURSE/C{cNumber}{outType}"
            with open(courseFile, "rb") as f: # Open input course data file
                # Check that the output folders exist (make them)
                Path(f"{courseOutputFolder}/").mkdir(parents=True, exist_ok=True)
                Path(f"{courseOutputFolder}/colliders").mkdir(parents=True, exist_ok=True)

                # Set logging output
                with open(f"{courseOutputFolder}/log.log", "w") as sys.stdout:
                    f.seek(0, os.SEEK_END)
                    fileSize = f.tell()
                    f.seek(0, os.SEEK_SET)
                    # Parse the course
                    course = CourseModel.fromFile(f, 0, fileSize)
                
                    # Export the main level mesh data
                    for i,level in enumerate(course.meshes):
                        for z, zRow in enumerate(level.chunks):
                            Path(f"{courseOutputFolder}/").mkdir(parents=True, exist_ok=True)
                            for x, (meshes, data) in enumerate(zRow):
                                for m, mesh in enumerate(meshes):
                                    with open(f"{courseOutputFolder}/C{cNumber}-{z}-{x}-{m}.{outType}", "w") as fout:
                                        mesh.writeMeshToType(outType, fout)

                    # Export all maps
                    for i,mesh in enumerate(course.mapMeshes):
                        with open(f"{courseOutputFolder}/C{cNumber}-map{i}.{outType}", "w") as fout:
                            mesh.writeMeshToType(outType, fout)
                    # Export any additional objects (e.g barrels)
                    for e,extra in enumerate(course.extras):
                        for i,mesh in enumerate(extra.meshes):
                            with open(f"{courseOutputFolder}/C{cNumber}-extra{e}-{i}.{outType}", "w") as fout:
                                mesh.writeMeshToType(outType, fout)
                    for collidersByMat in course.colliders:
                        for mat,colliders in collidersByMat.items():
                            for i,collider in enumerate(colliders):
                                with open(f"{courseOutputFolder}/colliders/C{cNumber}-collider{i}.{outType}", "w") as fout:
                                    collider.writeMeshToType(outType, fout)
                    
                    if len(course.textures) > 0:
                        Path(f"{courseOutputFolder}/tex/").mkdir(parents=True, exist_ok=True)
                    for i,texture in enumerate(course.textures):
                        try:
                            texture.writeTextureToPNG(f"{courseOutputFolder}/tex/t{cNumber}-{i}.png")
                        except:
                            print(f"Failed to write texture/palette probably decoded badly Course:{cNumber} Texture:{i} {texture}")
                    for e,extra in enumerate(course.extras):
                        for i,texture in enumerate(extra.textures):
                            try:
                                texture.writeTextureToPNG(f"{courseOutputFolder}/tex/t{cNumber}-e{e}-{i}.png")
                            except:
                                print(f"Failed to write texture/palette probably decoded badly Course:{cNumber} Texture:{i} {texture}")
                sys.stdout = sys.__stdout__

def process_fields(source, dest, outputFormats):
    print("Processing fields (FLD)")
    for fx in [0, 1, 2, 3]:
        for fy in [0, 1, 2, 3]:
            for fz in [0, 1, 2, 3]:
                fieldNumber = f"{fx}{fy}{fz}"
                fieldFile = f"{source}/FLD/{fieldNumber}.BIN"
                print(f"Processing {fieldFile}")
                for outType in outputFormats:
                    fieldOutputFolder = f"{dest}/FIELD/F{fieldNumber}{outType}"
                    with open(fieldFile, "rb") as f: # Open input field data file
                        # Check that the output folders exist (make them)
                        Path(f"{fieldOutputFolder}/").mkdir(parents=True, exist_ok=True)
                        Path(f"{fieldOutputFolder}/colliders").mkdir(parents=True, exist_ok=True)

                        # Set logging output
                        with open(f"{fieldOutputFolder}/log.log", "w") as sys.stdout:
                            f.seek(0, os.SEEK_END)
                            fileSize = f.tell()
                            f.seek(0, os.SEEK_SET)
                            # Parse the field
                            field = CourseModel.fromFile(f, 0, fileSize)
                        
                            # Export the main level mesh data
                            for i,level in enumerate(field.meshes):
                                for z, zRow in enumerate(level.chunks):
                                    Path(f"{fieldOutputFolder}/").mkdir(parents=True, exist_ok=True)
                                    for x, (meshes, data) in enumerate(zRow):
                                        for m, mesh in enumerate(meshes):
                                            with open(f"{fieldOutputFolder}/F{fieldNumber}-{z}-{x}-{m}.{outType}", "w") as fout:
                                                mesh.writeMeshToType(outType, fout)
    
                            # Export all maps
                            for i,mesh in enumerate(field.mapMeshes):
                                with open(f"{fieldOutputFolder}/F{fieldNumber}-map{i}.{outType}", "w") as fout:
                                    mesh.writeMeshToType(outType, fout)
                            # Export any additional objects (e.g barrels)
                            for e,extra in enumerate(field.extras):
                                for i,mesh in enumerate(extra.meshes):
                                    with open(f"{fieldOutputFolder}/F{fieldNumber}-extra{e}-{i}.{outType}", "w") as fout:
                                        mesh.writeMeshToType(outType, fout)

                            for collidersByMat in course.colliders:
                                for mat,colliders in collidersByMat.items():
                                    for i,collider in enumerate(colliders):
                                        with open(f"{fieldOutputFolder}/colliders/F{fieldNumber}-collider{i}.{outType}", "w") as fout:
                                            collider.writeMeshToType(outType, fout)
                            
                            if len(field.textures) > 0:
                                Path(f"{fieldOutputFolder}/tex/").mkdir(parents=True, exist_ok=True)
                            for i,texture in enumerate(field.textures):
                                try:
                                    texture.writeTextureToPNG(f"{fieldOutputFolder}/tex/t{fieldNumber}-{i}.png")
                                except:
                                    print(f"Failed to write texture/palette probably decoded badly Field:{fieldNumber} Texture:{i} {texture}")
                            for e,extra in enumerate(field.extras):
                                for i,texture in enumerate(extra.textures):
                                    try:
                                        texture.writeTextureToPNG(f"{fieldOutputFolder}/tex/t{fieldNumber}-e{e}-{i}.png")
                                    except:
                                        print(f"Failed to write texture/palette probably decoded badly Field:{fieldNumber} Texture:{i} {texture}")
                        sys.stdout = sys.__stdout__

def process_cars(source, dest, outputFormats):
    print("Processing cars")
    for carFolder in [f"{source}/CAR0", f"{source}/CAR1", f"{source}/CAR2", f"{source}/CAR3", f"{source}/CAR4", f"{source}/CARS"]:
        with os.scandir(carFolder) as it:
            for entry in it:
                if not entry.name.startswith('.') and entry.is_file():
                    process_file(entry, dest, outputFormats)

def process_file(entry, folderOut, outputFormats):
    if type(entry) is str:
        entry = pathlib.Path(entry)
    basename = entry.name[0 : entry.name.find('.')]
    print(f"Processing {entry}")
    with open(entry, "rb") as f:
        outfolder = f"{folderOut}/CARS/{basename}/"
        os.makedirs(outfolder, exist_ok=True)
        f.seek(0, os.SEEK_END)
        fileSize = f.tell()
        f.seek(0, os.SEEK_SET)
        car = CarModel.fromFile(f, 0, fileSize)
        for i,mesh in enumerate(car.meshes):
            for outType in outputFormats:
                with open(f"{outfolder}{basename}-{i}.ply", "w") as fout:
                    mesh.writeMeshToType(outType, fout)
        for i,tex in enumerate(car.textures):
            tex.writeTextureToPNG(f"{outfolder}{basename}-{i}.png")
            # tex.writePaletteToPNG(f"{outfolder}{basename}-{i}-p.png")

if __name__ == '__main__':
    colorama.init()
    if len(sys.argv) >= 3:
        folderIn = sys.argv[1]
        folderOut = sys.argv[2]
    else:
        show_help()
        print(Fore.RED +"ERROR: " + Style.RESET_ALL + "Not enough args")
        exit(1)
    
    obj = False
    ply = True
    if len(sys.argv) == 4:
        obj = True if sys.argv[3] == "1" else False
        ply = True if sys.argv[3] == "2" else False
    elif len(sys.argv) > 4:
        show_help()
        print(Fore.RED +"ERROR: " +Style.RESET_ALL+ "Too many args")
        exit(1)

    os.makedirs(folderOut, exist_ok=True)
    if not os.path.isdir(folderOut):
        print(Fore.RED +"ERROR: " +Style.RESET_ALL+ "Failed to create or use output folder")
        exit(1)

    if os.path.isfile(folderIn):
        print(Fore.RED +"ERROR: " +Style.RESET_ALL+ "This tool is for extracting all game data, not just a single file, see help")
        exit(1)

    outputFormats = []
    if obj == True:
        outputFormats.append("obj")
    if ply == True:
        outputFormats.append("ply")

    if os.path.isdir(folderIn):
        process_courses(folderIn, folderOut, outputFormats)
        process_actions(folderIn, folderOut, outputFormats)
        process_fields(folderIn, folderOut, outputFormats)
        process_cars(folderIn, folderOut, outputFormats)
    else:
        print(Fore.RED + "ERROR: " +Style.RESET_ALL+ "Failed to read source folder")
        exit(1)
    

    



    
    