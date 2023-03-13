
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
# Looks like array of floats? could be colors, or maybe 
# texture mapping info, on how to link texture x to model y
# Does not look like mesh data as does not contain 0x6c018000
# Does contain float, float, float, 1 groups after 0x610 for c00
# TODO:
#
# File 4: 
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
            magic = U.readLong(file)
            file.seek(offset+o, os.SEEK_SET)
            print(f"offset {offset + o} magic :{magic}")
            
            if CourseModel.matchesTextureMagic(magic):
                # File is possibly a texture

                # pass
                textureMax = 0
                # TODO: parse more than 1 texture
                
                print(f"Parsing texture @ {offset+o} {magic & 0x10120006} {magic & 0x10400006}")
                textures.append(Texture._fromFile(file, offset+o))
                nextTextureOffset = file.tell()
                nextTexture = U.readLong(file)
                file.seek(nextTextureOffset, os.SEEK_SET)

                print(f"nextTextureOffset {nextTextureOffset}")
                print(f"nextTexture {nextTexture}")

                while CourseModel.matchesTextureMagic(nextTexture):
                    # Then we have more that 1 texture
                    textureMax += 1
                    textures.append(Texture._fromFile(file, nextTextureOffset))
                    nextTextureOffset = file.tell()
                    nextTexture = U.readLong(file)
                    file.seek(nextTextureOffset, os.SEEK_SET)
                    print(f"nextTextureOffset {nextTextureOffset}")
                    print(f"nextTexture {nextTexture}")
                print(file.tell())
                
            elif magic == 0x190:
                pass
                # Subfile is meshes/models
                print(f"Parsing meshes at {offset+o}")
                # Parse mesh offset list, 0 == end of list
                meshOffsets = []
                meshOffsets.append(U.readLong(file))
                while meshOffsets[-1] != 0:
                    meshOffsets.append(U.readLong(file))
                # Parse each mesh
                print(meshOffsets)
                print(len(meshOffsets))
                for mi,mo in enumerate(meshOffsets):
                    #print(f"reading mesh {len(meshes)} at {offset+o+mo} {offset} {o} {mo}")
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
                    if oi == 4:
                        mapMeshes += extra.meshes
                    else:
                        extras.append(extra)


            # TODO: parse subfile 3 & 4
        print(f"Got {len(meshes)} meshes")
        return CourseModel("", meshes, textures, colliders, mapMeshes, extras)

class CourseMesh(AMesh):

    def __init__(self, meshVertCount = [], meshVerts = [], meshNormals = [], meshUvs = [], meshFaces = [], meshColours = [], meshExtras = []):
        self.meshVertCount   = meshVertCount
        self.meshVerts       = meshVerts
        self.meshNormals     = meshNormals
        self.meshUvs         = meshUvs
        self.meshFaces       = meshFaces
        self.meshColours     = meshColours
        self.meshExtras      = meshExtras

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
                headBytes = ""
                for a in range(0, 44):
                    val = U.readByte(file)
                    if val < 0x10:
                        headBytes += f"0{hex(val)[2:4].upper()} "
                    else:
                        headBytes += f"{hex(val)[2:4].upper()} "
                print(headBytes)
                #file.seek(44, os.SEEK_CUR) # Skip rest of unknown header
            else:
                print(f"Sanity check failed {file.tell()}")
        return unkw0, nullF0, meshStartFlag
    
    @staticmethod
    def _parseSubHeader(file):
        # print(f"Parsing sub head {file.tell()}")
        shortHeaderType = U.readLong(file)
        skip = 44
        if shortHeaderType == 0x68058192:
            skip = 56
        sanityCheckFlag = U.readLong(file)
        # print(sanityCheckFlag & 0x8003)
        if sanityCheckFlag & 0x8003 == 0x8003:
            # If this is missing then dont skip header, as its probably missing
            # print("Skipping full header")
            # file.seek(44, os.SEEK_CUR) # Skip rest of unknown header
            headBytes = ""
            for a in range(0, 44):
                val = U.readByte(file)
                if val < 0x10:
                    headBytes += f"0{hex(val)[2:4].upper()} "
                else:
                    headBytes += f"{hex(val)[2:4].upper()} "
            print(f"{headBytes} {file.tell()}")
        elif sanityCheckFlag & 0x8004 == 0x8004:
            # If this is missing then dont skip header, as its probably missing
            # print("Skipping full header")
            # file.seek(skip, os.SEEK_CUR) # Skip rest of unknown header
            headBytes = ""
            for a in range(0, skip):
                val = U.readByte(file)
                if val < 0x10:
                    headBytes += f"0{hex(val)[2:4].upper()} "
                else:
                    headBytes += f"{hex(val)[2:4].upper()} "
            print(f"{headBytes} {file.tell()}")
        else:
            print(f"SUBSanity check failed {file.tell()}")

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
            # print("Skipping mesh, no mesh marker")
            return meshes

        # Read mesh
        meshFlag = U.readLong(file)

        meshVerts = []
        meshNormals = []
        meshUvs = []
        meshFaces = []
        meshColours = []
        meshExtras = []
        meshVertCount = 0

        hasExtraMesh = True
        
        # Read chunk of verticies
        while meshFlag == 0x6c018000:
            verts = [] 
            uvs = []
            normals = []
            faces = []
            colours = []
            extras = []
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
                fx, fy, fz = U.readXYZ(file)
                tu, tv, tw = U.readXYZ(file)
                
                c = (cr, cg, cb, 255) # Convert to RGBA
                verts.append((vx * -scale, vy * scale, vz * scale))
                normals.append((nx, ny, nz))
                colours.append(c)
                extras.append((fx, fy, fz))
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
            meshExtras += extras

            # See if there are more verticies/meshes we need to read
            meshFlag = U.readLong(file)
            isSubfile = subFile == 0
            isNewMesh = meshFlag == 0x6c018000
            isSubFlag = meshFlag & 0x68048192 >= 0x68048192 # Have seen 68058192
            if subFile or isNewMesh:
                # Process the next chunk as normal, and not as extras
                continue

            subFileCount = 0

            # There is more data to be parsed for this chunk, treating as sub file
            if isSubFlag: 
                # Check for end of extras section/start of new mesh
                while meshFlag != 0x6c018000 and meshFlag & 0x68048192 >= 0x68048192:
                    # Contains another ?mesh? that is missing the first 3 longs of the usual header
                    # Seemingly more files/more data, could be a way to seperate different materials for textures
                    
                    if meshFlag == 0x68058192:
                        # Skip 
                        #file.seek(68, os.SEEK_CUR) # Skip second "header"
                        # print(f"Entering sub2 load {subFile}")
                        meshes += CourseMesh._fromFile(file, file.tell()-4, scale, subFile+1)
                        subFileCount += 1
                        # print(f"Exiting sub2 load {subFile}")
                    elif meshFlag == 0x68048192:
                        # Skip 
                        #file.seek(52, os.SEEK_CUR) # Skip second "header"
                        # print(f"Entering sub1 load {subFile}")
                        meshes += CourseMesh._fromFile(file, file.tell()-4, scale, subFile+1)
                        subFileCount += 1
                        # print(f"Exiting sub1 load {subFile}")
                    else:
                        print(f"SubMesh with different flag {meshFlag} @ {file.tell()}")
                    file.seek(-4, os.SEEK_CUR)
                    meshFlag = U.readLong(file)
                    
                meshFlag = 0x6c018000 # Force reading as mesh
                print(subFileCount)

            
        if meshVertCount > 0:
            meshes.append(CourseMesh(meshVertCount, meshVerts, meshNormals, meshUvs, meshFaces, meshColours, meshExtras))
            # print(f"reading mesh at {offset} done {file.tell()}")
        # print(f"len {file.tell()-offset}")
        return meshes

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
        fout.write("#" + str(len(self.meshNormals)) + " vertex normals\n")
        
        # Write texture coordinates (uv)
        for i in range(0, len(self.meshUvs)):
            tu = '{:.20f}'.format(self.meshUvs[i][0])
            tv = '{:.20f}'.format(self.meshUvs[i][1])
            fout.write("vt " + tu + " " + tv + "\n")
        fout.write("#" + str(len(self.meshUvs)) + " texture vertices\n")
        
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
        
    def writeMeshToDBG(self, fout):
        for i in range(0, len(self.meshVerts)):
            vx = '{:.20f}'.format(self.meshVerts[i][0])
            vy = '{:.20f}'.format(self.meshVerts[i][1])
            vz = '{:.20f}'.format(self.meshVerts[i][2])
            fout.write("v " + vx + " " + vy + " " + vz + "\n")
            nx = '{:.20f}'.format(self.meshNormals[i][0])
            ny = '{:.20f}'.format(self.meshNormals[i][1])
            nz = '{:.20f}'.format(self.meshNormals[i][2])
            fout.write("vn " + nx + " " + ny + " " + nz + "\n")
            tu = '{:.20f}'.format(self.meshUvs[i][0])
            tv = '{:.20f}'.format(self.meshUvs[i][1])
            tw = '{:.20f}'.format(self.meshUvs[i][2])
            fout.write(f"vt {tu} {tv} {tw}\n")
            cr = '{:d}'.format(math.trunc(self.meshColours[i][0]))
            cg = '{:d}'.format(math.trunc(self.meshColours[i][1]))
            cb = '{:d}'.format(math.trunc(self.meshColours[i][2]))
            ca = '{:d}'.format(math.trunc(self.meshColours[i][3]))
            fout.write(f"c {cr} {cg} {cb} {ca}\n")
            ex = self.meshExtras[i][0]
            ey = self.meshExtras[i][1]
            ez = self.meshExtras[i][2]
            fout.write(f"e {ex} {ey} {ez}\n")

        for i in range(0, len(self.meshFaces)):
            fx = self.meshFaces[i][0]
            fy = self.meshFaces[i][1]
            fz = self.meshFaces[i][2]
            fout.write(f"f {fx} {fy} {fz}\n")

        fout.write("#" + str(len(self.meshVerts)) + " vertices\n")            
        fout.write("#" + str(len(self.meshNormals)) + " vertex normals\n")            
        fout.write("#" + str(len(self.meshUvs)) + " texture vertices\n")
        fout.write("#" + str(len(self.meshExtras)) + " texture vertices\n")
        fout.write("#" + str(len(self.meshFaces)) + " faces\n")
        

class CourseCollider(AMesh):

    def __init__(self, meshVertCount = [], meshVerts = [], meshNormals = [], meshFaces = []):
        self.meshVertCount   = meshVertCount
        self.meshVerts       = meshVerts
        self.meshNormals     = meshNormals
        self.meshFaces       = meshFaces

    @staticmethod
    def fromFile(file, offset):
        file.seek(offset, os.SEEK_SET)

        # Read in offset table and unknown table of shorts
        offsets = []
        for i in range(0, int(1024/4)):
            offsets.append(U.readLong(file))
        # offsets = U.remove_duplicates(offsets)

        shortsTable = []
        for i in range(0, int(512/2)):
            shortsTable.append(U.readShort(file))

        while offsets[-1] == offsets[-2]:
            # Remove all duplicate ending offsets
            offsets = offsets[:-1]

        # This might be colours
        lastOffset = U.readLong(file) # Last offset is just before the first offset's data
        lastSize = U.readLong(file) # This is the number of floats to read

        colliders = []
        scale = 1
        
        totalVerts = 0

        # Read the mesh data between this offset and the next
        for oi,o in enumerate(offsets[:-1]):
            file.seek(offset + o, os.SEEK_SET)

            meshVerts = []
            meshNormals = []
            meshUvs = []
            meshFaces = []
            meshColours = []
            meshVertCount = 0
        
            hasMore = True
            while hasMore:

                if file.tell() > offset+offsets[oi+1]:
                    hasMore = False
                    break
                vertCount = U.readByte(file)
                
                if U.readByte(file) != 0x80:
                    hasMore = False
                    file.seek(-1, os.SEEK_CUR)
                    print(f"probably at wrong position {file.tell()} {oi} {o}")
                    break
                U.readShort(file) # always 0000
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

            colliders.append(CourseCollider(meshVertCount, meshVerts, meshNormals, meshFaces))

            meshVerts = []
            meshNormals = []
            meshUvs = []
            meshFaces = []
            meshColours = []
            meshVertCount = 0

        
        # Process the last chunk, x,y,z,y2 forman and re-uses x/y for doing posts/towers
        file.seek(offset + lastOffset, os.SEEK_SET)
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


        
        # meshVertCount += len(verts)
        # meshVerts += verts
        # meshNormals += normals

        # colliders.append(CourseCollider(meshVertCount, meshVerts, meshNormals, meshFaces))

        return colliders

    @staticmethod
    def parseChunk(file, vertCount, scale):
        verts = []
        normals = []
        faces = []

        # Read in verticies
        for x in range(0, vertCount):
            vx, vy, vz = U.readXYZ(file)
            vw = U.readLong(file) # 1.0f
            verts.append((vx * -scale, vy * scale, vz * scale))

        # Read in normals
        if vertCount <= 40 and vertCount >= 3:
            for n in range(vertCount-2):
                normals.append(U.readXYZ(file))
                U.readLong(file) # 1.0f

        faces = CourseCollider.createFaceList(vertCount)
        return verts, normals, faces

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
        fout.write("#" + str(len(self.meshNormals)) + " vertex normals\n")
        
        # Write mesh face order/list
        for i in range(0, len(self.meshFaces)):
            fx = self.meshFaces[i][0]
            fy = self.meshFaces[i][1]
            fz = self.meshFaces[i][2]
            
            fout.write(f"f {fx} {fy} {fz}\n")
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
        
        # Write mesh face order/list
        for i in range(0, len(self.meshFaces)):
            fx = self.meshFaces[i][0]-1
            fy = self.meshFaces[i][1]-1
            fz = self.meshFaces[i][2]-1
            
            fout.write(f"4 {fx} {fy} {fz}\n")
        
    def writeMeshToDBG(self, fout):
        for i in range(0, len(self.meshVerts)):
            vx = '{:.20f}'.format(self.meshVerts[i][0])
            vy = '{:.20f}'.format(self.meshVerts[i][1])
            vz = '{:.20f}'.format(self.meshVerts[i][2])
            fout.write("v " + vx + " " + vy + " " + vz + "\n")
            nx = '{:.20f}'.format(self.meshNormals[i][0])
            ny = '{:.20f}'.format(self.meshNormals[i][1])
            nz = '{:.20f}'.format(self.meshNormals[i][2])
            fout.write("vn " + nx + " " + ny + " " + nz + "\n")
            
            # ex = self.meshExtras[i][0]
            # ey = self.meshExtras[i][1]
            # ez = self.meshExtras[i][2]
            # fout.write(f"e {ex} {ey} {ez}\n")

        for i in range(0, len(self.meshFaces)):
            fx = self.meshFaces[i][0]
            fy = self.meshFaces[i][1]
            fz = self.meshFaces[i][2]
            fout.write(f"f {fx} {fy} {fz}\n")

        fout.write("#" + str(len(self.meshVerts)) + " vertices\n")      
        fout.write("#" + str(len(self.meshNormals)) + " texture vertices\n")
        fout.write("#" + str(len(self.meshFaces)) + " faces\n")