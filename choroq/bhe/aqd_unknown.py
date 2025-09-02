import os
import choroq.read_utils as U
from choroq.amesh import AMesh


class AQDData(AMesh):
    STOP_ON_NEW = False

    def __init__(self, first, sizes, data, verts):
        self.first = first
        self.sizes = sizes
        self.data = data
        self.verts = verts

    @staticmethod
    def read_aqd(file, offset):
        file.seek(offset, os.SEEK_SET)

        # Read AQD header
        magic = file.read(4)

        first = U.readLong(file)
        sizes = []
        data = []
        for i in range(4):
            sizes.append(U.readShort(file))

        # Read data sections
        # Unsure on what this data is used for, or means
        for i in range(sizes[0]):
            #     u32 zeros;
            #     u16 val1;
            #     u16 val2;
            #     u16 val3;
            #     u16 val4;
            #     u32 count;
            #     u16 values[count];
            zeros = U.readLong(file)
            val1 = U.BreadShort(file)
            val2 = U.BreadShort(file)
            val3 = U.BreadShort(file)
            val4 = U.BreadShort(file)
            count = U.readLong(file)
            values = []
            for j in range(count):
                values.append(U.readShort(file))

            data.append([zeros, val1, val2, val3, val4, count, values])

        # Unsure on sizes[1] meaning, as its usually 0
        #for i in range(sizes[1]):
        #    pass

        # There is another section, before verts, no clue, even when sizes[1] == 0

        # Verts, maybe? sizes is not right
        verts = []
        #for i in range(sizes[2]):
        #    verts.append(U.readXYZW(file))

        return AQDData(first, sizes, data, verts)


