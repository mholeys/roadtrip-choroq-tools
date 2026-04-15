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

    def set_image(self, texture : APTexture):
        self.texture = texture
        if texture is not None:
            image = self.texture.get_image()
            if image is not None:
                self.imageTk = ImageTk.PhotoImage(image)
                self.canvas.width = image.size[0] + 20
                self.canvas.height = image.size[1] + 20
                self.canvas.create_image(10, 10, anchor="nw", image=self.imageTk)
            else:
                self.canvas.delete("all")
        else:
            self.canvas.delete("all")
