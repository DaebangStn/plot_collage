import tkinter as tk
from PIL import ImageGrab, Image
import subprocess
import re
import base64
import io
from .image_item import ImageItem
from urllib.request import urlopen


WINDOW_START_X = 3840
# WINDOW_START_X = 4200

class CollageCanvas:
    def __init__(self, root):
        self.root = root
        self.root.geometry(f"{720}x{720}+{WINDOW_START_X}+{720}")
        self.canvas = tk.Canvas(root, width=1200, height=1200, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.config(scrollregion=(-500, -500, 10000, 10000))
        # Draw boundary lines for x=0 and y=0 and store their IDs
        self.x_axis_id = self.canvas.create_line(0, 0, 0, 1200, fill='black', width=2)  # y-axis
        self.y_axis_id = self.canvas.create_line(0, 0, 1200, 0, fill='black', width=2)  # x-axis
        self.images = []
        self.current_scale = 0.25
        self.selected_image = None
        self.drag_offset = (0, 0)
        self.setup_bindings()
        self.root.bind_all('<space>', self.copy_collage_to_clipboard)

    def get_total_bbox(self):
        if not self.images:
            return None
        bboxes = [img.get_bbox() for img in self.images]
        min_x = min(b[0] for b in bboxes)
        min_y = min(b[1] for b in bboxes)
        max_x = max(b[2] for b in bboxes)
        max_y = max(b[3] for b in bboxes)
        return (min_x, min_y, max_x, max_y)

    def copy_collage_to_clipboard(self, event=None):
        bbox = self.get_total_bbox()
        if not bbox:
            return
        min_x, min_y, max_x, max_y = bbox
        width, height = int(max_x - min_x), int(max_y - min_y)
        collage = Image.new("RGBA", (width, height), (255, 255, 255, 0))
        for img in self.images:
            x, y = img.pos
            offset_x = int(x - img.pil.width // 2 - min_x)
            offset_y = int(y - img.pil.height // 2 - min_y)
            collage.paste(img.pil, (offset_x, offset_y), img.pil if img.pil.mode == 'RGBA' else None)
        # Now put collage to clipboard as PNG
        try:
            import io
            import subprocess
            output = io.BytesIO()
            collage.save(output, "PNG")
            data = output.getvalue()
            p = subprocess.Popen(['xclip', '-selection', 'clipboard', '-t', 'image/png', '-i'], stdin=subprocess.PIPE)
            p.communicate(data)
            print("Clipboard copy successful (PNG)")
        except Exception as e:
            print("Clipboard copy failed:", e)

    def boundary_check(self, bbox):
        # Returns True if bbox is within allowed boundaries (x >= 0, y >= 0)
        return bbox[0] >= 0 and bbox[1] >= 0

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

    def rerender_images(self, allow_collisions=True):
        for img in self.images:
            img.render(self.current_scale)
        if not allow_collisions:
            self.resolve_collisions()
        for img in self.images:
            if img.id is not None:
                x, y = int(img.pos[0] * self.current_scale), int(img.pos[1] * self.current_scale)
                self.canvas.coords(img.id, x, y)

        # Only draw axes for x>0 and y>0 (positive quadrant)
        x0 = self.canvas.canvasx(0) / self.current_scale
        y0 = self.canvas.canvasy(0) / self.current_scale
        x1 = self.canvas.canvasx(self.canvas.winfo_width()) / self.current_scale
        y1 = self.canvas.canvasy(self.canvas.winfo_height()) / self.current_scale

        # y-axis (vertical at x=0, only for y >= 0)
        self.canvas.coords(
            self.x_axis_id,
            int(0 * self.current_scale), int(max(0, y0) * self.current_scale),
            int(0 * self.current_scale), int(max(0, y1) * self.current_scale)
        )
        # x-axis (horizontal at y=0, only for x >= 0)
        self.canvas.coords(
            self.y_axis_id,
            int(max(0, x0) * self.current_scale), int(0 * self.current_scale),
            int(max(0, x1) * self.current_scale), int(0 * self.current_scale)
        )

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
        # 1. Try ImageGrab.grabclipboard()
        img = ImageGrab.grabclipboard()
        if not isinstance(img, Image.Image):
            # 2. Try to extract base64 image from HTML clipboard
            try:
                html = subprocess.check_output(
                    ['xclip', '-selection', 'clipboard', '-t', 'text/html', '-o'],
                    stderr=subprocess.DEVNULL
                ).decode(errors='ignore')
            except Exception:
                html = ''
            # Try base64 first
            m = re.search(r'<img[^>]+src="data:image/[^;]+;base64,([^"]+)"', html)
            if m:
                b64_data = m.group(1)
                try:
                    img_bytes = io.BytesIO(base64.b64decode(b64_data))
                    img = Image.open(img_bytes)
                except Exception:
                    img = None
            else:
                # Try remote URL
                m_url = re.search(r'<img[^>]+src="(https?://[^"]+)"', html)
                if m_url:
                    url = m_url.group(1)
                    try:
                        with urlopen(url) as response:
                            img_bytes = io.BytesIO(response.read())
                            img = Image.open(img_bytes)
                    except Exception as e:
                        print("Failed to download image from URL:", e)
                        img = None
        if img is not None:
            # Get mouse position if available, else center
            if event is not None:
                x0 = self.canvas.canvasx(event.x) / self.current_scale
                y0 = self.canvas.canvasy(event.y) / self.current_scale
            else:
                x0 = self.canvas.canvasx(self.canvas.winfo_width() // 2) / self.current_scale
                y0 = self.canvas.canvasy(self.canvas.winfo_height() // 2) / self.current_scale
            item = ImageItem(img, (x0, y0), len(self.images), self.canvas)
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
            new_bbox = self.selected_image.get_bbox_at((new_x, new_y))
            self.selected_image.pos = (new_x, new_y)
            self.rerender_images(allow_collisions=True)

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
            if not self.boundary_check((new_x, new_y)):
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

        max_attempts = 50  # Prevent infinite loops
        for i in range(len(self.images)):
            prev_imgs = self.images[:i]
            if not self.boundary_check(self.images[i].get_bbox()):
                _img = self.images[i]
                bbox = _img.get_bbox()
                x_depth = min(0, bbox[0])
                y_depth = min(0, bbox[1])
                _img.pos = (_img.pos[0] - x_depth, _img.pos[1] - y_depth)
            attempts = 0
            while len(prev_imgs) > 0 and attempts < max_attempts:
                colidx = self.append_colfree_list(prev_imgs, self.images[i])
                if colidx == -1:
                    break
                pos = self.find_non_overlapping_position(self.images[i], self.images[i].pos, prev_imgs[colidx])
                if pos == self.images[i].pos:
                    # No better position found, break to avoid infinite loop
                    break
                self.images[i].pos = pos
                attempts += 1
            if attempts >= max_attempts:
                print(f"Warning: Could not resolve collision for image {i} after {max_attempts} attempts.")

        if img is not None:
            self.images.pop()
            self.images.insert(img_idx, img)
