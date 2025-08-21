# DMA tag info https://psi-rockin.github.io/ps2tek/#dmacchainmode
# 0-15    QWC to transfer
# 16-25   Unused
# 26-27   Priority control
#         0=No effect
#         1=Reserved
#         2=Priority control disabled (D_PCR.31 = 0)
#         3=Priority control enabled (D_PCR.31 = 1)
# 28-30   Tag ID
# 31      IRQ
# 32-62   ADDR field (lower 4 bits must be zero)
# 63      Memory selection for ADDR (0=RAM, 1=scratchpad)
# 64-127  Data to transfer (only if Dn_CHCR.TTE==1)
# Source Chain Tag ID
#
# 0    refe    MADR=DMAtag.ADDR
#             TADR+=16
#             tag_end=true
#
# 1    cnt     MADR=TADR+16 (next to DMAtag)
#             TADR=MADR (next to transfer data)
#
# 2    next    MADR=TADR+16
#             TADR=DMAtag.ADDR
#
# 3    ref     MADR=DMAtag.ADDR
#             TADR+=16
#
# 4    refs    MADR=DMAtag.ADDR
#             TADR+=16
#
# 5    call    MADR=TADR+16
#             if (CHCR.ASP == 0)
#                 ASR0=MADR+(QWC*16)
#             else if (CHCR.ASP == 1)
#                 ASR1=MADR+(QWC*16)
#             TADR=DMAtag.ADDR
#             CHCR.ASP++
#
# 6    ret     MADR=TADR+16
#             if (CHCR.ASP == 2)
#                 TADR=ASR1
#                 CHCR.ASP--
#             else if (CHCR.ASP == 1)
#                 TADR=ASR0
#                 CHCR.ASP--
#             else:
#                 tag_end=true
#
# 7    end     MADR=TADR+16
#                 tag_end=true
# When tag_end=true, the transfer ends after QWC has been transferred.
#
# Dest Chain Tag ID
#
# 0    cnt     MADR=DMAtag.ADDR
#
# 1    cnts    MADR=DMAtag.ADDR
#
# 7    end     MADR=DMAtag.ADDR
#             tag_end=true
import os
import io
import struct
import math
import choroq.read_utils as U
from dataclasses import dataclass    

def decode_DMATag(file):
    starting_pos = file.tell()
    # 0-15
    qwordCount = U.readShort(file) # * 64 = Length of transfer
    # 16-31
    part2 = U.readShort(file) 
    unused = part2 & 0x3FF
    priorityControl = (part2 & 0xC00) >> 10
    tagId = (part2 & 0x7000) >> 12
    irq = (part2 & 0x8000) >> 15
    # 32-63
    part3 = U.readLong(file)
    addr = part3 & 0x7FFFFFFF
    memorySelect = (part3 >> 31) & 1
    # 64-127 # 4 bytes
    data = U.read64(file)

    return { 
        'qwordCount': qwordCount, 
        'unused': unused, 
        'priorityControl': priorityControl, 
        'tagId': tagId,
        'irq': irq,
        'addr': addr, 
        'memorySelect': memorySelect, 
        'data': data,
        'taddr': starting_pos
        }

def decode_DMATagID_source(dmaTag, ASR0 = 0, ASR1 = 0, ASP = 0):
    tagId = dmaTag['tagId']
    memAddress = 0
    tagAddress = dmaTag['taddr']
    tagEnd = False
    if tagId == 0:
        # Refe 
        memAddress = tagAddress
        tagAddress += 16
        tagEnd = True
    elif tagId == 1:
        # cnt (continue?)
        memAddress = tagAddress + 16
        tagAddress += 16
    elif tagId == 2:
        # next
        memAddress = tagAddress + 16
        tagAddress += dmaTag["addr"]
    elif tagId == 3:
        # refs
        memAddress = dmaTag["addr"]
        tagAddress += 16
    elif tagId == 4:
        memAddress = dmaTag["addr"]
        tagAddress += 16
    elif tagId == 5:
        # call
        memAddress = tagAddress + 16
        if ASP == 0:
            ASR0 = memAddress + dmaTag["qwordCount"]*16
        elif ASP == 1:
            ASR1 = memAddress + dmaTag["qwordCount"]*16
        tagAddress = dmaTag["addr"]
        ASP += 1
    elif tagId == 6:
        # ret
        # Does some things to Address Stack, ASR0/ASR1 changes
        memAddress = tagAddress + 16
        if ASP == 2:
            tagAddress = ASR1
            ASP -= 1
        elif ASP == 1:
            tagAddress = ASR0
            ASP -= 1
        else:
            tagEnd = True
    elif tagId == 7:
        memAddress = tagAddress + 16
        tagEnd = True
    else:
        print(f"Failed to decode dmaTag {dmaTag}")
        return None
    return { 'maddr': memAddress, 'taddr': tagAddress, 'tag_end': tagEnd, 'ASR0': ASR0, 'ASR1': ASR1, 'ASP': ASP }

def decode_DMATagID_dest(tagAddress, dmaTag):
    tagId = dmaTag['tagId']
    memAddress = 0
    tagAddress = dmaTag['taddr']
    tagEnd = False
    if tagId == 0:
        # cnt (continue?)
        memAddress = dmaTag['addr']
    elif tagId == 1:
        # cnts
        memAddress = dmaTag['addr']
    elif tagId == 7:
        memAddress = dmaTag['addr']
        tagEnd = True
    
    return { 'maddr': memAddress, 'taddr': tagAddress, 'tag_end': tagEnd }
    
def findAllImages(file, offset):
    file.seek(offset, os.SEEK_SET)
    dmaTag = decode_DMATag(file)
    tagId = decode_DMATagID_source(dmaTag)
    # print(dmaTag)
    # print(dmaTag['qwordCount']*16+16)
    # print(tagId)
    file.seek(offset, os.SEEK_SET)

    imageOffsets = [offset]

    nextAddr = dmaTag['qwordCount']*16+16
    imageOffsets.append(nextAddr)
    accumlatedDmaPos = nextAddr
    while not tagId['tag_end']:
        # print(f"seeking: {dmaTag['taddr']+nextAddr}")
        file.seek(dmaTag['taddr']+nextAddr, os.SEEK_SET)
        # print(f"Got DmaCont: {nextAddr}-> {f.tell()}")
        dmaTag = decode_DMATag(file)
        tagId = decode_DMATagID_source(dmaTag)
        # print(dmaTag)
        # print(dmaTag['qwordCount']*16+16)
        # print(tagId)
        nextAddr = dmaTag['qwordCount']*16+16
        imageOffsets.append(dmaTag['taddr']+nextAddr)
    
    file.seek(offset, os.SEEK_SET)
    return imageOffsets

def decodeFromVIFCode(file, offset, state):
    debugVIF = True

    # State holds register info, collected from tags
    # Hopefully this is enough to decode everything
    if state == None:
        state = {}
        state["WL"] = 1 # prevent /0
        state["CL"] = 1 # prevent /0
        state["OFFSET"] = 0
        state["BASE"] = 0
        state["ITOPS"] = 0
        state["MODE"] = 0
        state["MSKPATH3"] = False
        state["EXECADDR"] = 0
        state["MASK"] = 0
    data = {}
    expectedLength = 0
    

    file.seek(offset, os.SEEK_SET)
    vifCode = U.readLong(file)
    # VIF code structure, 32 bits
    # 00-15 (0x0000FFFF) - Immediate field
    # 16-23 (0x00FF0000) - NUM, Number field
    # 24-31 (0xFF000000) - CMD, Command field
    immediate = vifCode & 0x0000FFFF
    # Amount of data written, for MicroMeme * 64 bytes otherwise * 128 bytes
    # 0 = 256 apparently
    # This is not the amount of data in the packet, as it may repeat (See CYCLE register)
    num = (vifCode & 0x00FF0000) >> 16
    if num == 0: 
        num = 256 # As transfering 0 would make no sense

    cmd = (vifCode & 0xFF000000) >> 24
    interrupt = cmd & 0b10000000 # interrupt flag
    cmd = cmd & 0b01111111 # cmd without interrupt flag
    # Packet length 1 operations:
    if cmd == 0:
        # NOP operation
        if debugVIF: 
            print(f"VIF: NOP")
    elif cmd == 0b00000001:
        # STCYCL sets CYCLE register value
        wl = (immediate & 0xFF00) >> 8
        cl = immediate & 0xFF
        if debugVIF: 
            print(f"VIF: STCYCL CYCLE->{immediate} to WL/CL {wl} {cl}")
        state["WL"] = wl
        state["CL"] = cl
    elif cmd == 0b00000010:
        # OFFSET Sets OFFSET register value (VIF1 only)
        # Double buffer offset
        if debugVIF: 
            print(f"VIF: OFFSET->{immediate & 0x3F}")
        state["OFFSET"] = immediate & 0x3F
    elif cmd == 0b00000011:
        # BASE Sets BASE register value (VIF1 only)
        # BASE address of the double buffer
        if debugVIF: 
            print(f"VIF: BASE->{immediate & 0x3F}")
        state["BASE"] = immediate & 0x3F
    elif cmd == 0b00000100:
        # ITOP Sets ITOPS register value
        if debugVIF: 
            print(f"VIF: ITOP ITOPS->{immediate & 0x3F}")
        state["ITOPS"] = immediate & 0x3F
    elif cmd == 0b00000101:
        # STMOD Sets MODE register value
        if debugVIF: 
            print(f"VIF: STMOD MODE->{immediate & 0x3}")
        state["MODE"] = immediate & 0x3
    elif cmd == 0b00000110:
        # MSKPATH3 Masks GIF PATH3 transfer (VIF1 only)
        if debugVIF: 
            print(f"VIF: MSKPATH3 Masked/Disabled?->{immediate & 0x8000 == 0x8000}")
        state["MSKPATH3"] = immediate & 0x8000 == 0x8000
    elif cmd == 0b00000111:
        # MARK Sets MARK register value
        # The MARK VIF is always executed, even if a interrupt stall is triggered, I think
        if debugVIF: 
            print(f"VIF: MARK MARK->{immediate} Usually used for debugging with EE/CORE")
    elif cmd == 0b00010000:
        # FLUSHE Waits for end of microprogram
        if debugVIF: 
            print(f"VIF: FLUSHE")
    elif cmd == 0b00010001:
        # FLUSH Waits for the end of the micro program and for the end of GIF (PATH1/PATH2) transfer (VIF1 only)
        if debugVIF: 
            print(f"VIF: FLUSH")
    elif cmd == 0b00010011:
        # FLUSHA Waits for the end of the micro program and the end of GIF transfer (VIF1 only)
        if debugVIF: 
            print(f"VIF: FLUSHA->{immediate}")
        state["EXECADDR"] = immediate*8
    elif cmd == 0b00010100:
        # MSCAL Activates Micro programs
        if debugVIF: 
            print(f"VIF: MSCAL EXECADDR->{immediate*8}")
        state["EXECADDR"] = immediate*8
    elif cmd == 0b00010111:
        # MSCNT Executes the micro programs continuously
        if debugVIF: 
            print(f"VIF: MSCNT")
    elif cmd == 0b00010101:
        # MSCALF Activates micro programs (VIF1 only)
        if debugVIF: 
            print(f"VIF: MSCALF EXECADDR->{immediate*8}")
        state["EXECADDR"] = immediate*8
    # ^^^^^^^^^^^ END of 1 packet length Codes ^^^^^^^^^^^^^^
    elif cmd == 0b00100000:
        # STMASK Sets value to MASK register
        # 1+1 VIF packet length
        # I think is is
        maskValue = U.readLong(file)
        if debugVIF: 
            print(f"VIF: STMASK {maskValue}")
        state["MASK"] = maskValue
    elif cmd == 0b00110000:
        # STROW Sets value to Row register
        # 1+4 VIF packet length
        r0 = U.readFloat(file)
        r1 = U.readFloat(file)
        r2 = U.readFloat(file)
        r3 = U.readFloat(file)
        # Used by unpack for filling
        if debugVIF: 
            print(f"VIF: STROW R0-R3->{r0} {r1} {r2} {r3}")
        state["R0"] = r0
        state["R1"] = r1
        state["R2"] = r2
        state["R3"] = r3
    elif cmd == 0b00110001:
        # STCOL Sets value to Col register
        # 1+4 VIF packet length
        c0 = U.readFloat(file)
        c1 = U.readFloat(file)
        c2 = U.readFloat(file)
        c3 = U.readFloat(file)
        # Used by unpack for filling
        if debugVIF: 
            print(f"VIF: STCOL C0-C3->{c0} {c1} {c2} {c3}")
        state["C0"] = c0
        state["C1"] = c1
        state["C2"] = c2
        state["C3"] = c3
    elif cmd == 0b01001010:
        # MPG Loads Micro program
        # 1+NUM+2 VIF packet length
        # Next bit would be microprogram, unlikely to occur in RT  data
        program = []
        for i in range(0, num):
            program.append(U.read64(file))
        if debugVIF: 
            print(f"VIF: MPG loadAddr: {immediate*8}, amount: {num} x 64bit words ({num*8} bytes)")
        expectedLength = num*8
    elif cmd == 0b01010000:
        # DIRECT Transfers data to GIF via PATH2 (VIF1 only)
        # 1+IMMEDIATEx4 VIF packet length
        # This will require a GIF tag within the data, I think
        directData = []
        ddLen = immediate
        if ddLen == 0:
            ddLen = 65536 # As transfering 0 would make no sense
        for i in range(0, ddLen):
            # Doing it this way, as we will want the data as longs
            directData.append(U.readLong(file))
            directData.append(U.readLong(file))
            directData.append(U.readLong(file))
            directData.append(U.readLong(file))
        if debugVIF: 
            print(f"VIF: DIRECT to GIF via Path2 len={ddLen}")
        data["values"] = directData
        expectedLength = ddLen
    elif cmd == 0b01010001:
        # DIRECTHL Transfers data to GIF via PATH2 (VIF1 only)
        # 1+IMMEDIATEx4 VIF packet length
        # This will require a GIF tag within the data, I think
        
        # -- Does not interrupt PATH3, but thats irrelevent here
        #    also stalls until the end, if IMAGE mode data via PATH3
        directData = []
        ddLen = immediate
        if ddLen == 0:
            ddLen = 65536 # As transfering 0 would make no sense
        for i in range(0, ddLen):
            # Doing it this way, as we will want the data as longs
            directData.append(U.readLong(file))
            directData.append(U.readLong(file))
            directData.append(U.readLong(file))
            directData.append(U.readLong(file))
        if debugVIF: 
            print(f"VIF: DIRECTHL to GIF via Path2 len={ddLen}")
        data["values"] = directData
        expectedLength = ddLen
    elif cmd &  0b01100000 == 0b01100000:
        if debugVIF: 
            print(f"VIF: UNPACK command is {cmd}")
            print(f"VIF: UNPACK num is {num}")
            print(f"VIF: UNPACK immediate is {immediate}")
        # UNPACK Decompresses data and writes to VU memory
        # Varies?
        # num field is the amount of data written (in 128bit units)
        # - not always length read
        vuMemDestAddr = immediate & 0x3F
        
        # SignFlag changes how the extending of bits work, 
        #  - false = always 0, 
        #  - true = decompresses by sign extension
        signFlag = immediate & 0x4000 == 0x4000
        # ? +VIF1_TOPS
        addressMode = immediate & 0x8000 == 0x8000 
        otherBitsImmediate = immediate & 0x3C00 # For debugging

        if addressMode: # If flag set
            # VPU1: add value of VIF1_TOPS the selected address
            vuMemDestAddr += state["ITOPS"]
            # TODO: this might be hard to handle from here, so lets hope its not set
            print(f"VIF: UNPACK: addressMode={addressMode} needs VIF1_TOPS. Dest addr {vuMemDestAddr}, TOPS would probably be set to a big number, to avoid FB")
            # exit(89)
        else:
            print(f"VIF: UNPACK: addressMode={addressMode} no VIF1_TOPS. Dest addr {vuMemDestAddr}")

        # Calculate VIF packet length
        # WL<=CL:     1+(((32>>vl) x (vn+1)) x num//32)
        # WL>CL:      1+(((32>>vl) x (vn+1)) x n//32)
        #             However, n=CL x (num/WL)+limit(num%WL,CL)
        #             int limit(int a, int max)
        #             { return(a>max ? max : a);}

        # Split the command
        unpackCmd = cmd & 0b00001111
        # The m bit shows the presence of the supplementation and mask processing. See "6.3.6. Write Data Mask"
        maskBit   = cmd & 0b00010000 # m bit
        unpackVN = (cmd & 0b00001100) >> 2 # vn part of unpack
        unpackV1 = (cmd & 0b00000011) # v1 part of unpack
        print(f"VIF: UNPACK: VN:{unpackVN} V1:{unpackV1}")

        
        size1 = 1+(((32 >> unpackV1) * (unpackVN + 1)) * int(math.ceil(float(num) / 32.0)))
        n = state["CL"] * (num/state["WL"]) + min(num % state["WL"], state["CL"])
        size2 = 1+(((32 >> unpackV1) * (unpackVN + 1)) * int(math.ceil(float(n) / 32.0)))
        print(f"VIF: UNPACK: Size if WL <= CL would be: {size1}")
        print(f"VIF: UNPACK: Size if WL >  CL would be: {size2}")
        if state["WL"] <= state["CL"]:
            expectedLength = size1
        elif state["WL"] > state["CL"]:
            expectedLength = size2

        print(f"VIF: UNPACK: Going with: {expectedLength} ?bytes?64s?128s?")

        # Determine the format output_type, one of: S-XX or V2-XX or V2-XX or V3-XX or V4-XX
        formatS = unpackVN == 0   # Scaler varation
        formatV2 = unpackVN == 1  # Vector2 variation
        formatV3 = unpackVN == 2  # Vector3 variation
        formatV4 = unpackVN == 3  # Vector4 variation, unless V4-5 which is RGBa 5551 decoder

        # Used for printing types in human readable
        debugUnpackFromatString = "UUU"
        if formatS:
            debugUnpackFromatString = " S-"
        elif formatV2:
            debugUnpackFromatString = "V2-"
        elif formatV3:
            debugUnpackFromatString = "V3-"
        elif formatV2:
            debugUnpackFromatString = "V4-"

        # Determine format size # X-32 or X-16 or X-8 or (X-5)
        formatSize = 0
        if unpackV1 == 0:
            formatSize = 32
            dataLength = 32
        elif unpackV1 == 1:
            formatSize = 16
            dataLength = 16
        elif unpackV1 == 2:
            formatSize = 8
            dataLength = 8
        elif unpackV1 == 3 and formatV4:
            # V4-5 is handled differently
            formatSize = 5
            dataLength = 16
        else:
            print(f"VIF: UNPACK: {debugUnpackFromatString}{formatSize} with VN:{unpackVN} V1:{unpackV1}")
            print("VIF: UNPACK: Unknown Tag probably invalid")
            exit()

        
        # Number of elements e.g x/y or x/y/z or x/y/z/w or scaler
        elementSize = unpackVN + 1
        result = []
        directData = []

        if formatS:
            if formatSize == 32:
                # Read in the data we want
                # "uncompress" the read data
                for i in range(0, expectedLength):
                    scaler = U.readFloat(file)
                    directData.append(scaler)
                    result.append((scaler, scaler, scaler, scaler))
            elif formatSize == 16:
                print("VIF: UNPACK: Not implemeneted S-16")
                exit(89)
            elif formatSize == 8:
                print("VIF: UNPACK: Not implemeneted S-8")
                exit(89)
            else:
                print(f"VIF: UNPACK: Not implemeneted S unknown {formatSize}")
                exit(89)
        elif formatV2:
            if formatSize == 32:
                # Read in the data we want
                # "uncompress" the read data
                for i in range(0, expectedLength):
                    x = U.readFloat(file)
                    y = U.readFloat(file)
                    directData.append(x)
                    directData.append(y)
                    result.append((x, y, 0, 0))
            elif formatSize == 16:
                print("VIF: UNPACK: Not implemeneted V2-16")
                exit(89)
            elif formatSize == 8:
                print("VIF: UNPACK: Not implemeneted V2-8")
                exit(89)
            else:
                print(f"VIF: UNPACK: Not implemeneted V2 unknown {formatSize}")
                exit(89)
        elif formatV3:
            if formatSize == 32:
                # Read in the data we want
                # "uncompress" the read data
                for i in range(0, expectedLength):
                    x = U.readFloat(file)
                    y = U.readFloat(file)
                    z = U.readFloat(file)
                    directData.append(x)
                    directData.append(y)
                    directData.append(z)
                    result.append((x, y, z, 0))
            elif formatSize == 16:
                print("VIF: UNPACK: Not implemeneted V3-16")
                exit(89)
            elif formatSize == 8:
                print("VIF: UNPACK: Not implemeneted V3-8")
                exit(89)
            else:
                print(f"VIF: UNPACK: Not implemeneted V3 unknown {formatSize}")
                exit(89)
        elif formatV4:
            if formatSize == 32:
                # Read in the data we want
                # "uncompress" the read data
                for i in range(0, expectedLength):
                    x = U.readFloat(file)
                    y = U.readFloat(file)
                    z = U.readFloat(file)
                    w = U.readFloat(file)
                    directData.append(x)
                    directData.append(y)
                    directData.append(z)
                    directData.append(w)
                    result.append((x, y, z, w))
            elif formatSize == 16:
                print("VIF: UNPACK: Not implemeneted V4-16")
                exit(89)
            elif formatSize == 8:
                print("VIF: UNPACK: Not implemeneted V4-8")
                exit(89)
            elif formatSize == 5:
                print("VIF: UNPACK: Not implemeneted V4-5")
                exit(89)
            else:
                print(f"VIF: UNPACK: Not implemeneted V4 unknown {formatSize}")
                exit(89)
        else:
            print(f"VIF: UNPACK: Not implemeneted Type S/V2/V3/V4?? unknown {formatSize}")
            exit(89)

    else:
        print(f"VIF: Unknown format, not valid tag")
        exit(89)

    print(f"VIF: Finished Got to {file.tell()}")
    data["length"] = expectedLength
    return state, data

####################################################################
#   _______   __       __   ______     __                         
#  /       \ /  \     /  | /      \   /  |                        
#  $$$$$$$  |$$  \   /$$ |/$$$$$$  | _$$ |_     ______    ______  
#  $$ |  $$ |$$$  \ /$$$ |$$ |__$$ |/ $$   |   /      \  /      \ 
#  $$ |  $$ |$$$$  /$$$$ |$$    $$ |$$$$$$/    $$$$$$  |/$$$$$$  |
#  $$ |  $$ |$$ $$ $$/$$ |$$$$$$$$ |  $$ | __  /    $$ |$$ |  $$ |
#  $$ |__$$ |$$ |$$$/ $$ |$$ |  $$ |  $$ |/  |/$$$$$$$ |$$ \__$$ |
#  $$    $$/ $$ | $/  $$ |$$ |  $$ |  $$  $$/ $$    $$ |$$    $$ |
#  $$$$$$$/  $$/      $$/ $$/   $$/    $$$$/   $$$$$$$/  $$$$$$$ |
#                                                       /  \__$$ |
#                                                       $$    $$/ 
#                                                        $$$$$$/  
####################################################################


####################################################################
#   __     __  ______  ________                         __           
#  /  |   /  |/      |/        |                       /  |          
#  $$ |   $$ |$$$$$$/ $$$$$$$$/_______   ______    ____$$ |  ______  
#  $$ |   $$ |  $$ |  $$ |__  /       | /      \  /    $$ | /      \ 
#  $$  \ /$$/   $$ |  $$    |/$$$$$$$/ /$$$$$$  |/$$$$$$$ |/$$$$$$  |
#   $$  /$$/    $$ |  $$$$$/ $$ |      $$ |  $$ |$$ |  $$ |$$    $$ |
#    $$ $$/    _$$ |_ $$ |   $$ \_____ $$ \__$$ |$$ \__$$ |$$$$$$$$/ 
#     $$$/    / $$   |$$ |   $$       |$$    $$/ $$    $$ |$$       |
#      $/     $$$$$$/ $$/     $$$$$$$/  $$$$$$/   $$$$$$$/  $$$$$$$/ 
####################################################################

VIF_CMD_NOP = 0b0000000
VIF_CMD_SETCYCL = 0b0000001
VIF_CMD_OFFSET = 0b0000010
VIF_CMD_BASE = 0b0000011
VIF_CMD_ITOP = 0b0000100
VIF_CMD_STMOD = 0b0000101
VIF_CMD_MSKPATH3 = 0b0000110
VIF_CMD_MARK = 0b0000111
VIF_CMD_FLUSHE = 0b0010000
VIF_CMD_FLUSH = 0b0010001
VIF_CMD_FLUSHA = 0b0010011
VIF_CMD_MSCAL = 0b0010100
VIF_CMD_MSCALF = 0b0010101
VIF_CMD_MSCNT = 0b0010111
VIF_CMD_STMASK = 0b0100000
VIF_CMD_STROW = 0b0110000
VIF_CMD_STCOL = 0b0110001
VIF_CMD_MPG = 0b1001010
VIF_CMD_DIRECT = 0b1010000
VIF_CMD_DIRECTHL = 0b1010001
VIF_CMD_UNPACK_LOWEST = 0b1100000
VIF_CMD_UNPACK_HIGHEST = 0b1111111


# Dict to allow looking up the cmd field of the VIF command which will give the command info
# to say what this command is, if the cmd is not in this dict, it is invalid
vifCommandDebugMask = 0x7F
# Name
vifCommandDebugName = {
    VIF_CMD_NOP: "NOP",
    VIF_CMD_SETCYCL: "SETCYCL",
    VIF_CMD_OFFSET: "OFFSET",
    VIF_CMD_BASE: "BASE",
    VIF_CMD_ITOP: "ITOP",
    VIF_CMD_STMOD: "STMOD",
    VIF_CMD_MSKPATH3: "MSKPATH3",
    VIF_CMD_MARK: "MARK",
    VIF_CMD_FLUSHE: "FLUSHE",
    VIF_CMD_FLUSH: "FLUSH",
    VIF_CMD_FLUSHA: "FLUSHA",
    VIF_CMD_MSCAL: "MSCAL",
    VIF_CMD_MSCALF: "MSCALF",
    VIF_CMD_MSCNT: "MSCNT",
    VIF_CMD_STMASK: "STMASK",
    VIF_CMD_STROW: "STROW",
    VIF_CMD_STCOL: "STCOL",
    VIF_CMD_MPG: "MPG",
    VIF_CMD_DIRECT: "DIRECT",
    VIF_CMD_DIRECTHL: "DIRECTHL",
    # Unpack is multiple
    # Unmasked UNPACK first
    0b1100000: "UNPACK -  S-32 - No mask",
    0b1100001: "UNPACK -  S-16 - No mask",
    0b1100010: "UNPACK -  S-8  - No mask",
    0b1100100: "UNPACK - V2-32 - No mask",
    0b1100101: "UNPACK - V2-16 - No mask",
    0b1101010: "UNPACK - V2-8  - No mask",
    0b1101000: "UNPACK - V3-32 - No mask",
    0b1101001: "UNPACK - V3-16 - No mask",
    0b1101010: "UNPACK - V3-8  - No mask",
    0b1101100: "UNPACK - V4-32 - No mask",
    0b1101101: "UNPACK - V4-16 - No mask",
    0b1101110: "UNPACK - V4-8  - No mask",
    0b1101111: "UNPACK - V4-5  - No mask",
    # Masked UNPACK
    0b1110000: "UNPACK -  S-32 - Masked ",
    0b1110001: "UNPACK -  S-16 - Masked ",
    0b1110010: "UNPACK -  S-8  - Masked ",
    0b1110100: "UNPACK - V2-32 - Masked ",
    0b1110101: "UNPACK - V2-16 - Masked ",
    0b1111010: "UNPACK - V2-8  - Masked ",
    0b1111000: "UNPACK - V3-32 - Masked ",
    0b1111001: "UNPACK - V3-16 - Masked ",
    0b1111010: "UNPACK - V3-8  - Masked ",
    0b1111100: "UNPACK - V4-32 - Masked ",
    0b1111101: "UNPACK - V4-16 - Masked ",
    0b1111110: "UNPACK - V4-8  - Masked ",
    0b1111111: "UNPACK - V4-5  - Masked ",
}

vifCommandPacketLengthSimple = {
    VIF_CMD_NOP:        1,
    VIF_CMD_SETCYCL:    1,
    VIF_CMD_OFFSET:     1,
    VIF_CMD_BASE:       1,
    VIF_CMD_ITOP:       1,
    VIF_CMD_STMOD:      1,
    VIF_CMD_MSKPATH3:   1,
    VIF_CMD_MARK:       1,
    VIF_CMD_FLUSHE:     1,
    VIF_CMD_FLUSH:      1,
    VIF_CMD_FLUSHA:     1,
    VIF_CMD_MSCAL:      1,
    VIF_CMD_MSCALF:     1,
    VIF_CMD_MSCNT:      1,
    VIF_CMD_STMASK:     2,
    VIF_CMD_STROW:      5,
    VIF_CMD_STCOL:      5,
}

@dataclass
class VifState:
    # Registers used in handling the VIFcode and expanding data
    WL = 1 # Defaulting to 1 as it prevents /0
    CL = 1 # Defaulting to 1 as it prevents /0
    Offset = 0
    Base = 0
    ITOPS = 0 # Program related address
    Mode = 0 # 0 = No change       VuMemory = Input data
            # 1 = Offset mode     VuMemory = Input data + row registers (R0-R3) 
            # 2 = Difference mode VuMemory = Input data + row registers (R0-R3), and row registers (R0-R3) = last written value
    MaskPath3 = 0 # Disables Path3 if set
    Mark = 0 # Used for debugging afaik
    ExecAddr = 0 # Address of MicroProgram to run at, used to call subroutines afaik multiply by 8 to get actual address
    Mask = 0 # Used to mask of areas to write into, e.g dont write into the masked ones for X/Y but do for Z/W
    RowRegisters = [0, 0, 0, 0] # Values to write based on Mode register, Used for filling during unpack, requires mask == 1 for this bit
    ColRegisters = [0, 0, 0, 0] # Used for filling during unpack, requires mask == 2 for this bit
    LoadAddr = 0 # Used as addr for micro program, unsure if load means destination address in vu micromemory or something else

    # Auto init to 0
    def __init__(self):
        self.WL = 1 
        self.CL = 1 
        self.Offset = 0 
        self.Base = 0 
        self.ITOPS = 0 
        self.Mode = 0 
        self.MaskPath3 = 0 
        self.Mark = 0 
        self.ExecAddr = 0 
        self.Mask = 0 
        self.RowRegisters = [0, 0, 0, 0]
        self.ColRegisters = [0, 0, 0, 0]
        self.LoadAddr = 0 
            


# This will parse the next 32 bits as a vifcode, and read in any required data
# 
# If this should unpack, this function will expand as needed, and return expanded bytes
# The position of the stream will change
# vifState will keep track of changes to fields, if needed see class VifState
def VifHandle(file, vifState):
    if vifState is None: # This means the read state will be lost, but no errors
        vifState = VifState()
    # Determine what tag this is
    vifCode = U.readLong(file)
    cmd, num, immediate, interrupt, expectedLengthInPackets, fields = VifDecode(vifCode, vifState)
    readData = None
    expectedLengthOut = 0
    # Determine what needs to be done for this VIF tag
    # Only a few of these will effect any of my code, so I will only implement a subset
    # any others will cause the program to exit (with a 90-99 error code)
    if cmd == VIF_CMD_NOP:
        pass
    elif cmd == VIF_CMD_SETCYCL:
        vifState.WL = fields["WL"]
        vifState.CL = fields["CL"]
    elif cmd == VIF_CMD_OFFSET:
        vifState.Offset = fields["OFFSET"]
    elif cmd == VIF_CMD_BASE:
        vifState.Base = fields["BASE"]
    elif cmd == VIF_CMD_ITOP:
        vifState.ITOPS = fields["ITOPS"]
    elif cmd == VIF_CMD_STMOD:
        vifState.Mode = fields["Mode"]
    elif cmd == VIF_CMD_MSKPATH3:
        vifState.MaskPath3 = fields["MSKPATH3"]
    elif cmd == VIF_CMD_MARK:
        vifState.Mark = fields["MARK"]
    elif cmd == VIF_CMD_FLUSHE:
        pass
    elif cmd == VIF_CMD_FLUSH:
        pass
    elif cmd == VIF_CMD_FLUSHA:
        pass
    elif cmd == VIF_CMD_MSCAL:
        vifState.ExecAddr = fields["EXECADDR"]
    elif cmd == VIF_CMD_MSCALF:
        vifState.ExecAddr = fields["EXECADDR"]
    elif cmd == VIF_CMD_MSCNT:
        pass
    elif cmd == VIF_CMD_STMASK:
        vifState.Mask = U.readLong(file)
    elif cmd == VIF_CMD_STROW:
        vifState.RowRegisters[0] = U.readLong(file)
        vifState.RowRegisters[1] = U.readLong(file)
        vifState.RowRegisters[2] = U.readLong(file)
        vifState.RowRegisters[3] = U.readLong(file)
    elif cmd == VIF_CMD_STCOL:
        vifState.ColRegisters[0] = U.readLong(file)
        vifState.ColRegisters[1] = U.readLong(file)
        vifState.ColRegisters[2] = U.readLong(file)
        vifState.ColRegisters[3] = U.readLong(file)
    elif cmd == VIF_CMD_MPG:
        VifState.LoadAddr = fields["LOADDDR"]
        readData = U.read(fields["SIZE"] * 8)
    elif cmd == VIF_CMD_DIRECT:
        readData = U.read(fields["SIZE"] * 16)
    elif cmd == VIF_CMD_DIRECTHL:
        readData = U.read(fields["SIZE"] * 16)
    elif cmd >= VIF_CMD_UNPACK_LOWEST and cmd <= VIF_CMD_UNPACK_HIGHEST:
        lenToRead = (expectedLengthInPackets - 1) * 4 # convert to number of bytes
        vifDataIn = U.read(file, lenToRead)
        # Unpack, data
        expectedLengthOut, readData = VifUnpackData(cmd, num, immediate, interrupt, expectedLengthInPackets, fields, vifDataIn, vifState)
        pass

    return expectedLengthInPackets, expectedLengthOut, readData


# Given VIFcode is 32 bits/4 bytes
def VifDecode(vifCode, vifState):
    # VIF code structure, 32 bits
    # 00-15 (0x0000FFFF) - Immediate field
    # 16-23 (0x00FF0000) - NUM, Number field
    # 24-31 (0xFF000000) - CMD, Command field
    immediate = vifCode & 0x0000FFFF
    # Amount of data written, for MicroMeme * 64 bytes otherwise * 128 bytes
    # 0 = 256 apparently
    # This is not the amount of data in the packet, as it may repeat (See CYCLE register)
    num = (vifCode & 0x00FF0000) >> 16
    if num == 0: 
        num = 256 # As transfering 0 would make no sense

    cmd = (vifCode >> 24) & 0xFF
    interrupt = cmd & 0b10000000 # interrupt flag
    cmd = cmd & 0b01111111 # cmd without interrupt flag
    expected_length_in_packets = VifGetPacketSize(cmd, num, immediate)
    fields = VifDecodeFields(cmd, num, immediate)
    print(VifDebug(vifState, cmd, num, immediate, expected_length_in_packets, fields))

    return cmd, num, immediate, interrupt, expected_length_in_packets, fields

# Returns a string with information from the decoded VIF, used for debugging
def VifDebug(vifState, cmd, num, immediate, expectedLengthInPackets, fields):
    cmd = cmd & vifCommandDebugMask
    debugLine = ""
    # Add command's human-readable name
    if cmd not in vifCommandDebugName:
        debugLine += "Invalid VIF cmd"
    else:
        debugLine += vifCommandDebugName[cmd]
    
    # Add number field
    debugLine += f", NUM: {num}"

    # Add the expected packet size
    if cmd <= VIF_CMD_STCOL: # These are constant
        debugLine += ", Packet Length: "
    elif cmd == VIF_CMD_MPG:
        debugLine += ", Packet Length: 1+NUMx2 "
    elif cmd == VIF_CMD_DIRECT:
        debugLine += ", Packet Length: 1+IMMx4 "
    elif cmd == VIF_CMD_DIRECTHL:
        debugLine += ", Packet Length: 1+IMMx4 "
    else:
        debugLine += ", Packet Length: "
    debugLine += f"{expectedLengthInPackets} (packets * 4bytes)"
    
    if cmd >= VIF_CMD_UNPACK_LOWEST and cmd <= VIF_CMD_UNPACK_HIGHEST:
        debugLine += f", Expanded Length: {VifGetUnpackSize(cmd, num, immediate)} (bytes)"

    debugLine += f", Fields: {fields}"
    # debugLine += f", State: {vifState}"
    return debugLine


# Returns the number of 4 bytes used in this packet,
# this is not fully implemented, as it does not handle
# all of the unpack options, only the unpadded ones
# This returns the number of bytes that this will READ IN
# to get the expect unpack size use the other function
def VifGetPacketSize(cmd, num, immediate):
    # All packets are 1 + some extra amount, depending on output_type of packet
    if cmd <= VIF_CMD_STCOL:  # These are constant
        length = vifCommandPacketLengthSimple[cmd]
    elif cmd == VIF_CMD_MPG:
        length = 1+num*2
    elif cmd == VIF_CMD_DIRECT:
        length = 1+immediate*4
    elif cmd == VIF_CMD_DIRECTHL:
        length = 1+immediate*4
    elif cmd >= VIF_CMD_UNPACK_LOWEST and cmd <= VIF_CMD_UNPACK_HIGHEST:
        vn = VifGetVN(cmd)
        v1 = VifGetV1(cmd)
        elementLength = 4 >> v1 # 4 bytes down to 1 byte
        singleLength = elementLength * (vn + 1)
        print(f"VN: {vn} V1: {v1} {elementLength} {singleLength}")
        length = 1
        # TODO: fix to handle WC > CL
        # TODO: implement this byte form (with WC/CL considered) as other function
        if v1 == 0:
            # *-32 easy to calc
            # Shifting to get from num bytes to number of packets(32 bit)
            length = 1 + ((singleLength * num) >> 2)
        elif v1 == 1:
            # *-16 some are easy to calc
            # V2-16 = no padding
            # V4-16 = no padding
            if vn % 1 == 0: # Odd ones V2/ V4
                # Shifting to get from num bytes to number of packets(32 bit)
                length = 1 + ((singleLength * num) >> 2)
            else:
                print(f" Packet Length: complex, not implemented {vifCommandDebugName[cmd]}")
                exit(91)
        else:
            print(f" Packet Length: complex, not implemented {vifCommandDebugName[cmd]}")
            exit(91)
        # hard to handle (have padding) included
        # S-16, S-8, V2-8, V3-16, V3-8, V4-8, V4-5
    else:
        print(f"Command is probably invalid cmd {cmd} num {num} immediate {immediate}")
    # If you get an error and end up here, its because either a new cmd was found (very unlikely),
    # or very likely misread data that was then parsed as a VIF
    return length

# Returns the VN part of the Unpack command
# Assumes it is a UNPACK cmd
def VifGetVN(cmd):
    return (cmd >> 2) & 0b11
    
# Returns the V1 part of the Unpack command
# Assumes it is a UNPACK cmd
def VifGetV1(cmd):
    return cmd & 0b0011

# VU Mem address in transfer destination (address divided by 16.)
def VifGetUnpackAddr(immediate):
    return immediate & 0x3F

# Sign of 8-bit/16-bit input data S-16/S-8 V2-16/V2-8 ...
#   1 Unsigned (Decompresses by padding 0 to the upper field.)
#   0 Signed   (Decompresses by sign-extension.)
def VifGetUnpackSignBit(immediate):
    return (immediate >> 14) & 1

# If this bit is set the address would be adjusted based on
# the VIF1_TOPS register
def VifGetUnpackAddressMode(immediate):
    return (immediate >> 15) & 1

def VifGetUnpackSize(cmd, num, immediate):
    if cmd >= VIF_CMD_UNPACK_LOWEST and cmd <= VIF_CMD_UNPACK_HIGHEST:
        vn = VifGetVN(cmd)
        v1 = VifGetV1(cmd)
        elementLength = 4 >> v1 # 4 bytes down to 1 byte
        singleLength = elementLength * (vn + 1)
        # Now convert this input size to the expected, expanded length
         # S-32
        if vn == 0 and v1 == 0:
            return singleLength * 4 * num # Repeats each value 4 times to fill
         # V2-32
        elif vn == 1 and v1 == 0:
            return singleLength * 2 * num # Pads Z/W with unknown data
        # V2-16
        elif vn == 1 and v1 == 1: 
            return singleLength * num * 4  # Converts 16 bits into 32 bits, padding Z/w
        # V3-32
        elif vn == 2 and v1 == 0: 
            return (singleLength + elementLength) * num # Pads W with unknown data
        # V4-32
        elif vn == 3 and v1 == 0: 
            return singleLength * num # Just 1-1 copy
        # V4-16
        elif vn == 3 and v1 == 1: 
            return singleLength * num * 2 # Converts 16 bits into 32 bits
        else:
            print(F"Cannot parse this unpack, not implemented output size")
            exit(91)

    # Handle other packets as 0, as they are not expanding
    return 0

def VifDecodeFields(cmd, num, immediate):
    if cmd == VIF_CMD_NOP:
        return {}
    elif cmd == VIF_CMD_SETCYCL:
        wl = (immediate >> 8) & 0xFF
        cl = immediate & 0xFF
        if wl != 1 or cl != 1:
            print(f"WL/CL set to non 1 values WL:{wl} CL:{cl} this is not supportd")
            exit(92)
        return { "WL": wl, "CL": cl }
    elif cmd == VIF_CMD_OFFSET:
        return { "OFFSET": immediate & 0x3F }
    elif cmd == VIF_CMD_BASE:
        return { "BASE": immediate & 0x3F }
    elif cmd == VIF_CMD_ITOP:
        return { "ITOPS": immediate & 0x3F }
    elif cmd == VIF_CMD_STMOD:
        return { "MODE": immediate & 0x3 }
    elif cmd == VIF_CMD_MSKPATH3:
        return { "MSKPATH3": (immediate >> 15) & 1 }
    elif cmd == VIF_CMD_MARK:
        return { "MARK": immediate }
    elif cmd == VIF_CMD_FLUSHE:
        return {}
    elif cmd == VIF_CMD_FLUSH:
        return {}
    elif cmd == VIF_CMD_FLUSHA:
        return {}
    elif cmd == VIF_CMD_MSCAL:
        return { "EXECADDR": immediate*8 }
    elif cmd == VIF_CMD_MSCALF:
        return { "EXECADDR": immediate*8 }
    elif cmd == VIF_CMD_MSCNT:
        return {}
    elif cmd == VIF_CMD_STMASK:
        return {} #  This has next 32 bits as value for mask
    elif cmd == VIF_CMD_STROW:
        return {} # This has next 4x32 bits as value for R0-R3
    elif cmd == VIF_CMD_STCOL:
        return {} # This has next 4x32 bits as value for C0-C3
    elif cmd == VIF_CMD_MPG:
        return { "SIZE": num, "LOADADDR": immediate*8 } # This has next num*64 bits as instructions for micro mode
    elif cmd == VIF_CMD_DIRECT:
        if immediate == 0:
            immediate = 65536
        return { "SIZE": immediate }
    elif cmd == VIF_CMD_DIRECTHL:
        if immediate == 0:
            immediate = 65536
        return { "SIZE": immediate }
    elif cmd >= VIF_CMD_UNPACK_LOWEST and cmd <= VIF_CMD_UNPACK_HIGHEST:
        addr = immediate
        return { 
            "SIZE": num, 
            "ADDR": VifGetUnpackAddr(immediate),
            "USN": VifGetUnpackSignBit(immediate),
            "FLG": VifGetUnpackAddressMode(immediate) 
            }
    
    print("VifDecodeFields hit unknown cmd")
    return {}

def VifUnpackData(cmd, num, immediate, interrupt, expectedLengthInPackets, fields, vifDataIn, vifState):
    expectedLengthOut = VifGetUnpackSize(cmd, num, immediate)
    # Handle the unpacking of data
    vn = VifGetVN(cmd)
    v1 = VifGetV1(cmd)
    dataOut = io.BytesIO()
    dataIn = io.BytesIO(vifDataIn)
    # Handle S-32
    if vn == 0 and v1 == 0:
        for i in range(expectedLengthInPackets-1):
            value = U.readLong(dataIn)
            dataOut.write(struct.pack('<LLLL', value, value, value, value))

    # # Handle S-16
    # if vn == 0 and v1 == 1:
    #     for i in range((expectedLengthInPackets-1) * 2):
    #         value = U.readShort(dataIn)
    #         S1 = value & 0xFFFF
    #         # TODO: use signed/unsigned flag to extend to longs
    #         dataOut.write(struct.pack('<LLLL', S1, S1, S1, S1))
    #     if (expectedLengthInPackets-1) * 2 ==

    # Handle V2-32
    elif vn == 1 and v1 == 0:
        for i in range(int((expectedLengthInPackets-1)/2)):
            x = U.readLong(dataIn)
            y = U.readLong(dataIn)
            # TODO: use registers and mask and all that
            dataOut.write(struct.pack('<LLLL', x, y, 0, 0))

    # Handle V2-16
    elif vn == 1 and v1 == 1:
        for i in range(expectedLengthInPackets-1):
            x = U.readShort(dataIn)
            y = U.readShort(dataIn)
            # TODO: use registers and mask and all that
            # TODO: use signed/unsigned flag to extend to longs
            dataOut.write(struct.pack('<LLLL', x, y, 0, 0))
    
    
    # Handle V3-32
    elif vn == 2 and v1 == 0:
        for i in range(int((expectedLengthInPackets-1)/3)):
            x = U.readLong(dataIn)
            y = U.readLong(dataIn)
            z = U.readLong(dataIn)
            # TODO: use registers and mask and all that
            dataOut.write(struct.pack('<LLLL', x, y, z, 0))
            # dataOut.write(struct.pack('>LLLL', y, x, 0, z))
            # dataOut.write(struct.pack('>LLLL', 0, z, y, x))
    # # Handle V3-16
    # elif vn == 2 and v1 == 1:
    #     for i in range((expectedLengthInPackets-1)/3):
    #         x = U.readLong(dataIn)
    #         y = U.readLong(dataIn)
    #         z = U.readLong(dataIn)
    #         # TODO: use registers and mask and all that
    #         dataOut.write(struct.pack('<LLLL', x, y, z, 0))

    # Handle V4-32
    elif vn == 3 and v1 == 0:
        for i in range(int((expectedLengthInPackets-1)/4)):
            x = U.readLong(dataIn)
            y = U.readLong(dataIn)
            z = U.readLong(dataIn)
            w = U.readLong(dataIn)
            # TODO: use registers and mask and all that
            dataOut.write(struct.pack('<LLLL', x, y, z, w))
    # Handle V4-16
    elif vn == 3 and v1 == 1:
        for i in range(int((expectedLengthInPackets-1)/2)):
            x = U.readShort(dataIn)
            y = U.readShort(dataIn)
            z = U.readShort(dataIn)
            w = U.readShort(dataIn)
            # TODO: use registers and mask and all that
            # TODO: use signed/unsigned flag to extend to longs
            dataOut.write(struct.pack('<LLLL', x, y, z, w))
    # Handle V4-8
    elif vn == 3 and v1 == 2:
        for i in range(expectedLengthInPackets-1):
            x = U.readByte(dataIn)
            y = U.readByte(dataIn)
            z = U.readByte(dataIn)
            w = U.readByte(dataIn)
            # TODO: use registers and mask and all that
            # TODO: use signed/unsigned flag to extend to longs
            dataOut.write(struct.pack('<LLLL', x, y, z, w))
    # Handle V4-5
    # 5551 format
    # Same as a 16 format, but extract bits
    # elif vn == 3 and v1 == 2:
    #     for i in range(expectedLengthInPackets-1):
    #         x = U.readByte(dataIn)
    #         y = U.readByte(dataIn)
    #         z = U.readByte(dataIn)
    #         w = U.readByte(dataIn)
    #         # TODO: use registers and mask and all that
    #         # TODO: use signed/unsigned flag to extend to longs
    #         dataOut.write(struct.pack('<LLLL', x, y, z, w))
    else:
        print("This UNPACK format is not supported!")
        print(vifCommandDebugName[cmd])
        exit(91)
            
    dataOut.seek(0, os.SEEK_SET)
    print("Unpacked to:")
    print(dataOut.read(expectedLengthOut).hex())
    dataOut.seek(0, os.SEEK_SET)
    return expectedLengthOut, dataOut

####################################################################
#    ______   ______  ________  __                         
#   /      \ /      |/        |/  |                        
#  /$$$$$$  |$$$$$$/ $$$$$$$$/_$$ |_     ______    ______  
#  $$ | _$$/   $$ |  $$ |__  / $$   |   /      \  /      \ 
#  $$ |/    |  $$ |  $$    | $$$$$$/    $$$$$$  |/$$$$$$  |
#  $$ |$$$$ |  $$ |  $$$$$/    $$ | __  /    $$ |$$ |  $$ |
#  $$ \__$$ | _$$ |_ $$ |      $$ |/  |/$$$$$$$ |$$ \__$$ |
#  $$    $$/ / $$   |$$ |      $$  $$/ $$    $$ |$$    $$ |
#   $$$$$$/  $$$$$$/ $$/        $$$$/   $$$$$$$/  $$$$$$$ |
#                                                /  \__$$ |
#                                                $$    $$/ 
#                                                 $$$$$$/  
####################################################################
    
        
gifDebugMode = [
    # b00 
    "PACKED",
    # b01
    "REGLIST",
    # b10
    "IMAGE",
    # b11
    "DISABLED = IMAGE"
]

gifDebugRegisterDescriptor = [
    "PRIM",
    "RGBAQ",
    "ST",
    "UV",
    "XYZF2",
    "XYZ2",
    "TEX0_1",
    "TEX0_2",
    "CLAMP_1",
    "CLAMP_2",
    "FOG",
    "-",
    "XYZF3",
    "XYZ3",
    "Addr+Data",
    "NOP",
]

gifDebugRegisterAddress = [
    "0x00", # prim
    "0x01", # RGBAQ
    "0x02", # ST
    "0x03", # UV
    "0x04", # XYZF2
    "0x05", # XYZ2
    "0x06", # TEX0_1
    "0x07", # TEX0_2
    "0x08", # CLAMP_1
    "0x09", # CLAMP_2
    "0x0a", # FOG
    "-", # RESERVED
    "0x0c", # XYZF3
    "0x0d", # XYZ3
    "in data", # A+D
    "No Out", # NOP
]

gifDebugRegisterAddressName = {
    0x00: "PRIM",
    0x01: "RGBAQ",
    0x02: "ST",
    0x03: "UV",
    0x04: "XYZF2",
    0x05: "XYZ2",
    0x06: "TEX0_1",
    0x07: "TEX0_2",
    0x08: "CLAMP_1",
    0x09: "CLAMP_2",
    0x0A: "FOG",
    0x0C: "XYZF3",
    0x0D: "XYZ3",
    0x14: "TEX1_1",
    0x15: "TEX1_2",
    0x16: "TEX2_1",
    0x17: "TEX2_2",
    0x18: "XYOFFSET_1",
    0x19: "XYOFFSET_2",
    0x1A: "PRMODECONT",
    0x1B: "PRMODE",
    0x1C: "TEXCLUT",
    0x22: "SCANMSK",
    0x34: "MIPTBP1_1",
    0x35: "MIPTBP1_2",
    0x36: "MIPTBP2_1",
    0x37: "MIPTBP2_2",
    0x3B: "TEXA",
    0x3D: "FOGCOL",
    0x3F: "TEXFLUSH",
    0x40: "SCISSOR_1",
    0x41: "SCISSOR_2",
    0x42: "ALPHA_1",
    0x43: "ALPHA_2",
    0x44: "DIMX",
    0x45: "DTHE",
    0x46: "COLCLAMP",
    0x47: "TEST_1",
    0x48: "TEST_2",
    0x49: "PABE",
    0x4A: "FBA_1",
    0x4B: "FBA_2",
    0x4C: "FRAME_1",
    0x4D: "FRAME_2",
    0x4E: "ZBUF_1",
    0x4F: "ZBUF_2",
    0x50: "BITBLTBUF",
    0x51: "TRXPOS",
    0x52: "TRXREG",
    0x53: "TRXDIR",
    0x54: "HWREG",
    0x60: "SIGNAL",
    0x61: "FINISH",
    0x62: "LABEL",
}

gifDebugPrimType = [
    # b000
    "Point",
    # b001
    "Line",
    # b010
    "Line Strip",
    # b011
    "Triangle",
    # b100
    "Triangle Strip",
    # b101
    "Triangle Fan",
    # b110
    "Sprite",
    # b111
    "Invalid",
]

gifDebugPrimShadingMethod = [
    "Flat shading",
    "Gouraud shading",
    "Invalid"
]

gifDebugPSM = {
    0b000000 : "PSMCT32",
    0b000001 : "PSMCT24",
    0b000010 : "PSMCT16",
    0b001010 : "PSMCT16S",
    0b010011 : "PSMT8",
    0b010100 : "PSMT4",
    0b011011 : "PSMT8H",
    0b100100 : "PSMT4HL",
    0b101100 : "PSMT4HH",
    0b110000 : "PSMZ32",
    0b110001 : "PSMZ24",
    0b110010 : "PSMZ16",
    0b111010 : "PSMZ16S",
}

gifPsmToBitsPP = {
    "PSMCT32": 32,
    "PSMCT24": 24,
    "PSMCT16": 16,
    "PSMCT16S": 16, #signed
    "PSMT8": 8,
    "PSMT4": 4,
    "PSMT8H": 8, # upper 24 not used
    "PSMT4HL": 4, # upper 24 not used
    "PSMT4HH": 4, # upper nibble
    "PSMZ32": 32, # Z buffer
    "PSMZ24": 24, # Z buffer
    "PSMZ16": 16, # Z buffer
    "PSMZ16S": 16, # Z buffer signed
}

gifDebugPixelTransmissionOrder = [
    "UpperLeft -> LowerRight",
    "LowerLeft -> UpperRight",
    "UpperRight -> LowerLeft",
    "LowerRight -> UpperLeft",
]

gifDebugPrimOptions = [ "OFF", "ON" ]
gifDebugPrimFstOptions = [ "STQ", "UV" ]
gifDebugPrimCtxtOptions = [ "Env Ctx1", "Env Ctx2" ]
gifDebugPrimFixOptions = [ "Normal", "Fixed" ]



GIF_MODE_PACKED = 0
GIF_MODE_REGLIST = 1
GIF_MODE_IMAGE = 2
GIF_MODE_DISABLED = 3
GIF_REG_DESCRIPTOR_PRIM = 0
GIF_REG_DESCRIPTOR_RGBAQ = 1
GIF_REG_DESCRIPTOR_ST = 2
GIF_REG_DESCRIPTOR_UV = 3
GIF_REG_DESCRIPTOR_XYZF2 = 4
GIF_REG_DESCRIPTOR_XYZ2 = 5
GIF_REG_DESCRIPTOR_TEX0_1 = 6
GIF_REG_DESCRIPTOR_TEX0_2 = 7
GIF_REG_DESCRIPTOR_CLAMP_1 = 8
GIF_REG_DESCRIPTOR_CLAMP_2 = 9
GIF_REG_DESCRIPTOR_FOG = 10
GIF_REG_DESCRIPTOR_Reserved = 11
GIF_REG_DESCRIPTOR_XYZF3 = 12
GIF_REG_DESCRIPTOR_XYZ3 = 13
GIF_REG_DESCRIPTOR_AD = 14
GIF_REG_DESCRIPTOR_NOP = 15


# Number of repertition to perfom with this tag to get all data
def gifGetNLoop(gifTag):
    return gifTag & 0x7FFF

# Termination flag
# 0 with following primitive
# 1 witout following primitive, e.g end of stream of gs packet(single not plural)
def gifGetEop(gifTag):
    return (gifTag >> 15) & 1

# This area is marked as - so guessing its either used in special case, or should be 0/constant
def gifGetUnused(gifTag):
    return (gifTag >> 16) & 0x3FFFFFFF

# 46
# PRIM field enable (called pre)
# 0 ignore prim field
# 1 uses prim by moving to prim register
def gifGetPrimEnable(gifTag):
    return (gifTag >> 46) & 1

# Data for GS's PRIM register
def gifGetPrim(gifTag):
    return (gifTag >> 47) & 0x7FF

# flg
# 58-59
# Data format flag
# 00 PACKED   mode
# 01 REGLIST  mode
# 10 IMAGE    mode
# 11 Disable (Same operation with the IMAGE mode) - This might mean it shouldn't be used, but does same as image
def gifGetMode(gifTag):
    return (gifTag >> 58) & 0x3

# 60-63
# Number of register descriptors listed in REGS
# 0 actually means 16
def gifGetNReg(gifTag):
    nreg = (gifTag >> 60) & 0xF
    if nreg == 0:
        nreg = 16
    return nreg

# 64-127
# Register descriptors (4 bits each, max 16 registers)
# TODO: check
def gifGetRegisterDescriptors(gifTag):
    descriptorBits = gifTag >> 64
    descriptors = []
    for i in range(0, 16):
        descriptors.append(descriptorBits & 0xF)
        descriptorBits = descriptorBits >> 4
    return descriptors

def gifGetSize(gifTag):
    mode = gifGetMode(gifTag)
    nreg = gifGetNReg(gifTag)
    nloop = gifGetNLoop(gifTag)
    if mode == GIF_MODE_PACKED:
        size = nreg * nloop * 4
    elif mode == GIF_MODE_REGLIST:
        size = nreg * nloop * 4
    elif mode == GIF_MODE_IMAGE:
        size = nloop * 4
    elif mode == GIF_MODE_DISABLED:
        size = nloop * 4 # just incase
    else:
        print(f"This GIF tag is invalid, wrong mode {mode}?")
        exit(101)
    return size

def gifDecodePacked(descriptor):
    return gifDebugRegisterDescriptor[descriptor]

# This will probably not be used when VIF is involved, as I think
# the VU manipulates the data, 
def gifHandlePacked(file, gifTag, index, descriptor, gsState):
    if descriptor == GIF_REG_DESCRIPTOR_PRIM:
        prim = U.read128(file) & 0x7FF
        gsState.PRIM = parsePRIM(prim)
        return
    elif descriptor == GIF_REG_DESCRIPTOR_RGBAQ:
        r = U.readLong(file) & 0xFF
        g = U.readLong(file) & 0xFF
        b = U.readLong(file) & 0xFF
        a = U.readLong(file) & 0xFF
        gsState.RGBAQ['r'] = r
        gsState.RGBAQ['g'] = g
        gsState.RGBAQ['b'] = b
        gsState.RGBAQ['a'] = a
        gsState.RGBAQ['q'] = gsState.ST['q']
        return
    elif descriptor == GIF_REG_DESCRIPTOR_ST:
        s = U.readFloat(file)
        gsState.ST['s'] = s
        t = U.readFloat(file)
        gsState.ST['t'] = t
        q = U.readFloat(file)
        # This is usually stored internally in the GIF should be fine like this
        gsState.ST['q'] = q 
        return
    elif descriptor == GIF_REG_DESCRIPTOR_UV:
        u = U.readLong(file) & 0x3FFF # 0-13
        v = U.readLong(file) & 0x3FFF # 32-45
        # Convert these into floats, as they are 14bit fixed point numbers
        # so first parse as 14 bit (4 fractional)
        # u = fromFixed(u, 4)
        # v = fromFixed(v, 4)
        # TODO: implement fixed to float
        print("Not finished")
        gsState.UV['u'] = u
        gsState.UV['v'] = v
        pass
    elif descriptor == GIF_REG_DESCRIPTOR_XYZF2:
        # 16 bit fixed point x/y
        x = U.readLong(file) & 0xFFFF
        y = U.readLong(file) & 0xFFFF
        # 24 bits unsigned int
        z = (U.readLong(file) >> 4) & 0xFFFFFF
        fogAndAdc = U.readLong(file)
        # 8 bits unsigned int
        f = fogAndAdc & 0xFFF # TODO: check as this is wrong
        adc = fogAndAdc & 0x1 # TODO: check as this is wrong
        if adc == 0:
            gsState.XYZF2['x'] = x
            gsState.XYZF2['y'] = y
            gsState.XYZF2['z'] = z
            gsState.XYZF2['f'] = f
            # Drawing kick happens
            # TODO handle drawing kick?
        else:
            gsState.XYZF3['x'] = x
            gsState.XYZF3['y'] = y
            gsState.XYZF3['z'] = z
            gsState.XYZF3['f'] = f
            # No drawing kick happens
        print("Not finished")
        pass
    elif descriptor == GIF_REG_DESCRIPTOR_XYZ2:
        # 16 bit fixed point x/y
        x = U.readLong(file) & 0xFFFF
        y = U.readLong(file) & 0xFFFF
        # 24 bits unsigned int
        z = (U.readLong(file) >> 4) & 0xFFFFFFFF
        adc = U.readLong(file) & 0x1 # TODO: check as this is wrong
        if adc == 0:
            gsState.XYZ2['x'] = x
            gsState.XYZ2['y'] = y
            gsState.XYZ2['z'] = z
            # Drawing kick happens
            # TODO handle drawing kick?
        else:
            gsState.XYZ3['x'] = x
            gsState.XYZ3['y'] = y
            gsState.XYZ3['z'] = z
            # No drawing kick happens
        print("Not finished")
        pass
    elif descriptor == GIF_REG_DESCRIPTOR_TEX0_1:
        data = U.read64(file)
        U.read64(file)
        # TODO: parse TEX0_1 into fields
        print("Not finished")
        pass
    elif descriptor == GIF_REG_DESCRIPTOR_TEX0_2:
        data = U.read64(file)
        U.read64(file)
        # TODO: parse TEX0_2 into fields
        print("Not finished")
        pass
    elif descriptor == GIF_REG_DESCRIPTOR_CLAMP_1:
        data = U.read64(file)
        U.read64(file)
        # TODO: parse CLAMP_1 into fields
        print("Not finished")
        pass
    elif descriptor == GIF_REG_DESCRIPTOR_CLAMP_2:
        data = U.read64(file)
        U.read64(file)
        # TODO: parse CLAMP_2 into fields
        print("Not finished")
        pass
    elif descriptor == GIF_REG_DESCRIPTOR_FOG:
        U.readLong(file)
        U.readLong(file)
        U.readLong(file)
        fogIn = U.readLong(file)
        f = (fogIn >> 4) & 0xFF
        # TODO:
        gsState.FOG['f'] = f
        print("Not finished")
        pass
    elif descriptor == GIF_REG_DESCRIPTOR_Reserved:
        print("Not valid")
        pass
    elif descriptor == GIF_REG_DESCRIPTOR_XYZF3:
        print("Not finished")
        pass
    elif descriptor == GIF_REG_DESCRIPTOR_XYZ3:
        print("Not finished")
        pass
    elif descriptor == GIF_REG_DESCRIPTOR_AD:
        data = U.read64(file)
        addr = U.read64(file)
        print(f"Setting gsState [{addr:x}] to {data:x}")
        print(f"Setting gsState {gifDebugRegisterAddressName[addr & 0x7F]} to {data:x}")
        pos = file.tell()
        gsState.setAddr(addr & 0x7F, data)
        return
    elif descriptor == GIF_REG_DESCRIPTOR_NOP:
        print("Not finished")
        pass
    
    print("GifDecodeDescriptor hit unknown descriptor")
    return {}

def gifGetUnused(gifTag):
    unused = (gifTag >> 16) & 0x3FFFFFFF
    return unused

def gifGetUnused(gifTag):
    unused = (gifTag >> 16) & 0x3FFFFFFF
    return unused

def gifHandleRegList(file, gifTag, index, descriptor):
    pass

class GsState:
    # In Pipline data, yet to be rendered, being assembled, before any "KICK"
    # At a KICK move this data into rendered data (add on the end)
    pipelineData = { }
    # Rendered data, broken up after each "KICK", assembled
    renderedData = [
        # e.g will contain
        # { XYZs: [], UVs: [] }
    ]

    # Registers
    # 0x42 Alpha Blending Setting (CTX 1)
    ALPHA_1 = 0
    # 0x43 Alpha Blending Setting (CTX 2)
    ALPHA_2 = 0
    # 0x50 Buffer transfer settings
    BITBLTBUF = {}
    # 0x08 Texture Wrap Mode (CTX 1)
    CLAMP_1 = {}
    # 0x09 Texture Wrap Mode (CTX 2)
    CLAMP_2 = {}
    # 0x46 Color Clamp Control
    COLCLAMP = 0
    # 0x44 Dither Matrix Setting
    DIMX = 0
    # 0x45 Dither Control
    DTHE = 0
    # 0x4A Alpha Correction Value (CTX 1)
    FBA_1 = 0
    # 0x4B Alpha Correction Value (CTX 2)
    FBA_2 = 0
    # 0x61 Seems any data can be in here "FINISH Event Occurrence Request"
    FINISH = 0
    # 0x0A Vertex Fog Value 0 = lots of fog 255 = little fog
    FOG = {}
    # 0x3D Colour of distant fog 8bit r/g/b
    FOGCOL = (0,0,0)
    # 0x4C framebuffer settings (CTX 1)
    FRAME_1 = 0 
    # 0x4D framebuffer settings (CTX 2)
    FRAME_2 = 0
    # 0x54
    HWREG = 0  # Probably not ever used for this
    # 0x62
    LABEL = 0
    # 0x34 MipMap settings (CTX 1)
    MIPTBP1_1 = 0
    # 0x35 MipMap settings (CTX 2)
    MIPTBP1_2 = 0
    # 0x36 MipMap settings (CTX 1)
    MIPTBP2_1 = 0
    # 0x37 MipMap settings (CTX 2)
    MIPTBP2_2 = 0
    # 0x49 Alpha blending for pixels
    PABE = 0
    # 0x00 Drawing settings e.g sets triangle/shading/texture/fog stuff
    PRIM = {}
    # 0x1a  Selects between PRIM ^ and PRMODE v for some settings
    PRMODECONT = 0
    # 0x1b Mode changes drawing primitive settings?
    PRMODE = 0
    # 0x01 Vertex Colour settings
    RGBAQ = {}
    # 0x22 raster masking for all rows or every even or odd
    SCANMSK = 0
    # 0x40 (CTX 1)
    SCISSOR_1 = 0
    # 0x41 (CTX 2)
    SCISSOR_2 = 0
    # 0x60 related to SIGLBLID 
    SIGNAL = 0
    # 0x02 texture coord settings
    ST = {}
    # 0x47 (CTX 1)
    TEST_1 = 0
    # 0x48 (CTX 2)
    TEST_2 = 0
    # 0x06 Texture info, CTX1
    TEX0_1 = {}
    # 0x07 Texture info, CTX2
    TEX0_2 = {}
    # 0x14 Texture info, CTX1
    TEX1_1 = {}
    # 0x15 Texture info, CTX2
    TEX1_2 = {}
    # 0x16 Texture info, CTX1
    TEX2_1 = {}
    # 0x17 Texture info, CTX2
    TEX2_2 = {}
    # 0x3B Texture alpha conf
    TEXA = 0
    # 0x1C Texture CLUT (aka palette) location
    TEXCLUT = 0
    # 0x3F
    TEXFLUSH = 0
    # 0x51 buffer transfer related pos and scan direction
    TRXPOS = 0
    # 0x52 buffer transfer related size
    TRXREG = {}
    # 0x53 buffer transfer related direction
    TRXDIR = {}
    # 0x03 UV texture coord of vertex
    UV = {}
    # 0x18 coord offsetting (CTX 1)
    XYOFFSET_1 = 0
    # 0x19 coord offsetting (CTX 2)
    XYOFFSET_2 = 0
    # 0x04 coord values with fog
    XYZF2 = {}
    # 0x05 coord values 
    XYZ2 = {}
    # 0x0C coord values with fog # no draw kick
    XYZF3 = {}
    # 0x0D coord values # no draw kick
    XYZ3 = {}
    # 0x4E (CTX 1)
    ZBUF_1 = 0
    # 0x4F (CTX 2)
    ZBUF_2 = 0
    # There are others, but they are restricted, so assuming they have to be set
    # via EE or microprogram not via GIF

    def __init__(self):
        # Initialise all variables
        self.pipelineData = { }
        self.renderedData = []
        self.ALPHA_1 = 0
        self.ALPHA_2 = 0
        self.BITBLTBUF = parseBitbltbuf(0)
        self.CLAMP_1 = parseClamp_X(0)
        self.CLAMP_2 = parseClamp_X(0)
        self.COLCLAMP = 0
        self.DIMX = 0
        self.DTHE = 0
        self.FBA_1 = 0
        self.FBA_2 = 0
        self.FINISH = 0
        self.FOG = {}
        self.FOGCOL = parseFogCol(0)
        self.FRAME_1 = 0 
        self.FRAME_2 = 0
        self.HWREG = 0 # Probably not ever used for this
        self.LABEL = 0
        self.MIPTBP1_1 = 0
        self.MIPTBP1_2 = 0
        self.LABEL = 0
        self.MIPTBP2_1 = 0
        self.MIPTBP2_2 = 0
        self.PABE = 0
        self.PRIM = parsePRIM(0x100)  # Sets context to 1
        self.PRMODECONT = 0
        self.PRMODE = 0
        self.RGBAQ = { "R": 0, "G": 0, "B": 0, "A": 0, "q": 0 }
        self.SCANMSK = 0
        self.SCISSOR_1 = 0
        self.SCISSOR_2 = 0
        self.SIGNAL = 0
        self.ST = { "S": 0, "T": 0, "q": 0 }
        self.TEST_1 = 0
        self.TEST_2 = 0
        self.TEX0_1 = parseTex0_X(0)
        self.TEX0_2 = parseTex0_X(0)
        self.TEX1_1 = parseTex1_X(0)
        self.TEX1_2 = parseTex1_X(0)
        self.TEXA = 0
        self.TEXCLUT = 0
        self.TEXFLUSH = 0
        self.TRXPOS = 0
        self.TRXREG = parseTrxReg(0)
        self.TRXDIR = parseTrxDir(0)
        self.UV = {}
        self.XYOFFSET_1 = 0
        self.XYOFFSET_2 = 0
        self.XYZF2 = { }
        self.XYZ2 = { }
        self.XYZF3 = { }
        self.XYZ3 = { }
        self.ZBUF_1 = 0
        self.ZBUF_2 = 0

    def setAddr(self, addr, data):
        if addr == 0x00: 
            self.PRIM = parsePRIM(data)
        elif addr == 0x01: 
            self.RGBAQ = data
        elif addr == 0x02: 
            self.ST = data
        elif addr == 0x03: 
            self.UV = data
        elif addr == 0x04: 
            self.XYZF2 = data
        elif addr == 0x05: 
            self.XYZ2 = data
        elif addr == 0x06: 
            self.TEX0_1 = parseTex0_X(data)
        elif addr == 0x07: 
            self.TEX0_2 = parseTex0_X(data)
        elif addr == 0x08: 
            self.CLAMP_1 = parseClamp_X(data)
            if self.CLAMP_1["WMS"] > 1:
                print("CLAMP_1 horiz clamping unhandled")
                exit()
            if self.CLAMP_2["WMT"] > 1:
                print("CLAMP_1 vert clamping unhandled")
                exit()
        elif addr == 0x09: 
            self.CLAMP_2 = parseClamp_X(data)
            if self.CLAMP_2["WMS"] > 1:
                print("CLAMP_2 horiz clamping unhandled")
                exit()
            if self.CLAMP_2["WMT"] > 1:
                print("CLAMP_2 vert clamping unhandled")
                exit()
        elif addr == 0x0A:
            print("FOG set")
            exit() 
            self.FOG = data
        elif addr == 0x0C: 
            self.XYZF3 = data
        elif addr == 0x0D: 
            self.XYZ3 = data
        elif addr == 0x14: 
            self.TEX1_1 = parseTex1_X(data)
            print(self.TEX1_1)
        elif addr == 0x15: 
            self.TEX1_2 = parseTex1_X(data)
            print(self.TEX1_2)
        elif addr == 0x16: 
            self.TEX0_1 = parseTex0_X(data, self)
            print(self.TEX0_1)
        elif addr == 0x17: 
            self.TEX2_1 = parseTex2_X(data, self)
            print(self.TEX2_1)
        elif addr == 0x18: 
            print("XOFFSET_1 set")
            exit()
            self.XYOFFSET_1 = data
        elif addr == 0x19: 
            print("XOFFSET_2 set")
            exit()
            self.XYOFFSET_2 = data
        elif addr == 0x1A: 
            print("PRMODECONT set")
            exit()
            self.PRMODECONT = data
        elif addr == 0x1B: 
            print("PRMODE_1 set")
            exit()
            self.PRMODE = data
        elif addr == 0x1C: 
            print("TEXCLUT set")
            exit()
            self.TEXCLUT = data
        elif addr == 0x22: 
            print("SCANMSK set")
            exit()
            self.SCANMSK = data
        elif addr == 0x34:
            self.MIPTBP1_1 = parseMiptBp1_X(data)
            if self.MIPTBP1_1["TBP2"] != 0:
                print("Found mipmap value")
                print(self.MIPTBP1_1)
                # exit()
            print(self.MIPTBP1_1)
        elif addr == 0x35: 
            self.MIPTBP1_2 = parseMiptBp1_X(data)
            if self.MIPTBP1_2["TBP2"] != 0:
                print("Found mipmap value")
                print(self.MIPTBP1_2)
                # exit()
            print(self.MIPTBP1_2)
        elif addr == 0x36: 
            self.MIPTBP2_1 = parseMiptBp2_X(data)
            if self.MIPTBP2_1["TBP4"] != 0:
                print("Found mipmap value")
                print(self.MIPTBP2_1)
                # exit()
            print(self.MIPTBP2_1)
        elif addr == 0x37:
            self.MIPTBP2_2 = parseMiptBp2_X(data)
            if self.MIPTBP2_2["TBP4"] != 0:
                print("Found mipmap value")
                print(self.MIPTBP2_2)
                # exit()
            print(self.TEX2_2)
        elif addr == 0x3B: 
            print("TEXA set")
            exit()
            self.TEXA = data
        elif addr == 0x3D:
            self.FOGCOL = parseFogCol(data)
        elif addr == 0x3F: 
            self.TEXFLUSH = parseTexFlush(data)
        elif addr == 0x40: 
            print("SCISSOR_1 set")
            exit()
            self.SCISSOR_1 = data
        elif addr == 0x41:
            print("SCISSOR_2 set")
            exit() 
            self.SCISSOR_2 = data
        elif addr == 0x42: 
            print("ALPHA_1 set")
            exit()
            self.ALPHA_1 = data
        elif addr == 0x43:
            print("ALPHA_2 set")
            exit() 
            self.ALPHA_2 = data
        elif addr == 0x44:
            print("DIMX set")
            exit() 
            self.DIMX = data
        elif addr == 0x45: 
            print("DTHE set")
            exit()
            self.DTHE = data
        elif addr == 0x46: 
            print("COLCLAMP set")
            exit()
            self.COLCLAMP = data
        elif addr == 0x47: 
            print("TEST_1 set")
            exit()
            self.TEST_1 = data
        elif addr == 0x48: 
            print("TEST_2 set")
            exit()
            self.TEST_2 = data
        elif addr == 0x49: 
            print("PABE set")
            exit()
            self.PABE = data
        elif addr == 0x4A: 
            print("FBA_1 set")
            exit()
            self.FBA_1 = data
        elif addr == 0x4B: 
            print("FBA_2 set")
            exit()
            self.FBA_2 = data
        elif addr == 0x4C: 
            print("FRAME_1 set")
            exit()
            self.FRAME_1 = data
        elif addr == 0x4D: 
            print("FRAME_2 set")
            exit()
            self.FRAME_2 = data
        elif addr == 0x4E:
            print("ZBUF_1 set")
            exit() 
            self.ZBUF_1 = data
        elif addr == 0x4F: 
            print("ZBUF_2 set")
            exit()
            self.ZBUF_2 = data
        elif addr == 0x50: 
            self.BITBLTBUF = parseBitbltbuf(data)
            print(f"bitbltbuf src addr {self.BITBLTBUF['SBP']}")
            print(f"bitbltbuf dst addr {self.BITBLTBUF['DBP']}")
            print(f"bitbltbuf spsm {self.BITBLTBUF['SPSM']}")
            print(f"bitbltbuf dpsm {self.BITBLTBUF['DPSM']}")
        elif addr == 0x51: 
            self.TRXPOS = parseTrxPos(data)
            print(self.TRXPOS)
        elif addr == 0x52: 
            self.TRXREG = parseTrxReg(data)
            print(self.TRXREG)
        elif addr == 0x53: 
            self.TRXDIR = parseTrxDir(data)
            print(self.TRXDIR)
        elif addr == 0x54: 
            print("HWREG set")
            exit()
            self.HWREG = data
        elif addr == 0x60: 
            print("SIGNAL set")
            exit()
            self.SIGNAL = data
        elif addr == 0x61: 
            print("FINISH set")
            exit()
            self.FINISH = data
        elif addr == 0x62: 
            print("LABEL set")
            exit()
            self.LABEL = data
        else:
            print("GSSetAddr: Invalid address")
            exit()

def parsePRIM(prim):
    primType = prim & 0b11
    shadeMethod = (prim >> 2) & 0b1             # IIP
    textureMapped = (prim >> 3) & 0b1           # TME
    fogEnabled = (prim >> 4) & 0b1              # FGE
    alphaBlendung = (prim >> 5) & 0b1           # ABE 
    antialisasing = (prim >> 6) & 0b1           # AA1
    textureCoordMethod = (prim >> 7) & 0b1      # FST
    context = (prim >> 8) & 0b1                 # CTXT
    fragmentValueControl = (prim >> 9) & 0b1    # FIX
    return {
        "PRIM": primType,
        "IIP": shadeMethod,
        "TME": textureMapped,
        "FGE": fogEnabled,
        "ABE ": alphaBlendung,
        "AA1": antialisasing,
        "FST": textureCoordMethod,
        "CTXT": context,
        "FIX": fragmentValueControl,
    }
    

# Decodes the TEX0_1/TEX0_2 register into its components
def parseTex0_X(value):
    textureBasePointer0 = value & 0x3FFF
    textureBufferWidth = (value >> 14) & 0x3F
    pixelStorageMethod = gifDebugPSM[(value >> 20) & 0x3F]
    textureWidth = (value >> 26) & 0xF
    textureHeight = (value >> 30) & 0xF
    textureColorComponent = (value >> 34) & 1
    if textureColorComponent == 1:
        textureColorComponent = "RGBA"
    else:
        textureColorComponent = "RGB"
    textureFunction = (value >> 35) & 0x3
    clutBufferBasePointer = (value >> 37) & 0x3FFF
    clutPixelStorageMethod = (value >> 51) & 0xF
    clutStorageMode = (value >> 55) & 1
    if clutStorageMode == 1:
        clutStorageMode = "CSM1"
    else:
        clutStorageMode = "CSM2"
    # Entry offset if CSM2 this must be set
    clutStartAddress = (value >> 56) & 0x1F
    clutLoadControl = (value >> 61) & 0x7
    return { 
        "TBP0": textureBasePointer0,
        "TBW": textureBufferWidth,
        "PSM": pixelStorageMethod,
        "TW": pow(2, textureWidth),
        "TH": pow(2, textureHeight),
        "TCC": textureColorComponent,
        "TFX": textureFunction,
        "CBP": clutBufferBasePointer,
        "CPSM": clutPixelStorageMethod,
        "CSM": clutStorageMode,
        "CSA": clutStartAddress,
        "CLD": clutLoadControl,
    }

def parseTex1_X(value):
    lodCalcMethod = value & 0x1
    maxMipLevel = (value >> 4) & 0x7
    mmag = (value >> 5) & 0x1
    mmin = (value >> 6) & 0x7
    mipmapTextureBaseAddrMethod = (value >> 9) & 0x1
    lodLparam = (value >> 19) & 0x3
    lodKparam = (value >> 32) & 0xFFF
    return {
        "LCM": lodCalcMethod,
        "MXL": maxMipLevel,
        "MMAG": mmag,
        "MMIN": mmin,
        "MTBA": mipmapTextureBaseAddrMethod,
        "L": lodLparam,
        "K": lodKparam,
    }

def parseTex2_X(value, gs):
    # This register, is a register, that updates another register
    # but only some values, TEX0_x = TEX2_X | other bits
    print(f"Overriding texture values, TEX2_X being set")
    pixelStorageMethod = gifDebugPSM[(value >> 20) & 0x3F]
    clutBufferBasePointer = (value >> 37) & 0x3FFF
    clutPixelStorageMethod = (value >> 51) & 0xF
    clutStorageMode = (value >> 55) & 1
    if clutStorageMode == 1:
        clutStorageMode = "CSM1"
    else:
        clutStorageMode = "CSM2"
    # Entry offset if CSM2 this must be set
    clutStartAddress = (value >> 56) & 0x1F
    clutLoadControl = (value >> 61) & 0x7
    return { 
        "TBP0": gs.TEX0_1["TBP0"],
        "TBW": gs.TEX0_1["TBW"],
        "PSM": pixelStorageMethod,
        "TW": gs.TEX0_1["TW"],
        "TH": gs.TEX0_1["TH"],
        "TCC": gs.TEX0_1["TCC"],
        "TFX": gs.TEX0_1["TFX"],
        "CBP": clutBufferBasePointer,
        "CPSM": clutPixelStorageMethod,
        "CSM": clutStorageMode,
        "CSA": clutStartAddress,
        "CLD": clutLoadControl,
    }

def parseBitbltbuf(value):
    print("BITBLTBUF change")
    srcBufferBasePtr = value & 0x3FFF
    srcBufferWidth = (value >> 16) & 0x3F
    if (value >> 24) & 0x3F not in gifDebugPSM:
        print(f"failed to get SrcPSM from BITBLTBUF, unknown value {(value >> 24) & 0x3F}")
        srcPSM = gifDebugPSM[0]
    else:
        srcPSM = gifDebugPSM[(value >> 24) & 0x3F]

    dstBufferBasePtr = (value >> 32)  & 0x3FFF
    dstBufferWidth = (value >> 48) & 0x3F
    dstPSM = gifDebugPSM[(value >> 56) & 0x3F] # Should be same?

    return {
        "SBP": srcBufferBasePtr,
        "SBW": srcBufferWidth,
        "SPSM": srcPSM,
        "DBP": dstBufferBasePtr,
        "DBW": dstBufferWidth,
        "DPSM": dstPSM,
    }

def parseTrxPos(value):
    # docs specify upper left
    srcXCoord = value & 0x7FF
    srcYCoord = (value >> 16) & 0x7FF
    dstXCoord = (value >> 32) & 0x7FF
    dstYCoord = (value >> 48) & 0x7FF
    transmissionOrder = (value >> 59) & 0x3
    return {
        "SSAX": srcXCoord,
        "SSAY": srcYCoord,
        "DSAX": dstXCoord,
        "DSAY": dstYCoord,
        "DIR": transmissionOrder,
    }

def parseTrxReg(value):
    rectRegionWidth = value & 0xFFF
    rectRegionHeight = (value >> 32) & 0xFFF
    return {
        "RRW": rectRegionWidth,
        "RRH": rectRegionHeight
    }

def parseTrxDir(value):
    xDir = value & 0x3
    return {
        "XDIR": xDir
    }

# Has no data
def parseTexFlush(value):
    return 0

def parseClamp_X(value):
    wrapModeHorizontal = value & 0x3
    wrapModeVertical = (value >> 2) & 0x3
    # Used in region clamp mode:
    minU = (value >> 4) & 0x3FF
    maxU = (value >> 14) & 0x3FF
    maxV = (value >> 24) & 0x3FF
    minV = (value >> 34) & 0x3FF
    # if in Region repeat mode above are masks
    # MaskU FixU MaskV FixU
    return {
        "WMS": wrapModeHorizontal,
        "WMT": wrapModeVertical,
        "MINU": minU,
        "MAXU": maxU,
        "MINV": maxV,
        "MAXV": minV,
    }

def parseMiptBp1_X(value):
    # BP = base pointer for levelX (in 64s)
    # BW = buffer width for levelX (in 64s)
    TBP1 = value & 0x3FFF
    TBW1 = (value >> 14) & 0x3F
    TBP2 = (value >> 20) & 0x3FFF
    TBW2 = (value >> 34) & 0x3F
    TBP3 = (value >> 40) & 0x3FFF
    TBW3 = (value >> 54) & 0x3F
    return {
        "TBP1": TBP1,
        "TBW1": TBW1,
        "TBP2": TBP2,
        "TBW2": TBW2,
        "TBP3": TBP3,
        "TBW3": TBW3,
    }

def parseMiptBp2_X(value):
    # BP = base pointer for levelX (in 64s)
    # BW = buffer width for levelX (in 64s)
    TBP4 = value & 0x3FFF
    TBW4 = (value >> 14) & 0x3F
    TBP5 = (value >> 20) & 0x3FFF
    TBW5 = (value >> 34) & 0x3F
    TBP6 = (value >> 40) & 0x3FFF
    TBW6 = (value >> 54) & 0x3F
    return {
        "TBP4": TBP4,
        "TBW4": TBW4,
        "TBP5": TBP5,
        "TBW5": TBW5,
        "TBP6": TBP6,
        "TBW6": TBW6,
    }

def parseFogCol(value):
    # FCR, FCB, FCG
    # Distant fog color
    fog_r = value & 0xFF
    fog_g = (value >> 8) & 0xFF
    fog_b = (value >> 16) & 0xFF
    return fog_r, fog_g, fog_b