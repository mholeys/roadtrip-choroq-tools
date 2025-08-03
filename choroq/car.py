
# Class for holding car model data, and extracting it from a Qxx.BIN file

# Based on the format used in the game RoadTrip Adventure (UK/EU), aka ChoroQ HG 2 (JP) or Everywhere RoadTrip (US) for the Sony Playstation 2 (PS2)
# Information was gathered from multiple sources:
# - Most key mesh information was found https://forum.xentax.com/viewtopic.php?t=17567
#   The initial offset table info provided by Acewell (XeNTaX.com forums)
#   The mesh code was based on the 3DS Max script provided by killercracker (XeNTaX.com forums)
# - More information about the textures were extracted from https://zenhax.com/viewtopic.php?t=7405
#   Some information was provided related to a possible TIM/TIM2 style file for the textures
# 
# Other information was gathered from analysis or playstation/2 memory/data formats found in the manuals 

# Data format terms
# Float 4 bytes (No doubles anywhere)
# Long 4 bytes
# Short 2 bytes
# Byte = 8 bits
# All data is LittleEndian

#Qxx file format:
# [Offset table]
# First few bytes contain a list of longs that represent the start position of a sub file
# the last long in this list is the end of the file/files overall length
# The rest of the file is then just sub files, such as textures or meshes

# Mesh file
# [Offsets]
# The first two longs in the file represent the starting possitions for meshes in this file
# The offsets are as follows (16, <long0>, <long1>)
# 16 is the size of offset table, and so the first offset is always 16

# [Mesh]

# [MeshData]
# After these starts the actual mesh data for the models
# It is in roughly the following format
# DMAtag
#   - VIF tags, which setup the state, or expand the sent data
#   - GIF tags specifying the data to send to the GS, such as texture address
#   - Vertice data as shown below
#   - GIF tag to say use the data, and run the given program in the VU1
# After these the vertex information follows in the format below
# This is format is repeated for the number of vertices read in previously
# The index of vertex is based on where it was read from the first being 0
# This is used to build the faces of the mesh
#
# [Vertex/Vertices and data format]
# vertexX  = Float
# vertexY  = Float
# vertexZ  = Float
# normalX  = Float
# normalY  = Float
# normalZ  = Float
# colourX  = Float (or colorX)
# colourY  = Float (or colorY)
# colourZ  = Float (or colorZ)
# textureU = Float (UV U component)
# textureV = Float (UV V component)
# unknown  = Float (This may be a UV component of W but has not been checked)
#
# After the vertex data follows the VIF tag to execute the Vu1 program for this type of data
#
# [Face format]
# The faces are not actually stored in the file, and are statically calculated


import io
import sys
import os
import math
from choroq.amesh import AMesh
from choroq.texture import Texture
import choroq.read_utils as U
import choroq.ps2_utils as PS2


class CarModel:

    def __init__(self, name, meshes = [], textures = []):
        self.name = name
        self.meshes = meshes
        self.textures = textures

    @staticmethod
    def _parse_offsets(file, offset, size):
        file.seek(offset, os.SEEK_SET)
        sub_file_offsets = []
        o = U.readLong(file)
        sub_file_offsets.append(o)
        while o != size and o != 0 and (len(sub_file_offsets) == 0 or (file.tell() < offset+sub_file_offsets[0])):
            o = U.readLong(file)
            if o == 0:
                break
            sub_file_offsets.append(o)
        return sub_file_offsets

    @staticmethod
    def read_car(file, offset, size):
        sub_file_offsets = CarModel._parse_offsets(file, offset, size)
        print(f"Reading car model (full) from {file.tell()}")
        texture_offset = sub_file_offsets[-2]
        eof_offset = sub_file_offsets[-1]
        sub_file_offsets = sub_file_offsets[:-2]

        meshes = []
        textures = []

        for o in sub_file_offsets:
            mesh = CarMesh.from_file(file, offset+o)
            if len(mesh) > 0:
                meshes += mesh

        texture, last = Texture.read_texture(file, offset+texture_offset)
        textures.append(texture)
        while not last:
            texture, last = Texture.read_texture(file, file.tell())
            textures.append(texture)

        return CarModel("", meshes, textures)


class CarMesh(AMesh):

    def __init__(self, meshVertCount, meshVerts, meshNormals, meshUvs, meshFaces, meshColours):
        self.meshVertCount   = meshVertCount
        self.meshVerts       = meshVerts
        self.meshNormals     = meshNormals
        self.meshUvs         = meshUvs
        self.meshFaces       = meshFaces
        self.meshColours     = meshColours

    @staticmethod
    def _parse_offsets(file, offset):
        file.seek(offset, os.SEEK_SET)
        offset1 = U.readLong(file)
        offset2 = U.readLong(file)
        return 16, offset1, offset2

    @staticmethod
    def _parse_hg3_offsets(file, offset):
        file.seek(offset, os.SEEK_SET)
        # Header is as follows
        # byte/long (number of offsets in this mesh)
        # Jump 4 bytes to the start of the table
        # long is some sort of count, per offset
        # long is the offset (relative from here)

        offset_count = U.readLong(file)
        U.BreadLong(file)
        counts = []
        offsets = []
        for o in range(0, offset_count):
            counts.append(U.readLong(file))
            offsets.append(U.readLong(file))
            # offsets are 8 apart, I think to align with the offset table count
            file.seek(8, os.SEEK_CUR)

        return counts, offsets

    @staticmethod
    def from_file(file, offset, scale=1):
        file.seek(offset, os.SEEK_SET)
        print(f"reading car mesh {offset}")
        offsets = CarMesh._parse_offsets(file, offset)
        meshes = []
        hg3 = False
        if 1 <= offsets[1] <= 5:
            hg3 = True
            # Re-read offsets with different method
            counts, offsets = CarMesh._parse_hg3_offsets(file, offset)
        for o in offsets:
            if o < 16:
                if hg3:
                    # Some HG3 offsets in the different table are empty
                    continue
                # Not in HG2 though, so we are probably at an invalid location
                break
            print(offset)
            print(o)
            print(offset+o)
            mesh = CarMesh.read_car_part(file, offset+o, hg3)
            if mesh is not None:
                meshes.append(mesh)

        # returns [CarMesh())]
        return meshes

    @staticmethod
    def read_car_part(file, offset, hg3=False):
        file.seek(offset, os.SEEK_SET)

        # Registers that may occur during reading of Vif tags/codes
        vif_state = PS2.VifState()
        gs_state = PS2.GsState()

        mesh_verts = []
        mesh_normals = []
        mesh_uvs = []
        mesh_faces = []
        mesh_colours = []
        mesh_vert_count = 0

        # Follows this pattern:
        # 1 DMA tag
        # multiple:
        # - VIF tag/code
        #  - GIF tag
        # - VIF tag
        #   - Mesh data

        print(f"Reading car dmaTAG {file.tell()}")
        # Read DMATag for this section
        dma_start = file.tell()
        dma_tag = PS2.decode_DMATag(file)
        tag_id = PS2.decode_DMATagID_source(dma_tag)
        print(dma_tag)
        print(tag_id)
        dma_byte_length = dma_tag['qwordCount'] * 16 + 16
        # For meshes there is VIF tags in the data region, so jump back
        file.seek(-8, os.SEEK_CUR)
        processed_size = 0
        vif_processed_bytes = io.BytesIO(bytes())
        extracted_data = False
        data_count = 0
        gif_count = 0
        while file.tell() < dma_start + dma_byte_length:
            print(f"Data [{data_count}]: @ {file.tell()} out of {dma_start + dma_byte_length}")
            # Read viftag,  reading data until end of the read VIF tag
            # Updates the state if any cmds do that
            expected_length_in_packets, expected_length_out, vif_expanded_data = PS2.VifHandle(file, vif_state)
            # print(f"VIF: in:{expected_length_in_packets}, out:{expected_length_out}, {vif_expanded_data}")
            # print(vars(vif_state))
            if vif_state.ExecAddr != 0:
                # Call to run a subroutine/program on the VU1 microprogram
                if vif_state.ExecAddr == 32 or vif_state.ExecAddr == 80:
                    # Think this is process model data funct/subroutine call
                    # exec == 32 is for cars
                    # exec == 80 is also for cars, could be colour1 (32) vs colour2 (80)
                    vif_processed_bytes.seek(0, os.SEEK_SET)
                    vif_processed_bytes.seek(0, os.SEEK_SET)
                    verts, normals, uvs, faces, colours, count = CarMesh.parse_mesh(vif_processed_bytes, processed_size, gs_state, vif_state.ExecAddr, mesh_vert_count, hg3)
                    mesh_verts += verts
                    mesh_normals += normals
                    mesh_uvs += uvs
                    mesh_faces += faces
                    mesh_colours += colours
                    mesh_vert_count += len(verts)
                    gif_count += count
                    extracted_data = True
                    data_count += 1
                    # Reset length of data back to 0, as we have processed this section
                    vif_processed_bytes.seek(0, os.SEEK_SET)
                    vif_processed_bytes.truncate(0)
                    processed_size = 0
                    # Clear call after processing
                    vif_state.ExecAddr = 0

                    # Check if we have read all data for this
                    # if gif_count < count:
                    #     # Check we are at the end of this dma tag, before trying
                    #     # to get more data. And that the dma tag was not an end
                    #     if file.tell() + 16 > dma_start + dma_byte_length:
                    #         print(f"Checking for possible more data (more DMAs) @ {file.tell()}")
                    #         if not tag_id['tag_end']:
                    #             # Skip past any padding, as should be aligned
                    #             while file.tell() % 16 != 0:
                    #                 file.seek(1, os.SEEK_CUR)
                    #             print(f"Decided to process another dma tag @ {file.tell()}")
                    #
                    #             # try read next tag, almost like restarting
                    #             dma_start = file.tell()
                    #             dma_tag = PS2.decode_DMATag(file)
                    #             tag_id = PS2.decode_DMATagID_source(dma_tag)
                    #             print(dma_tag)
                    #             print(tag_id)
                    #             dma_byte_length = dma_tag['qwordCount'] * 16 + 16
                    #             # For meshes there is VIF tags in the data region, so jump back
                    #             file.seek(-8, os.SEEK_CUR)
                    #             print(f"Restarting readCourseChunk after more DMAs @ {file.tell()}")
                else:
                    print(f"Found new ExecAddr call: @{file.tell()} value: {vif_state.ExecAddr}")
                    exit(100)

            if vif_expanded_data is not None:
                print(f"Should get {expected_length_out} from {(expected_length_in_packets - 1) * 4}")
                # Copy the expanded data into another stream to process as one
                processed_size += expected_length_out
                vif_processed_bytes.write(vif_expanded_data.read(expected_length_out))
            print(f"Still reading? @ {file.tell()} out of {dma_start + dma_byte_length}")
        if not extracted_data:
            # Extract data at this point as it was missed somehow
            print("No data")

        if len(mesh_verts) == 0:
            return None
        # returns [CarMesh]
        return CarMesh(len(mesh_verts), mesh_verts, mesh_normals, mesh_uvs, mesh_faces, mesh_colours)

    @staticmethod
    def parse_mesh(file, length, gs_state, exec_type, vert_count_offset, hg3=False):
        verts = []
        normals = []
        uvs = []
        faces = []
        colours = []

        count = 0  # Number of GIF tags read
        # Read GIFTag
        while file.tell() < length:
            gif_tag = int.from_bytes(file.read(16), 'little')

            nloop = PS2.gifGetNLoop(gif_tag)
            eop = PS2.gifGetEop(gif_tag)
            pre = PS2.gifGetPrimEnable(gif_tag)
            prim = PS2.parsePRIM(PS2.gifGetPrim(gif_tag))
            mode = PS2.gifGetMode(gif_tag)
            nreg = PS2.gifGetNReg(gif_tag)
            descriptors = PS2.gifGetRegisterDescriptors(gif_tag)
            print(descriptors)

            registers = None
            if mode == PS2.GIF_MODE_PACKED:
                registers = []
                for i in range(0, 16):
                    registers.append(PS2.gifDecodePacked(file, gif_tag, i, descriptors[i], gs_state))
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
                        # Has extra at start unknown data
                        U.readXYZ(file)
                        U.readFloat(file)
                    for loop in range(nloop):
                        # X, Y, Z, W
                        vx, vy, vz = U.readXYZ(file)
                        vw = U.readFloat(file)

                        if hg3 and exec_type == 80:
                            nx, ny, nz, nw = 0, 0, 0, 0
                        else:
                            # Unsure on what these are, but they are not normals
                            nx, ny, nz = U.readXYZ(file)
                            nw = U.readFloat(file)

                        # This is the colour for each vert (possibly used when recolouring the car)
                        cr, cg, cb = U.readXYZ(file)
                        cw = U.readFloat(file)

                        # Texture coords
                        tu, tv, unkw2 = U.readXYZ(file)
                        tw = U.readFloat(file)

                        c = (cr, cg, cb, 255)  # Convert to RGBA
                        verts.append((offsetX + vx, offsetY + vy, offsetZ + vz))
                        colours.append(c)
                        normals.append((nx, ny, nz))
                        uvs.append((tu, 1 - tv, tw))

                    faces = CarMesh.create_face_list(nloop, 1, vert_count_offset=vert_count_offset)
                    print(f"Got to after verts {file.tell()}")
                else:
                    for loop in range(nloop):
                        for reg in range(nreg):
                            print(f"GsState change packet loop [{loop}] reg [{reg}]")
                            PS2.gifHandlePacked(file, gif_tag, reg, descriptors[reg], gs_state)

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

        return verts, normals, uvs, faces, colours, count

    def write_mesh_to_dbg(self, fout, start_index=0, material=None):
        self.write_mesh_to_obj(fout)
        fout.write("#" + str(len(self.meshColours)) + " colours R/G/B/A\n")
        for i in range(0, len(self.meshFaces)):
            cr = '{:d}'.format(math.trunc(self.meshColours[i][0]))
            cg = '{:d}'.format(math.trunc(self.meshColours[i][1]))
            cb = '{:d}'.format(math.trunc(self.meshColours[i][2]))
            ca = '{:d}'.format(math.trunc(self.meshColours[i][3]))
            
            fout.write(f"c {cr} {cg} {cb} {ca}\n")
        
        return len(self.meshVerts)

    def write_mesh_to_obj(self, fout, start_index = 0, material=None):
        fout.write(f"usemtl {material}\n")
        fout.write("s off\n")
        # Write vertices
        for i in range(0, len(self.meshVerts)):
            vx = '{:.20f}'.format(self.meshVerts[i][0])
            vy = '{:.20f}'.format(self.meshVerts[i][1])
            vz = '{:.20f}'.format(self.meshVerts[i][2])
            fout.write("v " + vx + " " + vy + " " + vz + "\n")
        fout.write("#" + str(len(self.meshVerts)) + " vertices\n")
            
        # Write normals
        for i in range(0, len(self.meshNormals)):
            nx = '{:.20f}'.format(self.meshNormals[i][0])
            ny = '{:.20f}'.format(self.meshNormals[i][1])
            nz = '{:.20f}'.format(self.meshNormals[i][2])
            fout.write("vn " + nx + " " + ny + " " + nz + "\n")
        fout.write("#" + str(len(self.meshNormals)) + " vertex normals\n")
        
        # Write texture coordinates (uv)
        for i in range(0, len(self.meshUvs)):
            tu = '{:.20f}'.format(self.meshUvs[i][0])
            tv = '{:.20f}'.format(self.meshUvs[i][1])
            fout.write("vt " + tu + " " + tv + "\n")
        fout.write("#" + str(len(self.meshUvs)) + " texture vertices\n")
        
        # Write mesh face order/list
        for i in range(0, len(self.meshFaces)):
            fx = self.meshFaces[i][0] + start_index
            fy = self.meshFaces[i][1] + start_index
            fz = self.meshFaces[i][2] + start_index
            
            fout.write(f"f {fx}/{fx}/{fx} {fy}/{fy}/{fy} {fz}/{fz}/{fz}\n")
        fout.write("#" + str(len(self.meshFaces)) + " faces\n")
    
        return len(self.meshVerts)

    def write_mesh_to_comb(self, fout, start_index=0, material=None):
        fout.write(f"vertex_count {len(self.meshVerts)}\n")
        fout.write(f"face_count {len(self.meshFaces)}\n")
        fout.write(f"texture {material}\n")
        fout.write("end_header\n")

        # Write verticies, colours, normals
        for i in range(0, len(self.meshVerts)):
            vx = '{:.20f}'.format(self.meshVerts[i][0])
            vy = '{:.20f}'.format(self.meshVerts[i][1])
            vz = '{:.20f}'.format(self.meshVerts[i][2])

            cr = '{:d}'.format(math.trunc(self.meshColours[i][0]))
            cg = '{:d}'.format(math.trunc(self.meshColours[i][1]))
            cb = '{:d}'.format(math.trunc(self.meshColours[i][2]))
            ca = '{:d}'.format(math.trunc(self.meshColours[i][3]))

            nx = '{:.20f}'.format(self.meshNormals[i][0])
            ny = '{:.20f}'.format(self.meshNormals[i][1])
            nz = '{:.20f}'.format(self.meshNormals[i][2])

            tu = '{:.10f}'.format(self.meshUvs[i][0])
            tv = '{:.10f}'.format(self.meshUvs[i][1])

            fout.write(f"{vx} {vy} {vz} {nx} {ny} {nz} {cr} {cg} {cb} {ca} {tu} {tv}\n")
        
        # Write mesh face order/list
        for i in range(0, len(self.meshFaces)):
            fx = self.meshFaces[i][0] - 1 + start_index
            fy = self.meshFaces[i][1] - 1 + start_index
            fz = self.meshFaces[i][2] - 1 + start_index
            
            fout.write(f"4 {fx} {fy} {fz}\n")
        
        return len(self.meshVerts)


    def write_mesh_to_ply(self, fout, start_index = 0):
        # Write header
        fout.write("ply\n")
        fout.write("format ascii 1.0\n")
        fout.write(f"element vertex {len(self.meshVerts)}\n")
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
        fout.write(f"element face {len(self.meshFaces)}\n")
        fout.write("property list uint8 int vertex_index\n")
        #fout.write(f"element texture {len(self.mesh_uvs)}\n")
        #fout.write("property list uint8 float texcoord\n")
        fout.write("end_header\n")

        # Write verticies, colours, normals
        for i in range(0, len(self.meshVerts)):
            vx = '{:.20f}'.format(self.meshVerts[i][0])
            vy = '{:.20f}'.format(self.meshVerts[i][1])
            vz = '{:.20f}'.format(self.meshVerts[i][2])

            cr = '{:d}'.format(math.trunc(self.meshColours[i][0]))
            cg = '{:d}'.format(math.trunc(self.meshColours[i][1]))
            cb = '{:d}'.format(math.trunc(self.meshColours[i][2]))
            ca = '{:d}'.format(math.trunc(self.meshColours[i][3]))

            nx = '{:.20f}'.format(self.meshNormals[i][0])
            ny = '{:.20f}'.format(self.meshNormals[i][1])
            nz = '{:.20f}'.format(self.meshNormals[i][2])

            tu = '{:.10f}'.format(self.meshUvs[i][0])
            tv = '{:.10f}'.format(self.meshUvs[i][1])

            fout.write(f"{vx} {vy} {vz} {nx} {ny} {nz} {cr} {cg} {cb} {ca} {tu} {tv}\n")
        
        # Write mesh face order/list
        for i in range(0, len(self.meshFaces)):
            fx = self.meshFaces[i][0] - 1 + start_index
            fy = self.meshFaces[i][1] - 1 + start_index
            fz = self.meshFaces[i][2] - 1 + start_index
            
            fout.write(f"4 {fx} {fy} {fz}\n")

        return len(self.meshVerts)
        
