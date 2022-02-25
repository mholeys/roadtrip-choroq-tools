# File to compare header data bytes

import io
import os
import sys
import numpy as np
import choroq.read_utils as U
import matplotlib as mpl
import matplotlib.pyplot as plt

class Header:
    
    def __init__(self, name, values, header):
        self.name = name
        self.values = np.array(list(values))
        self.header = np.array(list(header))

def find_differences(headers, length):
    data = []
    headerRef = []
    # Move all header byte value into 
    # [position, value, count] format
    #
    for hInd,h in enumerate(headers):
        print(h.name)
        for bInd,b in enumerate(h.header):
            # See if data already has a value and position pair
            # indexAlready = [i for i,d in enumerate(data) if d[0] == bInd]
            dataAlready = [i for i,d in enumerate(data) if d[0] == bInd and d[1] == b]
            if len(dataAlready) == 0:
                # Same value and position as another file
                data.append([bInd, b, 1])
            else:
                data[dataAlready[0]][2] += 1
    # Find differences, where there are two positions but with different values
    differences = []
    similarities = []
    for x in range(0, length):
        values = [d for d in data if d[0] == x]
        #print(values)
        if len(values) > 1:
            #print("Differences")
            differences.append([x, values])
        else:
            #print("Same")
            similarities.append([x, values])    

    return differences, similarities

def compare_differences(f1, f2):
    # Format of these are [bytePosition, list of [bytePosition, byteValue, count] ]
    differencesf1, similaritiesf1 = f1
    differencesf2, similaritiesf2 = f2
        
    
    # Build list of byte indicies that are the same int the control group
    indicies = []
    for i,l in similaritiesf1:
        # Similarities only have one entry
        #p,v,c = l[0]
        indicies.append(i)

    # Look through similarities of f2 and see if there are any differences between
    # the control (f1)'s similar bytes and the var (f2)'s similar bytes
    # if so those are the variables that may show what the user is after
    differences = []
    similarities = []
    for i in indicies:
        # Get (position,value,count) for ctrl_similarities and and var_similarities
        s1 = [d[1][0] for d in similaritiesf1 if d[0] == i]
        s2 = [d[1][0] for d in similaritiesf2 if d[0] == i]
        #print(f"{s1} {s2}")
        if len(s1) == 0 or len(s2) == 0:
            # Files do not share same byte similarities throughout file
            continue
        # Extract the actual byte value for each
        d1 = s1[0][1]
        d2 = s2[0][1]

        if d1 == d2:
            # Both files have the same byte value at i
            similarities.append([i, d1])
        else:
            # One file is different, ie var different to control
            # this byte may hold info the user is looking for
            # format [psoition, data_control, data_var]
            differences.append([i, d1, d2])

    return differences, similarities
        




def load_headers(folder):
    headers = []
    if os.path.isdir(folder):
        with os.scandir(folder) as it:
            for entry in it:
                if not entry.name.startswith('.') and entry.is_file():
                    headers.append(process_file(entry))
    
    return headers

def process_file(entry):
    data = []
    values = []
    name = entry.name
    with open(entry, "rb") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(0, os.SEEK_SET)
        if size > 112:
            for i in range(0, 8):
                values.append(U.readShort(f))
        data = f.read()
    return Header(name, values, data)

def extract_header(folder, skip, byteLimit, out, prefix, data_prepend=[]):
    if os.path.isdir(folder):
        with os.scandir(folder) as it:
            for entry in it:
                if not entry.name.startswith('.') and entry.is_file():
                    print(entry.name)
                    size = entry.stat().st_size
                    with open(entry, "rb") as f:
                        offsets = [] 
                        o = 1
                        while o != 0 and o != size:
                            o = U.readLong(f)
                            offsets.append(o)
                        print(offsets)
                        textOffset = offsets[-2]
                        print(f"{textOffset} {size}")
                        name = os.path.basename(f.name)
                        basename = name[0 : name.find('.')]
                        with open(f"{out}/{prefix}-{basename}.HEAD", "wb") as fout:
                            f.seek(textOffset, os.SEEK_SET)
                            if len(data_prepend) > 0:
                                fout.write(bytes(data_prepend))
                            for i in range(0, byteLimit):
                                b = f.read(1)
                                fout.write(b)

def extract_palette_header(folder, skip, byteLimit, out, prefix, data_prepend=[]):
    if os.path.isdir(folder):
        with os.scandir(folder) as it:
            for entry in it:
                if not entry.name.startswith('.') and entry.is_file():
                    print(entry.name)
                    size = entry.stat().st_size
                    with open(entry, "rb") as f:
                        offsets = [] 
                        o = 1
                        while o != 0 and o != size:
                            o = U.readLong(f)
                            offsets.append(o)
                        print(offsets)
                        textOffset = offsets[-2]
                        paletteOffset = textOffset + 112 + 128*128
                        print(f"{paletteOffset} {size}")
                        name = os.path.basename(f.name)
                        basename = name[0 : name.find('.')]
                        with open(f"{out}/{prefix}-{basename}.PALE", "wb") as fout:
                            f.seek(paletteOffset, os.SEEK_SET)
                            if len(data_prepend) > 0:
                                fout.write(bytes(data_prepend))
                            for i in range(0, byteLimit):
                                b = f.read(1)
                                fout.write(b)

if __name__ == '__main__':
    if len(sys.argv) == 3:
        control = sys.argv[1]
        filename = sys.argv[2]
        ctrl_headers = load_headers(control)
        var_headers  = load_headers(filename)
        print(f"Comparing {len(ctrl_headers)} headers in {control}")
        ctrl_differences, ctrl_smiliarities = find_differences(ctrl_headers, 112)
        print(f"found {len(ctrl_smiliarities)} bytes the same, in control group")
        print(f"found {len(ctrl_differences)} bytes different, in control group")
        #print(ctrl_smiliarities)
        print(f"Comparing {len(var_headers)} headers in {filename}")
        var_differences, var_smiliarities = find_differences(var_headers, 112)
        print(f"found {len(var_smiliarities)} bytes the same, in var group")
        print(f"found {len(var_differences)} bytes different, in var group")
        print(var_smiliarities)
        var_ctrl_differences, var_ctrl_similarities = compare_differences((ctrl_differences, ctrl_smiliarities), (var_differences, var_smiliarities))
        print(f"found {len(var_ctrl_similarities)} byte positions that also dont vary (ctrl does not vary at x, and b also does not vary at x, but values may be different)")
        print(f"found {len(var_ctrl_differences)} byte values different, between groups")
        print("Differences:")
        print(var_ctrl_differences)

    if len(sys.argv) == 2:
        filename = sys.argv[1]
        var_headers  = load_headers(filename)
        var_differences, var_smiliarities = find_differences(var_headers, 112)
        print(var_differences)
        print(var_smiliarities)
        print([d[1] for d in var_differences if d[0] == 69])
        print([d[1] for d in var_smiliarities if d[0] == 69])

    if len(sys.argv) == 4:
        # Copy files into out
        if sys.argv[1] != "yeswilldo":
            print("See code")
            exit(1)
        filename = sys.argv[2]
        out = sys.argv[3]
        
        # 128x128 data values 8bb with palette
        # d = b'\x80\x80\x01\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        # 64x128 data values 8bb with palette
        # d = b'\x40\x80\x01\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        #extract_header(filename, 0, 112, out, "CART", data_prepend=d)
        extract_palette_header(filename, 0, 112, out, "CART")
    
