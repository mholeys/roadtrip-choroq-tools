from choroq.texture import Texture
from choroq.car import CarModel, CarMesh
from choroq.car_hg3 import HG3CarModel, HG3CarMesh
from choroq.course import CourseModel, Course
from choroq.garage import GarageModel
from choroq.shop import Shop
from choroq.quickpic import QuickPic

import io
import os
import sys
from pathlib import Path
import colorama
from colorama import Fore, Back, Style

# Set to true if you want 16x16 grid of collision mesh's (probably not that useful for most people)
OUTPUT_CHUNKED_COLLIDER = False
# Output obj files wih "o" lines, to split sections of the read mesh (probably not that useful for most people)
OUTPUT_GROUPED_OBJS = False
# Create log files or not (probably not that useful for most people)
CREATE_LOG_FILES = False

should_exit = False

def show_help():
    print(Fore.BLUE+"##############################################################################################")
    print(Fore.BLUE+"ChoroQ HG 2 extractor by Matthew Holey")
    print(Fore.BLUE+"##############################################################################################")
    print(Style.RESET_ALL+"")
    print("Extracts Road Trip Adventure model/textures")
    print("Works on the UK/EU version of the game aka ChoroQ 2 HG")
    print("Textures are exported in PNG format") #, and the texture palette is marked \"-p\"")
    print("Models will be exported as OBJ by default")
    print("")
    print("Currently this will only work when given the path to the game root")
    print("")
    print("Options: <REQUIRED> [OPTIONAL]")
    print("<source path>")
    print("<output folder>")
    # print("[makefolders]             : whether to create sub folders for each car : 1 = Yes")
    print("[type]                    : model output format")
    print("                            -- 1 = OBJ only, grouped by texture (default)")
    print("                            -- C = OBJ only, grouped by texture with r/g/b after x/y/z (blender)")
    # print("                            -- 2 = PLY only")

    print("The output folder structure will be as follows:")
    print("<output dir>/")
    print(" - COURSES/")
    print("   - Cxx{obj/ply}/ # where xx is the course number")
    print("     - colliders/ # Colliders/other mesh data")
    print("     - meshes/ # All level meshes ")
    print("     - meshes/tex/ # All textures for the level ")
    print("     - / extra meshes that move, such as the level's map or a door")
    print(" - ACTIONS/")
    print("   - Axx{obj/ply}/ # where xx is the action number")
    print("     - colliders/ # Colliders/other mesh data")
    print("     - meshes/ # All level meshes ")
    print("     - meshes/tex/ # All textures for the level ")
    print("     - / extra meshes that move, such as the level's map or a door e.g C00-map0.obj")
    print(" - FIELDS/")
    print("   - Fxxx{obj/ply}/ # where xxx is the field number")
    print("     - colliders/ # Folder for colliders/other mesh data")
    print("     - meshes/ # All field meshes ")
    print("         - Fxxx-{texture_index}.{obj/ply}")
    print("         - Fxxx-{texture_index}.{mtl}")
    print("     - meshes/tex/ # Folder for all textures ")
    print(" - CARS/")
    print("   - PARTS/ # Folder with models/textures for the extra parts")
    print("   - Qxx/ # Folders with model and textures for car Qxx")
    print("   - TIRE/ # Folder with models/textures for the tires")
    print("   - WHEEL/ # Folder with models/textures for the wheels")

    print(Fore.YELLOW+" WARNING: This may produce a large number of files, and take some time,")
    print(Fore.YELLOW+"          with all data currently supported this will be around OBJ: 2GB.")
    print(Fore.YELLOW+"          On my pc, on a HDD 5900RPM it takes ~15mins for OBJ.")
    print(Fore.YELLOW+"          Courses (obj): ~7.2k files ~160 MB")
    print(Fore.YELLOW+"          Courses (obj+C): ~7.2k files ~230 MB")
    # print(Fore.YELLOW+"          Courses (ply): ~110k files ~500 MB")
    print(Fore.YELLOW+"          Courses ( 3 ): ~ 12K files ~130 MB")
    print(Fore.YELLOW+"          Actions (obj): ~7.5K files ~130 MB")
    print(Fore.YELLOW+"          Actions (obj+C): ~7.5K files ~190 MB")
    # print(Fore.YELLOW+"          Actions (ply): ~100k files ~400 MB")
    print(Fore.YELLOW+"          Actions ( 3 ): ~ 14K files ~100 MB")
    print(Fore.YELLOW+"          Fields  (obj): ~22K files ~1.7 GB")
    print(Fore.YELLOW+"          Fields  (obj+C): ~22K files ~1.25 GB")
    # print(Fore.YELLOW+"          Fields  (ply): ~730K files ~2.8 GB")
    print(Fore.YELLOW+"          Fields  ( 3 ): ~230K files ~483 MB")
    print(Fore.YELLOW+"          Cars    (obj): ~1.7k files ~120 MB")
    print(Fore.YELLOW+"          Cars    (obj+C): ~1.7k files ~160 MB")
    # print(Fore.YELLOW+"          Cars    (ply): ~1.5k files ~100 MB")
    print(Fore.YELLOW + "        HG3: with all data currently supported this will be around OBJ: 1.2GB.")


def group_meshes_by_material(meshes):
    # Sort all meshes into meshes by type
    number_of_meshes = 0
    mesh_by_material = {}
    for i, level in enumerate(meshes):
        for z, zRow in enumerate(level.chunks):
            for x, meshesByData in enumerate(zRow):
                for dataKey, mm in meshesByData.items():
                    # Add meshes that match this material to the list of meshes
                    if dataKey not in mesh_by_material:
                        mesh_by_material[dataKey] = []
                    mesh_by_material[dataKey] += mm
                    number_of_meshes += 1
                    print(len(mesh_by_material[dataKey]))

    return mesh_by_material, number_of_meshes
    

def save_course_type_grouped(mesh_by_material, number_of_meshes, dest_folder, file_number, out_type, file_prefix, textures):
    # Save all meshes into one file, based on their data/mat type
    mat_index = 0
    print("Mesh by material keys")
    print(mesh_by_material.keys())
    print("Number of meshes")
    print(number_of_meshes)

    Path(f"{dest_folder}/meshes/tex/").mkdir(parents=True, exist_ok=True)
    mat_index = 0
    done_textures = []
    for key, mm in mesh_by_material.items():
        if should_exit:
            break
        # Export textures
        material_name = f"{file_prefix}{file_number}-{mat_index}"
        texture_path_relative = f"tex/t{file_number}-{mat_index}.png"
        # save texture for this mesh
        if key not in done_textures:
            clut_address, texture_address = key

            if texture_address == 0 or clut_address == 0:  # 0, 0 is often added, but with no meshes
                if len(mm) != 0:
                    print(
                        f"Mat index {mat_index} has no texture {texture_address} or no clut {clut_address} meshes {len(mm)}")
                    for m in mm:
                        print(vars(m))
            elif texture_address not in textures:
                print(f"Texture addressing wrong, check value {texture_address}")
                exit(2)
            else:
                texture = textures[texture_address]

                if clut_address not in textures:
                    # Check texture type
                    if texture.bpp > 8:
                        # This is possibly just an image, no clut, esp if bpp == 24 or 32
                        # save texture as is, without using any CLUTs
                        print(f"Clut addressing wrong, {clut_address} but image should be fine as is")
                        print(f"{dest_folder}/meshes/{texture_path_relative}")
                        texture.write_texture_to_png(f"{dest_folder}/meshes/{texture_path_relative}",
                                                     use_palette=False)
                    else:
                        # This texture almost certainly needs a CLUT, as it would be B&W otherwise, unlikely
                        print(f"Clut addressing wrong, check value {clut_address}")
                else:
                    # Fetch the texture, and the clut to use
                    clut = textures[clut_address]
                    print(
                        f"Creating paletted image {texture_address} {texture_address:x} using {clut_address} {clut_address:x}")
                    print(f"clut bpp: {clut.bpp}")
                    if clut.bpp != 32 and clut.bpp != 24:
                        print(f"Not using CLUT: as bpp {clut.bpp} is not right")
                        print(f"{dest_folder}/meshes/{texture_path_relative}")
                        texture.write_texture_to_png(f"{dest_folder}/meshes/{texture_path_relative}",
                                                     use_palette=False)
                    else:
                        # Clut valid enough
                        # Unswizzle the palette, as these are (should) be swizzled for the PS2
                        unswizzled = Texture.unswizzle_bytes(clut)
                        texture.palette = unswizzled  # Set the texture's palette accordingly
                        texture.palette_width = clut.width
                        texture.palette_height = clut.height
                        try:
                            # Save the texture using the given clut
                            print(f"{dest_folder}/meshes/{texture_path_relative}")
                            texture.write_texture_to_png(f"{dest_folder}/meshes/{texture_path_relative}")
                            print(f"Saved texture for material group {mat_index} t{file_number}-{mat_index}.png")
                            print()
                        except Exception as e:
                            if isinstance(e, ValueError):
                                if len(e.args) == 1 and e.args[0] == "invalid palette size":
                                    # Assume this is a normal b&w texture and the clut is probably just a different tex
                                    print(f"Not using CLUT: as bpp {clut.bpp} is not right")
                                    print(f"{dest_folder}/meshes/{texture_path_relative}")
                                    texture.palette = []
                                    texture.palette_width = 0
                                    texture.palette_height = 0
                                    texture.write_texture_to_png(f"{dest_folder}/meshes/{texture_path_relative}", use_palette=False)
                            else:
                                texture.write_texture_to_png(f"{dest_folder}/meshes/failed-t{file_number}-{mat_index}-{texture_address:x}.png", use_palette=False)
                                clut.write_texture_to_png(f"{dest_folder}/meshes/failed-clut-t{file_number}-{mat_index}-{clut_address:x}.png")
                                print(f"Failed to write texture probably decoded badly Course:{file_number} Texture: {texture_address} {clut_address} {texture}")
                                print(f"Info: W: {texture.width} x H:{texture.height}  pW: {texture.palette_width} x pH: {texture.palette_height}")
                                print(e)

                # create material for this texture, for obj
                if out_type == "obj" or out_type == "obj-combined" or out_type == "obj+colour":
                    with open(f"{dest_folder}/meshes/{material_name}.mtl", "w") as fout:
                        Texture.save_material_file_obj(fout, material_name, texture_path_relative)

                done_textures.append(key)

        # If you come across this, this is a custom file format I have made, expect this to change over time
        # you will have to modify this file to get this to output
        if out_type == "comb":
            with open(f"{dest_folder}/meshes/{file_prefix}{file_number}-{mat_index}.{out_type}", "w") as fout:
                fout.write("comb - mesh data format\n")
                fout.write(f"meshes {len(mm)}\n")
                fout.write(f"type field\n")

                for m, mesh in enumerate(mm):
                    fout.write(f"s z-{m}\n") # Start of a mesh
                    mesh.write_mesh_to_type(out_type, fout, material=texture_path_relative)
                    fout.write(f"e z-{m}\n") # End of a mesh
        elif out_type == "obj" or out_type == "obj+colour":
            extension = out_type
            if out_type == "obj+colour":
                extension = "obj"
            with open(f"{dest_folder}/meshes/{file_prefix}{file_number}-{mat_index}.{extension}", "w") as fout:
                vert_count = 0
                for m, mesh in enumerate(mm):
                    if OUTPUT_GROUPED_OBJS:
                        fout.write(f"o {m}\n") # Start of an object
                    vert_count += mesh.write_mesh_to_type(out_type, fout, vert_count, material_name)
        elif out_type == "ply":
            with open(f"{dest_folder}/meshes/{file_prefix}{file_number}-{mat_index}.{out_type}", "w") as fout:
                vert_count = 0
                for m, mesh in enumerate(mm):
                    vert_count += mesh.write_mesh_to_type(out_type, fout, vert_count, material_name)

        mat_index += 1


def save_course_type(meshes, dest_folder, file_number, out_type, file_prefix):
    # Export the main level mesh data
    for i, level in enumerate(meshes):
        if should_exit:
            break
        for z, zRow in enumerate(level.chunks):
            Path(f"{dest_folder}/").mkdir(parents=True, exist_ok=True)
            for x, ((meshes, data), _) in enumerate(zRow):
                for m, mesh in enumerate(meshes):
                    if should_exit:
                        break
                    with open(f"{dest_folder}/{file_prefix}{file_number}-{z}-{x}-{m}.{out_type}", "w") as fout:
                        mesh.write_mesh_to_type(out_type, fout)


# Open parse, and extract the common data, for fields/courses/actions
def process_course_type(course_file, dest_folder, file_number, out_type, file_prefix):
    with open(course_file, "rb") as f:  # Open input course data file
        # Check that the output folders exist (make them)
        Path(f"{dest_folder}/").mkdir(parents=True, exist_ok=True)
        Path(f"{dest_folder}/colliders").mkdir(parents=True, exist_ok=True)

        if CREATE_LOG_FILES:
            log_dest = f"{dest_folder}/log.log"
        else:
            log_dest = os.devnull
        # Set logging output
        prev_std_out = sys.stdout
        with open(log_dest, "w") as sys.stdout:
            f.seek(0, os.SEEK_END)
            file_size = f.tell()
            f.seek(0, os.SEEK_SET)
            # Parse the course
            course = CourseModel.read_course(f)

            # Need to group the meshes by the "data/material" info
            Path(f"{dest_folder}/meshes").mkdir(parents=True, exist_ok=True)
            mesh_by_material, number_of_meshes = group_meshes_by_material(course.meshes)
            save_course_type_grouped(mesh_by_material, number_of_meshes, dest_folder, file_number, out_type, file_prefix, course.textures)

            extension = out_type
            if out_type == "obj+colour":
                extension = "obj"

            # Export all maps
            for i, mesh in enumerate(course.map_meshes):
                if should_exit:
                    break
                with open(f"{dest_folder}/{file_prefix}{file_number}-map{i}.{extension}", "w") as fout:
                    mesh.write_mesh_to_type(out_type, fout)
            # Export any additional objects (e.g barrels)
            for e, extra in enumerate(course.extras):
                if should_exit:
                    break
                for i, mesh in enumerate(extra.meshes):
                    with open(f"{dest_folder}/{file_prefix}{file_number}-extra{e}-{i}.{extension}", "w") as fout:
                        mesh.write_mesh_to_type(out_type, fout)
                for i in range(0, len(extra.textures)):
                    address, texture = extra.textures[i]
                    if texture is None:
                        continue
                    print(f"{address}: {i} bpp: {texture.bpp} {texture.width}x{texture.height}")
                    if texture.bpp <= 8:
                        # Get next image as clut
                        clut_address, clut = extra.textures[i + 1]
                        print(f"Using clut to merge, bpp: {clut.bpp} {clut.width}x{clut.height}")
                        print(f"{clut_address}: {i}")
                        # texture.write_texture_to_png(f"{out_folder}/{entry.name}-{address:x}-raw.png")
                        if clut is None:
                            texture.write_texture_to_png(f"{dest_folder}/t{file_number}-e{e}-{address:x}-{i}.png")
                            continue
                        # clut.write_texture_to_png(f"{dest_folder}/t{file_number}-{clut_address:x}-raw.png")
                        # Set the texture's palette accordingly
                        unswizzled = Texture.unswizzle_bytes(clut)
                        texture.palette = unswizzled
                        texture.palette_width = clut.width
                        texture.palette_height = clut.height
                        try:
                            texture.write_texture_to_png(f"{dest_folder}/t{file_number}-e{e}-{address:x}.png")
                        except e:
                            print(f"Failed to write texture/palette probably decoded badly Course:Extra:{file_number} Texture:{address:x}/{i} {texture}")
            collider_mat_index = 0
            for mat, colliders in course.colliders_by_mat.items():
                if should_exit:
                    break
                # If you come across this, this is a custom file format I have made, expect this to change over time
                # you will have to modify this file to get this to output
                if out_type == "comb":
                    with open(f"{dest_folder}/colliders/{file_prefix}{file_number}-{collider_mat_index}.{out_type}",
                              "w") as fout:
                        fout.write("comb - mesh data format\n")
                        fout.write(f"meshes {len(colliders)}\n")
                        fout.write(f"type collider\n")
                        for i, collider in enumerate(colliders):
                            fout.write(f"s {i}\n")  # Start of a mesh
                            collider.write_mesh_to_type(out_type, fout)
                            fout.write(f"e {i}\n")  # End of a mesh

                elif out_type == "obj" or out_type == "obj+colour":
                    with open(f"{dest_folder}/colliders/{file_prefix}{file_number}-{collider_mat_index}.{extension}", "w") as fout:
                        vert_count = 0
                        for i, collider in enumerate(colliders):
                            if OUTPUT_GROUPED_OBJS:
                                fout.write(f"o {i}\n")  # Start of an object
                            vert_count += collider.write_mesh_to_type(out_type, fout, vert_count)
                collider_mat_index += 1
            if out_type == "obj" and OUTPUT_CHUNKED_COLLIDER or out_type == "obj+colour":
                Path(f"{dest_folder}/colliders/all").mkdir(parents=True, exist_ok=True)
                for z, z_row in enumerate(course.colliders):
                    if should_exit:
                        break
                    for x, collider in enumerate(z_row):
                        if should_exit:
                            break
                        with open(f"{dest_folder}/colliders/all/{file_prefix}{file_number}-{z}-{x}.{extension}", "w") as fout:
                            if OUTPUT_GROUPED_OBJS:
                                fout.write(f"o {z}-{x}\n")  # Start of an object
                            collider.write_mesh_to_type(out_type, fout)

            # Handle post colliders (thinks like fence posts, and tree centres)
            if len(course.post_colliders) > 0:
                if out_type == "comb":
                    with open(f"{dest_folder}/colliders/{file_prefix}{file_number}-posts.{out_type}",
                              "w") as fout:
                        fout.write("comb - mesh data format\n")
                        fout.write(f"meshes {len(course.post_colliders)}\n")
                        fout.write(f"type post-collider\n")
                        for p, post in enumerate(course.post_colliders):
                            fout.write(f"s {p}\n")  # Start of a mesh
                            post.write_mesh_to_type(out_type, fout)
                            fout.write(f"e {p}\n")  # End of a mesh
                elif out_type == "obj" or out_type == "obj+colour":
                    with open(f"{dest_folder}/colliders/{file_prefix}{file_number}-posts.{extension}",
                              "w") as fout:
                        for p, post in enumerate(course.post_colliders):
                            if OUTPUT_GROUPED_OBJS:
                                fout.write(f"o {p}\n")  # Start of an object
                            post.write_mesh_to_type(out_type, fout)

            if len(course.extra_fields) > 0:
                Path(f"{dest_folder}/extras/meshes").mkdir(parents=True, exist_ok=True)
                Path(f"{dest_folder}/extras/colliders").mkdir(parents=True, exist_ok=True)
                mesh_by_material, number_of_meshes = group_meshes_by_material(course.extra_fields)
                save_course_type_grouped(mesh_by_material, number_of_meshes, f"{dest_folder}/extras/", file_number, out_type, file_prefix + "-E", course.textures)
                collider_mat_index = 0

                for ci, col in enumerate(course.extra_field_colliders):
                    if should_exit:
                        break
                    if isinstance(col, list):
                        # Probably post colliders
                        for c in col:
                            # TODO: save posts
                            pass
                    else:
                        for mat, colliders in col.items():
                            # If you come across this, this is a custom file format I have made,
                            # expect this to change over time you will have to modify this file
                            # to get this to output
                            if out_type == "comb":
                                with open(f"{dest_folder}/extras/colliders/{file_prefix}{file_number}-{ci}-{collider_mat_index}.{out_type}",
                                          "w") as fout:
                                    fout.write("comb - mesh data format\n")
                                    fout.write(f"meshes {len(colliders)}\n")
                                    fout.write(f"type collider\n")
                                    for i, collider in enumerate(colliders):
                                        fout.write(f"s {i}\n")  # Start of a mesh
                                        collider.write_mesh_to_type(out_type, fout)
                                        fout.write(f"e {i}\n")  # End of a mesh

                            elif out_type == "obj" or out_type == "obj+colour":
                                with open(f"{dest_folder}/extras/colliders/{file_prefix}{file_number}-{ci}-{collider_mat_index}.{extension}",
                                          "w") as fout:
                                    vert_count = 0
                                    for i, collider in enumerate(colliders):
                                        if OUTPUT_GROUPED_OBJS:
                                            fout.write(f"o {i}\n")  # Start of an object
                                        vert_count += collider.write_mesh_to_type(out_type, fout, vert_count)
                            collider_mat_index += 1
        sys.stdout = prev_std_out


def process_courses(source, dest, folder, output_formats):
    if not Path(f"{source}/{folder}").is_dir():
        print(f"No {folder}s to process, folder {folder} missing")
        return

    print(f"Processing {folder}s")
    with os.scandir(f"{source}/{folder}") as it:
        for entry in it:
            if should_exit:
                break
            process_course(entry, dest, folder, output_formats)


def process_course(entry, dest, folder, output_formats):
    if type(entry) is str:
        entry = Path(entry)
    if not entry.name.startswith('.') and entry.is_file():
        c_number = entry.name[0: entry.name.find('.')]
        c_prefix = c_number[0]
        c_number = c_number[1:]
        print(f"Processing {entry.name}")
        for outType in output_formats:
            if should_exit:
                break
            course_output_folder = f"{dest}/{folder}/{c_prefix}{c_number}{outType}"
            try:
                process_course_type(entry, course_output_folder, c_number, outType, c_prefix)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(e)
                sys.stdout = sys.__stdout__
                print(f"Failed to process file {entry.path}")


def process_fields(source, dest, output_formats, merge_by_data=False):
    if not Path(f"{source}/FLD").is_dir():
        print("FLD folder missing, assuming HG3")
        # for town in ["00", "00S01", "01", "02", "03"]:
        #     town_number = f"{town}"
        #     town_file = f"{source}/SYS/T{town_number}.BIN"
        #     print(f"Processing {town_file}")
        #     for out_type in output_formats:
        #         field_output_folder = f"{dest}/TOWN/T{town_number}{out_type}"
        #         process_course_type(town_file, field_output_folder, town_number, out_type, "T")
        return
    print("Processing fields (FLD)")
    for fx in [0, 1, 2, 3]:
        for fy in [0, 1, 2, 3]:
            for fz in [0, 1, 2, 3]:
                if should_exit:
                    break
                field_number = f"{fx}{fy}{fz}"
                field_file = f"{source}/FLD/{field_number}.BIN"
                print(f"Processing {field_file}")
                for out_type in output_formats:
                    if should_exit:
                        break
                    field_output_folder = f"{dest}/FIELD/F{field_number}{out_type}"
                    if not Path(field_file).exists():
                        continue
                    process_course_type(field_file, field_output_folder, field_number, out_type, "F")


def process_cars(source, dest, output_formats):
    print("Processing cars")
    # Default to hg2 cars
    version = 2
    if not Path(f"{source}/CAR0").is_dir():
        # Then using chq hg 3 cars
        print("HG3 cars")
        version = 3

    for carFolder in [f"{source}/CAR0", f"{source}/CAR1", f"{source}/CAR2", f"{source}/CAR3", f"{source}/CAR4", f"{source}/CARS"]:
        if should_exit:
            break
        if Path(carFolder).is_dir():
            with os.scandir(carFolder) as it:
                for entry in it:
                    if should_exit:
                        break
                    if entry.name == "WHEEL.BIN":
                        continue
                    if entry.name == "FASHION.BIN":
                        continue
                    if entry.name == "FROG.BIN":
                        continue
                    if entry.name == "STICKER.BIN":
                        continue
                    if not entry.name.startswith('.') and entry.is_file():
                        process_file(entry, dest, output_formats, version, True)


def process_file(entry, folder_out, output_formats, version, is_car=False):
    if type(entry) is str:
        entry = Path(entry)
    basename = entry.name[0 : entry.name.find('.')]
    print(f"Processing {entry}")
    with open(entry, "rb") as f:
        out_folder = f"{folder_out}/CARS/{basename}"
        Path(out_folder).mkdir(parents=True, exist_ok=True)
        if CREATE_LOG_FILES:
            log_dest = f"{out_folder}/log.log"
        else:
            log_dest = os.devnull
        prev_std_out = sys.stdout
        with open(log_dest, "w") as sys.stdout:
            f.seek(0, os.SEEK_END)
            file_size = f.tell()
            f.seek(0, os.SEEK_SET)
            if version == 2:
                car = CarModel.read_car(f, 0, file_size)
            elif version == 3:
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
            texture.write_texture_to_png(f"{out_folder}/{basename}.png")
            # texture.writePaletteToPNG(f"{out_folder}/{basename}-{i}-p.png")
            texture_path = f"{basename}.png"

            mesh_section_names = ["body", "lights", "brake-light", "lp-body", "lp-lights", "spoiler", "spoiler2", "jets", "sticker"]
            # this varies by car currently (HG3) so it is not implemented
            mesh_section_names_hg3 = ["body", "brake-light", "lights", "lights2", "lp-body", "lp-lights", "lp-lights-2",
                                      "7", "spoiler", "9", "10", "11"]

            for i, mesh in enumerate(car.meshes):
                if should_exit:
                    break
                for outType in output_formats:
                    if should_exit:
                        break
                    extension = outType
                    if outType == "obj+colour":
                        extension = "obj"
                    if is_car and len(car.meshes) == 9:
                        mesh_path = f"{mesh_section_names[i]}.{extension}"
                    else:
                        mesh_path = f"{i}.{extension}"
                    with open(f"{out_folder}/{basename}-{mesh_path}", "w") as fout:
                        if outType == "comb":
                            mesh.write_mesh_to_type(outType, fout, material=texture_path)
                        else:
                            mesh.write_mesh_to_type(outType, fout, material=basename)
                    if outType == "obj" or outType == "obj+colour":
                        with open(f"{out_folder}/{basename}-{mesh_path}.mtl", "w") as fout:
                            Texture.save_material_file_obj(fout, basename, texture_path)
        sys.stdout = prev_std_out


def process_items(source, dest, output_formats):
    print("Processing items")

    item_folder = f"{source}/ITEM"
    if Path(item_folder).is_dir():
        with os.scandir(item_folder) as it:
            for entry in it:
                if should_exit:
                    break
                if not entry.name.startswith('.') and entry.is_file():
                    if type(entry) is str:
                        entry = Path(entry)
                    basename = entry.name[0 : entry.name.find('.')]
                    out_folder = f"{dest}/ITEM/{basename}"
                    Path(out_folder).mkdir(parents=True, exist_ok=True)
                    print(f"Processing {entry}")
                    with open(entry, "rb") as f:
                        if CREATE_LOG_FILES:
                            log_dest = f"{out_folder}/log.log"
                        else:
                            log_dest = os.devnull
                        prev_std_out = sys.stdout
                        with open(log_dest, "w") as sys.stdout:
                            textures = Texture.all_from_file(f, 0)
                            for i, (address, tex) in enumerate(textures):
                                if should_exit:
                                    break
                                if tex is None:
                                    continue
                                tex.write_texture_to_png(f"{out_folder}/{basename}-{address:x}.png")
                        sys.stdout = prev_std_out


def process_shops(source, dest, output_formats):
    print("Processing shops")

    item_folder = f"{source}/SHOP"
    # HG 3 does not have "SHOP" folder
    if Path(item_folder).is_dir():
        with os.scandir(item_folder) as it:
            for entry in it:
                if should_exit:
                    break
                if not entry.name.startswith('.') and entry.is_file():
                    if type(entry) is str:
                        entry = Path(entry)
                    basename = entry.name[0 : entry.name.find('.')]
                    out_folder = f"{dest}/SHOP/{basename}"
                    Path(out_folder).mkdir(parents=True, exist_ok=True)
                    print(f"Processing {entry} to {out_folder}")
                    with open(entry, "rb") as f:
                        if CREATE_LOG_FILES:
                            log_dest = f"{out_folder}/log.log"
                        else:
                            log_dest = os.devnull
                        prev_std_out = sys.stdout
                        with open(log_dest, "w") as sys.stdout:
                            if basename == "GARAGE":
                                # GARAGE is different
                                # garage = GarageModel.from_file(f, 0)
                                # for ei, g_entry in enumerate(garage.textures):
                                #     for i, mesh in enumerate(g_entry.meshes):
                                #         for outType in output_formats:
                                #             with open(f"{out_folder}/{basename}-{ei}-{i}.{outType}", "w") as fout:
                                #                 mesh.write_mesh_to_type(outType, fout)
                                #     for i, tex in enumerate(g_entry.textures):
                                #         try:
                                #             tex.write_texture_to_png(f"{out_folder}/{basename}-{ei}-{i}.png")
                                #         except Exception as E:
                                #             print(f"Failed to write texture/palette probably decoded badly Garage[{ei}]:{g_entry} Texture:{i} {tex} {E}")
                                pass
                                # TODO: need to rewrite now dma tags are understood better
                            else:
                                shops = Shop.from_file(f, 0)
                                print(f"Done shop {entry}")
                                for i, tex in enumerate(shops.textures):
                                    if should_exit:
                                        break
                                    if tex is None:
                                        continue
                                    # for i, tex in enumerate(shop):
                                    try:
                                        tex.write_texture_to_png(f"{out_folder}/{basename}-{i}.png")
                                    except Exception as E:
                                        print(f"Failed to write texture/palette probably decoded badly Shop[{entry}]: Texture:{i} {tex} {E}")
                                        raise E
                        sys.stdout = prev_std_out


def process_sys(source, dest, output_formats):
    print("Processing items")

    sys_folder = f"{source}/SYS"
    if Path(sys_folder).is_dir():
        with os.scandir(sys_folder) as it:
            for entry in it:
                if should_exit:
                    break
                if not entry.name.startswith('.') and entry.is_file():
                    if type(entry) is str:
                        entry = Path(entry)

                    basename = entry.name[0: entry.name.find('.')]
                    extension = entry.name[entry.name.find('.')+1:]
                    out_folder = f"{dest}/SYS/{entry.name}"
                    Path(out_folder).mkdir(parents=True, exist_ok=True)
                    print(f"Processing {entry}")
                    with open(entry, "rb") as f:
                        if CREATE_LOG_FILES:
                            log_dest = f"{out_folder}/log.log"
                        else:
                            log_dest = os.devnull
                        prev_std_out = sys.stdout
                        with open(log_dest, "w") as sys.stdout:
                            if extension == "GSL":
                                textures = Texture.all_from_file(f, 0)
                                for i in range(0, len(textures)):
                                    if should_exit:
                                        break
                                    address, texture = textures[i]
                                    if texture is None:
                                        continue
                                    print(f"{address}: {i} bpp: {texture.bpp} {texture.width}x{texture.height}")
                                    if texture.bpp <= 8:
                                        # Get next image as clut
                                        clut_address, clut = textures[i+1]
                                        # texture.write_texture_to_png(f"{out_folder}/{entry.name}-{address:x}-raw.png")
                                        if clut is None:
                                            texture.write_texture_to_png(f"{out_folder}/{entry.name}-{address:x}.png")
                                            continue
                                        print(f"Using clut to merge, bpp: {clut.bpp} {clut.width}x{clut.height}")
                                        print(f"{clut_address}: {i}")
                                        clut.write_texture_to_png(f"{out_folder}/{entry.name}-{clut_address:x}-raw.png")
                                        # Set the texture's palette accordingly
                                        unswizzled = Texture.unswizzle_bytes(clut)
                                        texture.palette = unswizzled
                                        texture.palette_width = clut.width
                                        texture.palette_height = clut.height

                                        texture.write_texture_to_png(f"{out_folder}/{entry.name}-{address:x}.png")
                            elif entry.name == "PUTI.BIN":
                                textures = []
                                total_length = 49152
                                img_length = 47216

                                for i in range(0, 100):
                                    if should_exit:
                                        break
                                    result = Texture.all_from_file(f, i * total_length)
                                    texture = result[0][1]
                                    clut = result[1][1]
                                    if texture is None:
                                        continue

                                    if texture.bpp <= 8:
                                        # Get next image as clut
                                        print(f"Using clut to merge, bpp: {clut.bpp} {clut.width}x{clut.height}")
                                        # texture.write_texture_to_png(f"{out_folder}/{entry.name}-{address:x}-raw.png")
                                        if clut is None:
                                            texture.write_texture_to_png(f"{out_folder}/{entry.name}-{i}.png")
                                            continue
                                        clut.write_texture_to_png(f"{out_folder}/{entry.name}-{i}-p.png")
                                        # Set the texture's palette accordingly
                                        unswizzled = Texture.unswizzle_bytes(clut)
                                        texture.palette = unswizzled
                                        texture.palette_width = clut.width
                                        texture.palette_height = clut.height

                                        texture.write_texture_to_png(f"{out_folder}/{entry.name}-{i}.png")
                            elif extension == "E3D" and basename != "TAKARA" and basename != "ENKEI":
                                meshes = Course.read_course_meshes(f, 0)
                                textures = {}
                                with open(f"{entry.path[0: entry.path.find('.E3D')]}.GSL", "rb") as ftextures:
                                    textures_read = Texture.all_from_file(ftextures, 0)
                                    # Convert to dict
                                    for (address, texture) in textures_read:
                                        textures[address] = texture

                                # Need to group the meshes by the "data/material" info
                                mesh_by_material, number_of_meshes = group_meshes_by_material(meshes)
                                for out_type in output_formats:
                                    if should_exit:
                                        break
                                    save_course_type_grouped(mesh_by_material, number_of_meshes, out_folder,
                                                             basename, out_type, "", textures)
                            elif extension == "BIN":
                                process_file(entry, out_folder, output_formats, 2)

                        sys.stdout = prev_std_out


if __name__ == '__main__':
    colorama.init()
    if len(sys.argv) >= 3:
        folder_in = sys.argv[1]
        folder_out = sys.argv[2]
    else:
        show_help()
        print(Fore.RED +"ERROR: " + Style.RESET_ALL + "Not enough args")
        exit(1)
    
    obj = False
    ply = False
    obj_colours = False
    if len(sys.argv) == 4:
        obj_colours = True if sys.argv[3] == "c" or sys.argv[3] == "C" else False
        obj = True if sys.argv[3] == "1" else False
        ply = True if sys.argv[3] == "2" else False
    elif len(sys.argv) > 4:
        show_help()
        print(Fore.RED + "ERROR: " + Style.RESET_ALL + "Too many args")
        exit(1)

    # Default to obj
    if not obj and not ply and not obj_colours:
        obj = True

    os.makedirs(folder_out, exist_ok=True)
    if not os.path.isdir(folder_out):
        print(Fore.RED + "ERROR: " + Style.RESET_ALL + "Failed to create or use output folder")
        exit(1)

    if os.path.isfile(folder_in):
        print(Fore.RED + "ERROR: " + Style.RESET_ALL + "This tool is for extracting \"all\" game data, not just a single file, see help")
        exit(1)

    output_formats = []
    if obj:
        output_formats.append("obj")
    if obj_colours:
        output_formats.append("obj+colour")
    if ply:
        output_formats.append("ply")
        print("Warning, PLY files are broken, they can be manually fixed, but for now please use OBJ/OBJ+Colours")

    if len(sys.argv) == 4 and sys.argv[3] == "M":
        obj = False
        ply = False
        obj_colours = False
        output_formats = ["comb"]

    if os.path.isdir(folder_in):
        process_courses(folder_in, folder_out, "COURSE", output_formats)
        process_cars(folder_in, folder_out, output_formats)
        process_courses(folder_in, folder_out, "ACTION", output_formats)
        process_fields(folder_in, folder_out, output_formats)
        # These are other bits from the game, might be useful for some
        # process_items(folder_in, folder_out, output_formats)
        # process_shops(folder_in, folder_out, output_formats)
        # process_sys(folder_in, folder_out, output_formats)

    else:
        print(Fore.RED + "ERROR: " + Style.RESET_ALL + "Failed to read source folder")
        exit(1)
    
