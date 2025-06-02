import tkinter as tk
from collage_canvas import CollageCanvas

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Tkinter Canvas Example")
    app = CollageCanvas(root)
    root.mainloop()
