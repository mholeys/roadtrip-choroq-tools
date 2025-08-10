
# Class for holding course/racetrack model data, and extracting it from a Cxx.BIN file

# Course file Cxx.bin info:
#   Contains 4 sub files
#     - Textures
#     - Models
#     - Collision mesh (allowed areas that the cars can be in)
#     - Overlay map, or number of extra meshes such as doors/barrels

# Textures:
#   Uses DMA tags to transfer directly to GS with GIF tags
#   This is just a continuous block of textures
#   Each texture just follows the previous, usually with a
#   palette proceeding the texture data.
#

# The information below is old and mostly incorrect, DMAtags and VifTags and GIFtags are used to decode the data
# Models:
# The model starts with an array of offsets, assumed to be chunks (8x8), one long per chunk
# following this there are 8x8 numbers (shorts, two bytes) which I think contains the number of

#
# File 3:
#   This has not been updated to use DMA tags, or other ps2 known parts, unsure if it
#   uses dma/gs/vif at all as it might be cpu side
#
#   This file contains a mesh system used to keep the cars within certain
#   areas. Once a car leaves this area it is pulled back on the this mesh.
#   I think this is used to simplify collision checks in the game
#   The file is broken into chunks (16x16)
#   Each chunk contains a number of vertices, and sometimes normals
#
# File 4+: 
#   This is often the mini map, used for showing player position 
#   on the blue track ring overlay. 
#   It can be parsed as like a car mesh, using the CarMesh class as is and will produce the map
#   There may be more than 1 file from here onwards, usually holding 
#   movable items such as doors, chests or barrels.
#   
#   Some files (Field 023) hold more than just simple meshes, 023 holds the
#   MyCity meshes as field/course format meshes, so not all files 
#   only hold car format like meshes.
#
# The currently assumed structure is a follows, there are a few variations but this is
# the general idea of how each field/course is structured
#
# Offset table (Longs)
#
# Textures:
# DMAtag
#   Start of image
#     GIFtag
#       - Sets up image trasfer
#       - BITBLTBUF
#       - TRXPOS
#       - TRXREG
#       - TRXDIR
#       - DIMX
#     GIFtag IMAGE mode
#       - Sends image
#       - has img data length
# DmaTag
#    Clut
#      GIFTag
#        - BITBLTBUF
#        - TRXPOS
#        - TRXREG
#        - TRXDIR
#      GIFtag Image Mode
#        - has length of data
# Repeats until end of textures usually DMA tagId = 7
#
# Chunk offset table and size table, example below may have 3 in first chunk for instance
# Mesh:
# DMAtag
#   VIF tag = STCYCL CYCLE->257 to WL/CL 1 1 # Always has been 1/1 for everything I have tested including HG3
#   VIF tag unpack v32-3
#   - Gif tag
#     - Sets TEX1_2
#     - Sets TEX0_2(7)
#     - Sets CLAMP_2(9)
# 1- (think this is how the counter works)
#   VIF tag unpack as is
#   - Gif tag Packed
#     - ST
#     - RGBAQ
#     - XYZF2
#   Vif Tag unpack v32-3
#    - Mesh data
#   Vif Tag = MSCALF EXECADDR 64 in vif1 (run sub)
# 2- (think this is how the counter works)
#   Vif tag unpack as is
#    - GIF tag
#   Vif tag unpack v32-3
#    - Mesh data
#   Vif Tag = MSCALF EXECADDR 64 in vif1 (run sub)
# 3- (think this is how the counter works)
#   Vif tag unpack as is
#    - Gif tag
#   Vif tag unpack v32-3
#    - Mesh data
#   Vif tag = MSCALF EXECADDR->64 in vif1 (run sub)
#
# Extra meshes for the map, or in level objects, or for FLD/023 extra "fields" with chunk lists

import io
import os
import math
from choroq.amesh import AMesh
from choroq.texture import Texture
from choroq.car import CarModel, CarMesh
import choroq.read_utils as U
import choroq.ps2_utils as PS2


class CourseModel:

    def __init__(self, name, meshes=None, textures=None, colliders=None, colliders_by_mat=None, post_colliders=None, map_meshes=None,
                 extras=None, extra_fields=None, extra_field_colliders=None):
        if meshes is None:
            meshes = []
        if textures is None:
            textures = []
        if colliders is None:
            colliders = []
        if colliders_by_mat is None:
            colliders_by_mat = []
        if post_colliders is None:
            post_colliders = []
        if map_meshes is None:
            map_meshes = []
        if extras is None:
            extras = []
        if extra_fields is None:
            extra_fields = []
        if extra_field_colliders is None:
            extra_field_colliders = []
        self.name = name
        self.meshes = meshes
        self.colliders = colliders
        self.colliders_by_mat = colliders_by_mat
        self.post_colliders = post_colliders
        self.map_meshes = map_meshes
        self.textures = textures
        self.extras = extras
        self.extra_fields = extra_fields
        self.extra_field_colliders = extra_field_colliders

    @staticmethod
    def read_course(file):
        print("Reading course")
        textures_offset = U.readLong(file)
        mesh_offset = U.readLong(file)
        collider_offset = U.readLong(file)

        # Used for additional parts, such as extra fields for 023 (my city)
        other_offsets = []
        next_offset = U.readLong(file)
        while next_offset != 0:
            other_offsets.append(next_offset)
            next_offset = U.readLong(file)
        if len(other_offsets) == 0:
            print("Had zero extra offsets, e.g <= 3 offsets in file")
            exit(200)
        eof_offset = other_offsets[-1]
        other_offsets = other_offsets[:-1]

        print("Reading course: Textures")
        textures = CourseModel.read_course_textures(file, textures_offset, mesh_offset - textures_offset)
        print("Reading course: Meshes")
        meshes = Course.read_course_meshes(file, mesh_offset)

        print("Reading course: Colliders")
        # 4 point colliders, used for things like walls and fence posts
        colliders_by_mat, post_colliders, colliders = CourseCollider.from_file(file, collider_offset)

        # The name maps, and extras could/should probably be renamed
        maps = []
        extras = []
        extra_fields = []
        extra_field_colliders = []

        if len(other_offsets) > 0:
            other_offsets.append(eof_offset)
            print(other_offsets)
            for oi, o in enumerate(other_offsets[:-1]):
                print(f"reading extras {o}")
                file.seek(o, os.SEEK_SET)
                peek = U.readLong(file)
                file.seek(-4, os.SEEK_CUR)
                print(f"Peeked at extra got {peek}")
                if peek >= 1540:
                    # Probably a field collider table
                    print("Reading course: Field meshes")
                    extra_field_colliders += CourseCollider.from_file(file, o)
                elif 400 <= peek < 1000:
                    # Probably a field mesh table
                    print("Reading course: Field meshes")
                    extra_fields += Course.read_course_meshes(file, o)
                elif 48 > peek >= 16:
                    # Has whole car model style data
                    extras.append(CarModel.read_car(file, o, other_offsets[oi + 1]))
                else:
                    # Only has a mesh
                    maps += CarMesh.from_file(file, o)

        return CourseModel("", meshes, textures, colliders, colliders_by_mat, post_colliders, maps, extras, extra_fields, extra_field_colliders)
    
    @staticmethod
    def read_course_textures(file, offset, length):
        file.seek(offset, os.SEEK_SET)
        textures = {}
        while file.tell() < offset+length:
            (address, texture), end = Texture.read_texture(file, file.tell())
            if address is tuple:
                # Handle appends
                offset = address[1]
                address = address[0]
                print(offset)
                print(address)
                exit(200)

            if address in textures:
                print(f"Found overlapping/duplicated addresses {address}")
                # This is usually (has happened for A01 of HG3)
                # a way to copy a large texture, and append it by using DSAX DSAY fields

                exit()
            textures[address] = texture
            # Check for end of dma transfer
            if end:
                print(f"textures DMATAG END: @ {file.tell()}")
                break

        return textures
    
    @staticmethod
    def read_course_colliders(file, offset):
        pass


class Course:

    def __init__(self, chunks, chunk_offsets, shorts):
        self.chunks = chunks
        self.chunk_offsets = chunk_offsets
        self.shorts = shorts

    @staticmethod
    def read_course_meshes(file, offset):
        # This starts off with a chunk offset table,
        # and a table with counts for how many meshes
        # each chunk contains.
        file.seek(offset, os.SEEK_SET)
        first_offset = U.readLong(file)
        file.seek(offset, os.SEEK_SET)
        chunks = []  # Has x_max by z_max, z rows
        x_max = 8
        z_max = 8
        min_offset = 390

        choroq3_test = False
        if first_offset > 400:
            choroq3_test = True
            # This has larger table
            # At least 16x16
            x_max = 16
            z_max = 16
            # if first_offset >= 1544:
            #     # Has 32x32 chunks
            #     # Not seen, but adding in case
            #     x_max = 32
            #     z_max = 32
        if choroq3_test:
            print(f"This is probably a HG 3 mesh chunks (x:{x_max}, z:{z_max}) as first is {first_offset}")

        shorts_max = x_max * z_max

        chunk_offsets = []
        for z in range(0, z_max):
            for x in range(0, x_max):
                chunk_offsets.append(U.readLong(file))

        if not choroq3_test:
            extra_offset = U.readLong(file)

        # Number of sub files/meshes in chunk
        # This is not used in this script
        shorts = []
        for j in range(shorts_max):
            shorts.append(U.readShort(file))
        if not choroq3_test:
            extra_short = U.readShort(file)

        print("Reading course: Meshes: Chunk sizes")

        gs_state = PS2.GsState()

        for z in range(0, z_max):
            z_row = []
            for x in range(0, x_max):
                index = x + z * x_max
                print(f"Reading chunk {index} z{z} x{x}")
                if chunk_offsets[index] < min_offset:
                    # Must be empty or invalid chunk as offset table is within this region
                    print(f"Skipping chunk offset too low {chunk_offsets[index]}")
                    # z_row.append({})
                    continue
                if choroq3_test and index == z_max * x_max - 1:
                    print("Skipping as last for CHQ HG 3")
                    continue
                # print(f"Reading course: Meshes: Chunk[{index}] @ {chunk_offsets[index]} size: {shorts[index]} - ABS {offset+chunk_offsets[index]}")
                chunk = Course.read_course_chunk(file, offset + chunk_offsets[index], shorts[index], gs_state, choroq3_test)
                z_row += chunk
            chunks.append(z_row)

        # Process the extra part of the course
        # This is usually used in fields to hold the windows/trees
        # Ensure offset is after the offset table
        if not choroq3_test and extra_offset > min_offset:
            print(f"extra_offset {offset + extra_offset} {extra_offset} {extra_short} but at @ {file.tell()}")
            extra_chunk = Course.read_course_chunk(file, offset + extra_offset, extra_short, gs_state, choroq3_test)
            chunks.append(extra_chunk)

        return [Course(chunks, chunk_offsets, shorts)]

    @staticmethod
    def read_course_chunk(file, offset, count, gs_state, hg3=False):
        file.seek(offset, os.SEEK_SET)

        # Registers that may occur during reading of Vif tags/codes
        vif_state = PS2.VifState()
        gs_state = PS2.GsState()

        chunk_meshes = []

        # Follows this pattern:
        # 1 DMA tag
        # multiple:
        # - VIF tag/code
        #  - GIF tag
        # - VIF tag
        #   - Mesh data

        # Read DMATag for this chunk
        dma_start = file.tell()
        dma_tag = PS2.decode_DMATag(file)
        tag_id = PS2.decode_DMATagID_source(dma_tag)
        print(dma_tag)
        print(tag_id)
        chunk_byte_length = dma_tag['qwordCount'] * 16 + 16
        # For meshes there is VIF tags in the data region, so jump back
        file.seek(-8, os.SEEK_CUR)
        processed_size = 0
        vif_processed_bytes = io.BytesIO(bytes())
        extracted_data = False
        data_count = 0
        gif_count = 0
        while file.tell() < dma_start + chunk_byte_length:
            print(f"Data [{data_count}]: @ {file.tell()} out of {dma_start + chunk_byte_length}")
            # Read viftag,  reading data until end of the read VIF tag
            # Updates the state if any cmds do that
            expected_length_in_packets, expected_length_out, vif_expanded_data = PS2.VifHandle(file, vif_state)
            # print(f"VIF: in:{expected_length_in_packets}, out:{expected_length_out}, {vif_expanded_data}")
            # print(vars(vif_state))
            if vif_state.ExecAddr != 0:
                # Call to run a subroutine/program on the VU1 microprogram, i.e use the data
                if (vif_state.ExecAddr == 64
                        or vif_state.ExecAddr == 48
                        or (hg3 and vif_state.ExecAddr == 96)
                        or (hg3 and vif_state.ExecAddr == 80)):
                    # Think this is process model data funct/subroutine call
                    # exec == 48 used in extra chunk as "Billboard" / sprites, flat shape with offset x/y/z preceeding data
                    # exec == 64 used for normal meshes (fields at least)
                    # exec = 96 seen in hg3 for courses, has extra 4 floats
                    vif_processed_bytes.seek(0, os.SEEK_SET)
                    vif_processed_bytes.seek(0, os.SEEK_SET)
                    chunk, counts = Course.parse_chunk_mesh(vif_processed_bytes, processed_size, gs_state, vif_state.ExecAddr, hg3)
                    gif_count += counts
                    chunk_meshes.append(chunk)
                    extracted_data = True
                    data_count += 1
                    vif_processed_bytes.seek(0, os.SEEK_SET)
                    vif_processed_bytes.truncate(
                        0)  # Reset length of data back to 0, as we have processed this section of the chunk
                    processed_size = 0
                    # Clear call after processing
                    vif_state.ExecAddr = 0

                    # Check if we have read all data for this chunk
                    if gif_count < count:
                        # Check we are at the end of this dma tag, before trying
                        # to get more data. And that the dma tag was not an end
                        if file.tell() + 16 > dma_start + chunk_byte_length:
                            print(f"Checking for possible more data in chunk (more DMAs) @ {file.tell()}")
                            if not tag_id['tag_end']:
                                # Skip past any padding, as should be aligned
                                while file.tell() % 16 != 0:
                                    file.seek(1, os.SEEK_CUR)
                                print(f"Decided to process another dma tag @ {file.tell()}")

                                # try read next tag, almost like restarting
                                dma_start = file.tell()
                                dma_tag = PS2.decode_DMATag(file)
                                tag_id = PS2.decode_DMATagID_source(dma_tag)
                                print(dma_tag)
                                print(tag_id)
                                chunk_byte_length = dma_tag['qwordCount'] * 16 + 16
                                # For meshes there is VIF tags in the data region, so jump back
                                file.seek(-8, os.SEEK_CUR)
                                print(f"Restarting readCourseChunk after more DMAs @ {file.tell()}")
                    pass
                elif hg3 and vif_state.ExecAddr == 0xA0:
                    # Unsure on this, it has been: 3 0xFF then 0 then a float of 0.5, then integer (4 bytes) then float (800)
                    # Could be offsetting or positioning of the course? or anything else
                    # Just move past.
                    # Clear call after "processing"
                    vif_state.ExecAddr = 0
                    print(f"Came across 0xA0 (160) execAddr for HG3 course, skipping as unsure on use")
                    pass
                else:
                    print(f"Found new course ExecAddr call: @{file.tell()} value: {vif_state.ExecAddr}")
                    exit(100)

            if vif_expanded_data is not None:
                print(f"Should get {expected_length_out} from {(expected_length_in_packets - 1) * 4}")
                # Copy the expanded data into another stream to process as one
                processed_size += expected_length_out
                vif_processed_bytes.write(vif_expanded_data.read(expected_length_out))
            print(f"Still reading chunk? @ {file.tell()} out of {dma_start + chunk_byte_length}")
        if not extracted_data:
            # Extract data at this point as it was missed somehow
            print("No data")

        return chunk_meshes

    @staticmethod
    def parse_chunk_mesh(file, length, gs_state, exec_type, hg3=False):
        context = gs_state.PRIM["CTXT"]
        texture0_addr = gs_state.TEX0_1["TBP0"]
        texture1_addr = gs_state.TEX0_2["TBP0"]
        clut0_addr = gs_state.TEX0_1["CBP"]
        clut1_addr = gs_state.TEX0_2["CBP"]
        bitbltbuf_SBP = gs_state.BITBLTBUF["SBP"]
        bitbltbuf_SPSM = gs_state.BITBLTBUF["SPSM"]
        bitbltbuf_DBP = gs_state.BITBLTBUF["DBP"]
        bitbltbuf_DPSM = gs_state.BITBLTBUF["DPSM"]

        # Basic list of all meshes found
        meshes = []
        # Basic list of all texture references found (clut, texture)
        textures = []
        # list of meshes by (clut, texture)
        meshesByTexture = {}

        print("Parsing chunk mesh")
        verts = []
        normals = []
        uvs = []
        faces = []
        day_colours = []
        night_colours = []
        extras = []
        count = 0  # Number of GIF tags read
        # Read GIFTag
        while file.tell() < length:
            gif_tag = int.from_bytes(file.read(16), 'little')

            nloop = PS2.gifGetNLoop(gif_tag)
            eop = PS2.gifGetEop(gif_tag)
            pre = PS2.gifGetPrimEnable(gif_tag)
            prim = PS2.gifGetPrim(gif_tag)
            mode = PS2.gifGetMode(gif_tag)
            nreg = PS2.gifGetNReg(gif_tag)
            descriptors = PS2.gifGetRegisterDescriptors(gif_tag)
            print(descriptors)

            registers = None
            if mode == PS2.GIF_MODE_PACKED:
                registers = []
                for i in range(0, 16):
                    registers.append(PS2.gifDecodePacked(descriptors[i]))
                    # print(registers[-1])

                # if (gif_tag >> 96) == 0x313EC000:
                print(registers[0:3])
                if registers[0:3] == ["ST", "RGBAQ", "XYZF2"]:
                    # This is mesh data, ignore order above,
                    # it is changed in VU1 afaik
                    print("Match")
                    print(f"Got to before verts {file.tell()}")
                    offsetX, offsetY, offsetZ = (0, 0, 0)
                    if exec_type == 48:
                        # read offset x/y/z/w first
                        # I believe these parts of the data, are probably transparent meshes
                        offsetX, offsetY, offsetZ = U.readXYZ(file)
                        offsetW = U.readFloat(file)
                    if hg3:
                        # Unknown data
                        U.readXYZ(file)
                        U.readFloat(file)
                    for loop in range(nloop):
                        if hg3:
                            vx, vy, vz = U.readXYZ(file)
                            vw = U.readFloat(file)  # = 0

                            # Day time baked lighting data/colours
                            # This is used in the day time, and scaled down as night approaches
                            dr, dg, db = U.readXYZ(file)
                            U.readFloat(file)  # = 0

                            tu, tv, tw = U.readXYZ(file)  # Are texture coords
                            U.BreadFloat(file)

                            nx, ny, nz, nw = 0, 0, 0, 0
                            nr, ng, nb = 0, 0, 0

                            if exec_type == 96:
                                # Has 4 sets of 4 floats not the normal 3
                                # but unsure on what the new value is, some negative, most are small numbers e.g 3 -4.5
                                # Guessing?:
                                # Nighttime baked lighting data/colours
                                # This is used at the Night time, and scaled down as day approaches
                                nr, ng, nb = U.readXYZ(file)
                                U.BreadFloat(file)

                            day = (dr, dg, db, 255)  # Convert to RGBA
                            night = (nr, ng, nb, 255)  # Convert to RGBA
                            verts.append((offsetX + vx, offsetY + vy, offsetZ + vz))
                            day_colours.append(day)
                            night_colours.append(night)
                            normals.append((nx, ny, nz))
                            uvs.append((tu, 1 - tv, tw))
                        else:
                            # I think the order of floats is as follows:
                            # X, Y, Z, W
                            # RED, GREEN, BLUE, unused (Baked Lighting for daytime)
                            # Additional fields, E0, E1, E2
                            #   - Where E0 may hold transparency of the mesh
                            # RED, GREEN, BLUE, unused (Baked lighting for nighttime)
                            # TextureU, TextureV, TextureW, unused (texture coords)

                            vx, vy, vz = U.readXYZ(file)
                            vw = U.readFloat(file)  # = 0

                            # Day time baked lighting data/colours
                            # This is used in the day time, and scaled down as night approaches
                            dr, dg, db = U.readXYZ(file)
                            U.readFloat(file)  # = 0

                            # I suspect there is no real time lighting for world meshes and so no normals
                            # Writing to normals for easy parsing
                            nx = opacity = U.readFloat(
                                file)  # 1 = opaque, 0 = see through (mostly, like watery probably used for rivers?)
                            # I think these relate to lighting (unsure on what they are)
                            # Probably extra data to go with the day/night lighting
                            ny = U.readFloat(file)  # Unknown # Theses are usually ~100f 70-120 ish
                            nz = U.readFloat(file)  # Unknown
                            nw = U.readFloat(file)  # = 0

                            # Nighttime baked lighting data/colours
                            # This is used at the Night time, and scaled down as day approaches
                            nr, ng, nb = U.readXYZ(file)
                            U.BreadFloat(file)

                            tu, tv, tw = U.readXYZ(file)  # Are texture coords
                            U.BreadFloat(file)

                            day = (dr, dg, db, 255)  # Convert to RGBA
                            night = (nr, ng, nb, 255)  # Convert to RGBA
                            verts.append((offsetX + vx, offsetY + vy, offsetZ + vz))
                            day_colours.append(day)
                            night_colours.append(night)
                            normals.append((nx, ny, nz))
                            uvs.append((tu, 1 - tv, tw))

                    faces = CourseMesh.create_face_list(nloop, 1)
                    print(f"Got to after verts {file.tell()}")
                else:
                    for loop in range(nloop):
                        for reg in range(nreg):
                            print(f"GsState change packet loop [{loop}] reg [{reg}]")
                            PS2.gifHandlePacked(file, gif_tag, reg, descriptors[reg], gs_state)
                    change = False
                    if context != gs_state.PRIM["CTXT"]:
                        change = True
                        print("Context Changed")
                    if texture0_addr != gs_state.TEX0_1["TBP0"]:
                        print("Texture0 address Changed")
                        change = True
                    if texture1_addr != gs_state.TEX0_2["TBP0"]:
                        print("Texture1 address Changed")
                        change = True
                    if clut0_addr != gs_state.TEX0_1["CBP"]:
                        print("Clut0 address Changed")
                        change = True
                    if clut1_addr != gs_state.TEX0_2["CBP"]:
                        print("Clut1 address Changed")
                        change = True
                    if bitbltbuf_SBP == gs_state.BITBLTBUF["SBP"]:
                        print("BitBltBuf SBP Changed")
                        change = True
                    if bitbltbuf_SPSM == gs_state.BITBLTBUF["SPSM"]:
                        print("BitBltBuf SPSM Changed")
                        change = True
                    if bitbltbuf_DBP == gs_state.BITBLTBUF["DBP"]:
                        print("BitBltBuf DBP Changed")
                        change = True
                    if bitbltbuf_DPSM == gs_state.BITBLTBUF["DPSM"]:
                        print("BitBltBuf DPSM Changed")
                        change = True
                    if change:
                        print("Detected change in texture")
                        # Move current mesh data into a new mesh
                        # and store it with its texture information
                        texture = None
                        if context == 0:
                            texture = (clut0_addr, texture0_addr)
                        else:
                            texture = (clut1_addr, texture1_addr)
                        if len(verts) != 0:
                            print(f"Started new mesh, old had {len(verts)} verts")
                            # Skip if there is no data
                            # This handles, the first case where nothing has been read
                            if texture not in meshesByTexture:
                                meshesByTexture[texture] = []
                            new_mesh = CourseMesh(len(verts), verts, normals, uvs, faces, day_colours, night_colours, extras)
                            meshes.append(new_mesh)
                            meshesByTexture[texture].append(new_mesh)

                        print(f"CTXT: {context} -> {gs_state.PRIM['CTXT']}")
                        print(f"tex0 addr {texture0_addr} -> {gs_state.TEX0_1['TBP0']}")
                        print(f"tex1 addr {texture1_addr} -> {gs_state.TEX0_2['TBP0']}")
                        print(f"clut0 addr {clut0_addr} -> {gs_state.TEX0_1['CBP']}")
                        print(f"clut1 addr {clut1_addr} -> {gs_state.TEX0_2['CBP']}")
                        print(f"clut1 addr {clut1_addr} -> {gs_state.TEX0_2['CBP']}")
                        print(gs_state.TEX0_1)
                        print(gs_state.TEX0_2)
                        print(f"bitbltbuf src addr {bitbltbuf_SBP} -> {gs_state.BITBLTBUF['SBP']}")
                        print(f"bitbltbuf dst addr {bitbltbuf_DBP} -> {gs_state.BITBLTBUF['DBP']}")
                        print(f"bitbltbuf spsm {bitbltbuf_SPSM} -> {gs_state.BITBLTBUF['SPSM']}")
                        print(f"bitbltbuf dpsm {bitbltbuf_DPSM} -> {gs_state.BITBLTBUF['DPSM']}")
                        # Update tracked values
                        context = gs_state.PRIM["CTXT"]
                        texture0_addr = gs_state.TEX0_1["TBP0"]
                        texture1_addr = gs_state.TEX0_2["TBP0"]
                        clut0_addr = gs_state.TEX0_1["CBP"]
                        clut1_addr = gs_state.TEX0_2["CBP"]
                        bitbltbuf_SBP = gs_state.BITBLTBUF["SBP"]
                        bitbltbuf_SPSM = gs_state.BITBLTBUF["SPSM"]
                        bitbltbuf_DBP = gs_state.BITBLTBUF["DBP"]
                        bitbltbuf_DPSM = gs_state.BITBLTBUF["DPSM"]
                        # Restart mesh arrays
                        verts = []
                        normals = []
                        uvs = []
                        faces = []
                        day_colours = []
                        night_colours = []
                        extras = []

            elif mode == PS2.GIF_MODE_REGLIST:
                print("RegList not implemented")
                exit(101)
            elif mode == PS2.GIF_MODE_IMAGE:
                print("IMAGE not implemented")
                exit(102)
            else:
                print("GIF issue mode?")
                exit(103)

            print(registers)
            count += 1

        # Catch any at the end
        new_mesh = CourseMesh(len(verts), verts, normals, uvs, faces, day_colours, night_colours, extras)
        meshes.append(new_mesh)
        texture = None
        if context == 0:
            texture = (clut0_addr, texture0_addr)
        else:
            texture = (clut1_addr, texture1_addr)
        if texture not in meshesByTexture:
            meshesByTexture[texture] = []
        meshesByTexture[texture].append(new_mesh)

        # return ((meshes, textures), meshesByTexture)
        return meshesByTexture, count


class CourseMesh(AMesh):

    def __init__(self, mesh_vert_count=None, mesh_verts=None, mesh_normals=None, mesh_uvs=None, mesh_faces=None,
                 mesh_day_colours=None, mesh_night_colours=None, mesh_extras=None):
        if mesh_verts is None:
            mesh_verts = []
        if mesh_normals is None:
            mesh_normals = []
        if mesh_uvs is None:
            mesh_uvs = []
        if mesh_faces is None:
            mesh_faces = []
        if mesh_day_colours is None:
            mesh_day_colours = []
        if mesh_night_colours is None:
            mesh_night_colours = []
        if mesh_extras is None:
            mesh_extras = []
        self.mesh_vert_count    = mesh_vert_count
        self.mesh_verts         = mesh_verts
        self.mesh_normals       = mesh_normals
        self.mesh_uvs           = mesh_uvs
        self.mesh_faces         = mesh_faces
        self.mesh_day_colours   = mesh_day_colours
        self.mesh_night_colours = mesh_night_colours
        self.mesh_extras        = mesh_extras

    def write_mesh_to_obj(self, fout, start_index=0, material=None, with_colours=False):
        # Write vertices
        for i in range(0, len(self.mesh_verts)):
            vx = '{:.20f}'.format(self.mesh_verts[i][0])
            vy = '{:.20f}'.format(self.mesh_verts[i][1])
            vz = '{:.20f}'.format(self.mesh_verts[i][2])
            if with_colours:
                # Some programs support additional data, e.g colors after x/y/z
                # the following section can be used to export with colors (blender supports first set)
                dr = '{:.20f}'.format(self.mesh_day_colours[i][0] / 255.0)
                dg = '{:.20f}'.format(self.mesh_day_colours[i][1] / 255.0)
                db = '{:.20f}'.format(self.mesh_day_colours[i][2] / 255.0)
                nr = '{:.20f}'.format(self.mesh_night_colours[i][0] / 255.0)
                ng = '{:.20f}'.format(self.mesh_night_colours[i][1] / 255.0)
                nb = '{:.20f}'.format(self.mesh_night_colours[i][2] / 255.0)
                fout.write(f"v {vx} {vy} {vz} {dr} {dg} {db} {nr} {ng} {nb}\n")
            else:
                fout.write(f"v {vx} {vy} {vz}\n")
        fout.write("#" + str(len(self.mesh_verts)) + " vertices\n")
            
        # Course meshes have no normals, but swapped with other data
        # Write normals
        # for i in range(0, len(self.mesh_normals)):
        #     nx = '{:.20f}'.format(self.mesh_normals[i][0])
        #     ny = '{:.20f}'.format(self.mesh_normals[i][1])
        #     nz = '{:.20f}'.format(self.mesh_normals[i][2])
        #     fout.write("vn " + nx + " " + ny + " " + nz + "\n")
        # fout.write("#" + str(len(self.mesh_normals)) + " vertex normals\n")
        for i in range(0, len(self.mesh_normals)):
            fout.write("vn 0 0 0\n")
        fout.write("#" + str(len(self.mesh_normals)) + " vertex normals\n")
        # Write texture coordinates (uv)
        for i in range(0, len(self.mesh_uvs)):
            tu = '{:.20f}'.format(self.mesh_uvs[i][0])
            tv = '{:.20f}'.format(self.mesh_uvs[i][1])
            fout.write("vt " + tu + " " + tv + "\n")
        fout.write("#" + str(len(self.mesh_uvs)) + " texture vertices\n")
        
        fout.write(f"usemtl {material}\n")
        fout.write("s off\n")

        # Write mesh face order/list
        for i in range(0, len(self.mesh_faces)):
            fx = self.mesh_faces[i][0] + start_index
            fy = self.mesh_faces[i][1] + start_index
            fz = self.mesh_faces[i][2] + start_index
            
            fout.write(f"f {fx}/{fx}/{fx} {fy}/{fy}/{fy} {fz}/{fz}/{fz}\n")
        fout.write("#" + str(len(self.mesh_faces)) + " faces\n")

        return len(self.mesh_verts)

    def write_mesh_to_comb(self, fout, start_index=0, material=None):
        fout.write(f"vertex_count {len(self.mesh_verts)}\n")
        fout.write(f"face_count {len(self.mesh_faces)}\n")
        fout.write(f"texture {material}\n")
        fout.write("end_header\n")
        # Write vertices, colours, normals
        for i in range(0, len(self.mesh_verts)):
            vx = '{:.20f}'.format(self.mesh_verts[i][0])
            vy = '{:.20f}'.format(self.mesh_verts[i][1])
            vz = '{:.20f}'.format(self.mesh_verts[i][2])

            dr = '{:d}'.format(math.trunc(self.mesh_day_colours[i][0]))
            dg = '{:d}'.format(math.trunc(self.mesh_day_colours[i][1]))
            db = '{:d}'.format(math.trunc(self.mesh_day_colours[i][2]))
            da = '{:d}'.format(math.trunc(self.mesh_day_colours[i][3]))

            nr = '{:d}'.format(math.trunc(self.mesh_day_colours[i][0]))
            ng = '{:d}'.format(math.trunc(self.mesh_day_colours[i][1]))
            nb = '{:d}'.format(math.trunc(self.mesh_day_colours[i][2]))
            na = '{:d}'.format(math.trunc(self.mesh_day_colours[i][3]))

            if len(self.mesh_extras) != 0:
                ex = '{:.20f}'.format(self.mesh_extras[i][0])
                ey = '{:.20f}'.format(self.mesh_extras[i][1])
                ez = '{:.20f}'.format(self.mesh_extras[i][2])
            else:
                ex, ey, ez = 0, 0, 0

            if len(self.mesh_normals) != 0:
                nx = '{:.20f}'.format(self.mesh_normals[i][0])
                ny = '{:.20f}'.format(self.mesh_normals[i][1])
                nz = '{:.20f}'.format(self.mesh_normals[i][2])
            else:
                nx, ny, nz = 0, 0, 0

            tu = '{:.10f}'.format(self.mesh_uvs[i][0])
            tv = '{:.10f}'.format(self.mesh_uvs[i][1])

            fout.write(f"{vx} {vy} {vz} {ex} {ey} {ez} {nx} {ny} {nz} {dr} {dg} {db} {da} {nr} {ng} {nb} {na} {tu} {tv}\n")
        
        # Write mesh face order/list
        for i in range(0, len(self.mesh_faces)):
            fx = self.mesh_faces[i][0] - 1 + start_index
            fz = self.mesh_faces[i][2] - 1 + start_index
            fy = self.mesh_faces[i][1] - 1 + start_index
            
            fout.write(f"4 {fx} {fy} {fz}\n")
        
        return len(self.mesh_verts)

    def write_mesh_to_ply(self, fout, start_index=0):
        # Write header
        if start_index == 0:
            fout.write("ply\n")
            fout.write("format ascii 1.0\n")
            fout.write(f"element vertex {len(self.mesh_verts)}\n")
            fout.write("property float x\n")
            fout.write("property float y\n")
            fout.write("property float z\n")
            fout.write("property float nx\n")
            fout.write("property float ny\n")
            fout.write("property float nz\n")
            fout.write("property uchar red\n")
            fout.write("property uchar green\n")
            fout.write("property uchar blue\n")
            fout.write("property uchar alpha\n")
            fout.write("property float s\n")
            fout.write("property float t\n")
            fout.write(f"element face {len(self.mesh_faces)}\n")
            fout.write("property list uint8 int vertex_index\n")

            # Write out the "extra" data sets
            fout.write("comment extra data:\n")
            for i in range(0, len(self.mesh_verts)):
                fx = '{:.20f}'.format(self.mesh_verts[i][0])
                fy = '{:.20f}'.format(self.mesh_verts[i][1])
                fz = '{:.20f}'.format(self.mesh_verts[i][2])
                fout.write(f"comment {fx} {fy} {fz}\n")
            fout.write("comment extra end\n")

            #fout.write(f"element texture {len(self.mesh_uvs)}\n")
            #fout.write("property list uint8 float texcoord\n")
            fout.write("end_header\n")

        # Write vertices, colours, normals
        for i in range(0, len(self.mesh_verts)):
            vx = '{:.20f}'.format(self.mesh_verts[i][0])
            vy = '{:.20f}'.format(self.mesh_verts[i][1])
            vz = '{:.20f}'.format(self.mesh_verts[i][2])

            cr = '{:d}'.format(math.trunc(self.mesh_day_colours[i][0]))
            cg = '{:d}'.format(math.trunc(self.mesh_day_colours[i][1]))
            cb = '{:d}'.format(math.trunc(self.mesh_day_colours[i][2]))
            ca = '{:d}'.format(math.trunc(self.mesh_day_colours[i][3]))

            # Normals are not here, this is different data
            nx = '{:.20f}'.format(self.mesh_normals[i][0])
            ny = '{:.20f}'.format(self.mesh_normals[i][1])
            nz = '{:.20f}'.format(self.mesh_normals[i][2])

            tu = '{:.10f}'.format(self.mesh_uvs[i][0])
            tv = '{:.10f}'.format(self.mesh_uvs[i][1])

            fout.write(f"{vx} {vy} {vz} {nx} {ny} {nz} {cr} {cg} {cb} {ca} {tu} {tv}\n")
        
        # Write mesh face order/list
        for i in range(0, len(self.mesh_faces)):
            fx = self.mesh_faces[i][0] - 1 + start_index
            fz = self.mesh_faces[i][2] - 1 + start_index
            fy = self.mesh_faces[i][1] - 1 + start_index
            
            fout.write(f"4 {fx} {fy} {fz}\n")
        
        return len(self.mesh_verts)
        
    def write_mesh_to_dbg(self, fout, start_index=0, material=None):
        for i in range(0, len(self.mesh_verts)):
            
            vx = '{:.20f}'.format(self.mesh_verts[i][0])
            vy = '{:.20f}'.format(self.mesh_verts[i][1])
            vz = '{:.20f}'.format(self.mesh_verts[i][2])
            fout.write("v " + vx + " " + vy + " " + vz + "\n")
            # Normals are not here, this is different data
            nx = '{:.20f}'.format(self.mesh_normals[i][0])
            ny = '{:.20f}'.format(self.mesh_normals[i][1])
            nz = '{:.20f}'.format(self.mesh_normals[i][2])
            cr = '{:.20f}'.format(self.mesh_day_colours[i][0])
            cg = '{:.20f}'.format(self.mesh_day_colours[i][1])
            cb = '{:.20f}'.format(self.mesh_day_colours[i][2])
            ca = '{:.20f}'.format(self.mesh_day_colours[i][3])
            ex = self.mesh_extras[i][0]
            ey = self.mesh_extras[i][1]
            ez = self.mesh_extras[i][2]
            fout.write(f"# {ex} {ey} {ez} {nx} {ny} {nz} {cr} {cg} {cb}\n")

            tu = '{:.20f}'.format(self.mesh_uvs[i][0])
            tv = '{:.20f}'.format(self.mesh_uvs[i][1])
            tw = '{:.20f}'.format(self.mesh_uvs[i][2])
            fout.write(f"vt {tu} {tv} {tw}\n")

        for i in range(0, len(self.mesh_faces)):
            fx = self.mesh_faces[i][0] + start_index
            fy = self.mesh_faces[i][1] + start_index
            fz = self.mesh_faces[i][2] + start_index
            fout.write(f"f {fx} {fy} {fz}\n")

        fout.write("#" + str(len(self.mesh_verts)) + " vertices\n")
        fout.write("#" + str(len(self.mesh_normals)) + " vertex normals\n")
        fout.write("#" + str(len(self.mesh_uvs)) + " texture vertices\n")
        fout.write("#" + str(len(self.mesh_extras)) + " texture vertices\n")
        fout.write("#" + str(len(self.mesh_faces)) + " faces\n")

        return len(self.mesh_verts)
        

# I believe this is referenced as "PMP format" by the developers ("Old style PMP format") but might be the other
# offset table
# If the first offset is 1536 it will print "Old style PMP format" (untested)
# If the first offset is 1544 it will load, otherwise an error "PMP Format Error!"
class CourseCollider(AMesh):

    def __init__(self, mesh_vert_count=None, mesh_verts=None, mesh_normals=None, mesh_faces=None, collider_properties=None):
        if mesh_vert_count is None:
            mesh_vert_count = []
        if mesh_verts is None:
            mesh_verts = []
        if mesh_normals is None:
            mesh_normals = []
        if mesh_faces is None:
            mesh_faces = []
        self.mesh_vert_count = mesh_vert_count
        self.mesh_verts      = mesh_verts
        self.mesh_normals    = mesh_normals
        self.mesh_faces      = mesh_faces
        self.properties      = collider_properties

    @staticmethod
    def from_file(file, offset):
        file.seek(offset, os.SEEK_SET)
        first_offset = U.readLong(file)
        file.seek(offset, os.SEEK_SET)

        x_chunks = 16
        y_chunks = 16
        if first_offset > 1544:
            print(f"Assuming HG3 collider as first offset is {first_offset}")
            # Table is probably larger
            # Assume HG 3 format file
            x_chunks = 32
            y_chunks = 32

        chunk_offsets = []
        for z in range(0, x_chunks):
            for x in range(0, y_chunks):
                chunk_offsets.append(U.readLong(file))
        print("Collider offsets:")
        print(chunk_offsets)
        # extraOffset = U.readLong(file)
        # chunk_offsets.append(extraOffset)

        # Number of sub files/meshes in chunk
        # This is not used in this script
        shorts = []
        for j in range(x_chunks * y_chunks):
            shorts.append(U.readShort(file))
        print("Collider shorts:")
        print(shorts)
        # extraShort = U.readShort(file)
        # shorts.append(extraShort)

        last_offset = U.readLong(file)  # Last offset is just before the first offset's data
        last_size = U.readLong(file)  # This is the number of vertices to read

        colliders = []
        colliders_by_mat = {}
        scale = 1
        collider_count = 0
        
        total_verts = 0

        offsets_done = set([])

        file.seek(0, os.SEEK_END)
        max_length = file.tell()

        # Read the mesh data between this offset and the next
        for z in range(0, y_chunks):
            z_row = []
            x_limit = x_chunks
            for x in range(0, x_limit):
                index = x + z * x_limit
                meshes = []
                data = []

                # Skip duplicates, removed as some chunks were being missed
                #if chunk_offsets[index] in offsets_done:
                    #print(f"!!Chunk offset has been visited skipping {x} {z} expected {shorts[index]}")
                    # continue
                offsets_done.add(chunk_offsets[index])

                if offset+chunk_offsets[index] >= max_length:
                    # At end of file
                    continue

                print(f"reading collider chunk {index} z{z} x{x} count: {shorts[index]}")

                file.seek(offset+chunk_offsets[index], os.SEEK_SET)

                mesh_verts = []
                mesh_normals = []
                mesh_uvs = []
                mesh_faces = []
                mesh_colours = []
                mesh_vert_count = 0
                collider_properties = None

                mesh_faces_all = []

                count = 0

                while count < shorts[index]:
                    print(f"Reading collider chunk {z} {x} {index} {count}/{shorts[index]} {collider_count} from: {file.tell()}")
                    vert_count = U.readByte(file)
                    check80 = U.BreadByte(file)  # always 0x80
                    if check80 != 0x80:
                        # This check is here for ChoroQ HG 3 files, mainly
                        print(f"Collider does not have 80 after count, must be in wrong location, skipping {count}/{shorts[index]}")
                        count += 1
                        continue
                    U.BreadShort(file)  # always 0x0000
                    
                    f1 = U.BreadLong(file)  # Often the same value (00 40 22 20), needs investigating
                    f2 = U.BreadLong(file)  # Often the save value (41 00 00 00), needs investigating
                    if f1 != 0x20224000:
                        print(f"Collider Flag 1 different @ {file.tell()} colIndex {count} z{z} x{x}")
                        raise NameError(f"Collider Flag 1 different @ {file.tell()} colIndex {count} z{z} x{x}")
                    
                    if f2 != 0x00000041:
                        print(f"Collider Flag 2 different @ {file.tell()} colIndex {count} z{z} x{x}")
                        raise NameError(f"Collider Flag 2 different @ {file.tell()} colIndex {count} z{z} x{x}")

                    # Usually 00 00 for roads, and 55 04 for ice
                    slip = U.readByte(file)  # Surface grip, 0=grippy 55=ice, might be forward slip
                    b = U.readByte(file)  # Unknown, probably slip related, could be side slip seen 01/02/03/04/11
                    # Other properties varies for river
                    # Seems to be 0 so far, 10 seen for a cave road seen 19 underwater
                    # (might be shader related (blue underwater))
                    c = U.readByte(file)
                    # 10 seen for river, (80 bottom of ocean sometimes)
                    # Seen 10 for other meshes (roads)
                    water_flag = U.readByte(file)
                    
                    collider_properties = (1 - (slip/255.0), b/255.0, c, water_flag)

                    verts, normals, faces = CourseCollider.parse_chunk(file, vert_count, scale)
                    
                    for i in range(0, len(faces)):
                        vertices = faces[i]
                        mesh_faces.append((vertices[0] + mesh_vert_count, vertices[1] + mesh_vert_count, vertices[2] + mesh_vert_count))
                        mesh_faces_all.append((vertices[0] + mesh_vert_count, vertices[1] + mesh_vert_count, vertices[2] + mesh_vert_count))
                        # mesh_faces.append((vertices[0], vertices[1], vertices[2]))
                    
                    mesh_vert_count += len(verts)
                    mesh_verts += verts
                    mesh_normals += normals

                    total_verts += len(verts)
                    count += 1
                    collider_count += 1

                    if collider_properties not in colliders_by_mat:
                        colliders_by_mat[collider_properties] = []

                    # Store collider by material
                    colliders_by_mat[collider_properties].append(CourseCollider(len(verts), verts, normals, faces, collider_properties))

                    mesh_faces = []
                print(f"Got {mesh_vert_count} {count} vs {shorts[index]}")
                if count != shorts[index]:
                    print(f"Number of colliders read is different")
                
                z_row.append(CourseCollider(mesh_vert_count, mesh_verts, mesh_normals, mesh_faces_all, collider_properties))
            colliders.append(z_row)
        if sum(shorts) != collider_count:
            print(f"Number of colliders read is different {sum(shorts)} {collider_count}")

        file.seek(offset + last_offset, os.SEEK_SET)
        post_colliders = []
        # Process the last chunk, x,y,z,y2 format and re-uses x/y for doing posts/towers
        if offset + last_offset + (last_size * 16) < max_length:
            print(f"Reading last colliders (4 point) at {file.tell()} should have {last_size} floats len {last_size * 16}")
            post_colliders += CoursePostCollider.parse_post_collider(file, last_size, scale)

        return colliders_by_mat, post_colliders, colliders

    @staticmethod
    def parse_chunk(file, vert_count, scale):
        verts = []
        normals = []
        faces = []

        # Read in vertices
        for x in range(0, vert_count):
            vx, vy, vz = U.readXYZ(file)
            vw = U.BreadLong(file) # 1.0f
            verts.append((vx * scale, vy * scale, vz * scale))

        # Read in normals
        #if vert_count <= 40 and vert_count >= 3:
        if vert_count >= 3:
            for n in range(vert_count - 2):
                normals.append(U.readXYZ(file))
                U.BreadLong(file) # 1.0f
            
            normals.append(normals[-1])
            normals.append(normals[-1])
        else:
            print("NOT READING NORMALS")

        faces = CourseCollider.create_face_list(vert_count, 3)
        return verts, normals, faces

    def write_mesh_to_obj(self, fout, start_index=0, material=None, with_colours=False):
        # Write vertices
        for i in range(0, len(self.mesh_verts)):
            vx = '{:.20f}'.format(self.mesh_verts[i][0])
            vy = '{:.20f}'.format(self.mesh_verts[i][1])
            vz = '{:.20f}'.format(self.mesh_verts[i][2])
            fout.write("v " + vx + " " + vy + " " + vz + "\n")
        fout.write("#" + str(len(self.mesh_verts)) + " vertices\n")
            
        # Write normals
        for i in range(0, len(self.mesh_normals)):
            nx = '{:.20f}'.format(self.mesh_normals[i][0])
            ny = '{:.20f}'.format(self.mesh_normals[i][1])
            nz = '{:.20f}'.format(self.mesh_normals[i][2])
            fout.write("vn " + nx + " " + ny + " " + nz + "\n")
        fout.write("#" + str(len(self.mesh_normals)) + " vertex normals\n")
        
        # Write empty uvs
        for i in range(0, len(self.mesh_verts)):
            fout.write("vt 0 0\n")

        # Write mesh face order/list
        for i in range(0, len(self.mesh_faces)):
            fx = self.mesh_faces[i][0] + start_index
            fy = self.mesh_faces[i][1] + start_index
            fz = self.mesh_faces[i][2] + start_index
            
            fout.write(f"f {fx}/{fx}/{fx} {fy}/{fy}/{fy} {fz}/{fz}/{fz}\n")
        fout.write("#" + str(len(self.mesh_faces)) + " faces\n")

        fout.write(f"usemtl {material}\n")
        fout.write("s off\n")
    
        return len(self.mesh_verts)

    def write_mesh_to_comb(self, fout, start_index=0, material=None):
        fout.write(f"vertex_count {len(self.mesh_verts)}\n")
        fout.write(f"face_count {len(self.mesh_faces)}\n")
        if self.properties:
            slip, b, c, waterFlag = self.properties
            fout.write(f"colliderprop {slip} {b} {c} {waterFlag}\n")
        fout.write("end_header\n")

        if len(self.mesh_normals) != len(self.mesh_verts):
            needed = abs(len(self.mesh_normals) - len(self.mesh_verts))
            for i in range(needed):
                self.mesh_normals.append((0.0, 0.0, 0.0))

        # Write vertices, normals
        for i in range(0, len(self.mesh_verts)):
            vx = '{:.20f}'.format(self.mesh_verts[i][0])
            vy = '{:.20f}'.format(self.mesh_verts[i][1])
            vz = '{:.20f}'.format(self.mesh_verts[i][2])

            nx = '{:.20f}'.format(self.mesh_normals[i][0])
            ny = '{:.20f}'.format(self.mesh_normals[i][1])
            nz = '{:.20f}'.format(self.mesh_normals[i][2])

            fout.write(f"{vx} {vy} {vz} {nx} {ny} {nz}\n")
        
        # Write mesh face order/list
        for i in range(0, len(self.mesh_faces)):
            fx = self.mesh_faces[i][0] - 1 + start_index
            fy = self.mesh_faces[i][1] - 1 + start_index
            fz = self.mesh_faces[i][2] - 1 + start_index
            
            fout.write(f"4 {fx} {fy} {fz}\n")

        return len(self.mesh_verts)

    def write_mesh_to_ply(self, fout, start_index = 0):
        if len(self.mesh_verts) != len(self.mesh_normals):
            # print("Cannot produce collider in ply format for:")
            # print(f"dst = {fout.name}")
            # return
            fout.write("ply\n")
            fout.write("format ascii 1.0\n")
            fout.write(f"element vertex {len(self.mesh_verts)}\n")
            fout.write("property float x\n")
            fout.write("property float y\n")
            fout.write("property float z\n")
            fout.write(f"element face {len(self.mesh_faces)}\n")
            fout.write("property list uint8 int vertex_index\n")
            fout.write("end_header\n")

            for i in range(0, len(self.mesh_verts)):
                vx = '{:.20f}'.format(self.mesh_verts[i][0])
                vy = '{:.20f}'.format(self.mesh_verts[i][1])
                vz = '{:.20f}'.format(self.mesh_verts[i][2])

                fout.write(f"{vx} {vy} {vz}\n")
        else:
            # Write header
            fout.write("ply\n")
            fout.write("format ascii 1.0\n")
            fout.write(f"element vertex {len(self.mesh_verts)}\n")
            fout.write("property float x\n")
            fout.write("property float y\n")
            fout.write("property float z\n")
            fout.write("property float nx\n")
            fout.write("property float ny\n")
            fout.write("property float nz\n")
            fout.write(f"element face {len(self.mesh_faces)}\n")
            fout.write("property list uint8 int vertex_index\n")
            fout.write("end_header\n")

            # Write vertices, normals
            for i in range(0, len(self.mesh_verts)):
                vx = '{:.20f}'.format(self.mesh_verts[i][0])
                vy = '{:.20f}'.format(self.mesh_verts[i][1])
                vz = '{:.20f}'.format(self.mesh_verts[i][2])

                nx = '{:.20f}'.format(self.mesh_normals[i][0])
                ny = '{:.20f}'.format(self.mesh_normals[i][1])
                nz = '{:.20f}'.format(self.mesh_normals[i][2])

                fout.write(f"{vx} {vy} {vz} {nx} {ny} {nz}\n")

        # print(f"v {len(self.mesh_verts)}")
        # print(f"n {len(self.mesh_normals)}")
        
        # Write mesh face order/list
        for i in range(0, len(self.mesh_faces)):
            fx = self.mesh_faces[i][0] - 1 + start_index
            fy = self.mesh_faces[i][1] - 1 + start_index
            fz = self.mesh_faces[i][2] - 1 + start_index
            
            fout.write(f"4 {fx} {fy} {fz}\n")

        return len(self.mesh_verts)
        
    def write_mesh_to_dbg(self, fout, start_index=0, material=None):
        for i in range(0, len(self.mesh_verts)):
            vx = '{:.20f}'.format(self.mesh_verts[i][0])
            vy = '{:.20f}'.format(self.mesh_verts[i][1])
            vz = '{:.20f}'.format(self.mesh_verts[i][2])
            fout.write("v " + vx + " " + vy + " " + vz + "\n")

        for i in range(0, len(self.mesh_normals)):
            nx = '{:.20f}'.format(self.mesh_normals[i][0])
            ny = '{:.20f}'.format(self.mesh_normals[i][1])
            nz = '{:.20f}'.format(self.mesh_normals[i][2])
            fout.write("vn " + nx + " " + ny + " " + nz + "\n")
            
            # ex = self.mesh_extras[i][0]
            # ey = self.mesh_extras[i][1]
            # ez = self.mesh_extras[i][2]
            # fout.write(f"e {ex} {ey} {ez}\n")

        for i in range(0, len(self.mesh_faces)):
            fx = self.mesh_faces[i][0] + start_index
            fy = self.mesh_faces[i][1] + start_index
            fz = self.mesh_faces[i][2] + start_index
            fout.write(f"f {fx} {fy} {fz}\n")

        fout.write("#" + str(len(self.mesh_verts)) + " vertices\n")
        fout.write("#" + str(len(self.mesh_normals)) + " texture vertices\n")
        fout.write("#" + str(len(self.mesh_faces)) + " faces\n")

        return len(self.mesh_verts)


class CoursePostCollider(AMesh):

    def __init__(self, mesh_vert_count=None, mesh_verts=None):
        if mesh_vert_count is None:
            mesh_vert_count = []
        if mesh_verts is None:
            mesh_verts = []
        self.mesh_vert_count = mesh_vert_count
        self.mesh_verts      = mesh_verts

    @staticmethod
    def parse_post_collider(file, last_size, scale):
        vert_count = 0
        face_direction = 1
        posts = []
        for i in range(int(last_size)):
            post_vertices = []
            post_faces = []

            x = U.readFloat(file)
            y = U.readFloat(file)
            z = U.readFloat(file)
            y2 = U.readFloat(file)
            # Convert 2 point collider into box collider

            post_vertices.append((x * scale, y2 * scale, z * scale))
            post_vertices.append((x * scale, y * scale, z * scale))
            
            # post_vertices.append((x+0.01, y2, z))
            # post_vertices.append((x+0.01, y, z))

            # post_vertices.append((x+0.01, y2, z+0.01))
            # post_vertices.append((x+0.01, y, z+0.01))

            # post_vertices.append((x, y2, z+0.01))
            # post_vertices.append((x, y, z+0.01))

            # post_vertices.append((x, y, z)) # Upper post
            # post_vertices.append((x, y2, z)) # Lower post

            post_vert_count = len(post_vertices)
            # faces = CourseCollider.createFaceList(len(post_vertices), 2, face_direction)
            # if i % 2 == 0:
            #     face_direction *= -1
            # for i in range(0, len(faces)):
            #     vertices = faces[i]
            #     post_faces.append((vertices[0], vertices[1], vertices[2]))
            
            #posts.append(CourseCollider(len(post_vertices), post_vertices, [], post_faces))
            posts.append(CoursePostCollider(len(post_vertices), post_vertices))
        return posts

    def write_mesh_to_obj(self, fout, start_index=0, material=None, with_colours=False):
        # Write vertices
        for i in range(0, len(self.mesh_verts)):
            vx = '{:.20f}'.format(self.mesh_verts[i][0])
            vy = '{:.20f}'.format(self.mesh_verts[i][1])
            vz = '{:.20f}'.format(self.mesh_verts[i][2])
            fout.write("v " + vx + " " + vy + " " + vz + "\n")
        fout.write("#" + str(len(self.mesh_verts)) + " vertices\n")
        fout.write(f"usemtl {material}\n")
        fout.write("s off\n")

        return len(self.mesh_verts)

    def write_mesh_to_comb(self, fout, start_index=0, material=None):
        fout.write(f"vertex_count {len(self.mesh_verts)}\n")
        fout.write(f"face_count {0}\n")
        fout.write("end_header\n")

        # Write vertices, normals
        for i in range(0, len(self.mesh_verts)):
            vx = '{:.20f}'.format(self.mesh_verts[i][0])
            vy = '{:.20f}'.format(self.mesh_verts[i][1])
            vz = '{:.20f}'.format(self.mesh_verts[i][2])

            fout.write(f"{vx} {vy} {vz} {0} {0} {0}\n")

        return len(self.mesh_verts)

    def write_mesh_to_ply(self, fout, start_index=0):
        # Write header
        fout.write("ply\n")
        fout.write("format ascii 1.0\n")
        fout.write(f"element vertex {len(self.mesh_verts)}\n")
        fout.write("property float x\n")
        fout.write("property float y\n")
        fout.write("property float z\n")
        fout.write("end_header\n")

        # Write vertices, normals
        for i in range(0, len(self.mesh_verts)):
            vx = '{:.20f}'.format(self.mesh_verts[i][0])
            vy = '{:.20f}'.format(self.mesh_verts[i][1])
            vz = '{:.20f}'.format(self.mesh_verts[i][2])

            fout.write(f"{vx} {vy} {vz}\n")

        return len(self.mesh_verts)
        
    def write_mesh_to_dbg(self, fout, start_index=0, material=None):
        for i in range(0, len(self.mesh_verts)):
            vx = '{:.20f}'.format(self.mesh_verts[i][0])
            vy = '{:.20f}'.format(self.mesh_verts[i][1])
            vz = '{:.20f}'.format(self.mesh_verts[i][2])
            fout.write("v " + vx + " " + vy + " " + vz + "\n")

        fout.write("#" + str(len(self.mesh_verts)) + " vertices\n")

        return len(self.mesh_verts)
