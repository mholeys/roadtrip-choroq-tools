import os
import choroq.read_utils as U
from choroq.bhe.bhe_mesh import BHEMesh


# Mesh Polygon Data
class MPDModel(BHEMesh):
    STOP_ON_NEW = False
    PRINT_DEBUG = False

    def __init__(self, texture_references, vert_count, vertices, normal_count, normals, uv_count, uvs, colour_count, colours, faces):
        super().__init__()
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
    def read_mpd(file, offset):
        file.seek(offset, os.SEEK_SET)
        mpds = []

        # Read MPD header
        magic = file.read(4)
        if magic != b'MPD\x00':
            print(f"MPD header invalid at @ {file.tell()}")
            return

        first = U.readLong(file)
        val1 = U.readShort(file)
        val2 = U.readShort(file)

        # I am unsure what any value in this section means so far
        entry_count = U.readLong(file)
        entry_values = []
        for i in range(entry_count):
            s1 = U.BreadShort(file)
            s2 = U.BreadShort(file)
            position = U.BreadLong(file)
            size = U.BreadLong(file)
            empty = U.BreadLong(file)
            entry = [s1, s2, position, size, empty]
            entry_values.append(entry)

        offsets = [first+offset]

        last_name = f"MPD-{offset}"
        for o in offsets:
            file.seek(o, os.SEEK_SET)
            if MPDModel.PRINT_DEBUG:
                print(f"Reading MPD section from {file.tell()}")
            # Read single MPD section
            sizes = []
            for i in range(8):
                sizes.append(U.readLong(file))

            name = f"{last_name}-{o}"
            texture_references = []
            for i in range(sizes[0]):
                if MPDModel.PRINT_DEBUG:
                    print(f"Header name next: {file.tell()}")
                t_width = U.readShort(file)
                t_height = U.readShort(file)
                t_format = U.readShort(file)
                t_unknown = U.readShort(file)
                U.BreadLong(file)
                U.BreadLong(file)
                name = file.read(16)
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
                        raise e2

                texture_references.append((name, (t_width, t_height, t_format, t_unknown)))
                last_name = texture_references[0][0]

            for i in range(sizes[6]):
                # Unknown data
                U.readXYZW(file)
                U.readXYZW(file)

            if MPDModel.PRINT_DEBUG:
                print(f"Vert section start: {file.tell()}")
            # Data starts
            # XYZ(W)
            verts = []
            for i in range(sizes[1]):
                x, y, z, w = U.readXYZW(file)
                verts.append((-x, -y, z, w))

            if MPDModel.PRINT_DEBUG:
                print(f"Normal section start: {file.tell()}")
            # Normals
            normals = []
            for i in range(sizes[2]):
                nx, ny, nz, nw = U.readXYZW(file)
                normals.append((nx, -ny, nz, nw))

            if MPDModel.PRINT_DEBUG:
                print(f"UVs section start: {file.tell()}")
            # UV
            uvs = []
            for i in range(sizes[3]):
                uvs.append((U.readFloat(file), 1-U.readFloat(file)))

            if MPDModel.PRINT_DEBUG:
                print(f"Vertex colour section start: {file.tell()}")
            # Vertex Colours
            colours = []
            for i in range(sizes[4]):
                colours.append((U.readByte(file), U.readByte(file), U.readByte(file), U.readByte(file)))

            faces, other_faces = MPDModel.read_faces(file, texture_references)

            mpds.append(MPDModel(texture_references, sizes[1], verts, sizes[2], normals, sizes[3], uvs, sizes[4], colours, [faces, other_faces]))

        return mpds

    def write_mesh_to_comb(self, fout, start_index=0, material=None):
        return 0

    def write_mesh_to_ply(self, fout, start_index=0):
        return 0

    def write_mesh_to_dbg(self, fout, start_index=0, material=None):
        return self.write_mesh_to_obj(fout, start_index, material, True)



