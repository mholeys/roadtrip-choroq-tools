
# Class for holding course/racetrack model data, and extracting it from a Cxx.BIN file

# Course file Cxx.bin info:
#   Contains 4 sub files
#     - Textures
#     - Models
#     - ?
#     - ?

# Textures:
#
#

# Models:
# Magic: 90 01 00 00
# Followed by a offset list of models/meshes
# !Not all meshes are in the list, and are probably sub models/meshes to split up for texture mapping!
# Some models/meshes in the list end up being:
#    00 00 00 10 00 00 00 00 01 01 00 01 00 00 00 00 00 00 00 60 00 00 00 00 00 00 00 00 00 00 00 00
#  Unknown reason for this "empty" version
# Speculation: the first offset is not in the file and is fixed at x, possibly @400
# offset list ends with 0s not eof offset
# 
# Each mesh is then as follows:
# vertCount = readByte(file)
# ?? single byte
# zero short
# 16 bytes of unknown
# Then the rest of the data is verticies:
#    vertex  x, y, z (floats)
#    normals x, y, z
#    unknown x, y, z set
#    unknown x, y, z set
#    uv(w)   u, v, w set
# a unknown long
# 
# If at this point there is the mesh continue flag: 0x6c018000
# then repeat above as extra verticies of the same mesh
# 
# If not then end of this mesh start next mesh from offset list
#
# File 3: 
# Looks like array of floats? could be colors, or maybe 
# texture mapping info, on how to link texture x to model y
# Does not look like mesh data as does not contain 0x6c018000
# Does contain float, float, float, 1 groups after 0x610 for c00
# TODO:
#
# File 4: 
# After testing this is the mini map, used for showing player position 
# on the blue track ring overlay. It can be parsed as a car mesh class 
# using as is and will produce the map

import io
import os
import math
from choroq.texture import Texture
import choroq.read_utils as U

class CourseModel:

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
        subFileOffsets = CourseModel._parseOffsets(file, offset, size)
        print(f"Got subfiles: {subFileOffsets}")
        meshes = []
        textures = []
        for oi, o in enumerate(subFileOffsets):
            if (o == size or o == 0):
                # At end of file
                break
            file.seek(offset+o, os.SEEK_SET)
            magic = U.readLong(file)
            file.seek(offset+o, os.SEEK_SET)
            print(f"offset {offset + o} magic :{magic}")
            
            if magic & 0x10120006 >= 0x10120006 or magic & 0x10400006 >= 0x10400006:
                # TODO: parse more than 1 texture
                # File is possibly a texture
                print(f"Parsing texture @ {offset+o} {magic & 0x10120006} {magic & 0x10400006}")
                #textures.append(Texture._fromFile(file, offset+o))
                
            elif magic == 0x190:
                # Subfile is meshes/models
                print(f"Parsing meshes at {offset+o}")
                U.readLong(file) # Skip magic
                # Parse list
                meshOffsets = []
                meshO = 1
                while meshO != 0:
                    meshO = U.readLong(file)
                    meshOffsets.append(meshO)
                # Parse each mesh
                print(meshOffsets)
                print(len(meshOffsets))
                for mi,mo in enumerate(meshOffsets):
                    print(f"reading mesh at {offset+o+mo} {offset} {o} {mo}")
                    meshes += CourseMesh._fromFile(file, offset+o+mo)
                    
                    # hasExtraMesh = True
                    # outerContinue = False
                    # while hasExtraMesh:
                    #     # Check if there is another mesh(es) after this one
                    #     # without being in the offset list
                    #     #file.seek(12, os.SEEK_CUR) # Unknown bytes
                    #     startingPos = file.tell()

                    #     for skipV in range(0, 64):
                    #         U.readLong(file)
                    #         nextOffset = file.tell()
                    #         print(f"Looking for extra mesh: {nextOffset}")
                    #         outerContinue = False
                    #         if mi+1 < len(meshOffsets) and meshOffsets[mi+1] == nextOffset:
                    #             file.seek(startingPos, os.SEEK_SET) # Jump back to where we were
                    #             print(f"Next in list")
                    #             hasExtraMesh = False
                    #             outerContinue = True # Next pos is in the list
                    #             break

                    #         # Current pos is no the next item in the list
                    #         # and so may be a missed mesh

                    #         headerTest = U.readLong(file) # See if the header matches ????????
                    #         print(f"Long: {headerTest & 0x10000000} @ {file.tell()}")
                    #         if headerTest & 0x10000000 >= 0x10000000:
                    #             hasExtraMesh = True
                    #         else:
                    #             hasExtraMesh = False
                    #         file.seek(startingPos, os.SEEK_SET)
                    #         if hasExtraMesh:
                    #             print(f"reading extra mesh at {nextOffset} {file.tell()}")
                    #             meshes += CourseMesh._fromFile(file, nextOffset)
                            
                    #     # Break outer for loop from inner
                    #     if outerContinue:
                    #             continue

            # TODO: parse subfile 3 & 4
        print(f"Got {len(meshes)} meshes")
        return CourseModel("", meshes, textures)

class CourseMesh:

    def __init__(self, meshVertCount, meshVerts, meshNormals, meshUvs, meshFaces, meshColours):
        self.meshVertCount   = meshVertCount
        self.meshVerts       = meshVerts
        self.meshNormals     = meshNormals
        self.meshUvs         = meshUvs
        self.meshFaces       = meshFaces
        self.meshColours     = meshColours

    @staticmethod
    def _parseHeader(file):
        unkw0 = U.readLong(file)
        nullF0 = U.readLong(file)
        meshStartFlag = U.readLong(file)
        if meshStartFlag != 0x01000101:
            print(f"Mesh's start flag is different {meshStartFlag} from usual, continuing")
        unkw1 = U.readLong(file)
        if unkw1 == 0x6C018000:
            print(f"Got data marker {file.tell()}")
            # Odd version, just has data with very short header
            file.seek(-4, os.SEEK_CUR)
        else:
            sanityCheckFlag = U.readLong(file)
            # print(sanityCheckFlag & 0x8003)
            if sanityCheckFlag & 0x8003 >= 0x8003:
                # If this is missing then dont skip header, as its probably missing
                # print("Skipping full header")
                file.seek(44, os.SEEK_CUR) # Skip rest of unknown header
            else:
                print(f"Sanity check failed {file.tell()}")
        return unkw0, nullF0, meshStartFlag
    
    @staticmethod
    def _parseSubHeader(file):
        print(f"Parsing sub head {file.tell()}")
        shortHeaderType = U.readLong(file)
        skip = 44
        if shortHeaderType == 0x68058192:
            skip = 56
        sanityCheckFlag = U.readLong(file)
        # print(sanityCheckFlag & 0x8003)
        if sanityCheckFlag & 0x8003 == 0x8003:
            # If this is missing then dont skip header, as its probably missing
            # print("Skipping full header")
            file.seek(44, os.SEEK_CUR) # Skip rest of unknown header
        elif sanityCheckFlag & 0x8004 == 0x8004:
            # If this is missing then dont skip header, as its probably missing
            # print("Skipping full header")
            file.seek(skip, os.SEEK_CUR) # Skip rest of unknown header
        else:
            print(f"Sanity check failed {file.tell()}")
        return 0, 0, 0x01000101

    @staticmethod
    def _fromFile(file, offset, scale=1, subFile=0):
        meshes = []
        file.seek(offset, os.SEEK_SET)
        if subFile > 0:
            header = CourseMesh._parseSubHeader(file)    
        else:
            header = CourseMesh._parseHeader(file)
        if header[2] != 0x01000101:
            print("Skipping mesh as no mesh marker")
            return meshes
        # Read mesh
        meshFlag  = U.readLong(file)

        meshVerts = []
        meshNormals = []
        meshUvs = []
        meshFaces = []
        meshColours = []
        meshVertCount = 0

        hasExtraMesh = True
        # print(f"reading mesh at {file.tell()}")
        # Read chunk of verticies
        while meshFlag == 0x6c018000:
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
                # These seem to be ints saved as floats, 
                # and so may not be the normals
                nx, ny, nz = U.readXYZ(file)
                cr, cg, cb = U.readXYZ(file)
                U.readXYZ(file)
                tu, tv, tw = U.readXYZ(file)
                
                c = (cr, cg, cb, 255) # Convert to RGBA
                verts.append((vx * scale, vy * scale, vz * scale))
                normals.append((nx, ny, nz))
                colours.append(c)
                uvs.append((tu, 1-tv, tw))
            unkw3 = U.readShort(file)
            unkw4 = U.readShort(file)
            # Add faces
            faces = CourseMesh.createFaceList(vertCount)
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

            if subFile == 0 and meshFlag != 0x6c018000 and meshFlag & 0x68048192 >= 0x68048192: # Have seen 68058192
                while meshFlag != 0x6c018000 and meshFlag & 0x68048192 >= 0x68048192:
                    # Contains another mesh? that is missing the first 3 longs of the usual header
                    # Seemingly more files/more data, could be way to seperate different materials for textures
                    print(f"Extras found @ {file.tell()}")
                    if meshFlag == 0x68058192:
                        # Skip 
                        #file.seek(68, os.SEEK_CUR) # Skip second "header"
                        print(f"Entering sub2 load {subFile}")
                        meshes += CourseMesh._fromFile(file, file.tell()-4, scale, subFile+1)
                        print(f"Exiting sub2 load {subFile}")
                    elif meshFlag == 0x68048192:
                        # Skip 
                        #file.seek(52, os.SEEK_CUR) # Skip second "header"
                        print(f"Entering sub1 load {subFile}")
                        meshes += CourseMesh._fromFile(file, file.tell()-4, scale, subFile+1)
                        print(f"Exiting sub1 load {subFile}")
                    file.seek(-4, os.SEEK_CUR)
                    meshFlag = U.readLong(file)
                    
                meshFlag = 0x6c018000 # Force reading as mesh

            
        if meshVertCount > 0:
            meshes.append(CourseMesh(meshVertCount, meshVerts, meshNormals, meshUvs, meshFaces, meshColours))
            print(f"reading mesh at {offset} done {file.tell()}")
        return meshes

    @staticmethod
    def createFaceList(vertexCount, faceType=1):
        # Creates a list of indices that order how to draw the 
        # verticies in order of how to render the triangles
        faces = []
    
        if (faceType == 1):
            startDirection = -1
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

    def writeMeshToPly(self, fout):
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
            fx = self.meshFaces[i][0]-1
            fy = self.meshFaces[i][1]-1
            fz = self.meshFaces[i][2]-1
            
            fout.write(f"4 {fx} {fy} {fz}\n")

        # Write texture coordinates (uv)
        #for i in range(0, len(self.meshUvs)):
        #    tu = '{:.10f}'.format(self.meshUvs[i][0])
        #    tv = '{:.10f}'.format(self.meshUvs[i][1])
        #    fout.write(f"2 {tu} {tv}\n")
        