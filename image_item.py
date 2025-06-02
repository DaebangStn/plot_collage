from PIL import Image, ImageTk

class ImageItem:
    def __init__(self, pil_image, pos):
        self.pil = pil_image
        self.pos = pos  # logical (unscaled) coordinates
        self.photo = None
        self.id = None

    def render(self, canvas, global_scale):
        x, y = int(self.pos[0] * global_scale), int(self.pos[1] * global_scale)
        w, h = int(self.pil.width * global_scale), int(self.pil.height * global_scale)
        if w < 1 or h < 1:
            return
        resized = self.pil.resize((w, h), Image.LANCZOS)
        self.photo = ImageTk.PhotoImage(resized)
        if self.id is None:
            self.id = canvas.create_image(x, y, image=self.photo)
        else:
            canvas.itemconfig(self.id, image=self.photo)
            canvas.coords(self.id, x, y)

    def get_bbox(self):
        x, y = self.pos
        w, h = self.pil.width, self.pil.height
        return (x - w // 2, y - h // 2, x + w // 2, y + h // 2)

    def get_bbox_at(self, pos):
        x, y = pos
        w, h = self.pil.width, self.pil.height
        return (x - w // 2, y - h // 2, x + w // 2, y + h // 2)
