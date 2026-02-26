import os
import choroq.egame.read_utils as U
from choroq.bhe.bhe_mesh import BHEMesh

class HML(BHEMesh):

    def __init__(self):
        pass

    @staticmethod
    def read_hml(file, offset):
        file.seek(offset, os.SEEK_SET)
        hmls = []

        # Read HML header
        magic = file.read(4)
        if magic != b'HML\x00':
            print(f"HML header invalid at @ {file.tell()}")
            return

        count = U.readLong(file)
        start_positions = []
        for i in range(count+1):
            start_positions.append(U.readLong(file))
        # extra values here are just repeated to pad to 16byte alignment

        # Read sections
        for i in range(count):
            part_position = offset + start_positions[i]
            file.seek(part_position, os.SEEK_SET)
            part_type = file.read(4)
            part_end = U.readLong(file)
            sub1_position = U.readLong(file)
            sub1_size = U.readLong(file)
            sub2_position = U.readLong(file)
            sub2_size = U.readLong(file)
            sub0_position = U.readLong(file)
            sub0_size = U.readLong(file)

            # Read subsection 0 of HPP
            # Possibly face data, if next is verts
            file.seek(part_position + sub0_position)
            for ssi in range(sub0_size):
                U.BreadShort(file)
                U.BreadShort(file)
                U.BreadShort(file)
                U.BreadShort(file)
                U.BreadShort(file)
                U.BreadShort(file)
                U.BreadShort(file)
                U.BreadShort(file)

            # Read subsection1 of HPP
            # Possibly verts
            file.seek(part_position + sub1_position)
            verts = []
            for ssi in range(sub1_size):
                x, y, z, w = U.readXYZW(file)
                verts.append((x, y, z, w))

            # Read subsection2 of HPP
            # Possibly normals
            file.seek(part_position + sub2_position)
            verts = []
            for ssi in range(sub2_size):
                x, y, z, w = U.readXYZW(file)
                verts.append((x, y, z, w))

        # Possibly after this is a list of other bits, models? pbls?
        # Probably old data that has not been wiped tho
        # preceded by a block of unknown data of varying length, ofc
