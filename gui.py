"""gui.py
Minimal Tkinter GUI placeholder to visualize the player on the map.
"""
from __future__ import annotations
import tkinter as tk
from typing import Callable


class SimpleGUI:
    def __init__(self, width=600, height=600):
        self.root = tk.Tk()
        self.root.title("AION AutoPlay Simulation - GUI (placeholder)")
        self.canvas = tk.Canvas(self.root, width=width, height=height, bg="black")
        self.canvas.pack()

    def start(self):
        self.root.mainloop()


def run_gui():
    gui = SimpleGUI()
    gui.start()


if __name__ == "__main__":
    run_gui()
