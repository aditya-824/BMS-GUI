from tkinter import *
from tkinter import ttk
from tkinter import filedialog
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import serial

DEFAULT_STACK_ROWS = 3  # Default number of stacks in a row
DEFAULT_STACK_COLS = 6  # Default number of stacks in a column
DEFAULT_CELLS = 6   # Default number of cells per stack
DEFAULT_TEMPS = 4  # Default number of temperature sensors per stack
DEFAULT_UV = 3.000  # Default undervoltage threshold
DEFAULT_OV = 4.200  # Default overvoltage threshold
DEFAULT_UT = 45.0   # Default under-temperature threshold
DEFAULT_OT = 60.0   # Default over-temperature threshold
DEFAULT_BAUD = 115200  # Default baud rate for serial communication
TIMESTAMP_COL = 0  # Column index for timestamp
LAST_CELL_DATA_COL = 181  # Last column index for cell voltage & temp data

all_cell_voltages = []  # List to store all cell voltages
all_cell_temps = []  # List to store all cell temperatures

def serial_ports():
    """ Lists serial port names

        :returns:
            A list of the serial ports available on the system
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

# comms = ['COM1', 'COM2', 'COM3', 'COM4'] # Example serial ports, replace with actual detection logic

def read_file(file_path, stack_rows, stack_cols, cells, temps):
    """ Reads a CSV file and returns its content as a pandas DataFrame.

        :param file_path: Path to the CSV file.
        :returns: DataFrame containing the CSV data.
    """
    indiv_cell_voltages = []  # List to store individual cell voltages
    indiv_cell_temps = []  # List to store individual cell temperatures
    global timestamps # List to store timestamps

    df = pd.read_csv(file_path, header=0, skiprows=[1])  # Read the CSV file, skipping the second line
    cols = df.columns.tolist()
    timestamps = df.iloc[:, TIMESTAMP_COL].tolist()  # Store timestamps from the first column
    # timestamp_col_name = cols[TIMESTAMP_COL]
    new_cols = []
    for i in range(TIMESTAMP_COL+1, LAST_CELL_DATA_COL, 4):
        group = cols[i:i+4]
        new_cols.extend(group[::-1])  # Reverse the order of each group of 4 columns
    all_cols = [cols[TIMESTAMP_COL]] + new_cols + cols[LAST_CELL_DATA_COL+1:]  # Reorder columns and keep the first and last few columns as is
    df_new = df[all_cols]
    for stack_data in range(TIMESTAMP_COL+1, LAST_CELL_DATA_COL, cells+temps):
        for cell in range(cells):
            indiv_cell_voltages.append(df_new.iloc[:, stack_data + cell].tolist())
        all_cell_voltages.append(indiv_cell_voltages)
        indiv_cell_voltages = []  # Reset for the next stack
        for temp in range(temps):
            indiv_cell_temps.append(df_new.iloc[:, stack_data + cells + temp].tolist())
        all_cell_temps.append(indiv_cell_temps)
        indiv_cell_temps = []

def plot_data(x, y, x_label, y_label, title):
    """ Plots the data using matplotlib. """
    plt.figure(figsize=(10, 6))
    # If y is a list of lists (all cells in a stack)
    if isinstance(y[0], list):
        for cell_index, cell_voltages in enumerate(y):
            plt.plot(x, cell_voltages, label=f'Cell {cell_index + 1}', linestyle='-')
        plt.legend()
    else:
        plt.plot(x, y, marker='o', linestyle='-', color='b')
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.title(title)
    plt.grid(True)
    plt.show()

class BatteryManagementSystem:
    def __init__(self, root):
        self.root = root
        self.root.title("BMS")
        self.root.geometry("1400x900")

        self.file_path = ""  # Initialize file path as instance variable

        # self.comms = serial_ports() # Searching for available serial ports
        self.choose_csv()

    def choose_csv(self):
        self.file_frame = ttk.LabelFrame(text='File Selection', padding=(10, 5))
        self.file_frame.grid(row=0, column=0, padx=10, pady=5, sticky='w')
        self.file_label = ttk.Label(self.file_frame, text='CSV File:')
        self.file_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.file_entry = ttk.Entry(self.file_frame, width=60)
        self.file_entry.grid(row=0, column=1, padx=5, pady=5)
        self.file_button = ttk.Button(self.file_frame, text='Browse', command=self.open_file)
        self.file_button.grid(row=1, column=2, padx=5, pady=5)
        self.go_button = ttk.Button(self.file_frame, text='Go', command=self.create_widgets)
        self.go_button.config(state='disabled')
        self.go_button.grid(row=0, column=2, padx=5, pady=5)

    def open_file(self):
        """ Opens a file dialog to select a CSV file. """
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if file_path:
            self.file_path = file_path  # Store as instance variable
            self.file_entry.delete(0, END)
            self.file_entry.insert(0, file_path)
            # Enable the Go button now that a file is selected
            self.go_button.config(state='normal')

    def create_widgets(self):
        self.file_frame.destroy()  # Remove the file selection frame
        self.notebook = ttk.Notebook(self.root)

        self.notebook.pack(expand=True, fill='both', padx=10, pady=5) # Notebook for tabs
        # Create tabs for different functionalities
        self.create_settings_tab()
        self.create_overview_tab()
        self.create_voltages_tab()
        self.create_temps_tab()

    def create_settings_tab(self):
        self.settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_tab, text='Settings')

        # Voltage Settings Frame
        self.voltage_frame = ttk.LabelFrame(self.settings_tab, text='Voltage Settings', padding=(10, 5))
        self.voltage_frame.grid(row=0, column=0, padx=10, pady=5, sticky='w')
        # Number of rows input
        self.stack_rows_label = ttk.Label(self.voltage_frame, text='Number stacks in a row:')
        self.stack_rows_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.stack_rows_entry = ttk.Entry(self.voltage_frame, width=5)
        self.stack_rows_entry.insert(0, DEFAULT_STACK_ROWS)
        self.stack_rows_entry.grid(row=0, column=1, padx=5, pady=5)
        # Number of stacks input
        self.stack_cols_label = ttk.Label(self.voltage_frame, text='Number stacks in a column:')
        self.stack_cols_label.grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.stack_cols_entry = ttk.Entry(self.voltage_frame, width=5)
        self.stack_cols_entry.insert(0, DEFAULT_STACK_COLS)
        self.stack_cols_entry.grid(row=1, column=1, padx=5, pady=5)
        self.cells_label = ttk.Label(self.voltage_frame, text='Cells per stack:')
        self.cells_label.grid(row=2, column=0, padx=5, pady=5, sticky='w')
        self.cells_entry = ttk.Entry(self.voltage_frame, width=5)
        self.cells_entry.insert(0, DEFAULT_CELLS)
        self.cells_entry.grid(row=2, column=1, padx=5, pady=5)
        self.UV_label = ttk.Label(self.voltage_frame, text='Undervoltage threshold (V):')
        self.UV_label.grid(row=0, column=2, padx=5, pady=5, sticky='w')
        self.UV_entry = ttk.Entry(self.voltage_frame, width=5)
        self.UV_entry.insert(0, DEFAULT_UV)
        self.UV_entry.grid(row=0, column=3, padx=5, pady=5)
        self.OV_label = ttk.Label(self.voltage_frame, text='Overvoltage threshold (V):')
        self.OV_label.grid(row=1, column=2, padx=5, pady=5, sticky='w')
        self.OV_entry = ttk.Entry(self.voltage_frame, width=5)
        self.OV_entry.insert(0, DEFAULT_OV)
        self.OV_entry.grid(row=1, column=3, padx=5, pady=5)

        # Temperature Settings Frame
        self.temp_frame = ttk.LabelFrame(self.settings_tab, text='Temperature Settings', padding=(10, 5))
        self.temp_frame.grid(row=0, column=1, padx=10, pady=5, sticky='nw')
        self.temps_label = ttk.Label(self.temp_frame, text='Number of temp. sensors per stack:')
        self.temps_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.temps_entry = ttk.Entry(self.temp_frame, width=5)
        self.temps_entry.insert(0, DEFAULT_TEMPS)
        self.temps_entry.grid(row=0, column=1, padx=5, pady=5)
        self.UT_label = ttk.Label(self.temp_frame, text='Under-temperature threshold (°C):')
        self.UT_label.grid(row=0, column=2, padx=5, pady=5, sticky='w')
        self.UT_entry = ttk.Entry(self.temp_frame, width=5)
        self.UT_entry.insert(0, DEFAULT_UT)
        self.UT_entry.grid(row=0, column=3, padx=5, pady=5)
        self.OT_label = ttk.Label(self.temp_frame, text='Over-temperature threshold (°C):')
        self.OT_label.grid(row=1, column=2, padx=5, pady=5, sticky='w')
        self.OT_entry = ttk.Entry(self.temp_frame, width=5)
        self.OT_entry.insert(0, DEFAULT_OT)
        self.OT_entry.grid(row=1, column=3, padx=5, pady=5)

        # File Selection Frame
        self.file_view_frame = ttk.LabelFrame(self.settings_tab, text='File Selection', padding=(10, 5))
        self.file_view_frame.grid(row=1, column=0, padx=10, pady=5, sticky='w')
        self.file_label = ttk.Label(self.file_view_frame, text='CSV File:')
        self.file_label.grid(row=0, column=0, padx=5, pady=5)
        self.file_path_label = ttk.Label(self.file_view_frame, text=self.file_path if self.file_path else "No file selected")
        self.file_path_label.grid(row=0, column=1, padx=5, pady=5)

        # Update data from input fields
        def update_data():
            """ Updates the instance variables with the values from the input fields. """
            stack_rows = int(self.stack_rows_entry.get())
            stack_cols = int(self.stack_cols_entry.get())
            cells = int(self.cells_entry.get())
            temps = int(self.temps_entry.get())
            UV = float(self.UV_entry.get())
            OV = float(self.OV_entry.get())
            UT = float(self.UT_entry.get())
            OT = float(self.OT_entry.get())
            read_file(self.file_path, stack_rows, stack_cols, cells, temps)  # Read the CSV file to update data
            self.create_dynamic_widgets(stack_rows, stack_cols, cells, temps)  # Recreate widgets with new settings

        # Confirm Settings Button
        self.confirm_button = ttk.Button(self.settings_tab, text='Confirm Settings', command=update_data)
        self.confirm_button.grid(row=2, column=0, columnspan=4, padx=10, pady=5)

        # Communication Settings Frame
        # self.comm_frame = ttk.LabelFrame(self.settings_tab, text='Communication Settings', padding=(10, 5))
        # self.comm_frame.grid(row=1, column=0, padx=10, pady=5, sticky='w')
        # self.port_label = ttk.Label(self.comm_frame, text='Serial Port:')
        # self.port_label.grid(row=0, column=0, padx=5, pady=5)
        # try:
        #     self.port_var = StringVar(value=self.comms[0])
        #     self.port_option = ttk.OptionMenu(self.comm_frame, self.port_var, self.comms[0], *self.comms)
        # except IndexError:
        #     print("No serial ports found.")
        #     exit(1)
        # self.port_option.grid(row=0, column=1, padx=5, pady=5)
        # self.baudrate_label = ttk.Label(self.comm_frame, text='Baud Rate:')
        # self.baudrate_label.grid(row=1, column=0, padx=5, pady=5)
        # bauds = ['300', '600', '750', '1200', '2400', '4800', '9600', '19200', '28800', '31250', '38400', '57600', '74880', '115200', '230400', '250000', '460800', '500000', '921600', '1000000', '2000000']
        # self.baud_var = StringVar(value=DEFAULT_BAUD)
        # self.baudrate_option = ttk.OptionMenu(self.comm_frame, self.baud_var, DEFAULT_BAUD, *bauds)
        # self.baudrate_option.grid(row=1, column=1, padx=5, pady=5)

    def create_temps_tab(self):
        self.temps_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.temps_tab, text='Temperatures')

        # Create temperatures structure
        self.temps_view_frame = ttk.Frame(self.temps_tab, padding=(10, 5))
        self.temps_view_frame.pack(padx=10, pady=5, fill=BOTH, expand=True)

        # Use a Canvas to enable scrolling
        self.t_canvas = Canvas(self.temps_view_frame, xscrollcommand=None)
        self.t_canvas.pack(side=LEFT, fill=BOTH, expand=True)

        # Vertical scrollbar
        self.t_scrollbar = ttk.Scrollbar(self.temps_view_frame, orient=VERTICAL, command=self.t_canvas.yview)
        self.t_scrollbar.pack(side=RIGHT, fill=Y)
        self.t_canvas.configure(yscrollcommand=self.t_scrollbar.set)

        # Horizontal scrollbar
        self.t_hscrollbar = ttk.Scrollbar(self.temps_view_frame, orient=HORIZONTAL, command=self.t_canvas.xview)
        self.t_hscrollbar.pack(side=BOTTOM, fill=X)
        self.t_canvas.configure(xscrollcommand=self.t_hscrollbar.set)

        self.temps_frame = ttk.Frame(self.t_canvas)
        self.t_canvas.create_window((0, 0), window=self.temps_frame, anchor='nw')

        # Make the canvas scrollable
        def on_frame_configure(event):
            self.t_canvas.configure(scrollregion=self.t_canvas.bbox('all'))
        self.temps_frame.bind('<Configure>', on_frame_configure)

    def create_voltages_tab(self):
        self.voltages_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.voltages_tab, text='Voltages')

        # Create voltages structure
        self.voltage_view_frame = ttk.Frame(self.voltages_tab, padding=(10, 5))
        self.voltage_view_frame.pack(padx=10, pady=5, fill=BOTH, expand=True)

        # Use a Canvas to enable scrolling
        self.v_canvas = Canvas(self.voltage_view_frame, xscrollcommand=None)
        self.v_canvas.pack(side=LEFT, fill=BOTH, expand=True)

        # Vertical scrollbar
        self.v_scrollbar = ttk.Scrollbar(self.voltage_view_frame, orient=VERTICAL, command=self.v_canvas.yview)
        self.v_scrollbar.pack(side=RIGHT, fill=Y)
        self.v_canvas.configure(yscrollcommand=self.v_scrollbar.set)

        # Horizontal scrollbar
        self.v_hscrollbar = ttk.Scrollbar(self.voltage_view_frame, orient=HORIZONTAL, command=self.v_canvas.xview)
        self.v_hscrollbar.pack(side=BOTTOM, fill=X)
        self.v_canvas.configure(xscrollcommand=self.v_hscrollbar.set)

        self.voltages_frame = ttk.Frame(self.v_canvas)
        self.v_canvas.create_window((0, 0), window=self.voltages_frame, anchor='nw')

        # Make the canvas scrollable
        def on_frame_configure(event):
            self.v_canvas.configure(scrollregion=self.v_canvas.bbox('all'))
        self.voltages_frame.bind('<Configure>', on_frame_configure)
        
    def create_overview_tab(self):
        self.overview_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.overview_tab, text='Overview')

        # Overview Frame
        self.overview_frame = ttk.Frame(self.overview_tab, padding=(10, 5))
        self.overview_frame.pack(padx=10, pady=5, fill=BOTH, expand=True)

        self.TPV_frame = ttk.LabelFrame(self.overview_frame, text='Total Pack Voltage', padding=(10, 5))
        self.TPV_frame.grid(row=0, column=0, padx=10, pady=5, sticky='w')
        self.TPV_value = ttk.Label(self.TPV_frame, text='0.00')
        self.TPV_value.grid(row=0, column=0, padx=5, pady=5)
        self.TPV_unit = ttk.Label(self.TPV_frame, text='V')
        self.TPV_unit.grid(row=0, column=1, padx=5, pady=5)
        self.ACV_frame = ttk.LabelFrame(self.overview_frame, text='Average Cell Voltage', padding=(10, 5))
        self.ACV_frame.grid(row=0, column=1, padx=10, pady=5)
        self.ACV_value = ttk.Label(self.ACV_frame, text='0.00')
        self.ACV_value.grid(row=0, column=0, padx=5, pady=5)
        self.ACV_unit = ttk.Label(self.ACV_frame, text='V')
        self.ACV_unit.grid(row=0, column=1, padx=5, pady=5)
        self.ACT_frame = ttk.LabelFrame(self.overview_frame, text='Average Cell Temperature', padding=(10, 5))
        self.ACT_frame.grid(row=0, column=2, padx=10, pady=5)
        self.ACT_value = ttk.Label(self.ACT_frame, text='0.00')
        self.ACT_value.grid(row=0, column=0, padx=5, pady=5)
        self.ACT_unit = ttk.Label(self.ACT_frame, text='°C')
        self.ACT_unit.grid(row=0, column=1, padx=5, pady=5)

    def create_dynamic_widgets(self, stack_rows, stack_cols, cells, temps):
        # Creating voltage widget grid
        for row in range(stack_rows):
            for col in range(stack_cols):
                stack_index = row * stack_cols + col
                stack_frame = ttk.LabelFrame(self.voltages_frame, text=f'Stack {stack_index + 1}')
                stack_frame.grid(row=row, column=col, padx=5, pady=5, sticky='nw')

                for cell in range(cells):
                    cell_label = ttk.Label(stack_frame, text=f'Cell {cell + 1}')
                    cell_label.grid(row=cell, column=0, padx=5, pady=5)
                    cell_voltage = ttk.Label(stack_frame, text=str(round(all_cell_voltages[stack_index][cell][0], 4)) if all_cell_voltages else '0.00')
                    cell_voltage.grid(row=cell, column=1, padx=5, pady=5)
                    cell_plot_button = ttk.Button(stack_frame, text='Plot', command=lambda s=stack_index, c=cell: plot_data(timestamps, all_cell_voltages[s][c], 'Time', 'Voltage', f'Stack {s + 1} Cell {c + 1} Voltage'))
                    cell_plot_button.grid(row=cell, column=2, padx=5, pady=5)
                stack_v_plot_button = ttk.Button(stack_frame, text='Plot All', command=lambda s=stack_index: plot_data(timestamps, all_cell_voltages[s], 'Time', 'Voltage', f'Stack {s + 1} Voltages'))
                stack_v_plot_button.grid(row=cells, column=0, columnspan=3, padx=5, pady=5)

        # Creating temperature widget grid
        for row in range(stack_rows):
            for col in range(stack_cols):
                stack_index = row * stack_cols + col
                stack_frame = ttk.LabelFrame(self.temps_frame, text=f'Stack {stack_index + 1}')
                stack_frame.grid(row=row, column=col, padx=5, pady=5, sticky='nw')

                for temp in range(temps):
                    temp_label = ttk.Label(stack_frame, text=f'Temp. {temp + 1}')
                    temp_label.grid(row=temp, column=0, padx=5, pady=5)
                    temp_value = ttk.Label(stack_frame, text=str(round(all_cell_temps[stack_index][temp][0], 4)) if all_cell_temps else '0.00')
                    temp_value.grid(row=temp, column=1, padx=5, pady=5)
                    temp_plot_button = ttk.Button(stack_frame, text='Plot', command=lambda s=stack_index, t=temp: plot_data(timestamps, all_cell_temps[s][t], 'Time', 'Temperature', f'Stack {s + 1} Temperature {t + 1}'))
                    temp_plot_button.grid(row=temp, column=2, padx=5, pady=5)
                stack_t_plot_button = ttk.Button(stack_frame, text='Plot All', command=lambda s=stack_index: plot_data(timestamps, all_cell_temps[s], 'Time', 'Temperature', f'Stack {s + 1} Temperatures'))
                stack_t_plot_button.grid(row=temps, column=0, columnspan=3, padx=5, pady=5)

def main():
    root = Tk()
    app = BatteryManagementSystem(root)
    root.mainloop()

if __name__ == "__main__":
    main()