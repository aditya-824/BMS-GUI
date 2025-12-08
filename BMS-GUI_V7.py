from tkinter import *
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import serial
from threading import Thread
from tkinter import messagebox

port_var = "COM8"
root = Tk()
serial_vals = [StringVar(value='0.0') for _ in range(180)]
serial_running = False
serial_port = None
DEFAULT_ROWS = 3
DEFAULT_COLS = 6
DEFAULT_CELLS = 6
DEFAULT_TEMPS = 4


def serial_ports():
    """ Lists serial port names

        :returns: A list of the serial ports available on the system
    """

    ports = ['COM%s' % (i + 1) for i in range(256)]

    comms = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            comms.append(port)
        except (OSError, serial.SerialException):
            pass
    return comms


def start_serial_read():
    global serial_port, serial_running
    port = port_var
    try:
        serial_port = serial.Serial(port, 115200, timeout=1)
        serial_running = True
        serial_thread = Thread(target=worker, daemon=True)
        serial_thread.start()
    except serial.SerialException:
        print(f"Could not open serial port {port}")


def stop_serial_read():
    global serial_running
    serial_running = False
    if serial_port:
        serial_port.close()


def worker():
    global serial_running
    while serial_running:
        try:
            line = serial_port.readline().decode('utf-8').rstrip()
            if line:
                values = line.split(', ')
                for i, val in enumerate(values):
                    if i < len(serial_vals):
                        root.after(0, serial_vals[i].set, val)
        except Exception as e:
            print(f"Error reading from serial port: {e}")


def show_ports():
    ports = serial_ports()
    if ports:
        messagebox.showinfo("Available Serial Ports", "\n".join(ports))
    else:
        messagebox.showinfo("Available Serial Ports", "No serial ports found.")

notebook = ttk.Notebook(root)
notebook.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)

voltages_tab = ttk.Frame(notebook)
notebook.add(voltages_tab, text='Voltages')
for row in range(DEFAULT_ROWS):
    for col in range(DEFAULT_COLS):
        stack_index = row * DEFAULT_COLS + col
        stack_frame = LabelFrame(voltages_tab, text=f'Stack {stack_index+1}')
        stack_frame.grid(row=row, column=col, padx=15, pady=5)
        for i in range(DEFAULT_CELLS):
            Label(stack_frame, text=f'Cell {i+1}').grid(row=i, column=0, padx=5, pady=2)
            Label(stack_frame, textvariable=serial_vals[i]).grid(row=i, column=1, padx=5, pady=2)

temps_tab = ttk.Frame(notebook)
notebook.add(temps_tab, text='Temperatures')
for row in range(DEFAULT_ROWS):
    for col in range(DEFAULT_COLS):
        stack_index = row * DEFAULT_COLS + col
        stack_frame = LabelFrame(temps_tab, text=f'Stack {stack_index+1}')
        stack_frame.grid(row=row, column=col, padx=5, pady=5)
        for i in range(DEFAULT_TEMPS):
            Label(stack_frame, text=f'Temp {i+1}').grid(row=i, column=0, padx=5, pady=2)
            Label(stack_frame, textvariable=serial_vals[i]).grid(row=i, column=1, padx=5, pady=2)

Button(root, text='Start', command=start_serial_read).grid(
    row=DEFAULT_ROWS, column=0, pady=10)
Button(root, text='Stop', command=stop_serial_read).grid(
    row=DEFAULT_ROWS, column=1, pady=10)
Button(root, text='List Ports', command=show_ports).grid(
    row=DEFAULT_ROWS+1, column=0, columnspan=2, pady=10)

root.mainloop()
