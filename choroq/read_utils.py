import struct

class Coverage:
    enabled = False
    byteCoverage = dict()

    @staticmethod
    def markByte(position):
        if not Coverage.enabled:
            return
        count = 0
        if position in Coverage.byteCoverage:
            count = Coverage.byteCoverage[position]
        Coverage.byteCoverage.update({position: count+1})
    
    @staticmethod
    def markShort(position):
        Coverage.markByte(position)
        Coverage.markByte(position+1)

    @staticmethod
    def markLong(position):
        Coverage.markByte(position)
        Coverage.markByte(position+1)
        Coverage.markByte(position+2)
        Coverage.markByte(position+3)

    @staticmethod
    def markFloat(position):
        Coverage.markByte(position)
        Coverage.markByte(position+1)
        Coverage.markByte(position+2)
        Coverage.markByte(position+3)

    @staticmethod
    def markLength(position, length):
        if not Coverage.enabled:
            return
        for i in range(position, position+length):
            Coverage.markByte(i)

    @staticmethod
    def reset():
        byteCoverage = dict()



def readFloat(f):    
    Coverage.markFloat(f.tell())
    return struct.unpack('<f', f.read(4))[0]

def readLong(f):
    Coverage.markLong(f.tell())
    return int.from_bytes(f.read(4), byteorder='little')

def readShort(f):
    Coverage.markShort(f.tell())
    return int.from_bytes(f.read(2), byteorder='little')

def readByte(f):
    Coverage.markByte(f.tell())
    return int.from_bytes(f.read(1), byteorder='little')

def readXYZ(f):
    return (readFloat(f), readFloat(f), readFloat(f))

def read64(f):
    Coverage.markLength(f.tell(), 8)
    return int.from_bytes(f.read(8), byteorder='little')

def read128(f):
    Coverage.markLength(f.tell(), 16)
    return int.from_bytes(f.read(16), byteorder='little')

def read(f, length):
    Coverage.markLength(f.tell(), length)
    return f.read(length)

# Blind read, do not mark these as used
def BreadFloat(f):
    return struct.unpack('<f', f.read(4))[0]

def BreadLong(f):
    return int.from_bytes(f.read(4), byteorder='little')

def BreadShort(f):
    return int.from_bytes(f.read(2), byteorder='little')

def BreadByte(f):
    return int.from_bytes(f.read(1), byteorder='little')

def BreadXYZ(f):
    return (readFloat(f), readFloat(f), readFloat(f))

def remove_duplicates(seq):
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]

def readNormalOffsetTable(file, size):
    subFileOffsets = []
    o = 1
    while o != size and  o != 0:
        o = readLong(file)
        subFileOffsets.append(o)
    return subFileOffsets