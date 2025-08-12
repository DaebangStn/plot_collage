import tkinter as tk
from .collage_canvas import CollageCanvas


def main():
    root = tk.Tk()
    root.title("Plot Collage")
    app = CollageCanvas(root)
    root.mainloop()


if __name__ == "__main__":
    main()
