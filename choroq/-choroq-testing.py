
import io
import os
import sys
from choroq.texture import Texture
from choroq.car import CarModel, CarMesh
import choroq.read_utils as U

def jumpZeros(f):
    i = 1
    b = U.readByte(f)
    while b == 0:
        b = U.readByte(f)
        i += 1
    f.seek(-1, os.SEEK_CUR)
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

    if loadtype < 0 or loadtype > 2:
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
            isT = (t & 0x06) > 0
            print(f"HasAnotherTexture: {isT} {t} {f.tell()}")
            i = 0
            while (isT):
                tex = Texture._fromFile(f, o)
                tex.writeTextureToPNG(f"out/GARAGE.bin-{i}.png")
                tex.writePaletteToPNG(f"out/GARAGE.bin-{i}-p.png")
                o += jumpZeros()
                isT = (U.readByte() & 0x06) > 0
                print(f"HasAnotherTexture: {isT} {t} {f.tell()}")
                f.seek(-1, os.SEEK_CUR)
                i += 1
        elif loadtype == 2: 
            # Try loading as a texture + palette
            print("Loading as Texture file")
            
            f.seek(0, os.SEEK_SET)
            isT = U.readByte() & 0x06 > 0

            while (isT):
                tex = Texture._fromFile(f, 0)
                tex.writeTextureToPNG(f"{outfolder}/{basename}-bw.png", usepalette=False)
                tex.writeTextureToPNG(f"{outfolder}/{basename}.png")
                tex.writePaletteToPNG(f"{outfolder}/{basename}-p.png")
                jumpZeros(f)
                isT = U.readByte() & 0x06 > 0
                print(f"HasAnotherTexture: {isT}")
                f.seek(-1, os.SEEK_CUR)
            