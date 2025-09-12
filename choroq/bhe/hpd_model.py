import os
import choroq.read_utils as U
from choroq.amesh import AMesh
from choroq.bhe.bhe_mesh import BHEMesh


# Hit Polygon Data
class HPDModel(BHEMesh):
    STOP_ON_NEW = False
    PRINT_DEBUG = False

    def __init__(self, texture_references, vert_count, vertices, normal_count, normals, uv_count, uvs, faces):
        super().__init__()
        self.texture_references = texture_references
        self.vert_count = vert_count
        self.vertices = vertices
        self.normal_count = normal_count
        self.normals = normals
        self.uv_count = uv_count
        self.uvs = uvs
        self.faces = faces
        # Max value of face indices, maximum index for vertex
        self.max_vert = len(vertices)
        self.max_normal = len(normals)
        self.max_uv = len(uvs)
        self.max_colour = 0

    @staticmethod
    def read_hpd(file, offset):
        file.seek(offset, os.SEEK_SET)
        hpds = []

        # Read HPD header
        magic = file.read(4)
        if magic != b'HPD\x00':
            print(f"HPD header invalid at @ {file.tell()}")
            return

        hpd_size = U.readLong(file)

        floats_offset = U.readLong(file)  # Vertex Top ("v_top")
        verts_size = U.readLong(file)     # Vertex Total ("v_total")

        normals_offset = U.readLong(file)  # Normal Top ("n_top")
        normals_size = U.readLong(file)    # Normal Total ("n_total")

        uvs_offset = U.readLong(file)  # P? Top ("p_top") ? Properties?
        uvs_size = U.readLong(file)    # p? Total ("p_total") ? Properties?

        #file.seek(offset + sf_offset, os.SEEK_SET)

        # Start of faces, I think
        face_count = U.readLong(file)  # Labelled as b_total

        # These names are from the game
        hpd_base = U.readShort(file)
        hpd_shift = U.readShort(file)
        min_bx = U.readShort(file)
        min_bz = U.readShort(file)
        max_bx = U.readShort(file)
        max_bz = U.readShort(file)

        hpd_unit = 1 << (hpd_shift & 0x1F)
        hpd_offset = 0x40 - hpd_base

        print(f"Reading {face_count} faces from @ {file.tell()}")
        # Read faces
        tri_strips = []
        for f in range(face_count):
            # Game code reads as x,y,z,d I think
            fv, fvn, fvt, fvc = BHEMesh.read_face(file, 0)
            # print(f"{fv} {fvn} {fvt} {fvc}")
            tri_strips.append((fv, fvn, fvt, fvc))

        # Convert tri_strips to normal face list
        face_indices = AMesh.create_face_list(face_count, vert_count_offset=-1, start_direction=1)
        face_list = []
        for fi in face_indices:
            face_list.append((tri_strips[fi[0]], tri_strips[fi[1]], tri_strips[fi[2]], 0))
            # print(f"{face_list[-1][0][0]} {face_list[-1][1][0]} {face_list[-1][2][0]}")
        # for i in range(int(face_count / 3)):
        #     face_list.append((tri_strips[i * 3], tri_strips[i * 3 + 1], tri_strips[i * 3 + 2], 0))


        print(f"Finished reading {face_count} faces up to @ {file.tell()}")

        # Read xyzw data
        file.seek(offset + uvs_offset, os.SEEK_SET)
        print(f"Reading {uvs_size} unknown? from @ {file.tell()}")
        unknowns = []
        for i in range(uvs_size):
            unknowns.append((U.readLong(file), U.readLong(file), U.readLong(file), U.readLong(file)))

        print(f"Finished reading {uvs_size} uvs up to @ {file.tell()}")

        # Read xyzw data
        file.seek(offset + floats_offset, os.SEEK_SET)
        print(f"Reading {verts_size} verts? from @ {file.tell()}")
        verts = []
        for i in range(verts_size):
            x, y, z, w = U.readXYZW(file)
            verts.append((-x, -y, z, w))

        # Read normals (nx,ny,nz,nw)
        file.seek(offset + normals_offset, os.SEEK_SET)
        print(f"Reading {normals_size} normals? from @ {file.tell()}")
        normals = []
        for i in range(normals_size):
            nx, ny, nz, nw = U.readXYZW(file)
            normals.append((nx, -ny, nz, nw))
        print(f"Done @ {file.tell()} end {offset + hpd_size}")

        return HPDModel([], verts_size, verts, normals_size, normals, 0, [], [[], face_list])

    def write_mesh_to_comb(self, fout, start_index=0, material=None):
        return 0

    def write_mesh_to_ply(self, fout, start_index=0):
        return 0

    def write_mesh_to_dbg(self, fout, start_index=0, material=None):
        return self.write_mesh_to_obj(fout, start_index, material, True)


