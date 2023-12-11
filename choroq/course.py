
# Class for holding course/racetrack model data, and extracting it from a Cxx.BIN file

# Course file Cxx.bin info:
#   Contains 4 sub files
#     - Textures
#     - Models
#     - Possibly a collision mesh, as is usually just the roads
#     - Overlay map, or number of extra meshes such as doors/barrels

# Textures:
#
#

# Models:
# Magic: 90 01 00 00
# Followed by a offset list of models/meshes
# !Not all meshes are in the list, and are probably sub models/meshes to split up for texture mapping
# Some models/meshes in the list end up being:
#    00 00 00 10 00 00 00 00 01 01 00 01 00 00 00 00 00 00 00 60 00 00 00 00 00 00 00 00 00 00 00 00
#  Unknown reason for this "empty" version
# offset list ends with 0s not eof offset
# 
# Each mesh is then as follows:
# vertCount = readByte(file)
# 0x80 single byte
# zero short
# 16 bytes of unknown
# Then the rest of the data is verticies:
#    vertex  x, y, z (floats)
#    normals x, y, z (floats)
#    colours r, g, b set (int a float)
#    unknown x, y, z set (floats)
#    uv(w)   u, v, w set (floats)
# a unknown long
# 
# If at this point there is the mesh continue flag: 0x6c018000
# then repeat above as extra verticies of the same mesh
# 
# If not then this is the end of the current mesh, 
# and go back to the offset list for the start of the next mesh
#
# File 3: 
# Assuming that this file contains colliders or simplified mesh data
# The file is broken into chunks (16x16)
# Each chunk contains a number of verticies, and sometimes normals
#
# File 4+: 
# This is often the mini map, used for showing player position 
# on the blue track ring overlay. It can be parsed as like a car mesh, 
# using the CarMesh class as is and will produce the map
# There may be more than 1 file from here onwards, usually holding 
# movable items such as doors, chests or barrels.

import io
import os
import math
from choroq.amesh import AMesh
from choroq.texture import Texture
from choroq.car import CarModel, CarMesh
import choroq.read_utils as U

class CourseModel:

    def __init__(self, name, meshes = [], textures = [], colliders = [], mapMeshes = [], extras = []):
        self.name = name
        self.meshes = meshes
        self.colliders = colliders
        self.mapMeshes = mapMeshes
        self.textures = textures
        self.extras = extras

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
    def matchesTextureMagic(magic):
        return (magic & 0x10120006 >= 0x10120006 and magic & 0x10120006 <= 0x10FF0006) or (magic & 0x10400006 >= 0x10400006 and magic & 0x10400006 <= 0x10FF0006)

    @staticmethod
    def fromFile(file, offset, size):
        subFileOffsets = CourseModel._parseOffsets(file, offset, size)
        print(f"Got subfiles: {subFileOffsets}")
        meshes = []
        textures = []
        colliders = [] # Unsure of use of this, but is either road surface related or collider
        mapMeshes = [] # Holds ui overlay map
        extras = [] # Holds car like format extras (for actions)
        for oi, o in enumerate(subFileOffsets):
            if (o == size or o == 0):
                # At end of file
                break
            file.seek(offset+o, os.SEEK_SET)
            magic = U.BreadLong(file)
            file.seek(offset+o, os.SEEK_SET)
            print(f"offset {offset + o} magic :{magic}")
            
            if CourseModel.matchesTextureMagic(magic):
                textureCount = 0
                
                print(f"Parsing texture @ {offset+o} {magic & 0x10120006} {magic & 0x10400006}")
                textures.append(Texture._fromFile(file, offset+o))
                nextTextureOffset = file.tell()
                nextTexture = U.readLong(file)
                file.seek(nextTextureOffset, os.SEEK_SET)

                print(f"nextTextureOffset {nextTextureOffset}")
                print(f"nextTexture {nextTexture}")

                while CourseModel.matchesTextureMagic(nextTexture):
                    textureCount += 1
                    textures.append(Texture._fromFile(file, nextTextureOffset))
                    nextTextureOffset = file.tell()
                    nextTexture = U.readLong(file)
                    file.seek(nextTextureOffset, os.SEEK_SET)
                    print(f"nextTextureOffset {nextTextureOffset}")
                    print(f"nextTexture {nextTexture}")
                print(file.tell())
                
            elif oi == 1:
                meshes.append(Course._fromFile(file, offset+o))
            elif oi == 2: # 3rd Subfile
                colliders += CourseCollider.fromFile(file, offset+o)
            elif oi >= 3: # 4th Subfile
                # Holds the map for showing the player position, vs others on the hud
                # Might be other sub files, that hold moving object, e.g. doors
                file.seek(offset+o+8, os.SEEK_SET)
                if U.readLong(file) == 0x1000101:
                    file.seek(os.SEEK_SET, offset+o)
                    # No header, probably just a mesh
                    mapMeshes += CarMesh._fromFile(file, offset+o)
                else:
                    # First bit is offset table as usual
                    file.seek(offset+o, os.SEEK_SET)
                    extra = CarModel.fromFile(file, offset+o, subFileOffsets[oi+1] - o)
                    if oi != 4:
                        mapMeshes += extra.meshes
                    else:
                        extras.append(extra)


        print(f"Got {len(meshes)} meshes")
        return CourseModel("", meshes, textures, colliders, mapMeshes, extras)

class Course():

    def __init__(self, chunks, chunkOffsets, shorts):
        self.chunks = chunks
        self.chunkOffsets = chunkOffsets
        self.shorts = shorts

    @staticmethod
    def _parsePart(file, scale):
        dataType = U.readLong(file)
        if dataType == 0x6C018000:
            print(f"READING \"MESH\" AT {file.tell()-4}")
            # This is mesh data
            verts = [] 
            uvs = []
            normals = []
            faces = []
            colours = []
            extras = []
            vertCount = U.readByte(file)
            unkw1 = U.BreadByte(file)
            zeroF1 = U.BreadShort(file)
            # Skip 12 bytes as we dont know what they are used for
            file.seek(0xC, os.SEEK_CUR)
            meshFormatVar = U.readLong(file)

            # in groups of three floats
            meshDataLength = (meshFormatVar & 0x00FF0000) >> 16
            # Convert to number of bytes
            meshDataLength = meshDataLength * 3 * 4 

            numberOfExtra = 0
            # Most mesh data is 60 bytes long per vertex
            # eqiv to 5 * 3 floats per vertex
            if meshDataLength != 60 * vertCount:
                # Mesh data is different size to usual
                # more or less bytes per vertex
                # This is used for billboards (e.g trees)
                numberOfExtra = int((meshDataLength - vertCount * 60) / 4)
                print(f"Found unknown mesh format {meshFormatVar} {file.tell()} {meshDataLength / vertCount}")
                print(f"Number of extra bytes {numberOfExtra}")
                if numberOfExtra < 0:
                    print(f"Found unknown smaller mesh format {numberOfExtra}")
                    exit(51)

            xOffset = 0
            yOffset = 0
            zOffset = 0
            if numberOfExtra == 3: 
                # This is a billboard, and uses a preset x,y,z before rest of data
                # Starting position
                xOffset = U.readFloat(file)
                yOffset = U.readFloat(file)
                zOffset = U.readFloat(file)
            elif numberOfExtra != 0:
                print(f"Offset theory doesnt work {numberOfExtra} != 3")
                exit(50)

            for x in range(0, vertCount):
                vx, vy, vz = U.readXYZ(file)
                if numberOfExtra == 3:
                    vx += xOffset
                    vy += yOffset
                    vz += zOffset

                fx, fy, fz = U.readXYZ(file) # possibly emission info (light)
                # I suspect there is no real time lighting for world meshes and so no normals
                # Writing to normals for easy parsing
                nx = opacity = U.readFloat(file) # 1 = opaque, 0 = see through (mostly like watery, used for rivers?)
                ny = U.readFloat(file) # Unknown # Theses are usually ~100f 70-120 ish
                nz = U.readFloat(file) # Unknown
                
                # Red and green work, unsure on blue, probably blue works fine
                cr, cg, cb = U.readXYZ(file) # Are colours
                tu, tv, tw = U.readXYZ(file) # Are texture coords

                if fx > 255 or fy > 255 or fz > 255:
                    print("Found value > 255")
                    print(f"{fx} {fy} {fz}")
                    print(f"{nx} {ny} {nz}")
                    print(f"{cr} {cg} {cb}")
                    # exit(1)
                
                c = (cr, cg, cb, 255 * opacity) # Convert to RGBA
                verts.append((vx * scale, vy * scale, vz * scale))
                normals.append((nx, ny, nz))
                colours.append(c)
                extras.append((fx, fy, fz))
                uvs.append((tu, 1-tv, tw))
            
            unkw3 = U.BreadShort(file) # 0x0008 not when numberOfExtra != 0
            unkw4 = U.BreadShort(file) # 0x1500

            faces = CourseMesh.createFaceList(vertCount)

            mesh = CourseMesh(len(verts), verts, normals, uvs, faces, colours, extras)

            return "mesh", mesh
        elif dataType & 0xFF00FFFF == 0x68008192: 
            # Data section is labelled as DATA as I dont know what it is
            # it usually contains texture info, and other unknown data
            data = []
            # Unknown data type/use
            subType = (dataType & 0x00FF0000) >> 16 # Seen 04 and 05

            count = U.readByte(file) # Think length is count*3*4 bytes
            const80 = U.BreadByte(file) # always 80
            constNull = U.BreadShort(file) # always 0000
            unknown1 = U.BreadLong(file) # Usually 0x10000000
            unknown2 = U.BreadLong(file) # Usually 0x0000000E
            
            if count >= 3:
                U.BreadLong(file)
                U.BreadLong(file)
                U.BreadLong(file)

                # Texture reference is here, unsure how it wokrs
                # I think this could be a texture load register for GIF or similar

                # Seems to be texture reference, changes texture
                textureReferenceFirst = U.readLong(file)
                # Seems to relate to colours/CLUT?, texture stays roughly the same
                textureReferenceSecond = U.readLong(file)
                unknown4 = U.readLong(file) # Always 7 so far
                if unknown4 != 7:
                    print(f"Found new unknown4 texture reference @ {file.tell()}")

                textureType = U.readLong(file)

                data.append(textureReferenceFirst)
                data.append(textureReferenceSecond) 
                data.append(textureType)

                # Following is what works so far
                if textureType == 0:
                    pass
                elif textureType == 1:
                    pass
                elif textureType == 4:
                    # Non transparent texture
                    pass
                elif textureType == 5:
                    # Transparent texture
                    pass
                else:
                    # Unknown variation
                    print(F"Found new data texture reference type @ {file.tell()-4}")
                    exit(60)

                U.BreadLong(file) # 0 Always
                U.BreadLong(file) # 9 Always

                if count > 3:
                    for x in range(count-3):
                        d1 = U.BreadLong(file)
                        d2 = U.BreadLong(file)
                        d3 = U.BreadLong(file)
                        # data.append(d1)
                        # data.append(d2)
                        # data.append(d3)

            else:
                print(f"New mesh \"Data\" type @ {file.tell()} 03 probably should be at this address")
                for x in range(count):
                    d1 = U.BreadLong(file)
                    d2 = U.BreadLong(file)
                    d3 = U.BreadLong(file)
                    data.append(d1)
                    data.append(d2)
                    data.append(d3)
                exit(61)

            return "data", data
        else:
            print(f"Found new data type {dataType} {file.tell()}")
            return "err", []


    currentDataIndex = 0

    @staticmethod
    def _parseChunk(file, offset, count, scale):
        # Read chunk header
        file.seek(offset, os.SEEK_SET)

        print(f"Reading chunk @ {file.tell()} {offset}")
        unknown0 = U.BreadLong(file)
        nullF0 = U.BreadLong(file)
        meshStartFlag = U.readLong(file)
        if meshStartFlag != 0x01000101:
            print(f"Mesh's start flag is different {meshStartFlag} @{file.tell()}")
            exit(2)

        meshesByData = {}
        currentMeshes = []
        currentData = None
        meshes = []
        data = []

        nextDataType = U.readLong(file)
        file.seek(-4, os.SEEK_CUR)
        while nextDataType & 0xFF000000 > 0x60000000:
            dataType, result = Course._parsePart(file, scale)
            if dataType == "mesh":
                currentMeshes.append(result)
                meshes.append(result)
            elif dataType == "data":
                meshesByData[Course.currentDataIndex] = (result, currentMeshes)
                currentMeshes = []
                currentData = result
                Course.currentDataIndex += 1
                data.append(result)
            else:
                print(f"ERR")
                print(f"z{z}, x{x} Got {len(meshes)} meshses")
                print(f"z{z}, x{x} Got {len(data)} data")
                print(f"{file.tell()}")
                print(f"last {nextDataType}")
                exit(2)
            nextDataType = U.readLong(file)
            # Unusual cases
            if nextDataType == 0:
                # where theres a gap in the data
                file.seek(8, os.SEEK_CUR)
                meshTest = U.readLong(file)
                if meshTest == 0x01000101:
                    nextDataType = U.readLong(file)
                    file.seek(-4, os.SEEK_CUR)
                    print(f"Special case @ {file.tell()}")
            elif nextDataType == 0x3F666666: 
                # Unusual case, with special marker
                # Data seems to continue?
                file.seek(-4, os.SEEK_CUR)
            else:
                file.seek(-4, os.SEEK_CUR)
            
        print(f"Last dataType {nextDataType}")
        print(f"shorts {len(meshes)} == {count}: {len(meshes) == count}")
        if len(meshes) != count:
            print("Got different lengths")
            # exit(22)
        print(f"Done chunks @ {file.tell()}")
        return ((meshes, data), meshesByData)
            
    @staticmethod
    def _fromFile(file, offset, scale=1):
        file.seek(offset, os.SEEK_SET)
        print(f"Reading Course from {file.tell()}")
        chunks = [] #16x16 grid with meshes inside

        chunkOffsets = []
        for z in range(0, 8):
            for x in range(0, 8):
                chunkOffsets.append(U.readLong(file))
        extraOffset = U.readLong(file)

        # Number of sub files/meshes in chunk
        # This is not used in this script
        shorts = []
        for j in range(64):
            shorts.append(U.readShort(file))
        extraShort = U.readShort(file)

        print(f"Read end of table @ {file.tell()}")
        print(f"Reading Chunks from {offset+chunkOffsets[0]}")
        # Read each chunk
        for z in range(0, 8):
            zRow = []
            xLimit = 8
            for x in range(0, xLimit):
                index = x + z * 8
                print(f"Reading chunk {index} z{z} x{x}")
                chunk = Course._parseChunk(file, offset+chunkOffsets[index], shorts[index], scale)
                zRow.append(chunk)
            chunks.append(zRow)
        
        # Process the extra part of the course
        # This is usually used in fields to hold the windows
        # This allows the windows to light up at night
        print(f"extraOffset {offset+extraOffset} {extraOffset} {extraShort} but at @ {file.tell()}")
        extraChunk = Course._parseChunk(file, offset+extraOffset, extraShort, scale)
        chunks.append([extraChunk])

        return Course(chunks, chunkOffsets, shorts)


class CourseMesh(AMesh):

    def __init__(self, meshVertCount = [], meshVerts = [], meshNormals = [], meshUvs = [], meshFaces = [], meshColours = [], meshExtras = []):
        self.meshVertCount   = meshVertCount
        self.meshVerts       = meshVerts
        self.meshNormals     = meshNormals
        self.meshUvs         = meshUvs
        self.meshFaces       = meshFaces
        self.meshColours     = meshColours
        self.meshExtras      = meshExtras

    def writeMeshToObj(self, fout, startIndex = 0):
        # Write verticies
        for i in range(0, len(self.meshVerts)):
            vx = '{:.20f}'.format(self.meshVerts[i][0])
            vy = '{:.20f}'.format(self.meshVerts[i][1])
            vz = '{:.20f}'.format(self.meshVerts[i][2])
            fout.write("v " + vx + " " + vy + " " + vz + "\n")
        fout.write("#" + str(len(self.meshVerts)) + " vertices\n")
            
        # Course meshes have no normals, but swapped with other data
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

            ex = '{:.20f}'.format(self.meshExtras[i][0])
            ey = '{:.20f}'.format(self.meshExtras[i][1])
            ez = '{:.20f}'.format(self.meshExtras[i][2])

            nx = '{:.20f}'.format(self.meshNormals[i][0])
            ny = '{:.20f}'.format(self.meshNormals[i][1])
            nz = '{:.20f}'.format(self.meshNormals[i][2])

            tu = '{:.10f}'.format(self.meshUvs[i][0])
            tv = '{:.10f}'.format(self.meshUvs[i][1])

            fout.write(f"{vx} {vy} {vz} {ex} {ey} {ez} {nx} {ny} {nz} {cr} {cg} {cb} {ca} {tu} {tv}\n")
        
        # Write mesh face order/list
        for i in range(0, len(self.meshFaces)):
            fx = self.meshFaces[i][0]-1 + startIndex
            fz = self.meshFaces[i][2]-1 + startIndex
            fy = self.meshFaces[i][1]-1 + startIndex
            
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

        # Write out the "extra" data sets
        fout.write("comment extra data:\n")
        for i in range(0, len(self.meshVerts)):
            fx = '{:.20f}'.format(self.meshVerts[i][0])
            fy = '{:.20f}'.format(self.meshVerts[i][1])
            fz = '{:.20f}'.format(self.meshVerts[i][2])
            fout.write(f"comment {fx} {fy} {fz}\n")
        fout.write("comment extra end\n")

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

            # Normals are not here, this is different data
            nx = '{:.20f}'.format(self.meshNormals[i][0])
            ny = '{:.20f}'.format(self.meshNormals[i][1])
            nz = '{:.20f}'.format(self.meshNormals[i][2])

            tu = '{:.10f}'.format(self.meshUvs[i][0])
            tv = '{:.10f}'.format(self.meshUvs[i][1])

            fout.write(f"{vx} {vy} {vz} {nx} {ny} {nz} {cr} {cg} {cb} {ca} {tu} {tv}\n")
        
        # Write mesh face order/list
        for i in range(0, len(self.meshFaces)):
            fx = self.meshFaces[i][0]-1 + startIndex
            fz = self.meshFaces[i][2]-1 + startIndex
            fy = self.meshFaces[i][1]-1 + startIndex
            
            fout.write(f"4 {fx} {fy} {fz}\n")
        
        return len(self.meshVerts)
        
    def writeMeshToDBG(self, fout, startIndex = 0):
        for i in range(0, len(self.meshVerts)):
            
            vx = '{:.20f}'.format(self.meshVerts[i][0])
            vy = '{:.20f}'.format(self.meshVerts[i][1])
            vz = '{:.20f}'.format(self.meshVerts[i][2])
            fout.write("v " + vx + " " + vy + " " + vz + "\n")
            # Normals are not here, this is different data
            nx = '{:.20f}'.format(self.meshNormals[i][0])
            ny = '{:.20f}'.format(self.meshNormals[i][1])
            nz = '{:.20f}'.format(self.meshNormals[i][2])
            cr = '{:.20f}'.format(self.meshColours[i][0])
            cg = '{:.20f}'.format(self.meshColours[i][1])
            cb = '{:.20f}'.format(self.meshColours[i][2])
            ca = '{:.20f}'.format(self.meshColours[i][3])
            ex = self.meshExtras[i][0]
            ey = self.meshExtras[i][1]
            ez = self.meshExtras[i][2]
            fout.write(f"# {ex} {ey} {ez} {nx} {ny} {nz} {cr} {cg} {cb}\n")

            tu = '{:.20f}'.format(self.meshUvs[i][0])
            tv = '{:.20f}'.format(self.meshUvs[i][1])
            tw = '{:.20f}'.format(self.meshUvs[i][2])
            fout.write(f"vt {tu} {tv} {tw}\n")


        for i in range(0, len(self.meshFaces)):
            fx = self.meshFaces[i][0] + startIndex
            fy = self.meshFaces[i][1] + startIndex 
            fz = self.meshFaces[i][2] + startIndex
            fout.write(f"f {fx} {fy} {fz}\n")

        fout.write("#" + str(len(self.meshVerts)) + " vertices\n")            
        fout.write("#" + str(len(self.meshNormals)) + " vertex normals\n")            
        fout.write("#" + str(len(self.meshUvs)) + " texture vertices\n")
        fout.write("#" + str(len(self.meshExtras)) + " texture vertices\n")
        fout.write("#" + str(len(self.meshFaces)) + " faces\n")

        return len(self.meshVerts)
        

class CourseCollider(AMesh):

    def __init__(self, meshVertCount = [], meshVerts = [], meshNormals = [], meshFaces = []):
        self.meshVertCount   = meshVertCount
        self.meshVerts       = meshVerts
        self.meshNormals     = meshNormals
        self.meshFaces       = meshFaces

    @staticmethod
    def fromFile(file, offset):
        file.seek(offset, os.SEEK_SET)

        chunkOffsets = []
        for z in range(0, 16):
            for x in range(0, 16):
                chunkOffsets.append(U.readLong(file))
        print(chunkOffsets)
        # extraOffset = U.readLong(file)
        # chunkOffsets.append(extraOffset)

        # Number of sub files/meshes in chunk
        # This is not used in this script
        shorts = []
        for j in range(256):
            shorts.append(U.readShort(file))
        print(shorts)
        # extraShort = U.readShort(file)
        # shorts.append(extraShort)

        lastOffset = U.readLong(file) # Last offset is just before the first offset's data
        lastSize = U.readLong(file) # This is the number of floats to read

        colliders = []
        scale = 1
        
        totalVerts = 0

        offsetsDone = set([])

        file.seek(0, os.SEEK_END)
        maxLength = file.tell()

        # Read the mesh data between this offset and the next
        for z in range(0, 16):
            zRow = []
            xLimit = 16
            for x in range(0, xLimit):
                index = x + z * 16
                print(f"reading collider chunk {index} z{z} x{x}")
                meshes = []
                data = []

                # Skip duplicates
                if chunkOffsets[index] in offsetsDone:
                    continue
                offsetsDone.add(chunkOffsets[index])

                if offset+chunkOffsets[index] >= maxLength:
                    # At end of file
                    continue

                file.seek(offset+chunkOffsets[index], os.SEEK_SET)

                meshVerts = []
                meshNormals = []
                meshUvs = []
                meshFaces = []
                meshColours = []
                meshVertCount = 0

                count = 0

                while count < shorts[index]:
                    print(f"Reading collider chunk {z} {x} {index} from: {file.tell()}")
                    vertCount = U.readByte(file)
                    U.BreadByte(file) # always 0x80
                    U.BreadShort(file) # always 0x0000
                    # Skip 12 (todo workout)
                    file.seek(12, os.SEEK_CUR)

                    verts, normals, faces = CourseCollider.parseChunk(file, vertCount, scale)
                    
                    for i in range(0, len(faces)):
                        vertices = faces[i]
                        meshFaces.append((vertices[0] + meshVertCount, vertices[1] + meshVertCount, vertices[2] + meshVertCount))
                    
                    meshVertCount += len(verts)
                    meshVerts += verts
                    meshNormals += normals

                    totalVerts += len(verts)
                    count += 1
                print(f"Got {meshVertCount} {count} vs {shorts[index]}")
                if count != shorts[index]:
                    print(f"Number of colliders read is different")
                colliders.append(CourseCollider(meshVertCount, meshVerts, meshNormals, meshFaces))
        
        file.seek(offset + lastOffset, os.SEEK_SET)
        if offset + lastOffset + (lastSize * 12) < maxLength:
            # Process the last chunk, x,y,z,y2 format and re-uses x/y for doing posts/towers
            postVerticies = []
            for i in range(int(lastSize)):
                x = U.readFloat(file)
                y = U.readFloat(file)
                z = U.readFloat(file)
                y2 = U.readFloat(file)
                postVerticies.append((x, y, z)) # Upper post
                postVerticies.append((x, y2, z)) # Lower post

                
            faces = CourseCollider.createFaceList(len(postVerticies))
            for i in range(0, len(faces)):
                vertices = faces[i]
                meshFaces.append((vertices[0] + meshVertCount, vertices[1] + meshVertCount, vertices[2] + meshVertCount))

            colliders.append(CourseCollider(len(postVerticies), postVerticies, [], meshFaces))

        return colliders

    @staticmethod
    def parseChunk(file, vertCount, scale):
        verts = []
        normals = []
        faces = []

        # Read in verticies
        for x in range(0, vertCount):
            vx, vy, vz = U.readXYZ(file)
            vw = U.BreadLong(file) # 1.0f
            verts.append((vx * scale, vy * scale, vz * scale))

        # Read in normals
        if vertCount <= 40 and vertCount >= 3:
            for n in range(vertCount-2):
                normals.append(U.readXYZ(file))
                U.BreadLong(file) # 1.0f
            
            normals.append(normals[-1])
            normals.append(normals[-1])
        else:
            print("NOT READING NORMALS")

        faces = CourseCollider.createFaceList(vertCount)
        return verts, normals, faces

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
        
        # Write mesh face order/list
        for i in range(0, len(self.meshFaces)):
            fx = self.meshFaces[i][0] + startIndex
            fy = self.meshFaces[i][1] + startIndex
            fz = self.meshFaces[i][2] + startIndex
            
            fout.write(f"f {fx} {fy} {fz}\n")
        fout.write("#" + str(len(self.meshFaces)) + " faces\n")
    
        return len(self.meshVerts)

    def writeMeshToComb(self, fout, startIndex = 0):
        fout.write(f"vertex_count {len(self.meshVerts)}\n")
        fout.write(f"face_count {len(self.meshFaces)}\n")
        fout.write("end_header\n")

        if len(self.meshNormals) != len(self.meshVerts):
            needed = abs(len(self.meshNormals) -len(self.meshVerts))
            for i in range(needed):
                self.meshNormals.append((0.0, 0.0, 0.0))

        # Write verticies, normals
        for i in range(0, len(self.meshVerts)):
            vx = '{:.20f}'.format(self.meshVerts[i][0])
            vy = '{:.20f}'.format(self.meshVerts[i][1])
            vz = '{:.20f}'.format(self.meshVerts[i][2])

            nx = '{:.20f}'.format(self.meshNormals[i][0])
            ny = '{:.20f}'.format(self.meshNormals[i][1])
            nz = '{:.20f}'.format(self.meshNormals[i][2])

            fout.write(f"{vx} {vy} {vz} {nx} {ny} {nz}\n")
        
        # Write mesh face order/list
        for i in range(0, len(self.meshFaces)):
            fx = self.meshFaces[i][0]-1 + startIndex
            fy = self.meshFaces[i][1]-1 + startIndex
            fz = self.meshFaces[i][2]-1 + startIndex
            
            fout.write(f"4 {fx} {fy} {fz}\n")

        return len(self.meshVerts)

    def writeMeshToPly(self, fout, startIndex = 0):
        if len(self.meshVerts) != len(self.meshNormals):
            # print("Cannot produce collider in ply format for:")
            # print(f"dst = {fout.name}")
            # return
            fout.write("ply\n")
            fout.write("format ascii 1.0\n")
            fout.write(f"element vertex {len(self.meshVerts)}\n")
            fout.write("property float x\n")
            fout.write("property float y\n")
            fout.write("property float z\n")
            fout.write(f"element face {len(self.meshFaces)}\n")
            fout.write("property list uint8 int vertex_index\n")
            fout.write("end_header\n")

            for i in range(0, len(self.meshVerts)):
                vx = '{:.20f}'.format(self.meshVerts[i][0])
                vy = '{:.20f}'.format(self.meshVerts[i][1])
                vz = '{:.20f}'.format(self.meshVerts[i][2])

                fout.write(f"{vx} {vy} {vz}\n")
        else:
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
            fout.write(f"element face {len(self.meshFaces)}\n")
            fout.write("property list uint8 int vertex_index\n")
            fout.write("end_header\n")

            # Write verticies, normals
            for i in range(0, len(self.meshVerts)):
                vx = '{:.20f}'.format(self.meshVerts[i][0])
                vy = '{:.20f}'.format(self.meshVerts[i][1])
                vz = '{:.20f}'.format(self.meshVerts[i][2])

                nx = '{:.20f}'.format(self.meshNormals[i][0])
                ny = '{:.20f}'.format(self.meshNormals[i][1])
                nz = '{:.20f}'.format(self.meshNormals[i][2])

                fout.write(f"{vx} {vy} {vz} {nx} {ny} {nz}\n")

        # print(f"v {len(self.meshVerts)}")
        # print(f"n {len(self.meshNormals)}")
        
        # Write mesh face order/list
        for i in range(0, len(self.meshFaces)):
            fx = self.meshFaces[i][0]-1 + startIndex
            fy = self.meshFaces[i][1]-1 + startIndex
            fz = self.meshFaces[i][2]-1 + startIndex
            
            fout.write(f"4 {fx} {fy} {fz}\n")

        return len(self.meshVerts)
        
    def writeMeshToDBG(self, fout, startIndex = 0):
        for i in range(0, len(self.meshVerts)):
            vx = '{:.20f}'.format(self.meshVerts[i][0])
            vy = '{:.20f}'.format(self.meshVerts[i][1])
            vz = '{:.20f}'.format(self.meshVerts[i][2])
            fout.write("v " + vx + " " + vy + " " + vz + "\n")

        for i in range(0, len(self.meshNormals)):
            nx = '{:.20f}'.format(self.meshNormals[i][0])
            ny = '{:.20f}'.format(self.meshNormals[i][1])
            nz = '{:.20f}'.format(self.meshNormals[i][2])
            fout.write("vn " + nx + " " + ny + " " + nz + "\n")
            
            # ex = self.meshExtras[i][0]
            # ey = self.meshExtras[i][1]
            # ez = self.meshExtras[i][2]
            # fout.write(f"e {ex} {ey} {ez}\n")

        for i in range(0, len(self.meshFaces)):
            fx = self.meshFaces[i][0] + startIndex
            fy = self.meshFaces[i][1] + startIndex
            fz = self.meshFaces[i][2] + startIndex
            fout.write(f"f {fx} {fy} {fz}\n")

        fout.write("#" + str(len(self.meshVerts)) + " vertices\n")      
        fout.write("#" + str(len(self.meshNormals)) + " texture vertices\n")
        fout.write("#" + str(len(self.meshFaces)) + " faces\n")

        return len(self.meshVerts)