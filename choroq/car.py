
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
from choroq.texture import Texture
import choroq.read_utils as U

class CarModel:

    def __init__(self, name, meshes = [], textures = []):
        self.name = name
        self.meshes = meshes
        self.textures = textures

    @staticmethod
    def _parseOffsets(file, offset, size):
        file.seek(offset, os.SEEK_SET)
        subFileOffsets = []
        o = 1
        while o != size and  o != 0:
            o = U.readLong(file)
            subFileOffsets.append(o)
        return subFileOffsets

    @staticmethod
    def fromFile(file, offset, size):
        subFileOffsets = CarModel._parseOffsets(file, offset, size)
        meshes = []
        textures = []
        for o in subFileOffsets:
            if (o == size or o == 0):
                # At end of file
                break
            file.seek(offset+o, os.SEEK_SET)
            # print(f"Reading model from {file.tell()}")
            magic = U.readLong(file)
            file.seek(offset+o, os.SEEK_SET)
            if magic & 0x10120006 >= 0x10120006 or magic & 0x10400006 >= 0x10400006:
                # File is possibly a texture
                # print(f"Parsing texture @ {offset+o} {magic & 0x10120006} {magic & 0x10400006}")
                textures.append(Texture._fromFile(file, offset+o))
            elif magic == 0x0000050:
                # print(f"Parsing meshes found 0x50 @ {offset+o}")
                meshes += CarMesh._fromFile(file, offset+o+0x50)
            else:
                # print(f"Parsing meshes @ {offset+o}")
                meshes += CarMesh._fromFile(file, offset+o)
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
    def _parseOffsets(file, offset):
        file.seek(offset, os.SEEK_SET)
        offset1 = U.readLong(file)
        offset2 = U.readLong(file)
        return 16, offset1, offset2

    @staticmethod
    def _parseHeader(file):
        unkw0 = U.readLong(file)
        nullF0 = U.readLong(file)
        meshStartFlag = U.readLong(file)
        if meshStartFlag != 0x01000101:
            print(f"Mesh's start flag is different {meshStartFlag} from usual, continuing @{file.tell()}")
        return unkw0, nullF0, meshStartFlag

    @staticmethod
    def _fromFile(file, offset, scale=1):
        # Check to see if there is a offset table, or just header
        file.seek(offset+8, os.SEEK_SET)
        meshFlagNoTableTest = U.readLong(file) 
        file.seek(offset, os.SEEK_SET)
        if meshFlagNoTableTest == 0x01000101:
            print(f"Skipping offset table for Car Mesh, as there is a mesh flag")
            offsets = [0]
        else:
            offsets = CarMesh._parseOffsets(file, offset)
        meshes = []
        for o in offsets:
            file.seek(o + offset, os.SEEK_SET)
            print(f"Reading mesh from {file.tell()}")
            header = CarMesh._parseHeader(file)
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
            while meshFlag == 0x6c018000 or meshFlag == 0x68808000:
                verts = [] 
                uvs = []
                normals = []
                faces = []
                colours = []
                vertCount = U.readByte(file)
                unkw1 = U.readByte(file)
                zeroF1 = U.readShort(file)
                # Skip 16 bytes as we dont know what they are used for
                file.seek(0x10, os.SEEK_CUR)

                for x in range(0, vertCount):
                    vx, vy, vz = U.readXYZ(file)
                    nx, ny, nz = U.readXYZ(file)
                    cr, cg, cb = U.readXYZ(file)
                    tu, tv, unkw2 = U.readXYZ(file)
                    
                    c = (cr, cg, cb, 255) # Convert to RGBA
                    verts.append((vx * -scale, vy * scale, vz * scale))
                    normals.append((nx, ny, nz))
                    colours.append(c)
                    uvs.append((tu, 1-tv, 0))
                unkw3 = U.readShort(file)
                unkw4 = U.readShort(file)
                # Add faces
                faces = CarMesh.createFaceList(vertCount)
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
                meshes.append(CarMesh(meshVertCount, meshVerts, meshNormals, meshUvs, meshFaces, meshColours))
        return meshes

    def writeMeshToDBG(self, fout, startIndex = 0):
        self.writeMeshToObj(fout)
        fout.write("#" + str(len(self.meshColours)) + " colours R/G/B/A\n")
        for i in range(0, len(self.meshFaces)):
            cr = '{:d}'.format(math.trunc(self.meshColours[i][0]))
            cg = '{:d}'.format(math.trunc(self.meshColours[i][1]))
            cb = '{:d}'.format(math.trunc(self.meshColours[i][2]))
            ca = '{:d}'.format(math.trunc(self.meshColours[i][3]))
            
            fout.write(f"c {cr} {cg} {cb} {ca}\n")
        
        return len(self.meshVerts)

    def writeMeshToObj(self, fout, startIndex = 0):
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
            fx = self.meshFaces[i][0] + startIndex
            fy = self.meshFaces[i][1] + startIndex
            fz = self.meshFaces[i][2] + startIndex
            
            fout.write(f"f {fx}/{fx}/{fx} {fy}/{fy}/{fy} {fz}/{fz}/{fz}\n")
        fout.write("#" + str(len(self.meshFaces)) + " faces\n")
    
        return len(self.meshVerts)

    def writeMeshToComb(self, fout, startIndex = 0):
        fout.write(f"vertex_count {len(self.meshVerts)}\n")
        fout.write(f"face_count {len(self.meshFaces)}\n")
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
            fx = self.meshFaces[i][0]-1 + startIndex
            fy = self.meshFaces[i][1]-1 + startIndex
            fz = self.meshFaces[i][2]-1 + startIndex
            
            fout.write(f"4 {fx} {fy} {fz}\n")
        
        return len(self.meshVerts)


    def writeMeshToPly(self, fout, startIndex = 0):
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
        #fout.write(f"element texture {len(self.meshUvs)}\n")
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
            fx = self.meshFaces[i][0]-1 + startIndex
            fy = self.meshFaces[i][1]-1 + startIndex
            fz = self.meshFaces[i][2]-1 + startIndex
            
            fout.write(f"4 {fx} {fy} {fz}\n")

        return len(self.meshVerts)
        
