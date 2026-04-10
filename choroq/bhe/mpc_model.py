# Seems to have named subsections
# magic
# 36880 bytes from the start data starts
# subsections have extensions, .pb seen

import os
import choroq.read_utils as U
from choroq.bhe.bhe_mesh import BHEMesh


class MPCModel(BHEMesh):
    PRINT_DEBUG = False

    def __init__(self, name, texture_references, vert_count, vertices, normal_count, normals, uv_count, uvs, colour_count, colours, faces):
        super().__init__()
        self.name = name
        self.texture_references = texture_references
        self.vert_count = vert_count
        self.vertices = vertices
        self.normal_count = normal_count
        self.normals = normals
        self.uv_count = uv_count
        self.uvs = uvs
        self.colour_count = colour_count
        self.colours = colours
        self.faces = faces
        # Max value of face indices, maximum index for vertex
        self.max_vert = len(vertices)
        self.max_normal = len(normals)
        self.max_uv = len(uvs)
        self.max_colour = len(colours)

    @staticmethod
    def read_mpc(file, offset, next_offset):
        file.seek(offset, os.SEEK_SET)
        mpcs = []

        # Read HML header
        magic = file.read(4)
        if magic != b'MPC\x00':
            print(f"mpc header invalid at @ {file.tell()}")
            return
        # Skip the big mostly empty section
        file.seek(offset + 36880, os.SEEK_SET)

        valid = True
        while valid:
            mpc, valid = MPCModel.read_mpc_section(file, file.tell(), next_offset)
            if valid:
                mpcs.append(mpc)
                # Move to next aligned section
                position = file.tell()
                pad_by = 16 - (position - ((position >> 4) << 4))
                if pad_by == 16:
                    pad_by = 0
                file.seek(pad_by, os.SEEK_CUR)

        return mpcs

    @staticmethod
    def read_mpc_section(file, offset, next_offset):
        file.seek(offset, os.SEEK_SET)
        if MPCModel.PRINT_DEBUG:
            print(f"Part start: {file.tell()}")
        # Read possible name
        name = file.read(16)
        valid = False
        try:
            first_0 = name.index(0)
            name = name[0:first_0].decode("ascii").rstrip('\00')
            if ".pb" in name:
                valid = True
        except Exception as e:
            print("Failed to decode MPC part name")
            name = f"mpc-{offset}"

        if not valid:
            return None, False

        if file.tell() > next_offset:
            return None, False

        size_textures = U.readLong(file)
        size_verts = U.readLong(file)
        size_normals = U.readLong(file)
        size_uvs = U.readLong(file)
        size_colours = U.readLong(file)
        size_5 = U.readLong(file)
        size_6 = U.readLong(file)
        size_7 = U.readLong(file)

        texture_references = []
        for i in range(size_textures):
            t_width = U.readShort(file)
            t_height = U.readShort(file)
            t_format = U.readShort(file)
            t_unknown = U.readShort(file)
            U.BreadLong(file)
            U.BreadLong(file)
            t_name = file.read(16)
            try:
                first_0 = t_name.index(0)
                t_name = t_name[0:first_0].decode("ascii").rstrip('\00')
            except Exception as e:
                print("Failed to decode MPC texture name")
            if file.tell() > next_offset:
                return None, False

            texture_references.append((t_name, (t_width, t_height, t_format, t_unknown)))

        # Read data
        # XYZ(W)
        if MPCModel.PRINT_DEBUG:
            print(f"Vert section start: {file.tell()}")
        verts = []
        for i in range(size_verts):
            x, y, z, w = U.readXYZW(file)
            verts.append((-x, -y, z, w))
            if file.tell() > next_offset:
                return None, False

        if MPCModel.PRINT_DEBUG:
            print(f"Normal section start: {file.tell()}")
        # Normals
        normals = []
        for i in range(size_normals):
            nx, ny, nz, nw = U.readXYZW(file)
            normals.append((nx, -ny, nz, nw))
            if file.tell() > next_offset:
                return None, False

        if MPCModel.PRINT_DEBUG:
            print(f"UVs section start: {file.tell()}")
        # UV
        uvs = []
        for i in range(size_uvs):
            uvs.append((U.readFloat(file), 1 - U.readFloat(file)))
            if file.tell() > next_offset:
                return None, False

        if MPCModel.PRINT_DEBUG:
            print(f"Vertex colour section start: {file.tell()}")
        # Vertex Colours
        colours = []
        for i in range(size_colours):
            colours.append((U.readByte(file), U.readByte(file), U.readByte(file), U.readByte(file)))
            if file.tell() > next_offset:
                return None, False

        faces, other_faces = BHEMesh.read_faces(file, texture_references)

        mpc = MPCModel(name, texture_references, size_verts, verts, size_normals, normals, size_uvs, uvs, size_colours, colours, [faces, other_faces])
        return mpc, valid

    def write_mesh_to_comb(self, fout, start_index=0, material=None):
        return 0

    def write_mesh_to_ply(self, fout, start_index=0):
        return 0

    def write_mesh_to_dbg(self, fout, start_index=0, material=None):
        return self.write_mesh_to_obj(fout, start_index, material, True)