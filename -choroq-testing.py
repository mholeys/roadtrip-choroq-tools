
import io
import os
import sys
from PIL import Image, ImagePalette, ImageOps

from choroq.texture import Texture
from choroq.car import CarModel, CarMesh
import choroq.read_utils as U

def jumpZeros(f):
    print(f"jumping zeros from {f.tell()}")
    i = 1
    b = U.readByte(f)
    while b == 0:
        b = U.readByte(f)
        i += 1
    f.seek(-1, os.SEEK_CUR)
    print(f"jumped zeros to {b} {f.tell()} {i}")
    return i


if __name__ == '__main__':
    if len(sys.argv) == 3:
        filename = sys.argv[1]
        loadtype = int(sys.argv[2])
    else:
        print("Not enough args")
        exit(0)
    
    
    if len(filename) == 0:
        print("bad filename")
        exit(1)

    if loadtype < 0 or loadtype > 4:
        print("wrong load type")
        exit(1)

    with open(filename, "rb") as f:
        name = os.path.basename(f.name)
        basename = name[0 : name.find('.')]
        print(f"Loading file {basename}")
        outfolder = f"out/{basename}"
        print(f"Saving into {outfolder}")
        os.makedirs(os.path.dirname(f"{outfolder}/"), exist_ok=True)
        f.seek(0, os.SEEK_END)
        fileSize = f.tell()
        print(f"Reading file of {fileSize} bytes")
        f.seek(0, os.SEEK_SET)

        if loadtype == 0:
            # Load as carmodel

            print("Loading as normal CarModel")
            f.seek(0, os.SEEK_SET)
            car = CarModel.fromFile(f, 0, fileSize)
            for i,mesh in enumerate(car.meshes):
                with open(f"{outfolder}/{basename}-{i}.obj", "w") as fout:
                    mesh.writeMeshToObj(fout)
            for i,tex in enumerate(car.textures):
                tex.writeTextureToPNG(f"{outfolder}/{basename}-{i}.png")
                tex.writePaletteToPNG(f"{outfolder}/{basename}-{i}-p.png")

        elif loadtype == 1:
            # Try loading as garage

            print("Loading as Garage file")
            
            f.seek(0, os.SEEK_SET)
            meshes = CarMesh._fromFile(f, 16)
            for i,mesh in enumerate(meshes):
                with open(f"{outfolder}/{basename}-{i}.obj", "w") as fout:
                    mesh.writeMeshToObj(fout)
            o = f.tell()
            o += jumpZeros(f)
            t = U.readByte(f)
            isT = (t & 0x06) >= 0x06
            print(f"HasAnotherTexture: {isT} {t} {f.tell()}")
            i = 0
            while (isT):
                tex = Texture._fromFile(f, o)
                tex.writeTextureToPNG(f"out/GARAGE.bin-{i}.png")
                tex.writePaletteToPNG(f"out/GARAGE.bin-{i}-p.png")
                o += jumpZeros()
                isT = (U.readByte() & 0x06) >= 0x06
                print(f"HasAnotherTexture: {isT} {t} {f.tell()}")
                f.seek(-1, os.SEEK_CUR)
                i += 1
        elif loadtype == 2: 
            # Try loading as a (texture + palettes)s
            print("Loading as Texture file")
            
            f.seek(0, os.SEEK_SET)
            t = U.readByte(f)
            isT = t & 0x06 >= 0x06
            f.seek(0, os.SEEK_SET)
            i = 0
            pCount = 0
            if not isT:
                print("File not texture")
            while (isT):
                tex = Texture._fromFile(f, f.tell())
                tex.writeTextureToPNG(f"{outfolder}/{basename}-{i}-bw.png", usepalette=False)
                tex.writeTextureToPNG(f"{outfolder}/{basename}-{i}.png")
                tex.writePaletteToPNG(f"{outfolder}/{basename}-{i}-p.png")
                p =  U.readLong(f)
                isP = p & 0x70870002 >= 0x70870002 or p & 0x10ff0046 >= 0x10ff0046
                f.seek(-4, os.SEEK_CUR)
                while isP:
                    pCount += 1
                    print(f"Has extra palette? other data {p} {isP} @ {f.tell()}")
                    # Read palette
                    try:
                        paletteX = Texture._paletteFromFile(f, tex.width * tex.height, f.tell(), True)
                        texX = Texture([], paletteX[0], (0,0), paletteX[1])
                        texX.writePaletteToPNG(f"{outfolder}/{basename}-{i}-{pCount}-p.png")
                        print(f"Parsed PaletteX {f.tell()}")
                        jumpZeros(f)
                    except Exception as e:
                       print(f"fa {f.tell()}")
                       f.seek(48, os.SEEK_CUR) #  Skip odd header that is like a palette, often >= 8129
                       f.seek(8129, os.SEEK_CUR)
                       jumpZeros(f)
                       pass


                    p =  U.readLong(f)
                    isP = p & 0x70870002 >= 0x70870002
                    f.seek(-4, os.SEEK_CUR)
                e = U.readLong(f)
                isE = e & 0x10FF000E >= 0x10FF000E
                f.seek(-4, os.SEEK_CUR)
                while isE:
                    print(f"Has extra ?lighting?/other data {e} {isE} @ {f.tell()}")
                    f.seek(48, os.SEEK_CUR) #  Skip odd header that is unknown, perhaps lighting info contains data and circular object
                    f.seek(8129, os.SEEK_CUR)
                    jumpZeros(f)
                    e = U.readLong(f)
                    isE = p & 0x10FF000E >= 0x10FF000E
                    f.seek(-4, os.SEEK_CUR)
                t =  U.readByte(f)
                isT = t & 0x06 >= 0x06
                f.seek(-1, os.SEEK_CUR)
                print(f"HasAnotherTexture: {isT} {t} {f.tell()}")
                i += 1
        elif loadtype == 3: 
            # Try loading as much as possible from a FLD file
            print("Loading as FLD")
            
            #FLDs have offset table
            # First is a list of textures
            # Followed by SubFiles with offset table
            # Followed by ?
            # Followed by Minimap?
            f.seek(0, os.SEEK_SET)


            print("Reading subfile offsets")
            subFileOffsets = []
            o = 1
            while o != fileSize and  o != 0:
                o = U.readLong(f)
                subFileOffsets.append(o)

            print(f"File subOffsets {subFileOffsets}")

            # Try reading textures contiguously 
            f.seek(subFileOffsets[0], os.SEEK_SET)
            isT = U.readByte(f) & 0x06 >= 0x06
            print(f"Trying to read subFile 0 as textures {subFileOffsets[0]} isTexture:{isT}")
            f.seek(subFileOffsets[0], os.SEEK_SET)
            
            while (isT):
                try:
                    tex = Texture._fromFile(f, f.tell())
                    tex.writeTextureToPNG(f"{outfolder}/{basename}-bw.png", usepalette=False)
                    tex.writeTextureToPNG(f"{outfolder}/{basename}.png")
                    tex.writePaletteToPNG(f"{outfolder}/{basename}-p.png")
                    jumpZeros(f)
                    isT = U.readByte(f) & 0x06 >= 0x06
                    print(f"HasAnotherTexture: {isT}")
                    f.seek(-1, os.SEEK_CUR)
                except Exception as e:
                    print("Failed to parse textures")
                    print(e)

            print(f"Got to {f.tell()}")

            # Parse what ever is next
            #f.seek(subFileOffsets[1], os.SEEK_SET)
            #print(U.readLong(f))
            #f.seek(-4, os.SEEK_CUR)

            for o in subFileOffsets[1:]:
                meshes = CarMesh._fromFile(f, o)
                for i,mesh in enumerate(meshes):
                    print(f"{mesh.meshVertCount} from {f.tell() - o}")
                    with open(f"{outfolder}/{basename}-{i}.obj", "w") as fout:
                        mesh.writeMeshToObj(fout)
                print(f"Got to {f.tell()}")
        elif loadtype == 4: 
            # Load as palette

            paletteX = Texture._paletteFromFile(f, 0, 0, True)
            
            print(paletteX[0])

            cList = []
                
            for c in paletteX[0]:
                cList.append(c[0])
                cList.append(c[1])
                cList.append(c[2])
                cList.append(c[3])
            print(f"paletteLen = {len(cList)} should be {paletteX[1][0]},{paletteX[1][1]} len {len(bytes(cList))}")

            image = Image.frombytes('RGBA', (paletteX[1][0], paletteX[1][1]), bytes(cList), 'raw', 'RGBA')
            image.save(f"{outfolder}/{basename}.png", "PNG")

            print("Loading as palette")