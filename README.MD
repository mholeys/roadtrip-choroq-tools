# Choro Q PS2 extraction/modding tools

Collection of tools for working with Choro Q games, for the Playstation 2. Most of the code on here is focused on understanding and extracting the format of the car bodies, and maps. The most understood game is HG2 and this has the most support and functionality. 

Currently supported games, in varying capacity:
- Choro-Q HG2 (Road Trip Adventure (Eu), Everywhere Road Trip (NA), 쵸로QHG2 (Korea), チョロQHG2 (Japan)) (e-Game)
- Choro-Q HG3 (Gadget Races (Eu), チョロQHG3 (Japan)) (e-Game)
- Choro-Q HG1 (Penny Racers (Eu), Gadget Racers (NA), チョロQHG (Japan)) (Barnhouse Effect)
- Choro-Q HG4 (ChoroQ (Eu), ChoroQ (NA)) (Barnhouse Effect)
- Choro-Q Works (チョロQワークス (Japan)) (Atlus)
- Shin-Combat Choro-Q (Seek and Destroy (Eu/NA), 新コンバットチョロQ (Japan), 신 컴뱃쵸로Q (Korea))

## Sections
### 1. Road Trip Adventure / ChoroQ HG 2 / チョロQ HG 2 extraction tools
### 2. BHE (Barnhouse Effect) extraction tools (Penny racers/HG4/Works/Shin combat)
### 3. HG2/HG3 modding tools
### 4. Demo/examples of what can be done

## 1. Road Trip Adventure / ChoroQ HG 2 / チョロQ HG 2 extraction tools

If you are after a program to extract the models for either of these games, look at the [Releases](https://github.com/mholeys/roadtrip-choroq-tools/releases) page and download the latest extractor, "choroq-hg2-3-extractor-{version}.zip"

This is a set of tools used to extract the data from the PS2 game Road Trip Adventure (UK/EU) / Everywhere Road Trip (US/NA) / ChoroQ HG 2 (JP) チョロQ HG 2 / 쵸로QHG2 (Korea) - written in python.

As the next game, developed by e-Game, also uses a similar system HG3 has been mostly supported too. You may find a difference in the understanding, where HG2 has more available to be extracted than HG3 but both should be in a usable format. 

This has been tested mostly with the EU/UK version of the game, as this is the one I have. It should also work with the US/American version, and the JP/Japanese & KR/Korean version, as the main difference is the dialogue within the game executable.

### Detail

Originally I only wanted to create a tool to extract the car models, and textures, but the other files for the game are very similar and some data can be extracted from them as well. 
Building on my understanding of the car file format I have expanded this to work with the other files, most of the data on the disc is loaded directly to GS/VU1 via DMA transfers.

In fact most of the BIN files are pre-prepared commands and tags to send directly to the rendering pipeline, the game does very little CPU side processing for most of the rendered objects. 
This makes it possible to just load the data from the disk and send it to be rendered, with little to no overhead from the CPU.
Most of the data is processed by the VU1, in some capacity with different subroutines for the different parts of the game.
For further detail see the [docs](https://github.com/mholeys/roadtrip-choroq-tools/docs)

### Usage
See [Releases](https://github.com/mholeys/roadtrip-choroq-tools/releases) section for the GUI, this is the easiest way for most people to use the tool, the GUI is new and should have most features.
If you want to have the latest version, or make changes, or have any other options then you would be better off cloning, and running the tool you require (see [e-Game docs]()).

### Features
Currently, it is possible to get all field (FLD/xxx.BIN), course (COURSE/Cxx.BIN), action (ACTION/Axx.BIN), and car models (CAR{0,1,2,3,4,S}/Qxx.BIN).
The field/course file format are not fully understood, but the model, and nearly all textures can be extracted. 
It is possible to get the mini-map model, and some level extras such as doors/barrels.
The collision mesh is also extractable, but currently the collider properties are not exported, due to not having a nice format to hold it.
Textures should map to the correct mesh, which is defined via GIF tags in the .BIN files.

Working (HG 2):
- Car models/textures
- Main world (FLD/field), with textures and optional vertex colours
- Race Courses (COURSE), with textures and optional vertex colours
- Mini-games (ACTION), with textures and optional vertex colours
- Some system files
  - Quick Pic (small and big images)
  - Building/shop interior rendering textures
  - In game item icons

Working (HG 3):
- Car models/textures
- Race Courses (COURSE), with textures

### Extracting car models (HG2 or HG3)

Requires Python 3.7+
Requires Pillow (PIL) and colorama python libs

See the car_extractor.py file:
``` python car_extractor.py <input folder> <output folder> [type]```

e.g to make PLY files from the `CAR0` folder

``` python car_extractor.py CAR0 ~/cars 2```

e.g to make both OBJ and PLY files from the `CAR0` folder

``` python car_extractor.py CAR0 ~/cars```

e.g to make OBJ files from the Q00.BIN car (single car mode)

``` python car_extractor.py Q00.BIN ~/cars 1```

If you would like the vertex colours, PLY is the better choice, but you can also now use 'C' as the format option, which now adds colours to the OBJ format, however this is not universally supported. 

### Extracting Fields/Courses (HG2 or HG3):
See the choroq_extractor.py file for additional details:
Basic usage (help can be printed with no arguments)
``` python choroq_extractor.py <input folder> <output folder> [type]```

``` python choroq_extractor.py E:/ ~/road-trip/ ```

e.g to make OBJ files from road trip disc.
This will attempt to group all meshes within a field/course/action by their used texture, this reduces the number of files produced and saves on draw calls. This does however break the chunk based system the game uses, but this should be fine for most purposes.

``` python choroq_extractor.py E:/ C:/road-trip/ 1```

e.g to make OBJ (with coloured vertices, day time lighting only) files from road trip disc.

``` python choroq_extractor.py E:/ C:/road-trip/ C```

e.g to make PLY files from road trip disc, this mode has been neglected in the last few changes, so you may be better using the OBJ format

**PLY format for course/field/action is currently not working, this may not get fixed**

``` python choroq_extractor.py E:/ C:/road-trip/ 2```

## 2. BHE (Barnhouse Effect) extraction tools (Penny racers/HG4/Works/Shin combat)

This was started as a side project, again to mainly understand and extract the car models.
The game uses CPK files, a custom format container for this series of games, which contains various subfiles.
It is similar to a ZIP file which can hold many different types of file within one. 
Support for the different subfiles is being expanded as more is understood.

### Features

Partially/Supported subfile formats:
- PBL (small object mesh data) usually cars or moving objects
- APT textures
- MPD usually textured model, used for maps
- HPD I think is Hit Poly Mesh, aka collision mesh for maps
- MPC mesh data
- TOC I think is a scripting system, also contains dialogue
  - This only fractionally understood
- FONT DATA

Partial support (Choro Q Works):
- Cars (BODY.CPK)
- Maps/courses (3DMAP.CPK)
- Dialogue (STAGE.CPK TITLE.CPK)
- SYSETC.BIN various reused extras
- 3DETC.BIN various reused extras
- (lacks compressed data support for now, some textures missing)

Partial support (HG 4):
- Cars (BODY.CPK) + textures
- Maps/courses (3DMAP.CPK)
- ITEMPIC.CPK
- PARTS.CPK
- SIGN.CPK
- Dialogue (STAGE.CPK TITLE.CPK)

Partial support (HG 1/Penny racers):
- Cars (3DCAR.CPK)
- Maps/courses (3DMAP.CPK)
- SYSETC.BIN
- 3DETC.BIN

Partial support (ShinCombat):
- Tanks (TANK.CPK)
- Maps/courses (3DMAP.CPK)


### Extracting BHE Game data:

I recommend making a new output folder per CPK, as this prevents overwriting.
Currently, only obj format is supported (1), but the usage is as follows:

``` python bhe_extractor.py <path to cpk file> <path to save to> 1```

BODY.CPK/TANK.CPK will produce folders named pbl, each folder will have a car/part, to use this you will have to look at the .mtl file produced, which will tell you the required texture names (e.g cart_0.png), all textures are in the all_textures folder, but will need copying and renaming for automatic use. This is done as there are multiple textures per model, and it would mean making lots of duplicate files.

The 3DMAP.CPK should produce preassigned textured models, for nearly all models, this is not always right, but this is a new feature. 

## 3. HG2/HG3 modding tools
This is a very new addition, but I intend to expand this as much as I can. 
I have started work on replacing models in both HG2 and HG3, this has been a manual process, but automation has started.

It is currently possible to design a 3D model of a car or any object in the game (not fields or courses) and place it into the game.

There are some limitations to this, including the main one size; the game loads data from the disk using sector addressing.
This means that we cannot just put any size file on to the disk, but it is possible to make models with a good level of detail.
The process of modding the game is roughly as follows:
- Model a car or object you wish to place into the game
- Run the blender script found in blender/
- follow the instructions (see docs/, and instructions in blender)
- set up the model to have the required information
- export the model as a partial BIN
- copy/write the partial BIN into your car of choice Q00 for example (checking it fits)
- (texture replacement via PCSX2 for now)

[Modding Guide](docs/hg2-modding-guide)

## 4. Demo/examples of what can be done

Old 3D rendered world map (has some extraction faults from early code) created in Unity
![Mostly textured world of the RoadTrip Adventure game in 3D](results/Whole-World-01-2024.jpg)
![Sandpolis from RoadTrip Adventure game](results/Results-04-2024-Sandpolis.PNG)


#### Information sources:

- Most original mesh information was found on [Xenhax](https://forum.xentax.com/viewtopic.php?t=17567) (website closed)
- More information about the textures from [Zenhax](https://zenhax.com/viewtopic.php?t=7405) (website closed)
  - https://web.archive.org/web/20220309142950/https://zenhax.com/viewtopic.php?t=7405
- Some code is based on the BMS/3DS Max script in the forum above (note: forum has been closed)
  - But a lot of the code has now been rewritten after I understood that the game uses raw Playstation 2 commands/tags
- Other information was gathered from analysis of PlayStation/2 memory/data formats found in the manuals ([homebrew ps2sdk](https://github.com/ps2dev/ps2sdk), [ps2tek](https://psi-rockin.github.io/ps2tek/)), useful for how the TIM file and palette data is stored, although this game does not use TIM files or other storage files
- Not yet used but could be useful https://btest4he.com/cheat_code/index.html
- [Choro Q Universe Wiki](https://choroq.fandom.com/wiki/Choro_Q_Wiki)
- [Choro Q on TCRF](https://tcrf.net/Everywhere_Road_Trip)
- [Choro Q Wiki (JP)](https://w.atwiki.jp/choroq_game/pages/474.html)

#### Thanks:
- killercracker (3DS max script)
- Acewell (BMS script)
- e-Game (JP) for making a very interesting game that I and many others have spent many hours playing
- The Choro Q Universe Discord server for the support, ideas, and encouragement to start working on things I would have skipped

#### Other notes:
- I do not claim ownership of any content of the PS2 games, I have created this with the plan of understanding how the game works and to learn about the Playstation 2 era. Anyone who uses this takes responsibility for how they use the produced output.
- If you end up using my tool to produce something cool, please link to this github page so people can explore the game, also LMK how you use it (feel free to open an issue just to tell me)
- If you have any issues with the tool, check the issues at the top, things should be improving as I understand more, but feel free to open an issue, and I will try my best to help