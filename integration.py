import threading
import tkinter as tk
from tkinter import scrolledtext
import pygame
import sys

# Import functions and variables from main.py
from main import set_pixel, start_pygame, clear_grid, click_queue

def run_code():
    code = code_input.get("1.0", tk.END)
    local_vars = {
        "set_pixel": set_pixel,
        "clear_grid": clear_grid,
    }
    exec(code, globals(), local_vars)

def clear_grid_callback():
    clear_grid()

def quit_callback():
    pygame.quit()
    root.quit()
    root.destroy()
    sys.exit()

def process_clicks():
    while not click_queue.empty():
        x, y = click_queue.get()
        terminal.insert(tk.END, f"Clicked on cell: ({x}, {y})\n")
        terminal.see(tk.END)
    root.after(100, process_clicks)

# Start Pygame in a separate thread
pygame_thread = threading.Thread(target=start_pygame)
pygame_thread.start()

# Create Tkinter window
root = tk.Tk()
root.title("Algorithm Input")

# Create text area for code input
code_input = scrolledtext.ScrolledText(root, width=50, height=20)
code_input.pack()

# Create a button to run the code
run_button = tk.Button(root, text="Run Code", command=run_code)
run_button.pack()

# Create a button to clear the grid
clear_button = tk.Button(root, text="Clear Grid", command=clear_grid_callback)
clear_button.pack()

# Create a button to quit the application
quit_button = tk.Button(root, text="Quit", command=quit_callback)
quit_button.pack()

# Create terminal-like output for coordinates
terminal = scrolledtext.ScrolledText(root, width=50, height=10)
terminal.pack()

# Start processing clicks
root.after(100, process_clicks)

# Run the application
root.mainloop()
