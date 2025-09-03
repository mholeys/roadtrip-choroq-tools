# Choro Q PS2 extraction tools
## 1. Road Trip Adventure / ChoroQ HG 2 / チョロQ HG 2 extraction tools
## 2. BHE (Barnhouse Effect) extraction tools (Penny racers/HG4/Works/Shin combat)

This is a set of tools used to extract the data from the PS2 game Road Trip Adventure (UK/EU) / Everywhere Road Trip (US) / ChoroQ HG 2 (JP) チョロQ HG 2 - written in python.
Currently, there is work going on to support BHE games as well.

There has also been work on HG 3, but this is very much WIP, this game is also known as Gadget Racers or ChoroQ HG 3, made by e-Game. 

This has been tested with only the EU/UK version of the game, as this is the one I have. I have not really tested this with other games in the ChoroQ series, but after a quick look the files seem very different between games. It should also work with the US/American version, and the JP/Japanese & KR/Korean version, as the text is the main difference.

### Road Trip Adventure / ChoroQ HG 2 / チョロQ HG 2 extraction tools

Originally I only wanted to create a tool to extract the car models, and textures, but the other files for the game are very similar and some data can be extracted from them as well. Building on my understanding of the car file format I have expanded this to work with the other files, most of the data on the disc is loaded directly to GS/VU1 via DMA transfers. 

#### Usage
See [Releases](https://github.com/mholeys/roadtrip-choroq-tools/releases) section for the GUI, this is the easiest way for most people to use the tool, the GUI is new and should have most features.
If you want to have the latest version, or make changes, or have any other options then you would be better off cloning, and running the tool you require.

#### Features
Currently, it is possible to get all field (FLD/xxx.BIN), course (COURSE/Cxx.BIN), action (ACTION/Axx.BIN), and car models (CAR{0,1,2,3,4,S}/Qxx.BIN).
The field/course file format are not fully understood, but the model, and most of the textures can be extracted (if a texture fails to be understood the rest of the textures usually fail). It is possible to get the mini-map model, and some level extras such as doors/barrels. 
Textures should map to the correct mesh, which is setup via GIF tags in the .BIN files.

Working (HG 2):
- Car models/textures
- Main world (FLD/field), with textures and optional vertex colours
- Race Courses (COURSE), with textures and optional vertex colours
- Mini-games (ACTION), with textures and optional vertex colours

Working (HG 3):
- Car models/textures
- Race Courses (COURSE), with textures

Documentation of the file formats below are still being worked on, and the best source of info is within the code.
(Code is messy as it evolves, sorry)
- For field/course/action files see the choroq/course.py
- For car files see the choroq/car.py file
- For textures see the choroq/texture.py file
- For Sys/Shop/Item see above + choroq-extractor.py

Working (Choro Q Works):
- Cars, some (BODY.CPK) + some textures

Working (HG 4):
- Cars (BODY.CPK) + textures
- Bits of the courses (3DMAP.CPK) + textures

Working (HG 1/Penny racers):
- Cars (BODY.CPK)
- Bits of the courses (3DMAP.CPK) + textures

Working (ShinCombat):
- Tanks (TANK.CPK)
- Bits of the maps (3DMAP.CPK) + textures


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

### Extracting BHE Game data:
Currently, only obj format is supported (1), but the usage is as follows, I recommend making a new output folder per CPK, as this prevents overwriting.

BODY.CPK/TANK.CPK will produce folders named pbl, each folder will have a car/part, to use this you will have to look at the .mtl file produced, which will tell you the required texture names (e.g cart_0.png), all textures are in the all_textures folder, but will need copying and renaming for automatic use.

The 3DMAP.CPK should produce preassigned textured models, for nearly all models, this is not always right, but this is a new feature. 

``` python bhe_extractor.py <path to cpk file> <path to save to> 1```



#### Demo
![Mostly textured world of the RoadTrip Adventure game in 3D](results/Whole-World-01-2024.jpg)
![Sandpolis from RoadTrip Adventure game](results/Results-04-2024-Sandpolis.PNG)


#### Information sources:

- Most key mesh information was found https://forum.xentax.com/viewtopic.php?t=17567 (website closed)
- More information about the textures were extracted from https://zenhax.com/viewtopic.php?t=7405 (website closed)
  - https://web.archive.org/web/20220309142950/https://zenhax.com/viewtopic.php?t=7405
- Some code is based on the BMS/3DS Max script in the forum above (note: forum has been closed)
- Other information was gathered from analysis or PlayStation/2 memory/data formats found in the manuals, useful for how the TIM file and palette data is stored, although this game does not use TIM files or other storage files
- Not yet used but could be useful https://btest4he.com/cheat_code/index.html

#### Thanks:
- killercracker (3DS max script)
- Acewell (BMS script)
- e-Game (JP) for making a very interesting game that I and many others have spent many hours playing

#### Other notes:
- I do not claim ownership of any content of the PS2 games, I have created this with the plan of understanding how the game works. Anyone who uses this takes responsibility for how they use the produced output.
- If you end up using my tool to produce something cool, please link to this github page so people can explore the game, also LMK how you use it
- If you have any issues with the tool, check the issues at the top, things should be improving as I understand more