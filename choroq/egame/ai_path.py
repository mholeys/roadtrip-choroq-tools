# This is for path data in the game, such as roaming npc paths, or paths to follow when driving

import io
import os
import math
import choroq.egame.read_utils as U
from elftools.elf.elffile import ELFFile


class AiPath:

    def __init__(self, length, positions, data):
        self.length = length
        self.positions = positions
        self.data = data
        # path = AiPath.sort_path(data, length, positions)
        # path = AiPath.sort_path2(data, length, positions)
        # print(path)
        self.corrected_positions = AiPath.sort_path(data, length, positions)

    @staticmethod
    def read_from_file(file, position):
        elffile = ELFFile(file)
        data_section = None
        for section in elffile.iter_sections():
            if section.name.startswith('.data'):
                data_section = section
                break
        if data_section is None:
            return None
        data_section_addr = data_section.header.sh_addr
        data_section_offset = data_section.header.sh_offset

        start_offset = - data_section_addr + data_section_offset

        path_position = position + start_offset
        file.seek(path_position, os.SEEK_SET)

        path_ptr = U.readLong(file)
        data_ptr = U.readLong(file)

        # Read data first as it tells us the size of the array, and the order
        data, length = AiPath.read_data_section(file, data_ptr + start_offset)
        print(f"After data {file.tell()}")

        # Read positions
        positions = AiPath.read_positions(file, path_ptr + start_offset, length)
        print(f"After positions {file.tell()}")
        return AiPath(length, positions, data)


    @staticmethod
    def sort_path2(data, length, positions):
        new_positions = []
        for i in range(length):

            # print(data[i][2])
            # print(data[i][5])
            new_positions.append(positions[data[i][2]])
            # new_positions.append(positions[data[i][5]])
        return positions

    @staticmethod
    def sort_path(data, length, positions):
        starting_index = 0
        # The game uses the data section based on the position/condition of the cars
        # There are two choices the game makes based on the cross product result of the car/path difference
        # As I don't have the starting position of the car for this path,
        # I am going to start at the first path position (middle)
        # "current" position of the "car"/object
        # Convert to x/y/z assuming a y of 1, but I think all ai calcs are X/Z
        car_path_index = starting_index

        unknown_var_bVar1 = 0
        for p in range(length):
            current_path_index = car_path_index
            current_data = data[current_path_index]
            current_position = ((positions[current_path_index].lx - 2), 1,
                                (positions[current_path_index].lz - 2))
            # path[i].rightz -
            path_pos = positions[current_path_index]
            if (path_pos.rz - path_pos.lz) * (current_position[0] - path_pos.rx) - (path_pos.rx - path_pos.lx) * (current_position[2] - path_pos.rz) < 0.0:
                current_path_index = current_data[2]
                while True:
                    if current_path_index == current_data[3]:
                        car_path_index = current_path_index
                    elif ((positions[current_data[1]].zerosz - positions[current_data[0]].zerosz) * (current_position[0] - positions[current_data[1].zerosx]) -
                        (positions[current_data[1]].zerosx - positions[current_data[0]].zerosx) * (current_position[2] - positions[current_data[1].zerosz])) < 0.0:
                        car_path_index = current_path_index
                    else:
                        car_path_index = current_data[3]
                    current_path_index = car_path_index
                    current_data = data[current_path_index]
                    path_pos = positions[current_data[0]]
                    if ((path_pos.rz - path_pos.lz) * (current_position[0] - path_pos.rx) - (path_pos.rx - path_pos.lx) * (current_position[2] - path_pos.rz)) >= 0.0:
                        break
                    current_path_index = current_data[2]
                    print(f"New position A: i:{current_path_index} L: {positions[current_path_index].lx} {positions[current_path_index].lz} / R: {positions[current_path_index].rx} {positions[current_path_index].rz} / Z: {positions[current_path_index].zerosx} {positions[current_path_index].zerosz}")
                unknown_var_bVar1 = current_data[6]
            else:
                while True:
                    path_pos = positions[current_data[1]]
                    if ((path_pos.rz - path_pos.lz) * (current_position[0] - path_pos.rx) - (path_pos.rx - path_pos.lx) * (current_position[2] - path_pos.rz)) < 0.0:
                        break
                    current_path_index = current_data[4]
                    if current_path_index == current_data[5]:
                        car_path_index = current_path_index
                    elif ((path_pos.zerosz - positions[current_data[0]].zerosz) * (current_position[0] - path_pos.zerosx)) - (path_pos.zerosx - positions[current_data[0]].zerosx) * (current_position[2] - path_pos.zerosz) < 0.0:
                        car_path_index = current_path_index
                    else:
                        car_path_index = current_path_index[5]
                    current_path_index = car_path_index
                    current_data = data[current_path_index]
                    print(f"New position B: i:{current_path_index} L: {positions[current_path_index].lx} {positions[current_path_index].lz} / R: {positions[current_path_index].rx} {positions[current_path_index].rz} / Z: {positions[current_path_index].zerosx} {positions[current_path_index].zerosz}")
                unknown_var_bVar1 = current_data[6]
            print(f"New position: i:{current_path_index} L: {positions[current_path_index].lx} {positions[current_path_index].lz} / R: {positions[current_path_index].rx} {positions[current_path_index].rz} / Z: {positions[current_path_index].zerosx} {positions[current_path_index].zerosz}")
            car_bVar1 = unknown_var_bVar1






    @staticmethod
    def read_data_section(file, position):
        file.seek(position, os.SEEK_SET)
        data = []
        # Unsure on how it calculates length but this usually works
        size = max(U.readByte(file), 0)
        size = max(U.readByte(file), size)
        size = max(U.readByte(file), size)
        size = max(U.readByte(file), size)
        file.seek(position, os.SEEK_SET)
        i = 0
        while i < size:
            # Data is addressed in 8 byte sections, so I will follow that
            # First word?
            unk0 = U.readByte(file)
            unk1 = U.readByte(file)
            start_index = U.readByte(file)
            second_index = U.readByte(file)
            # Second word
            unk4 = U.readByte(file)
            unk5 = U.readByte(file)
            unk6 = U.readByte(file)
            unk7 = U.readByte(file)

            size = max(size, start_index)
            size = max(size, second_index)
            size = max(size, unk5)

            data.append([unk0, unk1, start_index, second_index, unk4, unk5, unk6, unk7])
            i += 1

        return data, size

    @staticmethod
    def read_positions(file, position, length):
        file.seek(position, os.SEEK_SET)
        positions = []
        for i in range(length+1):
            leftx = U.readFloat(file)
            leftz = U.readFloat(file)

            rightx = U.readFloat(file)
            rightz = U.readFloat(file)
            zerosx = U.readFloat(file)
            zerosz = U.readFloat(file)
            positions.append(PathPoint(leftx, leftz, rightx, rightz, zerosx, zerosz))
        return positions

class PathPoint:
    rx: float
    rz: float
    lx: float
    lz: float
    zerosx: float
    zerosz: float

    def __init__(self, lx, lz, rx, rz, zx, zz):
        self.lx = lx
        self.lz = lz
        self.rx = rx
        self.rz = rz
        self.zerosx = zx
        self.zerosz = zz

elf_path = "I:\\Console\\PS2\\RoadTripAdventure_Data\\RoadTripAdventure\\SLES_513.56"
out_folder = "I:\\Console\\PS2\\RoadTripAdventure_Data\\Tools\\MyTools\\Python\\RoadTrip-Tools\out\\hg2\\paths"
with open(elf_path, "rb") as file:
    positions = [
        0x002bf5f0, 0x002bf5f0+8, 0x002bf5f0+8*2, 0x002bf5f0+8*3, 0x002bf5f0+8*4, 0x002bf5f0+8*5,
        0x002bf620, 0x002bf620+8, 0x002bf620+8*2, 0x002bf620+8*3, 0x002bf620+8*4, 0x002bf620+8*5, 0x002bf620+8*6, 0x002bf620+8*7, 0x002bf620+8*7,
        0x002bf620+8*8, 0x002bf620+8*9, 0x002bf620+8*10, 0x002bf620+8*11, 0x002bf620+8*13, 0x002bf620+8*14,
        0x002bf620+8*16, 0x002bf620+8*22, 0x002bf620+8*31, 0x002bf620+8*32,

    ]
    for position in positions:
        try:
            path = AiPath.read_from_file(file, position)
            with open(f"{out_folder}\\path-{position}.obj", "w") as fout:
                i = 1
                faces = []
                for v in path.corrected_positions:
                    if v.lx == 0 and v.lz == 0 and v.rx == 0 and v.rz == 0:
                        continue
                    fout.write(f"v {v.lx} 0 {v.lz}\n")
                    fout.write(f"v {v.rx} 0 {v.rz}\n")
                    faces.append(f"f {i} {i + 2} {i + 1} \n")
                    faces.append(f"f {i + 1} {i + 2} {i + 3} \n")
                    i += 2
                # Close the path
                faces.append(f"f 1 {i - 2} {i - 1}\n")
                faces.append(f"f {i - 1} 1 2\n")
                for face in faces:
                    fout.write(face)
        except Exception as e:
            print(e)
            raise e