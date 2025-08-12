from PIL import Image, ImageTk

class ImageItem:
    def __init__(self, pil_image, pos, idx, canvas):
        self.pil = pil_image
        self._pos = pos  # logical (unscaled) coordinates
        self.photo = None
        self.id = None
        self.circle_id = None
        self.text_id = None
        self.idx = idx
        self.canvas = canvas
        self.r = 60

    def render(self, global_scale):
        x, y = int(self.pos[0] * global_scale), int(self.pos[1] * global_scale)
        w, h = int(self.pil.width * global_scale), int(self.pil.height * global_scale)
        if w < 1 or h < 1:
            return
        resized = self.pil.resize((w, h), Image.LANCZOS)
        self.photo = ImageTk.PhotoImage(resized)
        if self.id is None:
            self.id = self.canvas.create_image(x, y, image=self.photo)
        else:
            self.canvas.itemconfig(self.id, image=self.photo)
            self.canvas.coords(self.id, x, y)

        # Always (re)draw the circle and text
        if self.circle_id is not None:
            self.canvas.coords(self.circle_id, x - self.r, y - self.r, x + self.r, y + self.r)
        else:
            self.circle_id = self.canvas.create_oval(x - self.r, y - self.r, x + self.r, y + self.r, fill="#cccccc", outline="#888888", width=2)
        if self.text_id is not None:
            self.canvas.coords(self.text_id, x, y)
            self.canvas.itemconfig(self.text_id, text=str(self.idx))
        else:
            self.text_id = self.canvas.create_text(x, y, text=str(self.idx), fill="black", font=("Arial", int(self.r * 0.7), "bold"))

    def get_bbox(self):
        x, y = self.pos
        w, h = self.pil.width, self.pil.height
        return (x - w // 2, y - h // 2, x + w // 2, y + h // 2)

    def get_bbox_at(self, pos):
        x, y = pos
        w, h = self.pil.width, self.pil.height
        return (x - w // 2, y - h // 2, x + w // 2, y + h // 2)

    @property
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, pos):
        self._pos = pos
        if self.id is not None:
            self.canvas.coords(self.id, pos[0], pos[1])
        # Update the text position
        if self.text_id is not None:
            self.canvas.coords(self.text_id, pos[0], pos[1])
        # Update the circle position
        if self.circle_id is not None:
            self.canvas.coords(self.circle_id, pos[0] - self.r, pos[1] - self.r, pos[0] + self.r, pos[1] + self.r)
