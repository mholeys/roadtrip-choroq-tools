import os
from abc import ABC, abstractmethod
from choroq.amesh import AMesh
import choroq.read_utils as U


class BHEMesh(AMesh):
    PRINT_DEBUG = False

    def __init__(self):
        self.texture_references = []
        self.faces = []
        self.uvs = []
        self.normals = []
        self.vertices = []
        self.colours = []
        self.vert_count = 0

    # Creates OBJ file, of the meshes
    # The format includes Vertices, Vertex Normals,
    # Texture coordinates and Faces
    @abstractmethod
    def write_mesh_to_obj(self, fout, start_index=0, material=None, with_colours=False):
        # See below
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

    def write_mesh_to_obj(self, fout, start_index=0, material=None, with_colours=False):
        face_count = 0
        if material is not None:
            fout.write(f"usemtl {material}\n")
        fout.write("s off\n")
        # Write vertices
        for i in range(0, self.vert_count):
            vx = '{:.20f}'.format(self.vertices[i][0])
            vy = '{:.20f}'.format(self.vertices[i][1])
            vz = '{:.20f}'.format(self.vertices[i][2])
            fout.write(f"v {vx} {vy} {vz}\n")
        fout.write("#" + str(self.vert_count) + " vertices\n")

        # Write normals
        for i in range(0, len(self.normals)):
            nx = '{:.20f}'.format(self.normals[i][0])
            ny = '{:.20f}'.format(self.normals[i][1])
            nz = '{:.20f}'.format(self.normals[i][2])
            fout.write("vn " + nx + " " + ny + " " + nz + "\n")
        fout.write("#" + str(len(self.normals)) + " vertex normals\n")

        # Write texture coordinates (uv)
        for i in range(0, len(self.uvs)):
            tu = '{:.20f}'.format(self.uvs[i][0])
            tv = '{:.20f}'.format(self.uvs[i][1])
            fout.write("vt " + tu + " " + tv + "\n")
        fout.write("#" + str(len(self.uvs)) + " texture vertices\n")

        faces, other_faces = self.faces
        fout.write("g 0\n")
        face_count += BHEMesh.write_obj_faces(fout, other_faces)

        for tex_ref in faces:
            if tex_ref >= len(self.texture_references) or tex_ref < 0:
                if len(self.texture_references) > 0:
                    print("Bad texture reference got through!!")

            fout.write(f"g {tex_ref + 1}\n")
            if 0 <= tex_ref < len(self.texture_references):
                texture_name = self.texture_references[tex_ref][0]
                fout.write(f"usemtl {texture_name}\n")
            face_count += BHEMesh.write_obj_faces(fout, faces[tex_ref])

        return self.vert_count

    def save_material_file_obj(self, fout, texture_path):
        faces, other_faces = self.faces
        for tex_ref in faces:
            if tex_ref >= len(self.texture_references) or tex_ref < 0:
                if len(self.texture_references) > 0:
                    print("Bad texture reference got through!!")
                continue
            texture_name = self.texture_references[tex_ref][0]
            fout.write(f"newmtl {texture_name}\n")
            fout.write("Ka 1.000 1.000 1.000\n")  # ambient colour
            fout.write("Kd 1.000 1.000 1.000\n")  # diffused colour
            fout.write("Ks 0.000 0.000 0.000\n")  # Specular colour
            # fout.write("Ns 100") # specular exponent
            fout.write("d 1.0\n")
            fout.write(f"map_Ka {texture_path}/{texture_name}.png\n")  # Path to ambient texture (relative)
            # the diffuse texture map (most of the time, it will be the same
            fout.write(f"map_Kd {texture_path}/{texture_name}.png\n")  # Path to diffuse texture (relative)
            fout.write("\n")

    @staticmethod
    def write_obj_faces(fout, faces):
        face_count = 0
        for fv, fvn, fvt, fvc in faces:
            fv1 = fv[0] + 1
            fv2 = fvn[0] + 1
            fv3 = fvt[0] + 1
            fn1 = fv[1] + 1
            fn2 = fvn[1] + 1
            fn3 = fvt[1] + 1
            fuv1 = fv[2] + 1
            fuv2 = fvn[2] + 1
            fuv3 = fvt[2] + 1
            if fv1 == 65536:
                fv1 = ""
            if fv2 == 65536:
                fv2 = ""
            if fv3 == 65536:
                fv3 = ""
            if fn1 == 65536:
                fn1 = ""
            if fn2 == 65536:
                fn2 = ""
            if fn3 == 65536:
                fn3 = ""
            if fuv1 == 65536:
                fuv1 = ""
            if fuv2 == 65536:
                fuv2 = ""
            if fuv3 == 65536:
                fuv3 = ""

            fout.write(f"f {fv1}/{fuv1}/{fn1} {fv2}/{fuv2}/{fn2} {fv3}/{fuv3}/{fn3} \n")
            # fout.write(f"f {fv1} {fv2} {fv3} \n")
            face_count += 1
        return face_count

    @staticmethod
    def read_faces(file, texture_references):
        if BHEMesh.PRINT_DEBUG:
            print(f"Faces section start: {file.tell()}")
        # Read faces
        # Size of face list
        face_group_count = U.readLong(file)
        faces = {}
        other_faces = []

        if face_group_count > 70000:
            print(f"Reading loads of face groups {face_group_count} {file.tell()}")

        for i in range(face_group_count):
            val1_known = [0x1C, 0x0C, 0x1D, 0x4, 0x5C, 0x5B, 0x1B, 0x0B]
            value1 = U.BreadShort(file)  # 1C
            # texture assignment, from texture list (by name) at the start
            texture_index = U.BreadShort(file)
            face_type = U.readShort(file)  # This might not be useful, but it varies
            face_filler = U.readShort(file)  # This might not be useful, but its either 0 or FFFF

            file.seek(4, os.SEEK_CUR)
            strip_count = U.readLong(file)
            if strip_count > 70000:
                print(f"Reading loads of strips {strip_count}")
            tri_strips = []

            for f in range(strip_count):
                fv, fvn, fvt, fvc = BHEMesh.read_face(file, face_filler)
                tri_strips.append((fv, fvn, fvt, fvc))

            # Convert tri_strips to normal face list
            face_indices = AMesh.create_face_list(strip_count, vert_count_offset=-1)
            face_list = []
            for fi in face_indices:
                face_list.append((tri_strips[fi[0]], tri_strips[fi[1]], tri_strips[fi[2]], 0))
            if texture_index == 0xFFFF:
                texture_index = 0
            if texture_index > len(texture_references):
                other_faces += face_list
            else:
                if texture_index not in faces:
                    faces[texture_index] = []
                faces[texture_index] += face_list

        return faces, other_faces

    @staticmethod
    def read_face(file, face_filler):
        fv, fvn, fvt, fvc = -2, -2, -2, 0
        fv = U.readShort(file)  # Vert index
        fvn = U.readShort(file)  # Normal index
        fvt = U.readShort(file)  # UV index
        fvc = U.readShort(file)  # Colour index

        # Correct parts that are missing to be skipped e.g f1//f3 vs f1/f2/f3, total guess
        if face_filler == 1:
            if BHEMesh.PRINT_DEBUG:
                print(f"found face filler value of 1: @ {file.tell()}")
            fv = 0xFFFF
        if face_filler == 2:
            if BHEMesh.PRINT_DEBUG:
                print(f"found face filler value of 2: @ {file.tell()}")
            fvn = 0xFFFF
        if face_filler == 3:
            if BHEMesh.PRINT_DEBUG:
                print(f"found face filler value of 3: @ {file.tell()}")
            fvt = 0xFFFF
        if face_filler == 4:
            if BHEMesh.PRINT_DEBUG:
                print(f"found face filler value of 4: @ {file.tell()}")
            vc = 0xFFFF

        pp = file.tell()  # Debugging

        return fv, fvn, fvt, fvc

