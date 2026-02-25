import os
import choroq.egame.read_utils as U
from choroq.bhe.bhe_mesh import BHEMesh



class PBLModel(BHEMesh):
    STOP_ON_NEW = False
    PRINT_DEBUG = False

    def __init__(self, texture_references, first_section, vert_count, vertices, normal_count, normals, uv_count, uvs, colour_count, colours, faces):
        super().__init__()
        self.texture_references = texture_references
        self.first_section = first_section
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
            texture_references = []
            file.seek(o, os.SEEK_SET)
            if PBLModel.PRINT_DEBUG:
                print(f"Reading PBL section from {file.tell()}")
            # Read single PBL section
            sizes = []
            for i in range(8):
                sizes.append(U.readLong(file))

            for i in range(sizes[0]):
                if PBLModel.PRINT_DEBUG:
                    print(f"Header name next: {file.tell()}")
                # Unsure on value usage, might be name/texture related
                t_width = U.readShort(file)
                t_height = U.readShort(file)
                t_format = U.readShort(file)
                t_unknown = U.readShort(file)
                U.BreadLong(file)
                U.BreadLong(file)
                name = file.read(16)   # \0 terminated string, max 16 bytes
                try:
                    first_0 = name.index(0)
                    name = name[0:first_0].decode("ascii").rstrip('\00')
                except Exception as e1:
                    # Possible JP character in name, cannot really handle nicely, without custom d/encoding
                    print(f"{name} failed to convert to ascii")
                    end_letter = 1
                    for li in range(len(name)):
                        if name[li] > 0x7F:
                            end_letter = li - 1
                    try:
                        name = name[0:end_letter].decode("ascii").rstrip('\00')
                    except Exception as e2:
                        print("Cannot parse name, other error occurred")
                        print(f"Read failed at {file.tell()}")
                        raise e2
                        # return

                texture_references.append((name, (t_width, t_height, t_format, t_unknown)))

            # Unknown section, might be position/colour its floats * 8
            if PBLModel.PRINT_DEBUG:
                print(f"Float section start: {file.tell()}")
            floats_first_section = []
            for i in range(sizes[6]):
                floats_first_section.append(U.readXYZW(file))
                floats_first_section.append(U.readXYZW(file))

            if PBLModel.PRINT_DEBUG:
                print(f"Vert section start: {file.tell()}")
            # Data starts
            # XYZ(W)
            verts = []
            for i in range(sizes[1]):
                x, y, z, w = U.readXYZW(file)
                verts.append((-x, -y, z, w))

            if PBLModel.PRINT_DEBUG:
                print(f"Normal section start: {file.tell()}")
            # Normals
            normals = []
            for i in range(sizes[2]):
                nx, ny, nz, nw = U.readXYZW(file)
                normals.append((nx, -ny, nz, nw))

            if PBLModel.PRINT_DEBUG:
                print(f"UVs section start: {file.tell()}")
            # UV
            uvs = []
            for i in range(sizes[3]):
                uvs.append((U.readFloat(file), 1-U.readFloat(file)))

            if PBLModel.PRINT_DEBUG:
                print(f"Vertex colour section start: {file.tell()}")
            # Vertex Colours
            colours = []
            for i in range(sizes[4]):
                colours.append((U.readByte(file), U.readByte(file), U.readByte(file), U.readByte(file)))

            faces, other_faces = BHEMesh.read_faces(file, texture_references)

            pbls.append(PBLModel(texture_references, floats_first_section, sizes[1], verts, sizes[2], normals, sizes[3], uvs, sizes[4], colours, [faces, other_faces]))

        return pbls

    def write_mesh_to_comb(self, fout, start_index=0, material=None):
        return 0

    def write_mesh_to_ply(self, fout, start_index=0):
        return 0

    def write_mesh_to_dbg(self, fout, start_index=0, material=None):
        return self.write_mesh_to_obj(fout, start_index, material, True)

