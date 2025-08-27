import os
import choroq.read_utils as U
from choroq.amesh import AMesh


class PBLModel(AMesh):
    STOP_ON_NEW = False

    def __init__(self, name, first_section, vert_count, vertices, normal_count, normals, uv_count, uvs, face_group_count, faces):
        self.name = name
        self.first_section = first_section
        self.vert_count = vert_count
        self.vertices = vertices
        self.normal_count = normal_count
        self.normals = normals
        self.uv_count = uv_count
        self.uvs = uvs
        self.face_group_count = face_group_count
        self.faces = faces

    @staticmethod
    def read_pbl(file, offset):
        file.seek(offset, os.SEEK_SET)
        pbls = []

        # Read PBL header
        magic = file.read(4)
        if magic != b'PBL\x00':
            print(f"PBL header invalid at @ {file.tell()}")
            return

        subfile_count = U.readLong(file)
        subfile_offsets = []
        for i in range(subfile_count):
            subfile_offsets.append(offset + U.readLong(file))

        last_name = "unset"
        for o in subfile_offsets:
            file.seek(o, os.SEEK_SET)
            print(f"Reading PBL section from {file.tell()}")
            # Read single PBL section
            sizes = []
            for i in range(8):
                sizes.append(U.readLong(file))

            name = f"{last_name}-{o}"
            names = []
            for i in range(sizes[0]):
                print(f"Header name next: {file.tell()}")
                # Unsure on value usage, might be name/texture related
                U.readShort(file)
                U.readShort(file)
                U.readShort(file)
                file.seek(10, os.SEEK_CUR)
                name = file.read(16).decode("ascii").rstrip('\00')
                names.append(name)
                last_name = name
                name = names[0]
            print(f"Names: {names}")
            print(f"Name: {name}")

            # Unknown section, might be position/colour its floats * 8
            print(f"Float section start: {file.tell()}")
            floats_first_section = []
            for i in range(sizes[6]):
                floats_first_section.append(U.readXYZW(file))
                floats_first_section.append(U.readXYZW(file))

            print(f"Vert section start: {file.tell()}")
            # Data starts
            # XYZ(W)
            verts = []
            for i in range(sizes[1]):
                verts.append(U.readXYZW(file))

            print(f"Normal section start: {file.tell()}")
            # Normals
            normals = []
            for i in range(sizes[2]):
                normals.append(U.readXYZW(file))

            print(f"UVs section start: {file.tell()}")
            # UV
            uvs = []
            for i in range(sizes[3]):
                uvs.append((U.readFloat(file), 1-U.readFloat(file)))

            print(f"Vertex colour section start: {file.tell()}")
            # Vertex Colours
            for i in range(sizes[4]):
                U.BreadLong(file)

            print(f"Faces section start: {file.tell()}")
            # Read faces
            # Size of face list
            face_group_count = U.readLong(file)
            faces = []

            for i in range(face_group_count):
                val1_known = [0x1C, 0x0C, 0x1D, 0x4, 0x5C, 0x5B, 0x1B, 0x0B]
                value1 = U.BreadShort(file)  # 1C
                if value1 not in val1_known:
                    print(f"Face start value not as expected 1C != {value1:x} at {file.tell()}")
                    if PBLModel.STOP_ON_NEW:
                        exit()
                val2_known = [0, 0xFFFF, 1, 2]  # 1 and 2 seems same as 0
                value2 = U.BreadShort(file)  # 0000 or FFFF
                if value2 not in val2_known:
                    print(f"New face value2 found @ {file.tell()} value is {value2:x}")
                    if PBLModel.STOP_ON_NEW:
                        exit()
                # Read faces
                face_type = U.readShort(file)  # This might not be useful, but it varies
                face_filler = U.readShort(file)  # This might not be useful, but its either 0 or FFFF
                # values seen, I think FFFF part might be a value that says if you
                # see FFFF then that means that one is not included .e.g no UV index
                if (face_filler < 0 or face_filler > 3) and face_filler != 0xFFFF:
                    print(f"Face filler different @{file.tell()} value is {face_filler:x}")
                    if PBLModel.STOP_ON_NEW:
                        exit()
                known_types = list(range(0, 0x33)) + [0xFFFF]
                if face_type not in known_types:
                    print(f"New face size/type found @ {file.tell()} value is {face_type:x}")
                    if PBLModel.STOP_ON_NEW:
                        exit()

                file.seek(4, os.SEEK_CUR)
                strip_count = U.readLong(file)
                tri_strips = []
                face_type_a = known_types
                # face_type_b = [, ]
                for f in range(strip_count):
                    fv, fvn, fvt, fvc = -2, -2, -2, 0
                    if face_type in face_type_a:
                        fv = U.readShort(file)  # Vert index
                        fvn = U.readShort(file)  # Normal index
                        fvt = U.readShort(file)  # UV index
                        fvc = U.readShort(file)  # Colour index
                        # if value1 == 0x5c:
                        #     # 0x5C seems to have 4 values, with the 4th being 1/0 so far
                        #     if fvc != 1 and fvc != 0:
                        #         print(f"Found face 0x5C with 4th being != 1 {fvc} @ {file.tell()}")
                        #         if STOP_ON_NEW:
                        #             exit()
                    # Correct parts that are missing to be skipped e.g f1//f3 vs f1/f2/f3, total guess
                    if face_filler == 1:
                        print(f"found face filler value of 1: @ {file.tell()}")
                        fv = 0xFFFF
                    if face_filler == 2:
                        print(f"found face filler value of 2: @ {file.tell()}")
                        fvn = 0xFFFF
                    if face_filler == 3:
                        print(f"found face filler value of 3: @ {file.tell()}")
                        fvt = 0xFFFF
                    if face_filler == 4:
                        print(f"found face filler value of 4: @ {file.tell()}")
                        vc = 0xFFFF
                    pp = file.tell()  # Debugging
                    if value2 > 0:
                        for t in range(value2):
                            tri_strips.append((fv, fvn, fvt, fvc))
                    else:
                        tri_strips.append((fv, fvn, fvt, fvc))

                # Convert tri_strips to normal face list
                face_indices = AMesh.create_face_list(strip_count, vert_count_offset=-1)
                face_list = []
                for fi in face_indices:
                    face_list.append((tri_strips[fi[0]], tri_strips[fi[1]], tri_strips[fi[2]], 0))
                faces += face_list

            pbls.append(PBLModel(name, floats_first_section, sizes[1], verts, sizes[2], normals, sizes[3], uvs, face_group_count, faces))

        return pbls

    def write_mesh_to_obj(self, fout, start_index=0, material=None, with_colours=False):
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

        # Write mesh face order/list
        face_count = 0
        for fv, fvn, fvt, fvc in self.faces:
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

            face_count += 1

        fout.write(f"#{str(face_count)} faces in {self.face_group_count}\n")

        return self.vert_count

    def write_mesh_to_comb(self, fout, start_index=0, material=None):
        return 0

    def write_mesh_to_ply(self, fout, start_index=0):
        return 0

    def write_mesh_to_dbg(self, fout, start_index=0, material=None):
        return self.write_mesh_to_obj(fout, start_index, material, True)

