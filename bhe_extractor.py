from choroq.bhe.aptexture import APTexture
from choroq.bhe.pbl_model import PBLModel
from choroq.bhe.bhe_cpk import CPK

import sys
import os
import csv


# Create log files or not (probably not that useful for most people)
CREATE_LOG_FILES = True

def show_help():
    print("##############################################################################################")
    print("Choro Q Barnhouse Effect CPK extractor by Matthew Holey")
    print("##############################################################################################")
    print("")
    print("Extracts BHE Choro Q games CPK models and textures")
    print("Tested with HG 1 (Penny Racers), HG 4, Shin combat and Choro Q Works")
    print("Textures are exported in PNG format")
    print("Models will be exported as OBJ by default")
    print("")
    print("Currently this will only work when given the path to a single CPK file")
    print("Textures and objs are not linked, this is manual currently")
    print("")
    print("Options: <REQUIRED> [OPTIONAL]")
    print("<source path>")
    print("<output folder>")
    # print("[type]                    : model output format")
    # print("                            -- 1 = OBJ only")
    # print("                            -- 2 = PLY only")

    print("The output folder structure will be as follows:")
    print("<output dir>/")

    print(" WARNING: This may produce a large number of files, and will some time")


def process_cpk(path, out_path, output_formats):
    with open(path, "rb") as f:
        cpk = CPK.read_cpk(f, 0)
        cpk.read_subfiles(f)

        names_seen_pbl = []
        names_seen_apt = []
        deduplcate_id_pbl = 0
        toc_index = 0

        # if b'\x03\x18\x00\x00' in cpk.subfile_types:
        #     total_file = open(f"{out_path}\\toc-text.csv", "w", encoding="utf_8", newline='')
        #     total_writer = csv.writer(total_file, delimiter=',')
        #     total_writer.writerow(("Type", "Name", "Position (Dec)", "Flag (Dec)", "Length read", "Text Length", "Bytes eqiv", "Text"))

        for index in cpk.subfiles:
            sf_type, sf = cpk.subfiles[index]
            if sf is None:
                pass
            if sf_type == "PBL":  # Model format
                # continue
                out_index = 0
                for pbl in sf:
                    name = pbl.name
                    if name in names_seen_pbl:
                        name = f"{pbl.name}-{deduplcate_id_pbl}"
                        deduplcate_id_pbl += 1
                    for format in output_formats:
                        out = f"{out_path}\\{name}-{out_index}.{format}"
                        with open(out, "w") as fout:
                            pbl.write_mesh_to_type(format, fout)
                    out_index += 1
            elif sf_type == "APT":  # Texture format
                # continue
                for t in sf:
                    name = t.name
                    print(t.name)
                    deduplcate_id_apt = 0
                    while name in names_seen_apt and deduplcate_id_apt < 32:
                        name = f"{t.name}-{deduplcate_id_apt}"
                        deduplcate_id_apt += 1
                    names_seen_apt.append(name)
                    print(f"Read texture {t.name}")
                    t.write_texture_to_png(f"{out_path}\\{name}.png")
                    t.write_palette_to_png(f"{out_path}\\{name}-p.png")
        #     elif sf_type == b'\x03\x18\x00\x00':  # Toc format
        #         # Output all data types
        #         # with open(f"{out_path}\\toc-data-{toc_index}.csv", "w", encoding="utf_8", newline='') as csv_file:
        #         #     writer = csv.writer(csv_file, delimiter=',')
        #         #     for toc in sf:
        #         #         with open(f"{out_path}\\toc-data-{toc.name}.csv", "a", encoding="utf_8", newline='') as single_csv_file:
        #         #             single_writer = csv.writer(single_csv_file, delimiter=',')
        #         #             row = toc.type, toc.position, toc.flag, toc.length_read, toc.data
        #         #             writer.writerow(row)
        #         #             single_writer.writerow(row)
        #
        #         # Output text based data
        #
        #         if len(sf) > 0:
        #             with open(f"{out_path}\\toc-[{toc_index}]-text.csv", "w", encoding="utf_8", newline='') as csv_file:
        #                 toc_index += 1
        #                 writer = csv.writer(csv_file, delimiter=',')
        #                 current_name = ""
        #                 for toc in sf:
        #                     if toc.type != "text":
        #                         continue
        #                     row = toc.type, toc.name, toc.position, toc.flag, toc.length_read, toc.text_length, toc.data[1], toc.data[0]
        #                     writer.writerow(row)
        #                     total_writer.writerow(row)
        #                     # with open(f"{out_path}\\toc-text-{toc.name}.csv", "a", encoding="utf_8", newline='') as single_csv_file:
        #                     #     single_writer = csv.writer(single_csv_file, delimiter=',')
        #                     # single_writer.writerow(row)
        #         toc_index += 1
        # total_file.close()


if __name__ == '__main__':
    if len(sys.argv) >= 3:
        cpk_file_in = sys.argv[1]
        folder_out = sys.argv[2]
    else:
        show_help()
        print("ERROR: Not enough args")
        exit(1)

    obj = False
    ply = False
    if len(sys.argv) == 4:
        obj = True if sys.argv[3] == "1" else False
        ply = True if sys.argv[3] == "2" else False
    elif len(sys.argv) > 4:
        show_help()
        print("ERROR: Too many args")
        exit(1)

    # Default to obj
    if not obj and not ply:
        obj = True

    os.makedirs(folder_out, exist_ok=True)
    if not os.path.isdir(folder_out):
        print("ERROR: Failed to create or use output folder")
        exit(1)

    if os.path.isdir(cpk_file_in):
        print("ERROR: This tool is currently for extracting one cpk file, not a whole folder, see help")
        exit(1)

    output_formats = []
    if obj:
        output_formats.append("obj")
    if ply:
        output_formats.append("ply")
        print("Warning, PLY files are broken, they can be manually fixed, but for now please use OBJ/OBJ+Colours")

    if os.path.isfile(cpk_file_in):
        print(f"Reading from {cpk_file_in}")
        process_cpk(cpk_file_in, folder_out, output_formats)
