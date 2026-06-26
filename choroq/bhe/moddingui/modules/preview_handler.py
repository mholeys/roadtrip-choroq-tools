import math

from customtkinter import CTkCanvas
from customtkinter import CTkFrame

from PIL import Image, ImageTk

from choroq.bhe.aptexture import APTexture


class APTPreviewFrame(CTkFrame):

    def __init__(self, master):
        CTkFrame.__init__(self, master)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.canvas = CTkCanvas(self, bg="black")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.texture = None
        self.imageTk = None
        self.background_drawn = False

    def set_image(self, texture: APTexture):
        self.texture = texture
        if texture is not None:
            image = self.texture.get_image()
            if image is not None:
                self.imageTk = ImageTk.PhotoImage(image)
                self.canvas.width = image.size[0] + 20
                self.canvas.height = image.size[1] + 20

                # Remove image before drawing again
                self.canvas.delete("texture")

                if not self.background_drawn:
                    draw_checker_board(self.canvas, 768, 768, (10, 10))
                    self.background_drawn = True
                # Draw white border around image, to make it clearer
                self.canvas.create_rectangle(9, 9, image.size[0] + 10, image.size[1] + 10, outline='white', tags=["texture"])
                self.canvas.create_image(10, 10, anchor="nw", image=self.imageTk, tags=["texture"])
            else:
                self.canvas.delete("all")
        else:
            self.canvas.delete("all")

def draw_checker_board(canvas, width, height, offset=(10, 10), primary_colour='magenta3', secondary_colour='magenta4', tags=None):
    if tags is None:
        tags = ["background"]
    size = 16 # width/height of cell

    color = primary_colour
    for y in range(int(height/size)):
        for x in range(int(width/size)):
            x1 = offset[0] + x * size
            y1 = offset[1] + y * size
            canvas.create_rectangle((x1, y1, x1 + size, y1 + size), fill=color, tags=tags)
            if color == primary_colour:
                color = secondary_colour
            else:
                color = primary_colour

        if color == primary_colour:
            color = secondary_colour
        else:
            color = primary_colour
