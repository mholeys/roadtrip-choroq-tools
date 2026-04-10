import functools

import customtkinter

class MessageBox(customtkinter.CTkToplevel):

    def __init__(self, master, buttons, message, title, callback=None, warn=False):
        super().__init__(master)
        self.wm_transient(master)
        self.wm_title(title)

        self.callback = callback

        message_label = customtkinter.CTkLabel(self, text=message, corner_radius=6)

        self.rowconfigure(0, weight=1)

        col = 0
        self.buttons = []
        for button_index, button_text in enumerate(buttons):
            button = customtkinter.CTkButton(self, text=button_text,
                                             command=functools.partial(self.callback_internal, button_index,
                                                                       button_text))
            if warn:
                # Colour button red
                button.configure(fg_color="Red")
                button.after(1, self.update())
            button.grid(row=1, column=col, sticky="nesw")
            self.buttons.append(button)
            col += 1
            self.columnconfigure(0, weight=1)
        message_label.grid(row=0, column=0, columnspan=col, sticky="nesw")

    def callback_internal(self, button_index, button_name):
        if self.callback is not None:
            self.callback(button_index, button_name)
            self.destroy()
        else:
            self.destroy()