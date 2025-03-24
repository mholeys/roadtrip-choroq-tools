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
from choroq.amesh import AMesh
from choroq.car import CarModel, CarMesh
# from choroq.course import Course
from choroq.texture import Texture
import choroq.read_utils as U

class HG3CarModel(CarModel):

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
        while o != size and o != 0 and (len(sub_file_offsets) == 0 or (file.tell() < offset + sub_file_offsets[0])):
            o = U.readLong(file)
            if o == 0:
                break
            sub_file_offsets.append(o)
        return sub_file_offsets

    @staticmethod
    def from_file(file, offset, size):
        sub_file_offsets = HG3CarModel._parse_offsets(file, offset, size)
        meshes = []
        textures = []
        # for offsetIndex,o in enumerate(sub_file_offsets):
        #     if (o == size or o == 0):
        #         # At end of file
        #         break
        #     if offsetIndex < len(sub_file_offsets)-1:
        #         currentOffsetMax = sub_file_offsets[offsetIndex+1]
        #     else:
        #         currentOffsetMax = size
        #     file.seek(offset+o, os.SEEK_SET)
        #     # print(f"Reading model from {file.tell()}")
        #     magic = U.readLong(file)
        #     file.seek(offset+o, os.SEEK_SET)
        #     # Check to prevent overrun
        #     if offsetIndex < len(sub_file_offsets)-1:
        #         end = sub_file_offsets[offsetIndex+1]
        #     else:
        #         # This should not be a problem, as the last is usually the end of the file anyway
        #         end = size
        #
        #     U.BreadLong(file)
        #     U.BreadLong(file)
        #     textureCheck = U.readLong(file) #  This should be 00 at the end for textures (guesswork)
        #     file.seek(offset+o, os.SEEK_SET)
        #
        #     print(f"TextureCheck: pos: {offsetIndex}? {offsetIndex == len(sub_file_offsets)-2} and {textureCheck} {textureCheck & 0xFF000000 == 0}")
        #     if offsetIndex > 0 and offsetIndex == len(sub_file_offsets)-2 and textureCheck & 0xFF000000 == 0:
        #         textures += Texture.allFromFile(file, offset+o, end)
        #     elif magic & 0x10120006 >= 0x10120006 or magic & 0x10400006 >= 0x10400006:
        #         # File is possibly a texture
        #         # print(f"Parsing texture @ {offset+o} {magic & 0x10120006} {magic & 0x10400006}")
        #         # textures.append(Texture._fromFile(file, offset+o))
        #         textures += Texture.allFromFile(file, offset+o, end)
        #     elif magic == 0x0000050:
        #         # print(f"Parsing meshes found 0x50 @ {offset+o}")
        #         meshes += CarMesh.from_file(file, offset + o + 0x50)
        #     elif magic == 5: # CHOROQ HG 3
        #         # Has offset table different than usual
        #         # print(f"Parsing HG 3 offset found {offset+o}")
        #         meshes += HG3CarMesh.from_file(file, offset + o)
        #
        #     else:
        #         # print(f"Parsing meshes @ {offset+o}")
        #         #meshes += CarMesh._fromFile(file, offset+o+16)
        #         meshes += HG3CarMesh.from_file(file, offset + o)

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
            meshFlagNoTableTest = U.readLong(file)
            file.seek(offset, os.SEEK_SET)

            if meshFlagNoTableTest == 0x01000101:  # Checks for setting Cycle
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
        hg3Offsets = []
        file.seek(12, os.SEEK_CUR)
        hg3Offsets.append(U.readLong(file)) # usually 0x50 = 80
        file.seek(12, os.SEEK_CUR)
        hg3Offsets.append(U.readLong(file)) 
        file.seek(12, os.SEEK_CUR)
        hg3Offsets.append(U.readLong(file))
        file.seek(12, os.SEEK_CUR)
        hg3Offsets.append(U.readLong(file))
        file.seek(12, os.SEEK_CUR)
        hg3Offsets.append(U.readLong(file))
        # Remove all 0 values
        try:
            hg3Offsets.remove(0)
            hg3Offsets.remove(0)
            hg3Offsets.remove(0)
            hg3Offsets.remove(0)
            hg3Offsets.remove(0)
        except:
            pass
        return hg3Offsets

    @staticmethod
    def _parseHeader(file):
        unkw0 = U.readLong(file)
        nullF0 = U.readLong(file)
        meshStartFlag = U.readLong(file)
        if meshStartFlag != 0x01000101:
            print(f"Mesh's start flag is different {meshStartFlag} from usual, continuing @{file.tell()}")
        return unkw0, nullF0, meshStartFlag

    @staticmethod
    def from_file(file, offset, scale=1):
        # Check to see if there is a offset table, or just header
        file.seek(offset+8, os.SEEK_SET)
        meshFlagNoTableTest = U.readLong(file) 
        file.seek(offset, os.SEEK_SET)

        if meshFlagNoTableTest == 0x01000101:
            print(f"Skipping offset table for Car Mesh, as there is a mesh flag")
            offsets = [0]
        else:
            offsets = HG3CarMesh._parse_offsets(file, offset)
            
        meshes = []
        for o in offsets:
            file.seek(o + offset, os.SEEK_SET)
            # print(f"Reading mesh from {file.tell()}")
            header = HG3CarMesh._parseHeader(file)
            # Read mesh
            meshFlag  = U.readLong(file)
            # print(hex(meshFlag))

            meshVerts = []
            meshNormals = []
            meshUvs = []
            meshFaces = []
            meshColours = []
            meshVertCount = 0

            # Read chunk of verticies
            while meshFlag & 0xFF00FFFF == 0x68008000:
                verts = [] 
                uvs = []
                normals = []
                faces = []
                colours = []
                vertCount = U.readByte(file)
                unkw1 = U.readByte(file)
                zeroF1 = U.readShort(file)

                # Skip 12 bytes as we dont know what they are used for
                file.seek(12, os.SEEK_CUR)
                # Think this determines the structure of the mesh
                meshFormatVar = U.readLong(file)
                # print(hex(meshFormatVar))
                U.BreadLong(file)

                if meshFormatVar & 0xFF00FF00 == 0x3000C000:
                    # print("using shorter mesh")
                    pass

                for x in range(0, vertCount):
                    if meshFormatVar & 0xFF00FF00 == 0x3100C000:
                        # Mesh is normal
                        vx, vy, vz = U.readXYZ(file)
                        nx, ny, nz = U.readXYZ(file)
                        cr, cg, cb = U.readXYZ(file)
                        tu, tv, unkw2 = U.readXYZ(file)


                    elif meshFormatVar & 0xFF00FF00 == 0x3000C000:
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
                unkw3 = U.BreadShort(file) # 0400
                unkw4 = U.BreadShort(file) # 0015
                # Add faces
                faces = HG3CarMesh.create_face_list(vertCount)
                for i in range(0, len(faces)):
                    vertices = faces[i]
                    meshFaces.append((vertices[0] + meshVertCount, vertices[1] + meshVertCount, vertices[2] + meshVertCount))
                
                meshVertCount += len(verts)
                meshVerts += verts
                meshUvs += uvs
                meshColours += colours
                meshNormals += normals
                # See if there are more verticies we need to read
                meshFlag = U.readLong(file)
            if (meshVertCount > 0):
                meshes.append(HG3CarMesh(meshVertCount, meshVerts, meshNormals, meshUvs, meshFaces, meshColours))
        return meshes

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
        # Write verticies
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
        
        fout.write(f"usemtl {material}\n")
        fout.write("s off\n")
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
        
