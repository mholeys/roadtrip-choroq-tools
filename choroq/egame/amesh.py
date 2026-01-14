from abc import ABC, abstractmethod


class AMesh(ABC):

    # Creates OBJ file, of the meshes
    # The format includes Vertices, Vertex Normals,
    # Texture coordinates and Faces
    @abstractmethod
    def write_mesh_to_obj(self, fout, start_index=0, material=None, with_colours=False):
        pass

    # Custom file format for use in importing into unity
    # Based on the ply format, but without any compatibility, and no header.
    # Needed in order to store all meshes in single file, with all original data
    @abstractmethod
    def write_mesh_to_comb(self, fout, start_index=0, material=None):
        pass

    # Creates PLY file, of the meshes in custom format to include colours
    # The format includes Vertices, Vertex Normals,
    # Vertex colours, Texture coordinates and Faces
    @abstractmethod
    def write_mesh_to_ply(self, fout, start_index=0):
        pass

    # Creates a file with all available data from the file, usually in an
    # OBJ file format but one that does not comply with the usual waveform
    # file formats, may include extras that are yet to be understood.
    # This may match the OBJ file if everything is understood 
    # (Data may be missing in obj format)
    @abstractmethod
    def write_mesh_to_dbg(self, fout, start_index=0, material=None):
        pass

    def write_mesh_to_type(self, output_type, fout, start_index=0, material=None):
        output_type = output_type.lower()
        if output_type == "dbg":
            return self.write_mesh_to_dbg(fout, start_index, material)
        elif output_type == "obj" or output_type == "obj+colour":
            return self.write_mesh_to_obj(fout, start_index, material, output_type == "obj+colour")
        elif output_type == "comb":
            return self.write_mesh_to_comb(fout, start_index, material)
        else:
            # Default to ply
            return self.write_mesh_to_ply(fout, start_index)

    # Creates a list of indices that order how to draw the 
    # vertices in order of how to render the triangles
    # Credit due to killercracker https://forum.xentax.com/viewtopic.php?t=17567
    @staticmethod
    def create_face_list(vertex_count, face_type=1, start_direction=-1, vert_count_offset=0):
        faces = []

        if face_type == 1:
            x = 0
            a = 0
            b = 0
            
            f1 = a + 1
            f2 = b + 1
            face_direction = start_direction
            while x < vertex_count:
                x += 1
                
                f3 = x
                face_direction *= -1
                if (f1 != f2) and (f2 != f3) and (f3 != f1):
                    if face_direction > 0:
                        faces.append((vert_count_offset + f1, vert_count_offset + f2, vert_count_offset + f3))
                    else:
                        faces.append((vert_count_offset + f1, vert_count_offset + f3, vert_count_offset + f2))
                f1 = f2
                f2 = f3
        if face_type == 2:
            x = 0
            a = 0
            b = 0
            
            f1 = a + 1
            f2 = b + 1
            face_direction = start_direction
            while x < vertex_count + 2:
                x += 1
                
                f3 = x
                if f3 > vertex_count:
                    f3 = x % vertex_count
                print(f"F3: {f3} x{x} vc{vertex_count}")
                face_direction *= -1
                if (f1 != f2) and (f2 != f3) and (f3 != f1):
                    if face_direction > 0:
                        faces.append((vert_count_offset + f1, vert_count_offset + f2, vert_count_offset + f3))
                    else:
                        faces.append((vert_count_offset + f1, vert_count_offset + f3, vert_count_offset + f2))
                f1 = f2
                f2 = f3
        elif face_type == 3:
            # Do faces on both sides
            x = 0
            a = 0
            b = 0
            
            f1 = a + 1
            f2 = b + 1
            face_direction = start_direction
            while x < vertex_count:
                x += 1
                
                f3 = x
                face_direction *= -1
                if (f1 != f2) and (f2 != f3) and (f3 != f1):
                    faces.append((vert_count_offset + f1, vert_count_offset + f2, vert_count_offset + f3))
                    faces.append((vert_count_offset + f1, vert_count_offset + f3, vert_count_offset + f2))
                f1 = f2
                f2 = f3
        elif face_type == 0:
            a = 0
            b = 0
            c = 0
            
            for x in range(0, vertex_count, 3):
                a = x
                b = x+1
                c = x+2
                faces.append((vert_count_offset + a+1, vert_count_offset + b+1, vert_count_offset + c+1))
        return faces
