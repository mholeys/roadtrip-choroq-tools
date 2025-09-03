# Road Trip Adventure / ChoroQ HG 2 / チョロQ HG 2 extraction tools

# Extra information/detail on how the data works

##### Course/Field/Action file format
The information here was previously different, this was before I had realised that most of the data uses **DMA/GIF** and **VIF tags/codes** to directly load data from the disc to be drawn with little overhead. After this discovery (perhaps this should have been more obvious earlier), I have realised that the other files on the disc like the SYS/ files also use these DMA/VIF/GIF tags to basically load all data as is, with only minimal checks done by the CPU.

The course/field/action files contain multiple sub-files:
- Textures
  - This is all the textures that the field/course use, and are just one after each other
  - **Not all texture formats are understood**, so some may turn out wrong, or will cause other textures to be skipped
  - Each texture is prefixed with DMA tags (16bytes) with the length of the transfer, along with GIF tags to setup transfer parameters (PACKED mode, destination/size/format) and transfer the image data (IMAGE mode)
- Chunks
  - This is the level data, which holds all the details on each of the meshes within each chunk of the course/field
  - At the start of data there is a list of offsets (4 bytes)
    - This list is, usually, 8x8 chunks with an extra offset, which holds meshes spread across the whole region, such as trees (referred to as "extra" chunk)
  - After the list of chunk offsets, there is a list of shorts (2 bytes) which holds the number of (I think) GIF tags in each chunk
    - After this 8x8 list of counts, there is another short, holding the size for the "extra" chunk
    - If anyone wants to replicate this decoding with another method, I would recommend grouping meshes by the addresses that they reference, without this there will be a huge number of meshes produced/rendered, which can significantly be reduced by merging across chunks. 
  - The extra chunk can hold:
    - The water mesh (top layer) for rivers
    - Windows for fields (which may switch between two, to light up at night/day)
    - And billboards, which use a slightly modified layout for the mesh structure, with x/y/z starting points before the usual format (this is done via another GIF tag)
  - The data within each chunk is built up of DMA tags, VIF tags (used to expand the data into xyz+w where w is not really used, and is often 0) and GIF tags
    - Some of the GIF tags configure which textures (via addresses) are used in the mesh
    - DMA tags are 8 bytes as the additional bytes are used for VIF tags
    - GIF tag difference:
      - The GIF tags are not used by the GS directly in the game, the data is transferred to the GS, but a VU1 program manipulates the data into the data as the GS would expect, due to this the data is in easy to decode floats (4 bytes)
      - The ones I have come across are a GIF tag with the following registers ST RGBAQ and XYZ(F)(2/3)
      - For fields the data is usually in the format of X/Y/Z, Daytime R/G/B colours, texture coordinates, and Night R/G/B colours
      - The structure of the data after the GIF tag depends mostly on the VIF tag with MSCALF EXECADDR, where EXECADDR selects a different part of the VU1 program to run, which changes how the data is rendered. I have not decoded this VU1 code
- Probably a collision mesh, as this is usually just the roads for courses/actions, but covers everything in the fields
  - The course files seem to only use this to hold a copy of the road
  - The field files seem to use this section for most of the level in lower detail
  - I believe after playing with the meshes more, that this is used as an allowed boundary.
    I would guess the cars check if they are on the mesh (probably 4 corners), to detect collisions into walls and other solid objects. 
  - There are properties set within this data, such as an underwater or water parameter, and friction, these values are not yet understood fully
  - The format of this is similar to the mesh/model data but the chunk size is halved (16x16 chunks for each region)
    - This also has the size/count table, but it is 16x16
    - There are no DMA or VIF tags, but instead there is a GIF or very similar tag
- Overlay map, or number of extra meshes such as doors/barrels
  - The end of the file contains a mini-map of the roads, (not all actions have a map)
  - There may also be other models after the 3rd offset, which are usually spawned for different reasons
    - Examples:
      - Peach that falls from the peach tree in Field 223 (Peach town)
      - Stage cover in Fuji city (hiding the princess)
      - Treasure chest parts in the maze action

For HG3 files, there are some differences, key differences are that the size of the chunk array is often 16x16 for meshes, and 32x32 for collider, and that other functions of the GS/VIF are used. The exec addresses are different as the VU1 code is different between the games.

##### Car model file format
The car file format is the most understood, and it is possible to get the car body model, texture, as well as its accessories.
Sub-File structure (HG2):
- 0 Car body
- 1 Lights (front/back) probably used for night driving lights
- 2 Rear Lights, probably used for brake lights
- 3 Car body (low poly/reduced detail)
- 4 Lights (front/back) probably used at night for cars far away with lower detail car
- 5 Rear Spoiler 1
- 6 Rear Spoiler 2
- 7 Rockets (optional), used to change where the rocket model connects to the car
- 8 Sticker area model, not all cars have stickers

The car file format uses a similar system to the Field/Course/Action meshes, it uses DMA/VIF/GIF tags, and has different EXECADDRes (so a different VU1 program executes)
