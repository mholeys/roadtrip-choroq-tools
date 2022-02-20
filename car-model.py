
# Class for holding car model data, and extracting it from a Qxx.BIN file
# Based on the format used in the game RoadTrip Adventure (UK/EU), aka ChoroQ HG 2 (JP) or RoadTrip (US) for the Sony Playstation 2 (PS2)
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
# 16 is the size of header, and so is the first "offset"
#
#
# [Mesh]
# First long seems to be a value of [6C018000] meaning that there is another set of verticies following this one (MeshFlag)
# Second long is always null/[00000000] probably to match up with other file headers like the textures
# Third long is always [01 01 00 01] possibly a version or bitMask
#
# [MeshData]
# After these starts the actual mesh data for the models
# First of which is a long with the value of [00 80 01 6C]
#  this may be the mesh's real file start or an identifier for mesh's
#  TODO: Finish
# 
# Next Byte contains the number of verticies
# Followed by 128/0x80
# Followed by 0000
# e.g:
# [AA][BB][CCCC]
#  AA = vertex count
#  BB = 0x80
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
# See <> TODO: references


import io
import os
import struct
from PIL import Image, ImagePalette

class CarModel:

    def __init__(self, name, meshes = [], textures = []):
        self.name = name
        self.meshes = meshes
        self.textures = textures

    @staticmethod
    def _parseOffsets(file, offset, size):
        file.seek(offset, os.SEEK_SET)
        subFileOffsets = []
        o = 0
        while o != size:
            o = readLong(file)
            subFileOffsets.append(o)
        return subFileOffsets

    @staticmethod
    def fromFile(file, offset, size):
        subFileOffsets = CarModel._parseOffsets(file, offset, size)
        meshes = []
        textures = []
        for o in subFileOffsets:
            if (o == size):
                # At end of file
                break
            f.seek(offset+o, os.SEEK_SET)
            magic = readLong(f)
            f.seek(offset+o, os.SEEK_SET)
            if magic == 0x10120406:
                # File is a texture
                print(f"Parsing texture @ {offset+o}")
                textures.append(CarTexture._fromFile(file, offset+o))
            #elif magic == 0x:
            else:
                print(f"Parsing meshes @ {offset+o}")
                meshes += CarMesh._fromFile(file, offset+o)
        return CarModel("", meshes, textures)


class CarMesh:

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
        offset1 = readLong(file)
        offset2 = readLong(file)
        return 16, offset1, offset2

    @staticmethod
    def _parseHeader(file):
        unkw0 = readLong(file)
        nullF0 = readLong(file)
        meshStartFlag = readLong(file)
        if meshStartFlag != 0x01000101:
            print(f"Mesh's start flag is different {meshStartFlag} from usual, continuing")
        return unkw0, nullF0, meshStartFlag

    @staticmethod
    def _fromFile(file, offset, scale=50):
        offsets = CarMesh._parseOffsets(file, offset)
        meshes = []
        for o in offsets:
            file.seek(o + offset, os.SEEK_SET)
            header = CarMesh._parseHeader(file)
            # Read mesh
            meshFlag  = readLong(file)

            meshVerts = []
            meshNormals = []
            meshUvs = []
            meshFaces = []
            meshColours = []
            meshVertCount = 0

            # Read chunk of verticies
            while meshFlag == 0x6c018000:
                verts = [] 
                uvs = []
                normals = []
                faces = []
                colours = []
                vertCount = readByte(file)
                unkw1 = readByte(file)
                zeroF1 = readShort(file)
                # Skip 16 bytes as we dont know what they are used for
                file.seek(0x10, os.SEEK_CUR)

                for x in range(0, vertCount):
                    vx, vy, vz = readXYZ(file)
                    nx, ny, nz = readXYZ(file)
                    cr, cg, cb = readXYZ(file)
                    tu, tv, unkw2 = readXYZ(file)
                    
                    c = (cr, cg, cb, 0) # Convert to RGBA
                    verts.append((vx * scale, vy * scale, vz * scale))
                    normals.append((nx, ny, nz))
                    colours.append(c)
                    uvs.append((tu, tv, 0))
                unkw3 = readShort(file)
                unkw4 = readShort(file)
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
                meshFlag = readLong(file)
            if (meshVertCount > 0):
                meshes.append(CarMesh(meshVertCount, meshVerts, meshNormals, meshUvs, meshFaces, meshColours))
        return meshes

    @staticmethod
    def createFaceList(vertexCount, faceType=1):
        # Creates a list of indices that order how to draw the 
        # verticies in order of how to render the triangles
        faces = []
    
        if (faceType == 1):
            startDirection = 1
            x = 0
            a = 0
            b = 0
            
            f1 = a + 1
            f2 = b + 1
            faceDirection = startDirection
            while (x < vertexCount):
                x += 1
                
                f3 = x
                faceDirection *= -1
                if (f1 != f2) and (f2 != f3) and (f3 != f1):
                    if (faceDirection > 0):
                        faces.append((f1, f2, f3))
                    else:
                        faces.append((f1, f3, f2))
                f1 = f2
                f2 = f3
        if (faceType == 0):
            a = 0
            b = 0
            c = 0
            
            for x in range(0, vertexCount, 3):
                a = x
                b = x+1
                c = x+2
                faces.append((a, b, c))
        return faces

    def writeMeshToObj(self, fout):
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
        fout.write("#" + str(len(self.meshUvs)) + " vertex normals\n")
        
        # Write texture coordinates (uv)
        for i in range(0, len(self.meshUvs)):
            tu = '{:.20f}'.format(self.meshUvs[i][0])
            tv = '{:.20f}'.format(self.meshUvs[i][1])
            fout.write("vt " + tu + " " + tv + "\n")
        fout.write("#" + str(len(self.meshNormals)) + " texture vertices\n")
        
        # Write mesh face order/list
        for i in range(0, len(self.meshFaces)):
            fx = self.meshFaces[i][0]
            fy = self.meshFaces[i][1]
            fz = self.meshFaces[i][2]
            
            fout.write(f"f {fx}/{fx}/{fx} {fy}/{fy}/{fy} {fz}/{fz}/{fz}\n")
        fout.write("#" + str(len(self.meshFaces)) + " faces\n")

class CarTexture:

    def __init__(self, texture = [], palette = [], size=(0,0), fixAlpha=True):
        self.width = size[0]
        self.height = size[1]
        self.texture = texture
        self.palette = palette
        self.fixAlpha = fixAlpha

    @staticmethod
    def _fromFile(file, offset, scale=50, fixAlpha=True):
        file.seek(offset, os.SEEK_SET)
        
        nullPad = readLong(f)
        unkn1 = readShort(f)
        # TODO: find way to determine size
        #file.seek(offset+0x34, os.SEEK_SET)
        #length = readLong(f)
        file.seek(offset+0x70, os.SEEK_SET)
        width = 128
        height = 128
        length = width*height
        texture = f.read(length)
        colours = []
        # Skip header all values have unknown use atm
        f.seek(112, os.SEEK_CUR)

        # So far all palettes have been nonlinear but need to find
        # if all files are non Linear before ruling out option
        isNonLinear = True

        thisPaletteSize = 256
        rawPalette = []
        for i in range(0, thisPaletteSize):
            cr = readByte(f)
            cg = readByte(f)
            cb = readByte(f)
            ca = readByte(f)
            if fixAlpha and ca == 0x80:
                ca = 255
            rawPalette.append([cr, cg, cb, ca])

        if isNonLinear:            
            numParts = (int) (thisPaletteSize / 32)
            numBlocks = 2
            numStripes = 2
            numColours = 8

            paletteIndex = 0
            for part in range(0, numParts):
                for block in range(0, numBlocks):
                    for stripe in range(0, numStripes):
                        for c in range(0, numColours):
                            rawInd = part * numColours * numStripes * numBlocks + block * numColours + stripe * numStripes * numColours + c
                            colours.append(rawPalette[rawInd])
                            paletteIndex += 1
        else:
            colours = rawPalette
        return CarTexture(texture, colours, (width, height), fixAlpha)
    
    def writeTextureToPNG(self, path):
        cList = []
        for c in self.palette:
            cList.append(c[0])
            cList.append(c[1])
            cList.append(c[2])
            cList.append(c[3])
        image = Image.frombytes('P', (128,128), self.texture, 'raw', 'P')
        palette = ImagePalette.raw("RGBA", bytes(cList))
        palette.mode = "RGBA"
        image.palette = palette
        rgbd = image.convert("RGBA")
        rgbd.save(path, "PNG")

    def writePaletteToPNG(self, path):
        cList = []
        for c in self.palette:
            cList.append(c[0])
            cList.append(c[1])
            cList.append(c[2])
            cList.append(c[3])
        image = Image.frombytes('RGBA', (16,16), bytes(cList), 'raw', 'RGBA')
        image.save(path, "PNG")

def readFloat(f):
    return struct.unpack('<f', f.read(4))[0]
    
def readLong(f):
    return int.from_bytes(f.read(4), byteorder='little')
    
def readShort(f):
    return int.from_bytes(f.read(2), byteorder='little')

def readByte(f):
    return int.from_bytes(f.read(1), byteorder='little')

def readXYZ(f):
    return (readFloat(f), readFloat(f), readFloat(f))



with open("../Q00.BIN", "rb") as f:
    f.seek(0, os.SEEK_END)
    fileSize = f.tell()
    print(f"Reading file of {fileSize} bytes")
    f.seek(0, os.SEEK_SET)
    car = CarModel.fromFile(f, 0, fileSize)
    for i,mesh in enumerate(car.meshes):
        with open(f"out/Q00.bin-{i}.obj", "w") as fout:
            mesh.writeMeshToObj(fout)
    for i,tex in enumerate(car.textures):
        tex.writeTextureToPNG(f"out/Q00.bin-{i}.png")
        tex.writePaletteToPNG(f"out/Q00.bin-{i}-p.png")
        