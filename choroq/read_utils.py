import struct

def readFloat(f):
    return struct.unpack('<f', f.read(4))[0]

def readLong(f):
    return int.from_bytes(f.read(4), byteorder='little')

def readShort(f):
    return int.from_bytes(f.read(2), byteorder='little')

def readByte(f):
    return int.from_bytes(f.read(1), byteorder='little')

def readXYZ(f):
    return (readFloat(f), readFloat(f), readFloat(f))

def remove_duplicates(seq):
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]
