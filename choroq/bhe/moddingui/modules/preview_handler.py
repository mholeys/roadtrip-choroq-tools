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

    def set_image(self, texture: APTexture):
        self.texture = texture
        if texture is not None:
            image = self.texture.get_image()
            if image is not None:
                self.imageTk = ImageTk.PhotoImage(image)
                self.canvas.width = image.size[0] + 20
                self.canvas.height = image.size[1] + 20

                draw_checker_board(self.canvas, self.winfo_width(), self.winfo_height(), (10, 10))
                # Draw white border around image, to make it clearer
                self.canvas.create_rectangle(9, 9, image.size[0] + 10, image.size[1] + 10, outline='white')
                self.canvas.create_image(10, 10, anchor="nw", image=self.imageTk)
            else:
                self.canvas.delete("all")
        else:
            self.canvas.delete("all")

def draw_checker_board(canvas, width, height, offset=(10, 10), primary_colour='magenta3', secondary_colour='magenta4'):
    size = 16 # width/height of cell

    color = primary_colour
    for y in range(50):
        for x in range(50):
            x1 = offset[0] + x * size
            y1 = offset[1] + y * size
            x2 = offset[0] + x1 + size
            y2 = offset[1] + y1 + size
            canvas.create_rectangle((x1, y1, x2, y2), fill=color)
            if color == primary_colour:
                color = secondary_colour
            else:
                color = primary_colour

        if color == primary_colour:
            color = secondary_colour
        else:
            color = primary_colour
