# RoadTrip Adventure / ChoroQ 2 HG model extraction tools

#### Matthew Holey

This is a set of tools used to extract the Qxx.BIN files from the PS2 game RoadTrip Adventure (UK/EU) / Everywhere RoadTrip (US)/ChoroQ HG 2 (JP) チョロQ HG 2 - written in python

I have tried to document the information that I have found, and others have found.
I only wanted to create a tool to extract the models, and textures, but the other files for the game are very similar and some data can be extracted from them as well.

For most uses see the car-extractor.py file
``` python car-extractor.py <input folder> <output folder> [makedirs] [type]```

e.g to make PLY files from the `CAR0` folder, with subfolders for each car
``` python car-extractor.py CAR0 ~/cars 1 2```

e.g to make both OBJ and PLY files from the `CAR0` folder, directly in the ~/cars folder
``` python car-extractor.py CAR0 ~/cars```

e.g to make OBJ files from the Q00.BIN car
``` python car-extractor.py Q00.BIN ~/cars 1 1```


Information sources:

Most key mesh information was found https://forum.xentax.com/viewtopic.php?t=17567
More information about the textures were extracted from https://zenhax.com/viewtopic.php?t=7405
Some code is based on the BMS/3DS Max script in the forum above
Other information was gathered from analysis or playstation/2 memory/data formats found in the manuals, very useful for how the TIM file and palette data is stored

Thanks: killercracker, Acewell

