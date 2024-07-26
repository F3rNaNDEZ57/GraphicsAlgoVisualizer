import pygame
import threading
import tkinter as tk
from tkinter import scrolledtext
import sys
import re

# Import functions and variables from main.py
from main import set_pixel, start_pygame, clear_grid, click_queue

def interpret_pseudocode(pseudocode, xl, yl, xr, yr, m, b):
    pseudocode = pseudocode.strip()
    pseudocode = pseudocode.replace('PlotPixel', 'set_pixel')
    pseudocode = pseudocode.replace(';', '')
    
    pseudocode_lines = pseudocode.split('\n')
    python_code = f"x = {xl}\nxl = {xl}\nyl = {yl}\nxr = {xr}\nyr = {yr}\nm = {m}\nb = {b}\n"
    indent_level = 0

    for line in pseudocode_lines:
        stripped_line = line.strip()
        if 'while' in stripped_line:
            condition = re.findall(r'\((.*?)\)', stripped_line)[0]
            python_code += '    ' * indent_level + f'while {condition}:\n'
            indent_level += 1
        elif '}' in stripped_line:
            indent_level -= 1
        else:
            if 'Round' in stripped_line:
                parts = stripped_line.split('Round')
                var, expr = parts[0].strip(), parts[1].strip()[1:-1]
                python_code += '    ' * indent_level + f'{var} round({expr})\n'
            else:
                python_code += '    ' * indent_level + f'{stripped_line}\n'
    
    return python_code

def run_code():
    try:
        xl = int(xl_entry.get())
        yl = int(yl_entry.get())
        xr = int(xr_entry.get())
        yr = int(yr_entry.get())
    except ValueError:
        terminal.insert(tk.END, "Invalid input! Please enter numeric values.\n")
        return

    # Calculate m and b
    m = (yr - yl) / (xr - xl)
    b = yl - m * xl

    # Display m and b to the user
    terminal.insert(tk.END, f"Calculated values: m = {m}, b = {b}\n")

    pseudocode = code_input.get("1.0", tk.END)
    python_code = interpret_pseudocode(pseudocode, xl, yl, xr, yr, m, b)
    terminal.insert(tk.END, f"Generated Python code:\n{python_code}\n")  # Debugging line to show generated code

    local_vars = {
        "set_pixel": set_pixel,
        "clear_grid": clear_grid,
    }
    
    try:
        exec(python_code, globals(), local_vars)
    except Exception as e:
        terminal.insert(tk.END, f"Error in pseudocode: {e}\n")

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

# Create input fields for xl, yl, xr, yr
input_frame = tk.Frame(root)
input_frame.pack()

tk.Label(input_frame, text="xl:").grid(row=0, column=0)
xl_entry = tk.Entry(input_frame)
xl_entry.grid(row=0, column=1)

tk.Label(input_frame, text="yl:").grid(row=1, column=0)
yl_entry = tk.Entry(input_frame)
yl_entry.grid(row=1, column=1)

tk.Label(input_frame, text="xr:").grid(row=2, column=0)
xr_entry = tk.Entry(input_frame)
xr_entry.grid(row=2, column=1)

tk.Label(input_frame, text="yr:").grid(row=3, column=0)
yr_entry = tk.Entry(input_frame)
yr_entry.grid(row=3, column=1)

# Create text area for pseudocode input
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

# Create terminal-like output for coordinates and errors
terminal = scrolledtext.ScrolledText(root, width=50, height=10)
terminal.pack()

# Start processing clicks
root.after(100, process_clicks)

# Run the application
root.mainloop()
