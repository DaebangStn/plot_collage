import tkinter as tk
from PIL import Image, ImageTk, ImageGrab
import sys
import subprocess
import math

# Global state
current_scale = 1.0
pasted_images = []  # Each: {'pil': pil_image, 'id': canvas_image_id, 'photo': photoimage, 'pos': (x, y)}
selected_image = None
drag_offset = (0, 0)

# --- Utility Functions ---
def rects_overlap(rect1, rect2):
    # rect: (x1, y1, x2, y2)
    return not (rect1[2] <= rect2[0] or rect1[0] >= rect2[2] or rect1[3] <= rect2[1] or rect1[1] >= rect2[3])

def get_image_bbox(entry, pos=None, scale=None):
    if pos is None:
        pos = entry['pos']
    if scale is None:
        scale = current_scale
    pil_img = entry['pil']
    w, h = int(pil_img.width * scale), int(pil_img.height * scale)
    x, y = pos
    # Centered at (x, y)
    return (x - w // 2, y - h // 2, x + w // 2, y + h // 2)

def find_non_overlapping_position(entry, intended_pos, other_entries, step=10, max_radius=300):
    angle_steps = 36  # 10 degrees per step
    for radius in range(0, max_radius + 1, step):
        for angle in range(0, 360, 360 // angle_steps):
            rad = math.radians(angle)
            x = intended_pos[0] + int(radius * math.cos(rad))
            y = intended_pos[1] + int(radius * math.sin(rad))
            bbox = get_image_bbox(entry, pos=(x, y))
            collision = False
            for other in other_entries:
                if rects_overlap(bbox, get_image_bbox(other)):
                    collision = True
                    break
            if not collision:
                return (x, y)
    return intended_pos

# --- Canvas Operations ---
def rerender_images():
    for entry in pasted_images:
        pil_img = entry['pil']
        x, y = entry['pos']
        new_size = (int(pil_img.width * current_scale), int(pil_img.height * current_scale))
        if new_size[0] < 1 or new_size[1] < 1:
            continue
        resized = pil_img.resize(new_size, Image.LANCZOS)
        tk_img = ImageTk.PhotoImage(resized)
        entry['photo'] = tk_img
        if entry['id'] is None:
            entry['id'] = canvas.create_image(x, y, image=tk_img)
        else:
            canvas.itemconfig(entry['id'], image=tk_img)
            canvas.coords(entry['id'], x, y)
    resolve_all_collisions()
    # After resolving, update all positions
    for entry in pasted_images:
        if entry['id'] is not None:
            canvas.coords(entry['id'], entry['pos'][0], entry['pos'][1])

# --- Event Handlers ---
def zoomerP(event):
    global current_scale
    current_scale *= 1.1
    rerender_images()
    # Optionally, scale other canvas items (lines, shapes) as before

def zoomerM(event):
    global current_scale
    current_scale /= 1.1
    rerender_images()
    # Optionally, scale other canvas items (lines, shapes) as before

def start_drag(event):
    canvas.scan_mark(event.x, event.y)

def drag(event):
    canvas.scan_dragto(event.x, event.y, gain=1)

def check_xclip():
    try:
        subprocess.run(["xclip", "-version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except Exception:
        return False

def paste_clipboard_image(event=None):
    if not check_xclip():
        print("xclip is required for clipboard image paste on Linux. Please install it with: sudo apt install xclip")
        return
    img = ImageGrab.grabclipboard()
    if isinstance(img, Image.Image):
        x0 = canvas.canvasx(canvas.winfo_width() // 2)
        y0 = canvas.canvasy(canvas.winfo_height() // 2)
        temp_entry = {'pil': img, 'pos': (x0, y0)}
        pos = find_non_overlapping_position(temp_entry, (x0, y0), pasted_images)
        pasted_images.append({'pil': img, 'id': None, 'photo': None, 'pos': pos})
        rerender_images()
        canvas.configure(scrollregion=canvas.bbox("all"))
    else:
        print("No image in clipboard.")

def find_image_at(x, y):
    items = canvas.find_overlapping(x, y, x, y)
    for item in reversed(items):
        for entry in pasted_images:
            if entry['id'] == item:
                return entry
    return None

def on_image_press(event):
    global selected_image, drag_offset
    x, y = canvas.canvasx(event.x), canvas.canvasy(event.y)
    entry = find_image_at(x, y)
    if entry:
        selected_image = entry
        img_x, img_y = entry['pos']
        drag_offset = (x - img_x, y - img_y)

def on_image_drag(event):
    global selected_image
    if selected_image:
        x, y = canvas.canvasx(event.x), canvas.canvasy(event.y)
        new_x = x - drag_offset[0]
        new_y = y - drag_offset[1]
        temp_entry = selected_image.copy()
        temp_entry['pos'] = (new_x, new_y)
        other_entries = [e for e in pasted_images if e is not selected_image]
        pos = find_non_overlapping_position(temp_entry, (new_x, new_y), other_entries)
        canvas.coords(selected_image['id'], pos[0], pos[1])
        selected_image['pos'] = pos

def on_image_release(event):
    global selected_image
    selected_image = None
    resolve_all_collisions()
    for entry in pasted_images:
        if entry['id'] is not None:
            canvas.coords(entry['id'], entry['pos'][0], entry['pos'][1])

def resolve_all_collisions():
    for i, entry in enumerate(pasted_images):
        other_entries = pasted_images[:i] + pasted_images[i+1:]
        pos = find_non_overlapping_position(entry, entry['pos'], other_entries)
        entry['pos'] = pos

# --- Tkinter Setup ---
root = tk.Tk()
root.title("Tkinter Canvas Example")

canvas = tk.Canvas(root, width=1200, height=1200, bg="white")
canvas.pack(fill=tk.BOTH, expand=True)

# Linux-only zoom bindings
canvas.bind("<Button-4>", zoomerP)    # Scroll up
canvas.bind("<Button-5>", zoomerM)    # Scroll down

# Drag bindings (canvas panning)
canvas.bind("<ButtonPress-1>", start_drag)
canvas.bind("<B1-Motion>", drag)

# Bind Ctrl+V for paste
root.bind_all('<Control-v>', paste_clipboard_image)

canvas.configure(scrollregion=canvas.bbox("all"))

# Start the Tkinter event loop
root.bind('<Escape>', lambda e: root.destroy())

# Bindings for image dragging (right mouse button)
canvas.bind("<ButtonPress-3>", on_image_press)
canvas.bind("<B3-Motion>", on_image_drag)
canvas.bind("<ButtonRelease-3>", on_image_release)

root.mainloop()
