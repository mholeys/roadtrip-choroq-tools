from choroq.bhe.aptexture import APTexture
from choroq.bhe.pbl_model import PBLModel
from choroq.bhe.bhe_cpk import CPK

import sys
import os
import csv
from pathlib import Path

# import cProfile

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
    print("[type]                    : model output format")
    print("                            -- 1 = OBJ only")
    print("                            -- C = OBJ with vertex colours, r/g/b after x/y/z (blender)")
    # print("                            -- 2 = PLY only")

    print("The output folder structure will be as follows:")
    print("<output dir>/")

    print(" WARNING: This may produce a large number of files, and will some time")


def cpk_decode(path, out_path, output_formats, save_all_textures=True):
    with open(path, "rb") as f:
        cpk = CPK.read_cpk(f, 0)
        cpk.read_subfiles(f)

        print("Read all data, now saving......")

        current_texture_group = {}
        index_counts = { "PBL": 0, "MPD": 0, "APT": 0, "TOC": 0, "HPD": 0, "MPC": 0 }

        if save_all_textures:
            Path(f"{out_path}/all_textures/").mkdir(parents=True, exist_ok=True)

        # Check for any TOC entries,
        # to save to a file holding all text for this file (easier to search)
        if b'\x03\x18\x00\x00' in cpk.subfile_types or b'TOC\x00' in cpk.subfile_types:
            # Check folder exist/make them
            Path(f"{out_path}/text/").mkdir(parents=True, exist_ok=True)
            Path(f"{out_path}/other/").mkdir(parents=True, exist_ok=True)
            total_file = open(f"{out_path}/toc-text.csv", "w", encoding="utf_8", newline='')
            total_writer = csv.writer(total_file, delimiter=',')
            total_writer.writerow(
                ("Type", "Name", "Position (Dec)", "Flag (Dec)", "Length read", "Text Length", "Bytes eqiv", "Text"))

        # Work through all sub files, in order
        for index in cpk.subfiles:
            sf_type, sf = cpk.subfiles[index]
            if sf is None:
                pass

            # Update texture group with textures, only saving as required
            if sf_type == "APT":  # Texture format
                for ti, t in enumerate(sf):
                    name = t.name
                    current_texture_group[name] = t
                    if save_all_textures:
                        t.write_texture_to_png(f"{out_path}/all_textures/{name}-{index}-{t.offset}.png")
                        # t.write_palette_to_png(f"{out_path}/all_textures/{name}-p.png")
                        # t.write_texture_to_png(f"{out_path}/all_textures/{name}-i.png", use_palette=False)
                        # t.write_palette_to_ms_PAL(f"{out_path}/all_textures/{name}-p.pal")

            # Exports all model's and all referenced textures (if found)
            elif sf_type == "PBL":  # Model format
                # continue
                out_index = 0
                name = f"pbl-{index_counts['PBL']}"

                index_counts['PBL'] += 1
                for pbl in sf:
                    # If the object only uses one texture, then why not name it as it might help
                    if len(pbl.texture_references) == 1:
                        name = f"pbl-{index_counts['PBL']}-{pbl.texture_references[0][0]}"

                    # Create subfolder for each sub pbl
                    Path(f"{out_path}/pbl/{name}").mkdir(parents=True, exist_ok=True)
                    Path(f"{out_path}/pbl/{name}/tex").mkdir(parents=True, exist_ok=True)

                    # Write all required textures
                    for texture_reference in pbl.texture_references:
                        texture_name, (t_width, t_height, t_format, t_unknown) = texture_reference
                        if texture_name not in current_texture_group:
                            print(f"Missing texture in current APT list (Ignore if BODY.CPK), please let developer know, CPK file name and [sf-{index}, PBL, {texture_name}]")
                            continue
                        t = current_texture_group[texture_name]
                        t.write_texture_to_png(f"{out_path}/pbl/{name}/tex/{texture_name}.png")
                        # t.write_palette_to_png(f"{out_path}/pbl/{name}/tex/{texture_name}-p.png")

                    for out_format in output_formats:
                        extension = out_format
                        if out_format == "obj+colour":
                            extension = "obj"
                        out = f"{out_path}/pbl/{name}/{name}-{out_index}.{extension}"
                        with open(out, "w") as fout:
                            pbl.write_mesh_to_type(out_format, fout)
                    material_path = f"{out_path}/pbl/{name}/{name}-{out_index}.mtl"
                    texture_path = f"tex"
                    with open(material_path, "w") as fout:
                        pbl.save_material_file_obj(fout, texture_path)
                    out_index += 1
            elif sf_type == "MPD":  # Model format
                out_index = 0
                name = f"mpd-{index_counts['MPD']}"
                index_counts['MPD'] += 1
                for mpd in sf:
                    # Create subfolder for each sub mpd
                    Path(f"{out_path}/mpd/{name}").mkdir(parents=True, exist_ok=True)
                    Path(f"{out_path}/mpd/{name}/tex").mkdir(parents=True, exist_ok=True)

                    # Write all required textures
                    for texture_reference in mpd.texture_references:
                        texture_name, (t_width, t_height, t_format, t_unknown) = texture_reference
                        if texture_name not in current_texture_group:
                            print(f"Missing texture in current APT list, please let developer know, CPK file name and [{texture_name}]")
                            continue
                        t = current_texture_group[texture_name]
                        t.write_texture_to_png(f"{out_path}/mpd/{name}/tex/{texture_name}.png")
                        # t.write_palette_to_png(f"{out_path}/pbl/{name}/tex/{texture_name}-p.png")
                        # t.write_palette_to_png(f"{out_path}/pbl/{name}/tex/{texture_name}-i.png")

                    for out_format in output_formats:
                        extension = out_format
                        if out_format == "obj+colour":
                            extension = "obj"
                        out = f"{out_path}/mpd/{name}/{name}-{out_index}.{extension}"
                        with open(out, "w") as fout:
                            mpd.write_mesh_to_type(out_format, fout)
                    material_path = f"{out_path}/mpd/{name}/{name}-{out_index}.mtl"
                    texture_path = f"tex"
                    with open(material_path, "w") as fout:
                        mpd.save_material_file_obj(fout, texture_path)
                    out_index += 1
            elif sf_type == "HPD":  # Model format?
                out_index = 0
                name = f"hpd-{index_counts['HPD']}"
                index_counts['HPD'] += 1
                hpd = sf
                # Create subfolder for each sub hpd
                Path(f"{out_path}/hpd/{name}").mkdir(parents=True, exist_ok=True)
                Path(f"{out_path}/hpd/{name}/tex").mkdir(parents=True, exist_ok=True)

                # # Write all required textures
                # for texture_name in mpd.texture_references:
                #     if texture_name not in current_texture_group:
                #         print(f"Missing texture in current APT list, please let developer know, CPK file name and [{texture_name}]")
                #         continue
                #     t = current_texture_group[texture_name]
                #     t.write_texture_to_png(f"{out_path}/mpd/{name}/tex/{texture_name}.png")
                #     # t.write_palette_to_png(f"{out_path}/pbl/{name}/tex/{texture_name}-p.png")

                for out_format in output_formats:
                    extension = out_format
                    if out_format == "obj+colour":
                        extension = "obj"
                    out = f"{out_path}/hpd/{name}/{name}-{out_index}.{extension}"
                    with open(out, "w") as fout:
                        hpd.write_mesh_to_type(out_format, fout)
                # material_path = f"{out_path}/hpd/{name}/{name}-{out_index}.mtl"
                # texture_path = f"tex"
                # with open(material_path, "w") as fout:
                #     mpd.save_material_file_obj(fout, texture_path)
            # TOC, only text data is understood
            elif sf_type == b'TOC\x00':  # Toc format
                # Check folder exist/make them
                Path(f"{out_path}/text/").mkdir(parents=True, exist_ok=True)
                Path(f"{out_path}/other/").mkdir(parents=True, exist_ok=True)
                # Group all data by their toc name, slower but makes nicer files
                text_toc_by_name = {}
                other_toc_by_name = {}
                toc_by_name = {}
                for toc in sf:
                    if toc is None:
                        continue
                    if type(toc) == list:
                        break
                    if toc.name not in toc_by_name:
                        toc_by_name[toc.name] = []
                    toc_by_name[toc.name].append(toc)
                    if toc.type == "text":
                        if toc.name not in text_toc_by_name:
                            text_toc_by_name[toc.name] = []
                        text_toc_by_name[toc.name].append(toc)
                    else:
                        if toc.name not in other_toc_by_name:
                            other_toc_by_name[toc.name] = []
                        other_toc_by_name[toc.name].append(toc)

                for toc_name in text_toc_by_name:
                    with open(f"{out_path}/text/toc-{toc_name}-text.csv", "w", encoding="utf_8", newline='') as csv_file:
                        writer = csv.writer(csv_file, delimiter=',')
                        writer.writerow(("Type", "Name", "Position (Dec)", "Flag (Dec)", "Length read", "Text Length", "Bytes eqiv", "Text"))
                        for toc in text_toc_by_name[toc_name]:
                            if toc.type != "text":
                                continue
                            row = toc.type, toc.name, toc.position, toc.flag, toc.length_read, toc.text_length, toc.data[1], toc.data[0]
                            writer.writerow(row)
                            total_writer.writerow(row)

                for toc_name in other_toc_by_name:
                    with open(f"{out_path}/other/toc-{toc_name}-other.csv", "w", encoding="utf_8", newline='') as csv_file:
                        writer = csv.writer(csv_file, delimiter=',')
                        writer.writerow(("Type", "Name", "Position (Dec)", "Flag (Dec)", "Length read", "Bytes eqiv"))
                        for toc in other_toc_by_name[toc_name]:
                            if toc.type != "text":
                                continue
                            row = toc.type, toc.name, toc.position, toc.flag, toc.length_read, toc.text_length, toc.data
                            writer.writerow(row)
                            total_writer.writerow(row)
            elif sf_type == "FONT":  # Font data
                sf.save_font_data(f"{out_path}/font{index}/", str(index))
            elif sf_type == "MPC":  # Model format
                # Exports all model's and all referenced textures (if found)
                # continue
                out_index = 0
                name = f"mpc-{index_counts['MPC']}"
                mpc_index = index_counts['MPC']
                Path(f"{out_path}/mpc/{mpc_index}/tex").mkdir(parents=True, exist_ok=True)
                index_counts['MPC'] += 1
                for mpc in sf:
                    # If the object only uses one texture, then why not name it as it might help
                    name = mpc.name

                    # Create subfolder for each sub mpc
                    Path(f"{out_path}/mpc/{mpc_index}/{name}").mkdir(parents=True, exist_ok=True)

                    mpc_textures_done = {}

                    # Write all required textures
                    for texture_reference in mpc.texture_references:
                        texture_name, (t_width, t_height, t_format, t_unknown) = texture_reference
                        if texture_name not in current_texture_group:
                            print(
                                f"Missing texture in current APT list (Ignore if BODY.CPK), please let developer know, CPK file name and [sf-{index}, MPC, {texture_name}]")
                            continue
                        t = current_texture_group[texture_name]
                        if texture_name in mpc_textures_done:
                            if t != mpc_textures_done[texture_name]:
                                print(f"Found texture that is different between uses for this MPC {mpc} {texture_name} {t} vs {mpc_textures_done[texture_name]}")
                        else:
                            mpc_textures_done[texture_name] = t
                            t.write_texture_to_png(f"{out_path}/mpc/{mpc_index}/tex/{texture_name}.png")
                            # t.write_palette_to_png(f"{out_path}/mpc/{mpc_index}/{name}/tex/{texture_name}-p.png")

                    for out_format in output_formats:
                        extension = out_format
                        if out_format == "obj+colour":
                            extension = "obj"
                        out = f"{out_path}/mpc/{mpc_index}/{name}/{name}-{out_index}.{extension}"
                        with open(out, "w") as fout:
                            mpc.write_mesh_to_type(out_format, fout)
                    material_path = f"{out_path}/mpc/{mpc_index}/{name}/{name}-{out_index}.mtl"
                    texture_path = f"../tex"
                    with open(material_path, "w") as fout:
                        mpc.save_material_file_obj(fout, texture_path)
                    out_index += 1

        if b'\x03\x18\x00\x00' in cpk.subfile_types or b'TOC\x00' in cpk.subfile_types:
            total_file.close()


# def process_cpk(path, out_path, output_formats):
#     with open(path, "rb") as f:
#         cpk = CPK.read_cpk(f, 0)
#         cpk.read_subfiles(f)
#
#         names_seen_pbl = []
#         names_seen_apt = []
#         deduplicate_id_pbl = 0
#         toc_index = 0
#
#         # file holding all text for this file (easier to search)
#         if b'\x03\x18\x00\x00' in cpk.subfile_types or b'TOC\x00' in cpk.subfile_types:
#             # Check folder exist/make them
#             Path(f"{out_path}/text/tex/").mkdir(parents=True, exist_ok=True)
#             Path(f"{out_path}/other/tex/").mkdir(parents=True, exist_ok=True)
#             total_file = open(f"{out_path}/toc-text.csv", "w", encoding="utf_8", newline='')
#             total_writer = csv.writer(total_file, delimiter=',')
#             total_writer.writerow(("Type", "Name", "Position (Dec)", "Flag (Dec)", "Length read", "Text Length", "Bytes eqiv", "Text"))
#         else:
#             print("No TOC, skipping total file")
#
#         for index in cpk.subfiles:
#             sf_type, sf = cpk.subfiles[index]
#             if sf is None:
#                 pass
#             if sf_type == "PBL":  # Model format
#                 # continue
#                 out_index = 0
#                 for pbl in sf:
#                     name = pbl.name
#                     if name in names_seen_pbl:
#                         name = f"{pbl.name}-{deduplicate_id_pbl}"
#                         deduplicate_id_pbl += 1
#                     for out_format in output_formats:
#                         out = f"{out_path}/{name}-{out_index}.{out_format}"
#                         with open(out, "w") as fout:
#                             pbl.write_mesh_to_type(out_format, fout)
#                     # material_path = f"{out_path}/{name}-{out_index}.{out_format}"
#                     # with open(material_path, "w") as fout:
#                     #     pbl.save_material_file_obj(fout, )
#                     out_index += 1
#             elif sf_type == "APT":  # Texture format
#                 # continue
#                 for t in sf:
#                     name = t.name
#                     print(t.name)
#                     deduplicate_id_apt = 0
#                     while name in names_seen_apt and deduplicate_id_apt < 32:
#                         name = f"{t.name}-{deduplicate_id_apt}"
#                         deduplicate_id_apt += 1
#                     names_seen_apt.append(name)
#                     print(f"Read texture {t.name}")
#                     t.write_texture_to_png(f"{out_path}/{name}.png")
#                     # t.write_palette_to_png(f"{out_path}/{name}-p.png")
#             elif sf_type == b'TOC\x00':  # Toc format
#                 # Check folder exist/make them
#                 Path(f"{out_path}/text/").mkdir(parents=True, exist_ok=True)
#                 Path(f"{out_path}/other/").mkdir(parents=True, exist_ok=True)
#                 # Group all data by their toc name, slower but makes nicer files
#                 text_toc_by_name = {}
#                 other_toc_by_name = {}
#                 toc_by_name = {}
#                 for toc in sf:
#                     if toc is None:
#                         continue
#                     if type(toc) == list:
#                         break
#                     if toc.name not in toc_by_name:
#                         toc_by_name[toc.name] = []
#                     toc_by_name[toc.name].append(toc)
#                     if toc.type == "text":
#                         if toc.name not in text_toc_by_name:
#                             text_toc_by_name[toc.name] = []
#                         text_toc_by_name[toc.name].append(toc)
#                     else:
#                         if toc.name not in other_toc_by_name:
#                             other_toc_by_name[toc.name] = []
#                         other_toc_by_name[toc.name].append(toc)
#
#                 for toc_name in text_toc_by_name:
#                     with open(f"{out_path}/text/toc-{toc_name}-text.csv", "w", encoding="utf_8", newline='') as csv_file:
#                         writer = csv.writer(csv_file, delimiter=',')
#                         writer.writerow(("Type", "Name", "Position (Dec)", "Flag (Dec)", "Length read", "Text Length", "Bytes eqiv", "Text"))
#                         for toc in text_toc_by_name[toc_name]:
#                             if toc.type != "text":
#                                 continue
#                             row = toc.type, toc.name, toc.position, toc.flag, toc.length_read, toc.text_length, toc.data[1], toc.data[0]
#                             writer.writerow(row)
#                             total_writer.writerow(row)
#
#                 for toc_name in other_toc_by_name:
#                     with open(f"{out_path}/other/toc-{toc_name}-other.csv", "w", encoding="utf_8", newline='') as csv_file:
#                         writer = csv.writer(csv_file, delimiter=',')
#                         writer.writerow(("Type", "Name", "Position (Dec)", "Flag (Dec)", "Length read", "Bytes eqiv"))
#                         for toc in other_toc_by_name[toc_name]:
#                             if toc.type != "text":
#                                 continue
#                             row = toc.type, toc.name, toc.position, toc.flag, toc.length_read, toc.text_length, toc.data
#                             writer.writerow(row)
#                             total_writer.writerow(row)
#             elif sf_type == "FONT":  # Font data
#                 sf.save_font_data(f"{out_path}/font{index}/", str(index))
#
#
#                 # Output all data types
#                 # with open(f"{out_path}/toc-data-{toc_index}.csv", "w", encoding="utf_8", newline='') as csv_file:
#                 #     writer = csv.writer(csv_file, delimiter=',')
#                 #     for toc in sf:
#                 #         with open(f"{out_path}/toc-data-{toc.name}.csv", "a", encoding="utf_8", newline='') as single_csv_file:
#                 #             single_writer = csv.writer(single_csv_file, delimiter=',')
#                 #             row = toc.type, toc.position, toc.flag, toc.length_read, toc.data
#                 #             writer.writerow(row)
#                 #             single_writer.writerow(row)
#
#
#
#
#                 # if len(sf) > 0:
#                 #     with open(f"{out_path}/toc-[{toc_index}]-text.csv", "w", encoding="utf_8", newline='') as csv_file:
#                 #         toc_index += 1
#                 #         writer = csv.writer(csv_file, delimiter=',')
#                 #         current_name = ""
#                 #         for toc in sf:
#                 #             if toc.type != "text":
#                 #                 continue
#                 #             row = toc.type, toc.name, toc.position, toc.flag, toc.length_read, toc.text_length, toc.data[1], toc.data[0]
#                 #             writer.writerow(row)
#                 #             total_writer.writerow(row)
#                 #             # with open(f"{out_path}/toc-text-{toc.name}.csv", "a", encoding="utf_8", newline='') as single_csv_file:
#                 #             #     single_writer = csv.writer(single_csv_file, delimiter=',')
#                 #             # single_writer.writerow(row)
#                 # toc_index += 1
#         if b'\x03\x18\x00\x00' in cpk.subfile_types or b'TOC\x00' in cpk.subfile_types:
#             total_file.close()

# def process_cpk_once(path, out_path, output_formats):
#     with open(path, "rb") as f:
#         cpk = CPK.read_cpk(f, 0)
#
#         names_seen_pbl = []
#         names_seen_mpd = []
#         names_seen_apt = []
#         deduplicate_id_pbl = 0
#         deduplicate_id_mpd = 0
#         toc_index = 0
#
#         # file holding all text for this file (easier to search)
#         if b'\x03\x18\x00\x00' in cpk.subfile_types or b'TOC\x00' in cpk.subfile_types:
#             # Check folder exist/make them
#             Path(f"{out_path}/text/tex/").mkdir(parents=True, exist_ok=True)
#             Path(f"{out_path}/other/tex/").mkdir(parents=True, exist_ok=True)
#             total_file = open(f"{out_path}/toc-text.csv", "w", encoding="utf_8", newline='')
#             total_writer = csv.writer(total_file, delimiter=',')
#             total_writer.writerow(("Type", "Name", "Position (Dec)", "Flag (Dec)", "Length read", "Text Length", "Bytes eqiv", "Text"))
#         else:
#             print("No TOC, skipping total file")
#
#         for index in range(cpk.entry_count):
#             if index >= len(cpk.entry_positions):
#                 continue
#             cpk.read_subfile(f, index)
#             if index not in cpk.subfiles:
#                 print(f"Missed index [{index}] type: [{cpk.subfile_types[index]}]")
#                 continue
#             sf_type, sf = cpk.subfiles[index]
#             if sf is None:
#                 pass
#             if sf_type == "PBL":  # Model format
#                 # continue
#                 Path(f"{out_path}/pbl/").mkdir(parents=True, exist_ok=True)
#                 out_index = 0
#                 for pbl in sf:
#                     for out_format in output_formats:
#                         out = f"{out_path}/pbl/pbl-{index}.{out_format}"
#                         with open(out, "w") as fout:
#                             pbl.write_mesh_to_type(out_format, fout)
#                     material_path = f"{out_path}/pbl/pbl-{index}.mtl"
#                     texture_path = f"../tex"
#                     with open(material_path, "w") as fout:
#                         mpd.save_material_file_obj(fout, texture_path)
#                     out_index += 1
#             elif sf_type == "MPD":  # Model format
#                 # continue
#                 Path(f"{out_path}/mpd/").mkdir(parents=True, exist_ok=True)
#                 out_index = 0
#                 for mpd in sf:
#                     # name = mpd.name
#                     # if name in names_seen_mpd:
#                     #     name = f"{mpd.name}-{deduplicate_id_mpd}"
#                     #     deduplicate_id_mpd += 1
#                     for out_format in output_formats:
#                         out = f"{out_path}/mpd/mpd-{index}.{out_format}"
#                         with open(out, "w") as fout:
#                             mpd.write_mesh_to_type(out_format, fout)
#                     material_path = f"{out_path}/mpd/mpd-{index}.mtl"
#                     texture_path = f"../tex"
#                     with open(material_path, "w") as fout:
#                         mpd.save_material_file_obj(fout, texture_path)
#                     out_index += 1
#             elif sf_type == "APT":  # Texture format
#                 # continue
#                 Path(f"{out_path}/tex").mkdir(parents=True, exist_ok=True)
#                 for t in sf:
#                     name = t.name
#                     print(t.name)
#                     deduplicate_id_apt = 0
#                     while name in names_seen_apt and deduplicate_id_apt < 32:
#                         name = f"{t.name}-{deduplicate_id_apt}"
#                         deduplicate_id_apt += 1
#                     names_seen_apt.append(name)
#                     print(f"Save texture {t.name}")
#                     t.write_texture_to_png(f"{out_path}/tex/{name}.png")
#                     t.write_palette_to_png(f"{out_path}/tex/{name}-p.png")
#             elif sf_type == b'TOC\x00':  # Toc format
#                 # Check folder exist/make them
#                 Path(f"{out_path}/text/").mkdir(parents=True, exist_ok=True)
#                 Path(f"{out_path}/other/").mkdir(parents=True, exist_ok=True)
#                 # Group all data by their toc name, slower but makes nicer files
#                 text_toc_by_name = {}
#                 other_toc_by_name = {}
#                 toc_by_name = {}
#                 for toc in sf:
#                     if toc is None:
#                         continue
#                     if type(toc) == list:
#                         break
#                     if toc.name not in toc_by_name:
#                         toc_by_name[toc.name] = []
#                     toc_by_name[toc.name].append(toc)
#                     if toc.type == "text":
#                         if toc.name not in text_toc_by_name:
#                             text_toc_by_name[toc.name] = []
#                         text_toc_by_name[toc.name].append(toc)
#                     else:
#                         if toc.name not in other_toc_by_name:
#                             other_toc_by_name[toc.name] = []
#                         other_toc_by_name[toc.name].append(toc)
#
#                 for toc_name in text_toc_by_name:
#                     with open(f"{out_path}/text/toc-{toc_name}-text.csv", "w", encoding="utf_8", newline='') as csv_file:
#                         writer = csv.writer(csv_file, delimiter=',')
#                         writer.writerow(("Type", "Name", "Position (Dec)", "Flag (Dec)", "Length read", "Text Length", "Bytes eqiv", "Text"))
#                         for toc in text_toc_by_name[toc_name]:
#                             if toc.type != "text":
#                                 continue
#                             row = toc.type, toc.name, toc.position, toc.flag, toc.length_read, toc.text_length, toc.data[1], toc.data[0]
#                             writer.writerow(row)
#                             total_writer.writerow(row)
#
#                 for toc_name in other_toc_by_name:
#                     with open(f"{out_path}/other/toc-{toc_name}-other.csv", "w", encoding="utf_8", newline='') as csv_file:
#                         writer = csv.writer(csv_file, delimiter=',')
#                         writer.writerow(("Type", "Name", "Position (Dec)", "Flag (Dec)", "Length read", "Bytes eqiv"))
#                         for toc in other_toc_by_name[toc_name]:
#                             if toc.type != "text":
#                                 continue
#                             row = toc.type, toc.name, toc.position, toc.flag, toc.length_read, toc.text_length, toc.data
#                             writer.writerow(row)
#                             total_writer.writerow(row)
#
#             elif sf_type == "FONT":  # Font data
#                 sf.save_font_data(f"{out_path}/font{index}/", str(index))
#
#                 # Output all data types
#                 # with open(f"{out_path}/toc-data-{toc_index}.csv", "w", encoding="utf_8", newline='') as csv_file:
#                 #     writer = csv.writer(csv_file, delimiter=',')
#                 #     for toc in sf:
#                 #         with open(f"{out_path}/toc-data-{toc.name}.csv", "a", encoding="utf_8", newline='') as single_csv_file:
#                 #             single_writer = csv.writer(single_csv_file, delimiter=',')
#                 #             row = toc.type, toc.position, toc.flag, toc.length_read, toc.data
#                 #             writer.writerow(row)
#                 #             single_writer.writerow(row)
#
#
#
#
#                 # if len(sf) > 0:
#                 #     with open(f"{out_path}/toc-[{toc_index}]-text.csv", "w", encoding="utf_8", newline='') as csv_file:
#                 #         toc_index += 1
#                 #         writer = csv.writer(csv_file, delimiter=',')
#                 #         current_name = ""
#                 #         for toc in sf:
#                 #             if toc.type != "text":
#                 #                 continue
#                 #             row = toc.type, toc.name, toc.position, toc.flag, toc.length_read, toc.text_length, toc.data[1], toc.data[0]
#                 #             writer.writerow(row)
#                 #             total_writer.writerow(row)
#                 #             # with open(f"{out_path}/toc-text-{toc.name}.csv", "a", encoding="utf_8", newline='') as single_csv_file:
#                 #             #     single_writer = csv.writer(single_csv_file, delimiter=',')
#                 #             # single_writer.writerow(row)
#                 # toc_index += 1
#         if b'\x03\x18\x00\x00' in cpk.subfile_types or b'TOC\x00' in cpk.subfile_types:
#             total_file.close()



if __name__ == '__main__':
    if len(sys.argv) >= 3:
        cpk_file_in = sys.argv[1]
        folder_out = sys.argv[2]
    else:
        show_help()
        print("ERROR: Not enough args")
        exit(1)

    obj = False
    obj_colour = False
    ply = False
    if len(sys.argv) == 4:
        obj = True if sys.argv[3] == "1" else False
        obj_colour = True if sys.argv[3] == "C" or sys.argv[3] == "c" else False
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
    if obj_colour:
        output_formats.append("obj+colour")
    if ply:
        output_formats.append("ply")
        print("Warning, PLY files are broken, they can be manually fixed, but for now please use OBJ/OBJ+Colours")

    if os.path.isfile(cpk_file_in):
        print(f"Reading from {cpk_file_in}")
        # cProfile.runctx('cpk_decode(a, b, c)', {'a': cpk_file_in, 'b': folder_out, 'c': output_formats, 'cpk_decode': cpk_decode}, {})
        cpk_decode(cpk_file_in, folder_out, output_formats)
