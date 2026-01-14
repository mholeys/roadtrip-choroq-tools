# Following information is incorrect, in development/adaptation for HG 3
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
# There are two or more other values in the header, yet to be decoded TODO:
# 16 is the size of header, and so the first offset is always 16
# [Mesh]
# First long seems to be a value of XX XX 00 10 where XX are unknown meaning
# Second long is always null/[00000000] probably to match up with other file headers like the textures
# Third long is always [01 01 00 01] possibly a version or bitMask
# There is then a long of [00 80 01 6C] (MeshFlag) which is used to determine if there is more data 
# [MeshData]
# After these starts the actual mesh data for the models
# First of which is a long with the value of [06 80 00 00]
# 
# Next Byte contains the number of verticies
# Followed by 128/0x80 or sometimes 64/0x40
# Followed by 0000
# e.g:
# [AA][BB][CCCC]
#  AA = vertex count
#  BB = 0x80/0x40
#  CC = 0x0000
# 
# [Unknown]
# Skip 16 bytes at this point, data format unknown
# 
# After these the vertex information follows in the format below
# This is format is repeated for the number of verticies read in previously
# The index of vertex is based on where it was read from the first being 0
# This is used to build the faces of the mesh
#
# [Vertex/Verticies and data format]
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
#
# After the vertex data follows four bytes (Long/2Shorts) that contain unknown values
# This is then repeated as long  the MeshFlag is the expected value
#
# [Face format]
# The faces are not actually stored in the file, and are statically calculated


import io
import os
import math
from choroq.egame.amesh import AMesh
from choroq.egame.car import CarModel, CarMesh
# from choroq.course import Course
from choroq.egame.texture import Texture
import choroq.egame.read_utils as U


class HG3CarModel(CarModel):

    def __init__(self, name, meshes=[], textures=[]):
        self.name = name
        self.meshes = meshes
        self.textures = textures

    @staticmethod
    def _parse_offsets(file, offset, size):
        file.seek(offset, os.SEEK_SET)
        sub_file_offsets = []
        o = U.readLong(file)
        sub_file_offsets.append(o)
        while o != size and o != 0 and (len(sub_file_offsets) == 0 or (file.tell() < offset + sub_file_offsets[0])):
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
            mesh = HG3CarMesh.from_file(file, offset + o)
            # if len(mesh) > 0:
            #     meshes += mesh
            meshes.append(mesh)

        texture, last = Texture.read_texture(file, offset + texture_offset)
        textures.append(texture)
        while not last:
            texture, last = Texture.read_texture(file, file.tell())
            textures.append(texture)

        return HG3CarModel("", meshes, textures)

    @staticmethod
    def from_file(file, offset, size):
        sub_file_offsets = HG3CarModel._parse_offsets(file, offset, size)
        meshes = []
        textures = []

        print(f"Reading car model (full) from {file.tell()}")
        texture_offset = sub_file_offsets[-2]
        eof_offset = sub_file_offsets[-1]
        sub_file_offsets = sub_file_offsets[:-2]

        meshes = []
        textures = []

        for o in sub_file_offsets:
            # TODO: this check needs to be within a different part, probably for each mesh part
            file.seek(offset+o, os.SEEK_SET)
            test = U.readLong(file)
            file.seek(-4, os.SEEK_CUR)

            # Check if this is a DMA Cnt Tag, so use as is, if not handle variation
            if test & 0xFF000000 != 0x10000000:
                if test < 10:
                    # This is a little block of unknown data, this value
                    # is number of qwords, skip for now
                    print(f"Skipping unknown block of qwords HG3 {file.tell()}")
                    file.seek(test * 16, os.SEEK_CUR)
                    print(f"Skipping unknown block of qwords HG3 {file.tell()}")

            # TODO: this check might need to be here or another function like the check above
            # Now check to see if there is a sub mesh offset table, or if it is just as is
            file.seek(offset + 8, os.SEEK_SET)
            mesh_flag_no_table_test = U.readLong(file)
            file.seek(offset, os.SEEK_SET)

            if mesh_flag_no_table_test == 0x01000101:  # Checks for setting Cycle
                print(f"Skipping offset table for Car Mesh, as there is a mesh flag")
                mesh = CarMesh.read_car_part(file, offset + o)
                meshes.append(mesh)
            else:
                mesh = CarMesh.from_file(file, offset + o)

            if len(mesh) > 0:
                meshes += mesh

        texture, last = Texture.read_texture(file, offset + texture_offset)
        textures.append(texture)
        while not last:
            texture, last = Texture.read_texture(file, file.tell())
            textures.append(texture)

        return HG3CarModel("", meshes, textures)


class HG3CarMesh(CarMesh):

    def __init__(self, mesh_vert_count, mesh_verts, mesh_normals, mesh_uvs, mesh_faces, mesh_colours):
        super().__init__(mesh_vert_count, mesh_verts, mesh_normals, mesh_uvs, mesh_faces, mesh_colours)
        self.mesh_vert_count = mesh_vert_count
        self.mesh_verts = mesh_verts
        self.mesh_normals = mesh_normals
        self.mesh_uvs = mesh_uvs
        self.mesh_faces = mesh_faces
        self.mesh_colours = mesh_colours

    @staticmethod
    def _parse_offsets(file, offset):
        file.seek(offset, os.SEEK_SET)
        entry_count = U.readLong(file)
        file.seek(4, os.SEEK_CUR)
        hg3_offsets = []
        hg3_gifs = []
        for i in range(entry_count):
            hg3_offsets.append(U.readLong(file))
            hg3_gifs.append(U.readLong(file))
            file.seek(8, os.SEEK_CUR)
        return hg3_offsets, hg3_gifs

    @staticmethod
    def _parse_header(file):
        unkw0 = U.readLong(file)
        null_f0 = U.readLong(file)
        mesh_start_flag = U.readLong(file)
        if mesh_start_flag != 0x01000101:
            print(f"Mesh's start flag is different {mesh_start_flag} from usual, continuing @{file.tell()}")
        return unkw0, null_f0, mesh_start_flag

    @staticmethod
    def from_file(file, offset, scale=1):
        # Check to see if there is an offset table, or just header
        file.seek(offset+8, os.SEEK_SET)
        mesh_flag_no_table_test = U.readLong(file)
        file.seek(offset, os.SEEK_SET)
        gif_counts = []

        if mesh_flag_no_table_test == 0x01000101:
            print(f"Skipping offset table for Car Mesh, as there is a mesh flag")
            offsets = [0]
            gif_counts = [65536]
        else:
            offsets, gif_counts = HG3CarMesh._parse_offsets(file, offset)
            
        meshes = []
        for o in offsets:
            file.seek(o + offset, os.SEEK_SET)
            # print(f"Reading mesh from {file.tell()}")
            header = HG3CarMesh._parse_header(file)
            # Read mesh
            mesh_flag = U.readLong(file)
            # print(hex(mesh_flag))

            mesh_verts = []
            mesh_normals = []
            mesh_uvs = []
            mesh_faces = []
            mesh_colours = []
            mesh_vert_count = 0

            # Read chunk of vertices
            while mesh_flag & 0xFF00FFFF == 0x68008000:
                verts = [] 
                uvs = []
                normals = []
                faces = []
                colours = []
                vert_count = U.readByte(file)
                unkw1 = U.readByte(file)
                zero_f1 = U.readShort(file)

                # Skip 12 bytes as we dont know what they are used for
                file.seek(12, os.SEEK_CUR)
                # Think this determines the structure of the mesh
                mesh_format_var = U.readLong(file)
                # print(hex(mesh_format_var))
                U.BreadLong(file)
                cr, cg, cb = 0, 0, 0
                vx, vy, vz, nx, ny, nz = 0, 0, 0, 0, 0, 0
                tu, tv = 0, 0
                if mesh_format_var & 0xFF00FF00 == 0x3000C000:
                    # print("using shorter mesh")
                    pass

                for x in range(0, vert_count):
                    if mesh_format_var & 0xFF00FF00 == 0x3100C000:
                        # Mesh is normal
                        vx, vy, vz = U.readXYZ(file)
                        nx, ny, nz = U.readXYZ(file)
                        cr, cg, cb = U.readXYZ(file)
                        tu, tv, unkw2 = U.readXYZ(file)

                    elif mesh_format_var & 0xFF00FF00 == 0x3000C000:
                        # Mesh is shorter, no normals I think
                        vx, vy, vz = U.readXYZ(file)
                        nx, ny, nz = (0,0,0)
                        cr, cg, cb = U.readXYZ(file)
                        tu, tv, unkw2 = U.readXYZ(file)
                    
                    c = (cr, cg, cb, 255) # Convert to RGBA
                    verts.append((vx * -scale, vy * scale, vz * scale))
                    colours.append(c)
                    normals.append((nx, ny, nz))
                    uvs.append((tu, 1-tv, 0))
                unkw3 = U.BreadShort(file)  # 0400
                unkw4 = U.BreadShort(file)  # 0015
                # Add faces
                faces = HG3CarMesh.create_face_list(vert_count)
                for i in range(0, len(faces)):
                    vertices = faces[i]
                    mesh_faces.append((vertices[0] + mesh_vert_count,
                                       vertices[1] + mesh_vert_count,
                                       vertices[2] + mesh_vert_count))
                
                mesh_vert_count += len(verts)
                mesh_verts += verts
                mesh_uvs += uvs
                mesh_colours += colours
                mesh_normals += normals
                # See if there are more vertices we need to read
                mesh_flag = U.readLong(file)
            if mesh_vert_count > 0:
                meshes.append(HG3CarMesh(mesh_vert_count, mesh_verts, mesh_normals, mesh_uvs, mesh_faces, mesh_colours))
        return meshes

    def write_mesh_to_dbg(self, fout, start_index=0, material=None):
        self.write_mesh_to_obj(fout)
        fout.write("#" + str(len(self.mesh_colours)) + " colours R/G/B/A\n")
        for i in range(0, len(self.mesh_faces)):
            cr = '{:d}'.format(math.trunc(self.mesh_colours[i][0]))
            cg = '{:d}'.format(math.trunc(self.mesh_colours[i][1]))
            cb = '{:d}'.format(math.trunc(self.mesh_colours[i][2]))
            ca = '{:d}'.format(math.trunc(self.mesh_colours[i][3]))
            
            fout.write(f"c {cr} {cg} {cb} {ca}\n")
        
        return len(self.mesh_verts)

    def write_mesh_to_obj(self, fout, start_index=0, material=None, with_colours=False):
        # Write vertices
        for i in range(0, len(self.mesh_verts)):
            vx = '{:.20f}'.format(self.mesh_verts[i][0])
            vy = '{:.20f}'.format(self.mesh_verts[i][1])
            vz = '{:.20f}'.format(self.mesh_verts[i][2])
            if with_colours:
                # Some programs support additional data, e.g colors after x/y/z
                # the following section can be used to export with colors (blender supports first set)
                r = '{:.20f}'.format(self.mesh_colours[i][0] / 255.0)
                g = '{:.20f}'.format(self.mesh_colours[i][1] / 255.0)
                b = '{:.20f}'.format(self.mesh_colours[i][2] / 255.0)
                fout.write(f"v {vx} {vy} {vz} {r} {g} {b}\n")
            else:
                fout.write(f"v {vx} {vy} {vz}\n")
        fout.write("#" + str(len(self.mesh_verts)) + " vertices\n")
            
        # Write normals
        for i in range(0, len(self.mesh_normals)):
            nx = '{:.20f}'.format(self.mesh_normals[i][0])
            ny = '{:.20f}'.format(self.mesh_normals[i][1])
            nz = '{:.20f}'.format(self.mesh_normals[i][2])
            fout.write("vn " + nx + " " + ny + " " + nz + "\n")
        fout.write("#" + str(len(self.mesh_normals)) + " vertex normals\n")
        
        # Write texture coordinates (uv)
        for i in range(0, len(self.mesh_uvs)):
            tu = '{:.20f}'.format(self.mesh_uvs[i][0])
            tv = '{:.20f}'.format(self.mesh_uvs[i][1])
            fout.write("vt " + tu + " " + tv + "\n")
        fout.write("#" + str(len(self.mesh_uvs)) + " texture vertices\n")
        
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
        fout.write(f"texture {material}\n")
        fout.write("end_header\n")

        # Write vertices, colours, normals
        for i in range(0, len(self.mesh_verts)):
            vx = '{:.20f}'.format(self.mesh_verts[i][0])
            vy = '{:.20f}'.format(self.mesh_verts[i][1])
            vz = '{:.20f}'.format(self.mesh_verts[i][2])

            cr = '{:d}'.format(math.trunc(self.mesh_colours[i][0]))
            cg = '{:d}'.format(math.trunc(self.mesh_colours[i][1]))
            cb = '{:d}'.format(math.trunc(self.mesh_colours[i][2]))
            ca = '{:d}'.format(math.trunc(self.mesh_colours[i][3]))

            nx = '{:.20f}'.format(self.mesh_normals[i][0])
            ny = '{:.20f}'.format(self.mesh_normals[i][1])
            nz = '{:.20f}'.format(self.mesh_normals[i][2])

            tu = '{:.10f}'.format(self.mesh_uvs[i][0])
            tv = '{:.10f}'.format(self.mesh_uvs[i][1])

            fout.write(f"{vx} {vy} {vz} {nx} {ny} {nz} {cr} {cg} {cb} {ca} {tu} {tv}\n")
        
        # Write mesh face order/list
        for i in range(0, len(self.mesh_faces)):
            fx = self.mesh_faces[i][0] - 1 + start_index
            fy = self.mesh_faces[i][1] - 1 + start_index
            fz = self.mesh_faces[i][2] - 1 + start_index
            
            fout.write(f"4 {fx} {fy} {fz}\n")
        
        return len(self.mesh_verts)

    def write_mesh_to_ply(self, fout, start_index=0):
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
        fout.write("property uchar red\n")
        fout.write("property uchar green\n")
        fout.write("property uchar blue\n")
        fout.write("property uchar alpha\n")
        fout.write("property float s\n")
        fout.write("property float t\n")
        fout.write(f"element face {len(self.mesh_faces)}\n")
        fout.write("property list uint8 int vertex_index\n")
        # fout.write(f"element texture {len(self.mesh_uvs)}\n")
        # fout.write("property list uint8 float texcoord\n")
        fout.write("end_header\n")

        # Write vertices, colours, normals
        for i in range(0, len(self.mesh_verts)):
            vx = '{:.20f}'.format(self.mesh_verts[i][0])
            vy = '{:.20f}'.format(self.mesh_verts[i][1])
            vz = '{:.20f}'.format(self.mesh_verts[i][2])

            cr = '{:d}'.format(math.trunc(self.mesh_colours[i][0]))
            cg = '{:d}'.format(math.trunc(self.mesh_colours[i][1]))
            cb = '{:d}'.format(math.trunc(self.mesh_colours[i][2]))
            ca = '{:d}'.format(math.trunc(self.mesh_colours[i][3]))

            nx = '{:.20f}'.format(self.mesh_normals[i][0])
            ny = '{:.20f}'.format(self.mesh_normals[i][1])
            nz = '{:.20f}'.format(self.mesh_normals[i][2])

            tu = '{:.10f}'.format(self.mesh_uvs[i][0])
            tv = '{:.10f}'.format(self.mesh_uvs[i][1])

            fout.write(f"{vx} {vy} {vz} {nx} {ny} {nz} {cr} {cg} {cb} {ca} {tu} {tv}\n")
        
        # Write mesh face order/list
        for i in range(0, len(self.mesh_faces)):
            fx = self.mesh_faces[i][0] - 1 + start_index
            fy = self.mesh_faces[i][1] - 1 + start_index
            fz = self.mesh_faces[i][2] - 1 + start_index
            
            fout.write(f"4 {fx} {fy} {fz}\n")

        return len(self.mesh_verts)
        
