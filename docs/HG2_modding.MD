
# Modding HG2 cars guide

As usual no responsibility is taken by me with whatever you use/do to your game/console/pc/whatever; you are doing this, not me!
I am merely trying to provide tools that make things easier, and if they do something that breaks things I will not be responsible.
You have been warned. Although I do not forsee any issues, they may still occur.

This quite a long guide, with both simple and complex sections, some you may be able to skip over quickly, others will need a good read.

This is a developing tool, that might have some changes over time, so this guide will be an overview on how to take any given mesh and place it into the game.
You will also have to read the documentation within the blender UI, and this will probably be kept up-to-date more than this document.


## Background information, MUST READ
I know a lot of guides have a "Must Read" section, but this game has structures that require a little understanding to make modifications, at this time anyway.
I am going to write two version of the guide, one using a GUI tool, and one where you can edit more than just cars.

Every object model in HG2 is one of two things, this might be confusing but this is how the game works.

Cars are made up of what I will be calling "Parts" and "Meshes".
Every car has up to 7 Parts, the last of which is the texture, these are defined as a list of positions within the car.
The image below shows this "Offset table", each of these define where that "Part" is relative to the start of the car.

Parts are made up of Meshes, it can only ever have 3.

Some other objects in the game may not be made up of Parts, but is directly a Part itself. Unless you are modifying things other than cars, you do not need to know this. 
The difference is that my blender code exports 1 part, with up to 3 meshes. 
This means we can create 7 parts for each car, and fully populate/replace a Qxx.BIN, or we can replace just 1 part, such as the default spoiler.

See [Car model format](https://github.com/mholeys/roadtrip-choroq-tools/blob/master/docs/HG2_HG3.MD#car-model-file-format) to understand a which part of the car is used for which bit.

## Getting started
The code is written for Blender, and so will only work with Blender.
If you do not like blender or use another tool then feel free to make it in whatever, and just import it into blender.  

If you are having a go for the first time, I recommend downloading the .blend file in the blender-py folder as an example.
And to make your first one easier, stick to replacing the main body Part only, until you get to grips with things.

The first thing needed is a car or model that you wish to place into the game. As cars are probably most people's aim I will be covering them, but the same applies all objects in the game.
For a car I would recommend it being in the following structure, these can be multiple different meshes/collections whatever in blender:
- The main body of the car itself, with all bits except wheels and spoilers
- A copy of the headlights and taillights (used as nighttime driving lights, and flashes when NPCs talk)
- A mesh slightly larger than the brake lights, to allow for the transparent mesh to spill out naturally (used for when you brake) 
- All meshes having the same texture (an atlus if needed)
- The bottom right quarter of the texture (0.5, 0.5 to 1.0, 1.0) defined as the shadow for the car (see the exported/dumped textures as an example)

If you want to make you car behave the same as the original cars you will also need
- A spoiler (which placed in the correct location, but is a separate mesh, no gaps in the car body)
- A secondary spoiler (same as above) for when you select the other wing set
- A linking mesh to connect your car, to the existing jets of the car you wish to replace 
  - This is for advanced users, you will have to dump the original jets, and add your mesh to it.
  - This will have to be done on a per car to be replaced (Qxx) basis, as each car has its flames defined in code, this is not yet modifiable
- A stickers mesh, that covers/overlaps bits of the car like the original game (optional)

The game has fixed positions for all of its files, this means we cannot increase the size of the car but we can place a smaller or same size file in its place.
From early testing, a triangle count of around 1000-1200 seems to be a good staring point for the body; less triangles -> smaller export -> the easier it is to fit.

## Configuring blender


The following steps should work, but if not you will have to look online on how to install a python package (pip) in blender.





### Installing pyffi 
This is only required once. I apologise if this is a poor guide, it's not easy to cover all options. Online videos/guides may be better.

#### Windows:
Locate your blender's install directory, its python folder
Examples:

Steam: `C:\Steam\steamapps\common\Blender\[version]\python\bin`

Normal: `C:\Program Files\Blender Foundation\Blender [version]\python\bin`

Press Windows + R.
Enter cmd.exe in the open box
Press Ctrl+Shift+Enter to open command prompt as **Administrator** this is required.

Once you have confirmed administrator with UAC (Yes) you will have to navigate to your blender's folder.

`cd` will change into the path given

`cd C:\Program Files\Blender Foundation\Blender 5.0\5.0\python\bin`

`cd C:\Program Files\Blender Foundation\Blender 4.5\4.5\python\bin`

If your blender install is on a different drive than 'C' you for example 'D' you will have to type in
`D:` into command prompt, and press enter, changing the letter D for the drive required.

Once you are in your python folder you will need to type the following commands.
```python.exe -m pip install --force-reinstall pyffi```

You should then see something along the lines of the following
![Screeenshot in command prompt installing pyffi](docs/images/blender-python-pip.jpg)

If you have seen any errors please consult guides online on how to install packages to pip. 
This is a common task and there are multiple guides available, specifically for blender.

### Loading the script

Once you have all the above ready, open blender (if you haven't already), and go to the scripting tab at the top (red arrow).
Then press on Open in the middle (blue arrow) and browse to the blender script ([download](/blender-py/blender_hg2.py))

![Screenshot showing the scripting tab, and open button in Blender](docs/images/blender-scripting-tab.jpg)

Once loaded, you will need to press run script, again in the middle.

![Screenshot showing the script script loaded in Blender](docs/images/blender-script-loaded.jpg)

After this has executed, check that there are no errors in the bottom left, and that there is a message saying "bpy.ops.text.run_script()"
If you do encounter any errors at this point, there is an error with your blender setup, or the script, and you may not be able to use the script.
If you see pyffi not found or similar, you will need to install pyffi again, or try following an online guide for "installing python packages in blender"

## Using the script

Once the script has been executed, there should be a new panel available in the Layout tab. 
This is hidden within the side window, with settings for Tool/View/Animation and now HG2 Exporter.

Open this panel (shown in red), and if you see HG2 Exporter click that, it also means everything has worked so far.

![Screenshot showing the location of the panel on the right edge of the layout view](docs/images/blender-panel-closed.jpg)

Once open you should see the following:

![Screenshot showing the new HG2 Exporter panel on the right edge of the layout view](docs/images/blender-hg2-exporter-panel.jpg)

At this point you can proceed to read everything in the new panel, but I will cover some essential information to make things easier to follow for the first time.

The first thing that is needed, is to configure all objects you wish to export.
To do this we need to set up some additional attributes for all meshes, this is easy to do with the configure attributes button (it will only ever add 1, and will never delete/change any values)
All you need to do is select all objects you want to include or work with, and press the configure attributes button.
After this there will be some new attributes assigned for each selected object, this is visible under the "Data" section, shown as a green triangle, highlighted below with a red square.

__Remember where this is, and it is essential to remember to select the one you wish to edit highlighted when you are setting the mesh parameters.__

Before:
![Screenshot showing attributes of the selected object before setup](docs/images/blender-config-attributes-before.jpg)
After:
![Screenshot showing attributes of the selected object after setup](docs/images/blender-config-attributes-after.jpg)

### Configuring your model

At this point you need to go through and configure the different parts of the car.
This is a slow process, and a manual one, which may require some trial and error.
To set values for these attributes you will need to select the mesh you wish to edit,
and change into edit mode.

![Screenshot showing the location of the edit mode](docs/images/blender-edit-mode.jpg)

All the data is configured in the FACE domain (except vertex colours), this means you will have to work by selecting faces of the car.

![Screenshot showing the location of the face selection mode](docs/images/blender-edit-faces-mode.jpg)

The first thing is to select all faces you wish to set as the same value, you can select as many faces as you want, or do it in smaller chunks.
To set a value for the selected faces, you first need to select the attribute you wish to change, under Data->Attributes. 
Make sure the one you wish to change is highlighted (blue in the screenshot)
Then to set the value, you select Mesh from the top bar, and choose Set Attribute.
A window will appear, moving your mouse outside this window closes it, and may or may not set the value (I do not know)
At this point enter the value you wish (see the guide below or in blender) and hit enter while your mouse is not over the value box (black background)

![Screenshot showing the set attribute button](docs/images/blender-set-attribute-menu.jpg)

![Screenshot showing the set attribute window](docs/images/blender-set-attribute-window.jpg)

You will need to set up the UV maps for only the faces you want texturing, I think this means you might need to split all textured faces into a separate mesh. 
This is due to the code assuming any face having a UV map being treated as a textured face.

The baked colours for any mesh will also need to be in Vertex space, this means when you want to paint any vertices you will need to do this with a Vertex based colour attribute, (add new colour attribute Domain = "Vertex" not "Face corner") otherwise your mesh will not have the correct colours



There are currently 3 special properties:
- ObjectIndex (information in blender under the "Object assignment 0/1/2" heading)
  - This configures which of the 3 meshes for the exported part this face belongs to
  - For example selecting all faces of the main body, and setting their ObjectIndex to 0 will include them all in mesh[0], (the body mesh for a car)
  - Setting this value to 1 will make the face be included in the second mesh, mesh[1] (Lights for the first part of a car)
  - Setting this value to 2 will make the face be included in the second mesh, mesh[2] (Brake Lights for the first part of a car)
- ColourIndex (information in blender under the "Object colour assignment" heading)
  - This parameter defines what colour is used in game
    - Setting this to 0 will make the object use a combination of the texture (if the face has a UV map) and the Vertex colours (not face colours)
    - Setting this to 1 will mean this face gets colour the same as the primary colour in the game (first choice in the paint shop)
    - Setting this to 2 will mean this face gets the secondary colour in two-tone paint mode, or the primary colour when painted with 1 colour in game.
- SmoothnessHG2 (information in blender under the "Object smoothness assignment" heading)
  - This value is the more complicated one.
  - This defines how the face is rendered in game, usually this controls the reflectivity, but it only supports a set of numbers, you cannot put any value in this as it will either break or not work
  - The allowed values are shown in blender, but include:
    - 357.0 used for windows to give them the shine (blue in the image below)
    - 280.5 used on untextured (no UV map) faces of the main body's paint, but only the faces that are visible from the top down view (green in image below)
    - 255.0 used on underside body panels, such as the front splitter of some cars (dark blue in the image below)
    - 51.0 used for the other body faces, same as 280.5 but for the faces that do not face upwards (red in image below)
    - 1.0 used for the headlights and brake light meshes (unsure why but it works, white in the image below)
    - 0.0 used for the other panels, which are matte afaik, such as body panel gaps, and the window trim (black in the image below)

ObjectIndex demonstration car:
I have moved the lights/brake lights to make this easier to see, you should have yours positioned as you want them to show up in the game
- White means object index of 0
- Red means object index of 1
- Green means object index of 2

![Screenshot demonstrating the values for smoothness with a visual guide](docs/images/object-index-hg2-demo.jpg)

ColourIndex demonstration car:
I have moved the lights/brake lights to make this easier to see, you should have yours positioned as you want them to show up in the game
- White means colour index of 0
- Red means colour index of 1
- Green means colour index of 2

![Screenshot demonstrating the values for smoothness with a visual guide](docs/images/colour-index-hg2-demo.jpg)

Smoothness value demonstration car:
![Screenshot demonstrating the values for smoothness with a visual guide](docs/images/smoothness-hg2-demo1.jpg)
![Screenshot demonstrating the values for smoothness with a visual guide](docs/images/smoothness-hg2-demo2.jpg)

### Exporting the Part

The final step within blender is to export your model (the whole point right?).
To do this all you have to do is select all blender objects you wish to include in this Part, and then finally click export at the bottom of the HG2 Export Helper panel.

At this point a save file window will appear, with some settings on the right-hand side.
These settings configure how the data is saved, the main things to know for cars:
- For the car body Part - Mesh type should be:
  - Mesh 0 Normal
  - Mesh 1 Transparent
  - Mesh 2 Transparent
- For other Parts - Mesh type will have to be tested but most will be:
  - Mesh 0 Normal
  - Mesh 1 Normal
  - Mesh 2 Normal
- Normal type (this is related to the Vertex normals of the exported model)
  - Test with Normal and if it looks right great, if not reexport with Alternative
  - Alternative is usually for objects that have been imported in blender via the OBJ format (such as a different HG2 car)
  - If neither of these work you will have to edit the code, or contact me to find the setting for you.
    - In the future I plan to allow you to choose all combinations but I wanted to get this published sooner

### Putting you car in the game
#### GUI method:

TODO: sorry this is still being written at this point, and so I cannot show you how it works. 
I also realise that at this point the HxD method shown below is very much lacking. 

#### Hex editor method (HxD recommended)
If you wish to edit a different part of the game from a car, you will need to use a hex editor. 
The steps to take this are as follows, but are simplified as you will need to get comfortable doing this without my guide.

__You should never change the size of the file (ISO) this will break it__

0. Make a copy of your ISO (bin/cue will need converting _sorry_, 7Zip has a plugin you can use (no guide here))
1. Find the Sector number for the file you wish to edit
2. Open the ISO in HxD using the Open Disk Image (Ctrl+Shift+I)
3. Enter the sector number at the top of HxD (little text box in menu bar)
4. You should look at the offset table shown, this wil be multiple 4 byte numbers (readable using View->Toolbars->Data inspector)
5. Using the Data inspector highlight the first 4 bytes and see the UInt32 value, this is how much further down you need to move (from your current position)
4. Open your exported Part.BIN and copy all content (the warning is fine, if you get one)
5. Back in the ISO's tab, find which offset you need to replace, and navigate to it
6. This offset for cars is usually shown in the first 4 bytes of the sector 30 00 00 00, which means 3 * 16 bytes further down (3 rows if 16 bytes wide)
7. Move your cursor to this offset and Ctrl+B to paste write, not Paste insert
8. That is the model written
9. Save the ISO (as a copy if you like), but after saving there is no way to undo
10. Test it on PS2 or emulator

### Troubleshooting and debugging

Blender has a very handy window for inspecting the different values set on a mesh, this is called Spreadsheet.
To open this you click the upper left hand icon on any panel and choose Spreadsheet, I recommend opening a new window (Window -> New Window) and setting this to be your speadsheet.

In here you can see the different attributes of the mesh you have selected, and under the different domains, usually you will want to have face selected on the left.
The spreadsheet will show values for the current object you have selected (only 1 object)
If you select the little Arrowhead in the spreadsheet window you can show only the selected faces.
This way you can see if you have missed any selected faces.

![Opening the blender spreadsheet window](docs/images/blender-spreadsheet-window.jpg)
![Example of the data shown in the blender spreadsheet window (face)](docs/images/blender-spreadsheet-demo.jpg)

 It might also be useful to you to create/use the test materials provided in the example blender as shown below, they mimic the same view as the demo cars shown above under "Configuring your model" section towards the end.
