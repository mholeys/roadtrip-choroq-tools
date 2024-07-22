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
    print("Models will be exported as PLY by default, as OBJ does not contain vertex colours")
    print("")
    print("Currently this will only work when given the path to the game root")
    print("")
    print("Options: <REQUIRED> [OPTIONAL]")
    print("<source path>")
    print("<output folder>")
    # print("[makefolders]             : whether to create sub folders for each car : 1 = Yes")
    print("[type]                    : model output format")
    print("                            -- 1 = OBJ only")
    print("                            -- 2 = PLY only")
    print("                            -- 3 = Experimental OBJ grouped by material")
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
    print(Fore.YELLOW+"          with all data currently supported this will be around PLY: 4GB or OBJ: 3GB.")
    print(Fore.YELLOW+"          On my pc, on a HDD 5900RPM it takes ~15mins for OBJ.")
    print(Fore.YELLOW+"          Courses (obj): ~110K files ~450 MB")
    print(Fore.YELLOW+"          Courses (ply): ~110k files ~500 MB")
    print(Fore.YELLOW+"          Courses ( 3 ): ~ 12K files ~180 MB")
    print(Fore.YELLOW+"          Actions (obj): ~100K files ~400 MB")
    print(Fore.YELLOW+"          Actions (ply): ~100k files ~400 MB")
    print(Fore.YELLOW+"          Actions ( 3 ): ~ 13K files ~150 MB")
    print(Fore.YELLOW+"          Fields  (obj): ~600K files ~1.7 GB")
    print(Fore.YELLOW+"          Fields  (ply): ~730K files ~2.8 GB")
    print(Fore.YELLOW+"          Fields  ( 3 ): ~300K files ~850 MB")
    print(Fore.YELLOW+"          Cars    (obj): ~1.5k files ~120 MB")
    print(Fore.YELLOW+"          Cars    (ply): ~1.5k files ~100 MB")


# Open parse, and extract the common data, for fields/courses/actions
def process_course_type(courseFile, destFolder, fileNumber, outType, filePrefix, mergeByData = False):
    with open(courseFile, "rb") as f: # Open input course data file
        # Check that the output folders exist (make them)
        Path(f"{destFolder}/").mkdir(parents=True, exist_ok=True)
        Path(f"{destFolder}/colliders").mkdir(parents=True, exist_ok=True)

        # Set logging output
        with open(f"{destFolder}/log.log", "w") as sys.stdout:
            f.seek(0, os.SEEK_END)
            fileSize = f.tell()
            f.seek(0, os.SEEK_SET)
            # Parse the course
            course = CourseModel.fromFile(f, 0, fileSize)
        
            if mergeByData:
                # Need to group the meshes by the "data/material" info
                Path(f"{destFolder}/matLinked").mkdir(parents=True, exist_ok=True)
                # Sort all meshes into meshes by type
                numberOfMeshes = 0
                meshByMaterial = {}
                for i,level in enumerate(course.meshes):
                    for z, zRow in enumerate(level.chunks):
                        for x, ((meshes, data), meshesByData) in enumerate(zRow):
                            for dataIndex, (dd, mm) in meshesByData.items():
                                if dd == []:
                                    continue
                                dataKey = dd[0]
                                # Add meshes that match this material to the list of meshes
                                if dataKey not in meshByMaterial:
                                    meshByMaterial[dataKey] = []
                                meshByMaterial[dataKey] += mm
                                numberOfMeshes += 1
                                print(len(meshByMaterial[dataKey]))
                # Save all meshes into one file, based on their data/mat type
                matIndex = 0
                print("Mesh by material keys")
                print(meshByMaterial.keys())
                print("Number of meshes")
                print(numberOfMeshes)
                for key, mm in meshByMaterial.items():
                    # If you come across this, this is a custom file format I have made, expect this to change over time
                    # you will have to modify this file to get this to output
                    if outType == "comb":
                        with open(f"{destFolder}/matLinked/{filePrefix}{fileNumber}-{matIndex}.{outType}", "w") as fout:
                            fout.write("comb - mesh data format\n")
                            fout.write(f"meshes {len(mm)}\n")
                            fout.write(f"type field\n")

                            for m, mesh in enumerate(mm):
                                fout.write(f"s z{z}-x{x}-{m}\n") # Start of a mesh
                                mesh.writeMeshToType(outType, fout)
                                fout.write(f"e z{z}-x{x}-{m}\n") # End of a mesh
                    elif outType == "obj":
                        with open(f"{destFolder}/matLinked/{filePrefix}{fileNumber}-{matIndex}.{outType}", "w") as fout:
                            vertCount = 0
                            for m, mesh in enumerate(mm):
                                fout.write(f"o {m}\n") # Start of an object
                                vertCount += mesh.writeMeshToType(outType, fout, vertCount)
                    matIndex += 1
            else:
                # Export the main level mesh data
                for i,level in enumerate(course.meshes):
                    for z, zRow in enumerate(level.chunks):
                        Path(f"{destFolder}/").mkdir(parents=True, exist_ok=True)
                        for x, ((meshes, data), _) in enumerate(zRow):
                            for m, mesh in enumerate(meshes):
                                with open(f"{destFolder}/{filePrefix}{fileNumber}-{z}-{x}-{m}.{outType}", "w") as fout:
                                    mesh.writeMeshToType(outType, fout)

            # Export all maps
            for i,mesh in enumerate(course.mapMeshes):
                with open(f"{destFolder}/{filePrefix}{fileNumber}-map{i}.{outType}", "w") as fout:
                    mesh.writeMeshToType(outType, fout)
            # Export any additional objects (e.g barrels)
            for e,extra in enumerate(course.extras):
                for i,mesh in enumerate(extra.meshes):
                    with open(f"{destFolder}/{filePrefix}{fileNumber}-extra{e}-{i}.{outType}", "w") as fout:
                        mesh.writeMeshToType(outType, fout)
            for collidersByMat in course.colliders:
                for mat,colliders in collidersByMat.items():
                    for i,collider in enumerate(colliders):
                        with open(f"{destFolder}/colliders/{filePrefix}{fileNumber}-collider{i}.{outType}", "w") as fout:
                            collider.writeMeshToType(outType, fout)
            
            if len(course.textures) > 0:
                Path(f"{destFolder}/tex/").mkdir(parents=True, exist_ok=True)
            for i,texture in enumerate(course.textures):
                try:
                    texture.writeTextureToPNG(f"{destFolder}/tex/t{fileNumber}-{i}.png")
                except:
                    print(f"Failed to write texture/palette probably decoded badly Course:{fileNumber} Texture:{i} {texture}")
            for e,extra in enumerate(course.extras):
                for i,texture in enumerate(extra.textures):
                    try:
                        texture.writeTextureToPNG(f"{destFolder}/tex/t{fileNumber}-e{e}-{i}.png")
                    except:
                        print(f"Failed to write texture/palette probably decoded badly Course:{fileNumber} Texture:{i} {texture}")
        sys.stdout = sys.__stdout__

def process_courses(source, dest, folder, outputFormats, mergeByData = False):
    if not Path(f"{source}/{folder}").is_dir():
        print(f"No {folder}s to process, folder {folder} missing")
        return

    print(f"Processing {folder}s")
    with os.scandir(f"{source}/{folder}") as it:
        for entry in it:
            if not entry.name.startswith('.') and entry.is_file():
                cNumber = entry.name[0 : entry.name.find('.')]
                cPrefix = cNumber[0]
                cNumber = cNumber[1:]
                print(f"Processing {entry.name}")
                for outType in outputFormats:
                    courseOutputFolder = f"{dest}/{folder}/{cPrefix}{cNumber}{outType}"
                    try:
                        process_course_type(entry, courseOutputFolder, cNumber, outType, cPrefix, mergeByData)
                    except KeyboardInterrupt:
                        break
                    except:
                        sys.stdout = sys.__stdout__
                        print(f"Failed to process file {entry.path}")

def process_fields(source, dest, outputFormats, mergeByData = False):
    if not Path(f"{source}/FLD").is_dir():
        print("No fields to process, folder FLD missing")
        return
    print("Processing fields (FLD)")
    for fx in [0, 1, 2, 3]:
        for fy in [0, 1, 2, 3]:
            for fz in [0, 1, 2, 3]:
                fieldNumber = f"{fx}{fy}{fz}"
                fieldFile = f"{source}/FLD/{fieldNumber}.BIN"
                print(f"Processing {fieldFile}")
                for outType in outputFormats:
                    fieldOutputFolder = f"{dest}/FIELD/F{fieldNumber}{outType}"
                    process_course_type(fieldFile, fieldOutputFolder, fieldNumber, outType, "F", mergeByData)


def process_towns(source, dest, outputFormats, mergeByData = False):
    return
    if Path(f"{folderIn}/SYS").is_dir():
        for t in ["T00", "T00S01", "T01", "T02", "T03"]:
            townFile = f"{folderIn}/SYS/{t}.BIN"
            for outType in outputFormats:
                process_course_type(townFile, f"{folderOut}/TOWN/{t}-{outType}", t[1:], outType, "T", mergeByData)


def process_cars(source, dest, outputFormats):
    print("Processing cars")
    for carFolder in [f"{source}/CAR0", f"{source}/CAR1", f"{source}/CAR2", f"{source}/CAR3", f"{source}/CAR4", f"{source}/CARS"]:
        if Path(carFolder).is_dir():
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
        with open(f"{outfolder}/log.log", "w") as sys.stdout:
            os.makedirs(outfolder, exist_ok=True)
            f.seek(0, os.SEEK_END)
            fileSize = f.tell()
            f.seek(0, os.SEEK_SET)
            car = CarModel.fromFile(f, 0, fileSize)
            for i,mesh in enumerate(car.meshes):
                for outType in outputFormats:
                    with open(f"{outfolder}{basename}-{i}.{outType}", "w") as fout:
                        mesh.writeMeshToType(outType, fout)
            for i,tex in enumerate(car.textures):
                tex.writeTextureToPNG(f"{outfolder}{basename}-{i}.png")
                # tex.writePaletteToPNG(f"{outfolder}{basename}-{i}-p.png")
        sys.stdout = sys.__stdout__

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
    obj_grouped = False
    ply = True
    if len(sys.argv) == 4:
        obj = True if sys.argv[3] == "1" else False
        ply = True if sys.argv[3] == "2" else False
        obj_grouped = True if sys.argv[3] == "3" else False
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
    if obj_grouped == True:
        outputFormats.append("obj")

    # outputFormats = ["comb"]
    # obj_grouped = True

    if os.path.isdir(folderIn):
        process_courses(folderIn, folderOut, "COURSE", outputFormats, obj_grouped)
        process_courses(folderIn, folderOut, "ACTION", outputFormats, obj_grouped)
        process_fields(folderIn, folderOut, outputFormats, obj_grouped)
        process_cars(folderIn, folderOut, outputFormats)

        # Check for Towns for CHQ HG 3, DOESNT WORK ATM
        # process_towns(folderIn, folderOut, outputFormats, obj_grouped)


    else:
        print(Fore.RED + "ERROR: " +Style.RESET_ALL+ "Failed to read source folder")
        exit(1)
    

    



    
    