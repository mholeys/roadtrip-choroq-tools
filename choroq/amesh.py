from abc import ABC, abstractmethod

class AMesh(ABC):

    # Creates OBJ file, of the meshes
    # The format includes Verticies, Vertex Normals, 
    # Texture coords and Faces
    @abstractmethod
    def writeMeshToObj(self, fout, startIndex = 0):
        pass

    # Custom file format for use in importing into unity
    # Based on the ply format, but without any compatability, and no header.
    # Needed in order to store all meshes in single file
    @abstractmethod
    def writeMeshToComb(self, fout, startIndex = 0):
        pass

    # Creates PLY file, of the meshes in custom format to include colours
    # The format includes Verticies, Vertex Normals, 
    # Vertex colours, Texture coords and Faces
    @abstractmethod
    def writeMeshToPly(self, fout, startIndex = 0):
        pass

    # Creates a file with all available data from the file, usually in an
    # OBJ file format but one that does not comply with the usual waveform
    # file formats, may include extras that are yet to be understood.
    # This may match the OBJ file if everything is understood 
    # (Data may be missing in obj format)
    @abstractmethod
    def writeMeshToDBG(self, fout, startIndex = 0):
        pass

    def writeMeshToType(self, type, fout, startIndex = 0):
        type = type.lower()
        if type == "dbg":
            return self.writeMeshToDBG(fout, startIndex)
        elif type == "obj":
            return self.writeMeshToObj(fout, startIndex)
        elif type == "comb":
            return self.writeMeshToComb(fout, startIndex)
        else:
            # Default to ply
            return self.writeMeshToPly(fout, startIndex)
    

    # Creates a list of indices that order how to draw the 
    # verticies in order of how to render the triangles
    # Credit due to killercracker https://forum.xentax.com/viewtopic.php?t=17567
    @staticmethod
    def createFaceList(vertexCount, faceType=1, startDirection=-1):
        faces = []

        if faceType == 1:
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
        if faceType == 2:
            x = 0
            a = 0
            b = 0
            
            f1 = a + 1
            f2 = b + 1
            faceDirection = startDirection
            while (x < vertexCount + 2):
                x += 1
                
                f3 = x
                if f3 > vertexCount:
                    f3 = x % vertexCount
                print(f"F3: {f3} x{x} vc{vertexCount}")
                faceDirection *= -1
                if (f1 != f2) and (f2 != f3) and (f3 != f1):
                    if (faceDirection > 0):
                        faces.append((f1, f2, f3))
                    else:
                        faces.append((f1, f3, f2))
                f1 = f2
                f2 = f3
        elif faceType == 3:
            # Do faces on both sides
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
                    faces.append((f1, f2, f3))
                    faces.append((f1, f3, f2))
                f1 = f2
                f2 = f3
        elif faceType == 0:
            a = 0
            b = 0
            c = 0
            
            for x in range(0, vertexCount, 3):
                a = x
                b = x+1
                c = x+2
                faces.append((a+1, b+1, c+1))
        return faces