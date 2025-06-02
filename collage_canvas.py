import tkinter as tk
from PIL import ImageGrab
import subprocess
import math
from image_item import ImageItem

class CollageCanvas:
    def __init__(self, root):
        self.root = root
        self.canvas = tk.Canvas(root, width=1200, height=1200, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.images = []
        self.current_scale = 1.0
        self.selected_image = None
        self.drag_offset = (0, 0)
        self.setup_bindings()

    def setup_bindings(self):
        self.canvas.bind("<Button-4>", self.zoomerP)
        self.canvas.bind("<Button-5>", self.zoomerM)
        self.canvas.bind("<ButtonPress-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.root.bind_all('<Control-v>', self.paste_clipboard_image)
        self.root.bind('<Escape>', lambda e: self.root.destroy())
        self.canvas.bind("<ButtonPress-3>", self.on_image_press)
        self.canvas.bind("<B3-Motion>", self.on_image_drag)
        self.canvas.bind("<ButtonRelease-3>", self.on_image_release)

    def rerender_images(self):
        for img in self.images:
            img.render(self.canvas, self.current_scale)
        self.resolve_collisions()
        for img in self.images:
            if img.id is not None:
                x, y = int(img.pos[0] * self.current_scale), int(img.pos[1] * self.current_scale)
                self.canvas.coords(img.id, x, y)

    def zoomerP(self, event):
        self.current_scale *= 1.1
        self.rerender_images()

    def zoomerM(self, event):
        self.current_scale /= 1.1
        self.rerender_images()

    def start_drag(self, event):
        self.canvas.scan_mark(event.x, event.y)

    def drag(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def check_xclip(self):
        try:
            subprocess.run(["xclip", "-version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except Exception:
            return False

    def paste_clipboard_image(self, event=None):
        if not self.check_xclip():
            print("xclip is required for clipboard image paste on Linux. Please install it with: sudo apt install xclip")
            return
        img = ImageGrab.grabclipboard()
        if img is not None:
            x0 = self.canvas.canvasx(self.canvas.winfo_width() // 2) / self.current_scale
            y0 = self.canvas.canvasy(self.canvas.winfo_height() // 2) / self.current_scale
            item = ImageItem(img, (x0, y0))
            self.images.append(item)
            self.resolve_collisions(item)
            self.rerender_images()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        else:
            print("No image in clipboard.")

    def find_image_at(self, x, y):
        items = self.canvas.find_overlapping(x, y, x, y)
        for item_id in reversed(items):
            for img in self.images:
                if img.id == item_id:
                    return img
        return None

    def on_image_press(self, event):
        x, y = self.canvas.canvasx(event.x) / self.current_scale, self.canvas.canvasy(event.y) / self.current_scale
        img = self.find_image_at(int(x * self.current_scale), int(y * self.current_scale))
        if img:
            self.selected_image = img
            img_x, img_y = img.pos
            self.drag_offset = (x - img_x, y - img_y)

    def on_image_drag(self, event):
        if self.selected_image:
            x = self.canvas.canvasx(event.x) / self.current_scale
            y = self.canvas.canvasy(event.y) / self.current_scale
            new_x = x - self.drag_offset[0]
            new_y = y - self.drag_offset[1]
            self.selected_image.pos = (new_x, new_y)
            self.rerender_images()

    def on_image_release(self, event):
        self.selected_image = None
        self.resolve_collisions()
        for img in self.images:
            if img.id is not None:
                x, y = int(img.pos[0] * self.current_scale), int(img.pos[1] * self.current_scale)
                self.canvas.coords(img.id, x, y)

    def rects_overlap(self, rect1, rect2):
        return not (rect1[2] <= rect2[0] or rect1[0] >= rect2[2] or rect1[3] <= rect2[1] or rect1[1] >= rect2[3])

    def find_non_overlapping_position(self, item, intended_pos, other):
        x0, y0 = intended_pos
        directions = ['right', 'left', 'down', 'up']
        best_pos = intended_pos
        min_dist = float('inf')
        bbox0 = item.get_bbox_at((x0, y0))
        for direction in directions:
            min_step = None
            candidate_pos = None
            bbox1 = other.get_bbox()
            if not self.rects_overlap(bbox0, bbox1):
                continue
            # Calculate step needed to clear the overlap in this direction
            if direction == 'right':
                step = bbox1[2] - bbox0[0]
                new_x = x0 + step
                new_y = y0
            elif direction == 'left':
                step = bbox0[2] - bbox1[0]
                new_x = x0 - step
                new_y = y0
            elif direction == 'down':
                step = bbox1[3] - bbox0[1]
                new_x = x0
                new_y = y0 + step
            elif direction == 'up':
                step = bbox0[3] - bbox1[1]
                new_x = x0
                new_y = y0 - step
            else:
                continue

            if step > 0:
                dist = abs(new_x - x0) + abs(new_y - y0)
                if min_step is None or dist < min_step:
                    min_step = dist
                    candidate_pos = (new_x, new_y)
            if candidate_pos and min_step <= min_dist:
                min_dist = min_step
                best_pos = candidate_pos
        return best_pos
    
    def check_collision_free(self, img=None):
        collision_free = True
        if img is None:
            for i, img in enumerate(self.images):
                other_imgs = self.images[i+1:]
                bbox = img.get_bbox()
                for other in other_imgs:
                    if self.rects_overlap(bbox, other.get_bbox()):
                        collision_free = False
                        break
        else:
            for other in self.images:
                if other == img:
                    continue
                if self.rects_overlap(img.get_bbox(), other.get_bbox()):
                    collision_free = False
                    break
        return collision_free
    
    def append_colfree_list(self, colfree_list, img):
        for i in range(len(colfree_list)):
            if self.rects_overlap(img.get_bbox(), colfree_list[i].get_bbox()):
                return i
        return -1
    
    def resolve_collisions(self, img=None):
        """
        Resolve collisions for all images.
        If img is provided, move the image to resolve collisions.
        """
        if img is not None:
            img_idx = self.images.index(img)
            img = self.images.pop(img_idx)
            self.images.append(img)
        
        for i in range(1, len(self.images)):
            prev_imgs = self.images[:i]
            while True:
                colidx = self.append_colfree_list(prev_imgs, self.images[i])
                if colidx == -1:
                    break
                pos = self.find_non_overlapping_position(self.images[i], self.images[i].pos, prev_imgs[colidx])
                self.images[i].pos = pos
        
        if img is not None:
            self.images.pop()
            self.images.insert(img_idx, img)
