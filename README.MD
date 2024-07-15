# Road Trip Adventure / ChoroQ 2 HG extraction tools

This is a set of tools used to extract the data from the PS2 game Road Trip Adventure (UK/EU) / Everywhere Road Trip (US)/ChoroQ HG 2 (JP) チョロQ HG 2 - written in python. 

This has been tested with only the EU/UK version of the game, as this is the one I have. I have not really tested this with other games in the ChoroQ series, but after a quick look the files seem very different between games. It should also work with the US/American version, and the JP/Japanese & KR/Korean version, as the text is the main difference.

Originally only wanted to create a tool to extract the car models, and textures, but the other files for the game are very similar and some data can be extracted from them as well. Building on my understanding of the car file format I have expanded this to work with the other files. 

#### Features
Currently it is possible to get all field (FLD/xxx.BIN), course (COURSE/Cxx.BIN), action (ACTION/Axx.BIN), and car models (CAR{0,1,2,3,4,S}/Qxx.BIN).
The field/course file format are not fully understood, but the model, and most of the textures can be extracted (if a texture fails to be understood the rest of the textures usually fail). It is possible to get the mini-map model, and some level extras such as doors/barrels. I have not worked out how textures map to meshes, and so the field/course model will be untextured, the cars have 1 texture. 

Documentation of the file formats below are still being worked on, and the best source of info is within the code.
- For field/course/action files see the choroq/course.py
- For car files see the choroq/car.py file
- For textures see the choroq/texture.py file

##### Course/Field file format
The course/field/action files contain multiple sub-files:
- Textures
  - This is all the textures that the field/course use, and are just one after each other
  - Not all texture formats are understood, so some may turn out wrong, or will cause other textures to be skipped
- Models
  - This is the level data, which holds all the details on the model shape
  - I think the extra vertex data contains information about lighting
  - The models offsets are listed at the start of this sub-file
  - After the last chunk, there is another group of models
    - This holds the water mesh (top layer) for rivers
    - This holds windows for fields (to light up at night)
    - And billboards, which use a slightly modified layout for the mesh structure, with x/y/z starting points before the usual format
- Possibly a collision mesh, as is usually just the roads
  - I am unsure on the use of these files, I would suspect it has something to do with physics or collisions, I suspect this allows the game to treat different surfaces with different grip
  - The course files seem to only use this to hold a copy of the road
  - The field files seem to use this section for most of the level in lower detail
  - I believe after playing with the meshes more, that this is used as an allowed boundry. 
    I would guess the cars check if they are on the mesh (probably 4 corners), to detect collisions into walls and other solid objects. 
- Overlay map, or number of extra meshes such as doors/barrels
  - The end of the file contains a mini-map of the roads, along with some extra objects in the level

##### Car model file format
The car file format is the most understood, and it is possible to get the car body model, texture, as well as its accessories.
Sub-File structure:
- 0 Car body
- 1 Lights (front/back) probably used for night driving lights
- 2 Rear Lights, probably used for brake lights
- 3 Car body (low poly/reduced detail)
- 4 Lights (front/back) probably used at night for cars far away with lower detail car
- 5 Rear Spoiler 1
- 6 Rear Spoiler 2
- 7 Rockets (optional), used to change where the rocket model connects to the car
- 8 Sticker area model, not all cars have stickers

### Extracting car models
See the car-extractor.py file:
``` python car-extractor.py <input folder> <output folder> [makedirs] [type]```

e.g to make PLY files from the `CAR0` folder, with subfolders for each car

``` python car-extractor.py CAR0 ~/cars 1 2```

e.g to make both OBJ and PLY files from the `CAR0` folder, directly in the ~/cars folder

``` python car-extractor.py CAR0 ~/cars```

e.g to make OBJ files from the Q00.BIN car

``` python car-extractor.py Q00.BIN ~/cars 1 1```

### Extracting Fields/Courses:
While the code will get all the model information, it creates an odd bit of model that connects to the 0, 0, 0 point. I think this is due to the last part of the model being different, but I have not attempted to parse this section differently. If you are using the model, I would suggest removing this last mesh.
See the choroq-extractor.py file:
Basic usage
``` python choroq-extractor.py <input folder> <output folder> [type]```

``` python choroq-extractor.py E:/ ~/road-trip/ ```

e.g to make OBJ files from road trip disc

``` python choroq-extractor.py E:/ C:/road-trip/ 1```

e.g to make PLY files from road trip disc

``` python choroq-extractor.py E:/ C:/road-trip/ 2```

**Experimental grouped option**:
This should link all meshes by their texture, (not prooven) making texturing quicker, this will produce less files and might run quicker. The format might not work in all obj compatible programs.

``` python choroq-extractor.py E:/ C:/road-trip/ 3```

#### Demo
![Mostly textured world of the RoadTrip Adventure game in 3D](results/Whole-World-01-2024.jpg)
![Sandpolis from RoadTrip Adventure game](results/Results-04-2024-Sandpolis.PNG)


#### Information sources:

- Most key mesh information was found https://forum.xentax.com/viewtopic.php?t=17567 (website closed)
- More information about the textures were extracted from https://zenhax.com/viewtopic.php?t=7405 (website closed)
  - https://web.archive.org/web/20220309142950/https://zenhax.com/viewtopic.php?t=7405
- Some code is based on the BMS/3DS Max script in the forum above (note: forum has been closed)
- Other information was gathered from analysis or PlayStation/2 memory/data formats found in the manuals, useful for how the TIM file and palette data is stored

#### Thanks:
- killercracker (3DS max script)
- Acewell (BMS script)
