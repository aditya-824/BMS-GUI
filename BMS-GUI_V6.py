# LIBRARIES
from tkinter import *
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import filedialog
from ttkthemes import ThemedTk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                               NavigationToolbar2Tk)
import pandas as pd
# import serial
import mplcursors


# CONSTANTS
DEFAULT_STACK_ROWS = 3  # Default number of stacks in a row
DEFAULT_STACK_COLS = 6  # Default number of stacks in a column
DEFAULT_CELLS = 6   # Default number of cells per stack
DEFAULT_TEMPS = 4  # Default number of temperature sensors per stack
DEFAULT_UV = 3.100  # Default undervoltage threshold, in volts
DEFAULT_OV = 4.200  # Default overvoltage threshold, in volts
DEFAULT_UT = 10.0   # Default under-temperature threshold, in degrees Celsius
DEFAULT_OT = 50.0   # Default over-temperature threshold, in degrees Celsius
DEFAULT_BAUD = 115200  # Default baud rate for serial communication
TIMESTAMP_COL = 1  # Column index for timestamp
LAST_CELL_DATA_COL = 181  # Last column index for cell voltage & temp data
SOC_COL = 182
VSBAT_COL = 183
VSHV_COL = 184
CURR_COL = 185


# GLOBAL VARIABLES
all_cell_voltages = []  # List to store all cell voltages
all_cell_temps = []  # List to store all cell temperatures
total_pack_voltage = 0.0  # Total pack voltage
timestamps = []
SoC = []
VsBat = []
VsHV = []
curr = []
num_rows = 0  # Number of rows in the DataFrame
file_name = ''


# FUNCTIONS

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


def read_file(file_path, stack_rows, stack_cols, cells, temps, timestamp_col, SoC_col, VsBat_col, VsHV_col, curr_col):
    """ Reads a CSV file and returns its content as a pandas DataFrame.

        :param file_path: Path to the CSV file.
        :returns: DataFrame containing the CSV data.
    """
    indiv_cell_voltages = []  # List to store individual cell voltages
    indiv_cell_temps = []  # List to store individual cell temperatures
    global timestamps, SoC, VsBat, VsHV, current_converted, num_rows, all_cell_voltages, all_cell_temps

    # Read the CSV file, skipping the second line
    df = pd.read_csv(file_path, header=0, skiprows=[1])

    cols = df.columns.tolist()  # Get the list of column names
    num_rows = 0
    num_rows = len(df.index)  # Get the number of rows in the DataFrame
    # Store timestamps from the first column
    timestamps = df.iloc[:, timestamp_col-1].tolist()
    SoC = df.iloc[:, SoC_col-1].tolist()  # Store SoC data
    VsBat = df.iloc[:, VsBat_col-1].tolist()  # Store VsBat data
    VsHV = df.iloc[:, VsHV_col-1].tolist()  # Store VsHV data
    curr = df.iloc[:, curr_col-1].tolist()  # Store current data
    current_converted = [calc_curr(i)
                         for i in curr]  # Convert current to Amperes

    new_cols = []
    for i in range(timestamp_col, LAST_CELL_DATA_COL, 4):
        group = cols[i:i+4]
        # Reverse the order of each group of 4 columns
        new_cols.extend(group[::-1])
    all_cols = [cols[timestamp_col-1]] + new_cols + cols[LAST_CELL_DATA_COL+1:]
    df_new = df[all_cols]  # Creating new dataframe with reordered columns

    all_cell_temps.clear()  # Clear previous temperature data
    all_cell_voltages.clear()  # Clear previous voltage data
    # Extracting cell voltages and temperatures from the DataFrame
    for stack_data in range(timestamp_col, LAST_CELL_DATA_COL, cells+temps):
        for cell in range(cells):
            indiv_cell_voltages.append(
                df_new.iloc[:, stack_data + cell].tolist())
        all_cell_voltages.append(indiv_cell_voltages)
        indiv_cell_voltages = []  # Reset for the next stack
        for temp in range(temps):
            indiv_cell_temps.append(
                df_new.iloc[:, stack_data + cells + temp].tolist())
        all_cell_temps.append(indiv_cell_temps)
        indiv_cell_temps = []

    # Converting temperature values to Celsius
    for i in range(len(all_cell_temps)):
        for j in range(len(all_cell_temps[i])):
            all_cell_temps[i][j] = [calc_temp(temp)
                                    for temp in all_cell_temps[i][j]]


def plot_data(x, y, x_label, y_label, title, do, type='', top_lim=None, bot_lim=None):
    """ Plots the data using matplotlib.

        :param x: X-axis data (e.g., timestamps).
        :param y: Y-axis data (e.g., cell voltages or temperatures).
        :param x_label: Label for the X-axis.
        :param y_label: Label for the Y-axis.
        :param title: Title of the plot."""

    lines = []
    plt.style.use('Solarize_Light2')
    fig, ax = plt.subplots()

    if (type == 'voltages'):
        if isinstance(y[0], list):  # If y is a list of lists (all cells in a stack)
            for cell_index, voltage in enumerate(y):
                line, = ax.plot(x, voltage,
                                label=f'Cell {cell_index + 1}')
                lines.append(line)
            ax.legend()
        else:
            line, = ax.plot(x, y)
            lines.append(line)
        ax.set_ylim(bottom=0.0, top=5.0)

    elif (type == 'temps'):
        if isinstance(y[0], list):  # If y is a list of lists (all cells in a stack)
            for cell_index, temp in enumerate(y):
                line, = ax.plot(x, temp,
                                label=f'Cell {cell_index + 1}')
                lines.append(line)
            ax.legend()
        else:
            line, = ax.plot(x, y)
            lines.append(line)
        ax.set_ylim(bottom=0.0, top=60.0)

    else:
        line, = ax.plot(x, y)
        lines.append(line)
        ax.set_ylim(bottom=top_lim, top=bot_lim)

    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title)
    ax.grid(True)
    mplcursors.cursor(lines, hover=True)
    if (do == 'show'):
        plt.show()
    else:
        plt.savefig(title + ' ' + file_name.split('.')[0] + '.png')
        plt.close(fig)


def calc_temp(raw_temp):
    """ Calculates the temperature in Celsius from the raw temperature value.

        :param raw_temp: Raw temperature value.
        :returns: Temperature in Celsius.
    """
    r_inf = 10000 * np.exp(-3435 / 298.15)
    R = raw_temp / (3.0 - (raw_temp * 0.0001))  # Calculate resistance
    return ((3435 / np.log(R / r_inf)) - 273.15)  # Convert to Celsius


def calc_curr(raw_curr):
    """ Calculates the current in Amperes from the raw current value.

        :param raw_curr: Raw current value.
        :returns: Current in Amperes.
    """
    # Assuming raw_curr is in mA, convert to A
    voltage = raw_curr * 5.0 / 1023.0
    current = ((voltage - 2.4929) / 0.0057)
    return -current  # Temporary modification to inverse current


def check_status(value, lower, upper):
    """ Checks the status of a value against lower and upper limits.

        :param value: The value to check.
        :param lower: The lower limit.
        :param upper: The upper limit.
        :returns: A string indicating the colour in hex format
    """
    if value < lower:
        return INFO
    elif value > upper:
        return DANGER
    else:
        return SUCCESS


class BatteryManagementSystem:
    def __init__(self, root):
        """ Initializes the Battery Management System GUI.

            :param root: The root Tkinter window.
        """
        self.root = root
        self.root.title("BMS")
        self.root.iconbitmap('icon.ico')

        self.file_path = ""  # Initialize file path as instance variable

        # self.comms = serial_ports() # Searching for available serial ports
        self.create_widgets()
        self.root.geometry("1450x700")

    def create_widgets(self):
        """ Creates the main widgets for the application after file selection. """

        self.notebook = ttk.Notebook(self.root)  # Notebook for tabs
        self.notebook.pack(expand=True, fill='both', padx=10,
                           pady=10)

        # Create tabs for different functionalities
        self.create_settings_tab()
        self.create_overview_tab()
        self.create_voltages_tab()
        self.create_temps_tab()

    def open_file(self):
        """ Opens a file dialog to select a CSV file. """

        file_path = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv")])
        if file_path:
            self.file_path = file_path  # Store as instance variable
            self.file_entry.delete(0, END)
            self.file_entry.insert(0, file_path)
            # Enable the Confirm Settings button now that a file is selected
            self.confirm_button.config(state='normal')

    def create_settings_tab(self):
        """ Creates the settings tab with input fields for voltage and temperature settings. """

        self.settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_tab, text='Settings')

        # Voltage Settings Frame
        self.voltage_frame = ttk.LabelFrame(
            self.settings_tab, text='Voltage Settings', padding=(10, 5))
        self.voltage_frame.grid(
            row=0, column=0, padx=10, pady=5, sticky='nsew')
        # Number of rows input
        self.stack_rows_label = ttk.Label(
            self.voltage_frame, text='Number stacks in a row:')
        self.stack_rows_label.grid(
            row=0, column=0, padx=5, pady=5, sticky='e')
        self.stack_rows_entry = ttk.Entry(self.voltage_frame, width=5)
        self.stack_rows_entry.insert(0, DEFAULT_STACK_ROWS)
        self.stack_rows_entry.grid(row=0, column=1, padx=5, pady=5)
        # Number of stacks input
        self.stack_cols_label = ttk.Label(
            self.voltage_frame, text='Number stacks in a column:')
        self.stack_cols_label.grid(
            row=1, column=0, padx=5, pady=5, sticky='e')
        self.stack_cols_entry = ttk.Entry(self.voltage_frame, width=5)
        self.stack_cols_entry.insert(0, DEFAULT_STACK_COLS)
        self.stack_cols_entry.grid(row=1, column=1, padx=5, pady=5)
        # Cells per stack input
        self.cells_label = ttk.Label(
            self.voltage_frame, text='Cells per stack:')
        self.cells_label.grid(row=2, column=0, padx=5, pady=5, sticky='e')
        self.cells_entry = ttk.Entry(self.voltage_frame, width=5)
        self.cells_entry.insert(0, DEFAULT_CELLS)
        self.cells_entry.grid(row=2, column=1, padx=5, pady=5)
        # Voltage thresholds input
        self.UV_label = ttk.Label(
            self.voltage_frame, text='Undervoltage threshold (V):')
        self.UV_label.grid(row=0, column=2, padx=5, pady=5, sticky='e')
        self.UV_entry = ttk.Entry(self.voltage_frame, width=5)
        self.UV_entry.insert(0, DEFAULT_UV)
        self.UV_entry.grid(row=0, column=3, padx=5, pady=5)
        self.OV_label = ttk.Label(
            self.voltage_frame, text='Overvoltage threshold (V):')
        self.OV_label.grid(row=1, column=2, padx=5, pady=5, sticky='e')
        self.OV_entry = ttk.Entry(self.voltage_frame, width=5)
        self.OV_entry.insert(0, DEFAULT_OV)
        self.OV_entry.grid(row=1, column=3, padx=5, pady=5)

        # Temperature Settings Frame
        self.temp_frame = ttk.LabelFrame(
            self.settings_tab, text='Temperature Settings', padding=(10, 5))
        self.temp_frame.grid(row=0, column=1, padx=10, pady=5, sticky='nsew')
        # Number of temperature sensors input
        self.temps_label = ttk.Label(
            self.temp_frame, text='Number of temp. sensors per stack:')
        self.temps_label.grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.temps_entry = ttk.Entry(self.temp_frame, width=5)
        self.temps_entry.insert(0, DEFAULT_TEMPS)
        self.temps_entry.grid(row=0, column=1, padx=5, pady=5)
        # Temperature thresholds input
        self.UT_label = ttk.Label(
            self.temp_frame, text='Under-temperature threshold (°C):')
        self.UT_label.grid(row=0, column=2, padx=5, pady=5, sticky='e')
        self.UT_entry = ttk.Entry(self.temp_frame, width=5)
        self.UT_entry.insert(0, DEFAULT_UT)
        self.UT_entry.grid(row=0, column=3, padx=5, pady=5)
        self.OT_label = ttk.Label(
            self.temp_frame, text='Over-temperature threshold (°C):')
        self.OT_label.grid(row=1, column=2, padx=5, pady=5, sticky='e')
        self.OT_entry = ttk.Entry(self.temp_frame, width=5)
        self.OT_entry.insert(0, DEFAULT_OT)
        self.OT_entry.grid(row=1, column=3, padx=5, pady=5)

        # File Selection Frame
        self.file_frame = ttk.LabelFrame(
            self.settings_tab, text='File Selection', padding=(10, 5))
        self.file_frame.grid(row=1, column=0, padx=10, pady=5)
        # File name
        self.file_label = ttk.Label(self.file_frame, text='CSV File:')
        self.file_label.grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.file_entry = ttk.Entry(self.file_frame, width=60)
        self.file_entry.grid(row=0, column=1, padx=5, pady=5)
        # Browse button
        self.file_button = ttk.Button(
            self.file_frame, text='Browse', command=self.open_file)
        self.file_button.grid(row=0, column=2, padx=5, pady=5)
        # Column entries
        self.columns_frame = ttk.LabelFrame(
            self.file_frame, text='Data Columns:')
        self.columns_frame.grid(
            row=1, column=0, columnspan=3, padx=5, pady=5, sticky='ew')
        # Timestamps
        self.timestamps_label = ttk.Label(
            self.columns_frame, text='Timestamps:')
        self.timestamps_label.grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.timestamps_entry = ttk.Entry(self.columns_frame, width=5)
        self.timestamps_entry.insert(0, TIMESTAMP_COL)
        self.timestamps_entry.grid(row=0, column=1, padx=5, pady=5)
        # SoC
        self.SoC_label = ttk.Label(self.columns_frame, text='SoC:')
        self.SoC_label.grid(row=0, column=2, padx=5, pady=5, sticky='e')
        self.SoC_entry = ttk.Entry(self.columns_frame, width=5)
        self.SoC_entry.insert(0, SOC_COL)
        self.SoC_entry.grid(row=0, column=3, padx=5, pady=5)
        # VsBat
        self.VsBat_label = ttk.Label(self.columns_frame, text='VsBat:')
        self.VsBat_label.grid(row=0, column=4, padx=5, pady=5, sticky='e')
        self.VsBat_entry = ttk.Entry(self.columns_frame, width=5)
        self.VsBat_entry.insert(0, VSBAT_COL)
        self.VsBat_entry.grid(row=0, column=5, padx=5, pady=5)
        # VsHV
        self.VsHV_label = ttk.Label(self.columns_frame, text='VsHV:')
        self.VsHV_label.grid(row=0, column=6, padx=5, pady=5, sticky='e')
        self.VsHV_entry = ttk.Entry(self.columns_frame, width=5)
        self.VsHV_entry.insert(0, VSHV_COL)
        self.VsHV_entry.grid(row=0, column=7, padx=5, pady=5)
        # Current
        self.current_label = ttk.Label(self.columns_frame, text='Current:')
        self.current_label.grid(row=0, column=8, padx=5, pady=5, sticky='e')
        self.current_entry = ttk.Entry(self.columns_frame, width=5)
        self.current_entry.insert(0, CURR_COL)
        self.current_entry.grid(row=0, column=9, padx=5, pady=5)

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

        # Update data from input fields
        def update_data():
            """ Updates the instance variables with the values from the input fields. """

            self.root.title("BMS - Loading...")
            stack_rows = int(self.stack_rows_entry.get())
            stack_cols = int(self.stack_cols_entry.get())
            cells = int(self.cells_entry.get())
            temps = int(self.temps_entry.get())
            UV = float(self.UV_entry.get())
            OV = float(self.OV_entry.get())
            UT = float(self.UT_entry.get())
            OT = float(self.OT_entry.get())
            timestamp_col = int(self.timestamps_entry.get())
            SoC_col = int(self.SoC_entry.get())
            VsBat_col = int(self.VsBat_entry.get())
            VsHV_col = int(self.VsHV_entry.get())
            curr_col = int(self.current_entry.get())

            read_file(self.file_path, stack_rows, stack_cols, cells,
                      # Read the CSV file to update data
                      temps, timestamp_col, SoC_col, VsBat_col, VsHV_col, curr_col)
            self.create_dynamic_widgets(
                stack_rows, stack_cols, cells, temps, UV, OV, UT, OT)

        # Confirm Settings Button
        self.confirm_button = ttk.Button(
            self.settings_tab, text='Confirm & Launch', command=update_data)
        # Initially disabled until a file is selected
        self.confirm_button.config(state='disabled')
        self.confirm_button.grid(
            row=2, column=0, columnspan=2, padx=10, pady=5, sticky='')

    def create_temps_tab(self):
        """ Creates the temperatures tab with a scrollable view for temperature data. """

        self.temps_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.temps_tab, text='Temperatures')

        # Create temperatures structure
        self.temps_view_frame = ttk.Frame(self.temps_tab, padding=(10, 5))
        self.temps_view_frame.pack(padx=10, pady=5, fill=BOTH, expand=True)

        # Use a Canvas to enable scrolling
        self.t_canvas = Canvas(self.temps_view_frame, xscrollcommand=None)
        self.t_canvas.pack(side=LEFT, fill=BOTH, expand=True)

        # Vertical scrollbar
        self.t_scrollbar = ttk.Scrollbar(
            self.temps_view_frame, orient=VERTICAL, command=self.t_canvas.yview)
        self.t_scrollbar.pack(side=RIGHT, fill=Y)
        self.t_canvas.configure(yscrollcommand=self.t_scrollbar.set)

        # Horizontal scrollbar
        self.t_hscrollbar = ttk.Scrollbar(
            self.temps_view_frame, orient=HORIZONTAL, command=self.t_canvas.xview)
        self.t_hscrollbar.pack(side=BOTTOM, fill=X)
        self.t_canvas.configure(xscrollcommand=self.t_hscrollbar.set)

        self.temps_frame = ttk.Frame(self.t_canvas)
        self.t_canvas.create_window(
            (0, 0), window=self.temps_frame, anchor='nw')

        # Make the canvas scrollable
        def on_frame_configure(event):
            self.t_canvas.configure(scrollregion=self.t_canvas.bbox('all'))
            self.t_canvas.xview_moveto(0)
            self.t_canvas.yview_moveto(0)
        self.temps_frame.bind('<Configure>', on_frame_configure)

    def create_voltages_tab(self):
        """ Creates the voltages tab with a scrollable view for voltage data. """

        self.voltages_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.voltages_tab, text='Voltages')

        # Create voltages structure
        self.voltages_view_frame = ttk.Frame(
            self.voltages_tab, padding=(10, 5))
        self.voltages_view_frame.pack(padx=10, pady=5, fill=BOTH, expand=True)

        # Use a Canvas to enable scrolling
        self.v_canvas = Canvas(self.voltages_view_frame, xscrollcommand=None)
        self.v_canvas.pack(side=LEFT, fill=BOTH, expand=True)

        # Vertical scrollbar
        self.v_scrollbar = ttk.Scrollbar(
            self.voltages_view_frame, orient=VERTICAL, command=self.v_canvas.yview)
        self.v_scrollbar.pack(side=RIGHT, fill=Y)
        self.v_canvas.configure(yscrollcommand=self.v_scrollbar.set)

        # Horizontal scrollbar
        self.v_hscrollbar = ttk.Scrollbar(
            self.voltages_view_frame, orient=HORIZONTAL, command=self.v_canvas.xview)
        self.v_hscrollbar.pack(side=BOTTOM, fill=X)
        self.v_canvas.configure(xscrollcommand=self.v_hscrollbar.set)

        self.voltages_frame = ttk.Frame(self.v_canvas)
        self.v_canvas.create_window(
            (0, 0), window=self.voltages_frame, anchor='nw')

        # Make the canvas scrollable
        def on_frame_configure(event):
            self.v_canvas.configure(scrollregion=self.v_canvas.bbox('all'))
            self.v_canvas.xview_moveto(0)
            self.v_canvas.yview_moveto(0)
        self.voltages_frame.bind('<Configure>', on_frame_configure)

    def create_overview_tab(self):
        """ Creates the overview tab with summary information about the battery system. """

        self.overview_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.overview_tab, text='Overview')

        # --- Add vertical and horizontal scrollbars using Canvas ---
        self.overview_view_frame = ttk.Frame(
            self.overview_tab, padding=(10, 5))
        self.overview_view_frame.pack(padx=10, pady=5, fill=BOTH, expand=True)

        # Canvas for scrollable content
        self.o_canvas = Canvas(self.overview_view_frame, borderwidth=0)
        self.o_canvas.pack(side=LEFT, fill=BOTH, expand=True)

        # Vertical scrollbar
        self.o_scrollbar = ttk.Scrollbar(
            self.overview_view_frame, orient=VERTICAL, command=self.o_canvas.yview)
        self.o_scrollbar.pack(side=RIGHT, fill=Y)
        self.o_canvas.configure(yscrollcommand=self.o_scrollbar.set)

        # Horizontal scrollbar
        self.o_hscrollbar = ttk.Scrollbar(
            self.overview_view_frame, orient=HORIZONTAL, command=self.o_canvas.xview)
        self.o_hscrollbar.pack(side=BOTTOM, fill=X)
        self.o_canvas.configure(xscrollcommand=self.o_hscrollbar.set)

        # Frame inside canvas for actual content
        self.overview_frame = ttk.Frame(self.o_canvas)
        self.o_canvas.create_window(
            (0, 0), window=self.overview_frame, anchor='nw')

        # Make the canvas scrollable
        def on_frame_configure(event):
            self.o_canvas.configure(scrollregion=self.o_canvas.bbox('all'))
            self.o_canvas.xview_moveto(0)
            self.o_canvas.yview_moveto(0)
        self.overview_frame.bind('<Configure>', on_frame_configure)

    def create_dynamic_widgets(self, stack_rows, stack_cols, cells, temps, UV, OV, UT, OT):
        """ Creates dynamic widgets for voltages and temperatures based on user input.

            :param stack_rows: Number of rows of stacks.
            :param stack_cols: Number of columns of stacks.
            :param cells: Number of cells per stack.
            :param temps: Number of temperature sensors per stack.
        """
        global total_pack_voltage, SoC, VsBat, VsHV, current_converted, red, blue, green, num_rows, file_name
        total_pack_voltage = 0.0  # Reset total pack voltage
        avg_stack_voltages = []  # List to store average stack voltages

        # Clear previous widgets in voltages and temperatures frames
        for widget in self.voltages_frame.winfo_children():
            widget.destroy()
        for widget in self.temps_frame.winfo_children():
            widget.destroy()

        def save_graphs(stack_rows, stack_cols, x, y, x_label, y_label, type):
            """ Saves the current graphs to files.

                :param title: The title to use for the saved files.
            """
            self.root.title("BMS - Saving Graphs...")
            for stack_index in range(stack_rows * stack_cols):
                if (type == 'voltages'):
                    plot_data(x, y[stack_index], x_label, y_label,
                              f'Stack {stack_index+1} Voltages', 'save', type)
                else:
                    plot_data(x, y[stack_index], x_label, y_label,
                              f'Stack {stack_index+1} Temperatures', 'save', type)
            self.root.title(f"BMS - {file_name}")

        # Creating voltage widget grid
        for row in range(stack_rows):
            for col in range(stack_cols):
                stack_index = row * stack_cols + col
                stack_frame = ttk.LabelFrame(
                    self.voltages_frame, text=f'Stack {stack_index + 1}')
                stack_frame.grid(row=row, column=col,
                                 padx=5, pady=5, sticky='nw')

                total_stack_voltage = 0.0  # Reset total stack voltage for each stack
                for cell in range(cells):
                    # Cell voltages with plot buttons
                    cell_button = ttk.Button(stack_frame, text=f'Cell {cell + 1}', command=lambda s=stack_index, c=cell: plot_data(
                        timestamps, all_cell_voltages[s][c], 'Time (s)', 'Voltage (V)', f'Stack {s + 1} Cell {c + 1} Voltage', 'show', 'voltages'))
                    cell_button.grid(row=cell, column=0, padx=5, pady=5)
                    avg_cell_voltage = np.mean(
                        all_cell_voltages[stack_index][cell])
                    total_stack_voltage += avg_cell_voltage
                    cell_voltage_label = ttk.Label(
                        stack_frame, text=round(
                            avg_cell_voltage, 4), bootstyle=check_status(avg_cell_voltage, UV, OV))
                    cell_voltage_label.grid(row=cell, column=1, padx=5, pady=5)
                    voltage_unit = ttk.Label(stack_frame, text='V')
                    voltage_unit.grid(row=cell, column=2, padx=5, pady=5)

                avg_stack_voltages.append(total_stack_voltage)
                total_pack_voltage += total_stack_voltage

                # Plot all button
                stack_v_plot_button = ttk.Button(stack_frame, text='Plot All', command=lambda s=stack_index: plot_data(
                    timestamps, all_cell_voltages[s], 'Time (s)', 'Voltage (V)', f'Stack {s + 1} Voltages', 'show', 'voltages'))
                stack_v_plot_button.grid(
                    row=cells, column=0, columnspan=2, padx=5, pady=5)
        save_v_graphs_button = ttk.Button(
            self.voltages_frame, text='Save Stack Voltage Graphs', command=lambda: save_graphs(stack_rows, stack_cols, timestamps, all_cell_voltages, 'Time (s)', 'Voltage (V)', 'voltages'))
        save_v_graphs_button.grid(
            row=stack_rows, column=0, columnspan=stack_cols, padx=5, pady=5, sticky='ew')

        # Creating temperature widget grid
        for row in range(stack_rows):
            for col in range(stack_cols):
                stack_index = row * stack_cols + col
                stack_frame = ttk.LabelFrame(
                    self.temps_frame, text=f'Stack {stack_index + 1}')
                stack_frame.grid(row=row, column=col,
                                 padx=5, pady=5, sticky='nw')

                avg_cell_temps = []  # List to store average cell temperatures for the stack
                for temp in range(temps):
                    # Cell temperatures with plot buttons
                    temp_button = ttk.Button(
                        stack_frame, text=f'Temp. {temp + 1}', command=lambda s=stack_index, t=temp: plot_data(
                            timestamps, all_cell_temps[s][t], 'Time (s)', 'Temperature (°C)', f'Stack {s + 1} Temperature {t + 1}', 'show', 'temps'))
                    temp_button.grid(row=temp, column=0, padx=5, pady=5)
                    avg_cell_temp = np.mean(
                        all_cell_temps[stack_index][temp])
                    avg_cell_temps.append(avg_cell_temp)
                    temp_value = ttk.Label(stack_frame, text=round(
                        avg_cell_temp, 4), bootstyle=check_status(avg_cell_temp, UT, OT))
                    temp_value.grid(row=temp, column=1, padx=5, pady=5)
                    temp_unit = ttk.Label(stack_frame, text='°C')
                    temp_unit.grid(row=temp, column=2, padx=5, pady=5)
                # Temp delta
                temp_delta_label = ttk.Label(stack_frame, text='Delta:')
                temp_delta_label.grid(
                    row=temps, column=0, padx=5, pady=5, sticky='e')
                temp_delta_value = ttk.Label(stack_frame, text=(round(
                    max(all_cell_temps[stack_index][0]) - all_cell_temps[stack_index][0][0], 4)))
                temp_delta_value.grid(row=temps, column=1, padx=5, pady=5)
                temp_delta_unit = ttk.Label(stack_frame, text='°C')
                temp_delta_unit.grid(row=temps, column=2, padx=5, pady=5)
                # Plot all button
                stack_t_plot_button = ttk.Button(stack_frame, text='Plot All', command=lambda s=stack_index: plot_data(
                    timestamps, all_cell_temps[s], 'Time (s)', 'Temperature (°C)', f'Stack {s + 1} Temperatures', 'show', 'temps'))
                stack_t_plot_button.grid(
                    row=temps+1, column=0, columnspan=3, padx=5, pady=5)
        save_t_graphs_button = ttk.Button(
            self.temps_frame, text='Save Stack Temp. Graphs', command=lambda: save_graphs(stack_rows, stack_cols, timestamps, all_cell_temps, 'Time (s)', 'Temperature (°C)', 'temps'))
        save_t_graphs_button.grid(
            row=stack_rows, column=0, columnspan=stack_cols, padx=5, pady=5, sticky='ew')

        # Filling overview tab
        # Plots
        self.plot_frame = ttk.Frame(
            self.overview_frame, padding=(2, 2))
        self.plot_frame.grid(row=0, column=0, sticky='nw')

        def overview_plots(ro, col, data, title, unit, top_lim=None, bot_lim=None):
            """ Creates a plot in the overview tab.

                :param ro: Row index for the plot.
                :param col: Column index for the plot.
                :param data: Data to plot.
                :param title: Title for the plot.
            """
            sub_plot_frame = ttk.Frame(self.plot_frame)
            sub_plot_frame.grid(row=ro, column=col, padx=2, pady=2)
            plt.style.use('Solarize_Light2')  # Use dark background style
            fig, ax = plt.subplots(figsize=(6, 4.2))
            canvas = FigureCanvasTkAgg(fig, master=sub_plot_frame)
            canvas.get_tk_widget().grid(row=0, column=0, padx=2, pady=2)
            ax.plot(timestamps, data)
            ax.set_xlabel('Time (s)')
            ax.set_ylabel(f'{title} ({unit})')
            ax.set_title(title)
            ax.set_ylim(top=top_lim, bottom=bot_lim)
            ax.grid(True)
            mplcursors.cursor(hover=True)
            canvas.draw()
            plt.close(fig)
            expand_button = ttk.Button(
                sub_plot_frame, text='Expand', command=lambda: plot_data(
                    timestamps, data, 'Time (s)', f'{title} ({unit})', title, 'show', top_lim, bot_lim))
            expand_button.grid(row=1, column=0, padx=2, pady=8, sticky='new')

        # SoC
        # overview_plots(0, 0, SoC, 'State of Charge', '%')
        # VsBat
        # overview_plots(0, 1, VsBat, 'VsBat', 'V')
        # VsHV
        # overview_plots(1, 0, VsHV, 'VsHV', 'V')
        # Current
        overview_plots(0, 0, current_converted, 'Current', 'A')
        # Total Pack Voltage
        total_pack_voltage_arr = []  # List to store total pack voltages for plotting
        total_pack_voltage_arr.clear()  # Clear previous data
        temp_stack_voltage = 0.0  # Reset temp stack voltage
        temp_pack_voltage = 0.0  # Reset temp pack voltage
        for row in range(num_rows):
            for stack in range(stack_rows * stack_cols):
                for cell in range(cells):
                    temp_stack_voltage += all_cell_voltages[stack][cell][row]
                temp_pack_voltage += temp_stack_voltage
                temp_stack_voltage = 0.0
            total_pack_voltage_arr.append(temp_pack_voltage)
            temp_pack_voltage = 0.0
        overview_plots(0, 1, total_pack_voltage_arr,
                       'Total Pack Voltage', 'V', 453.6, 270)

        # Data & Stacks frame
        self.d_n_s_frame = ttk.Frame(self.overview_frame, padding=(10, 5))
        self.d_n_s_frame.grid(row=0, column=1, padx=10, pady=5, sticky='nw')
        # Data
        self.data_frame = ttk.LabelFrame(
            self.d_n_s_frame, text="Data", padding=(10, 5))
        self.data_frame.grid(row=0, column=0, padx=10, pady=5, sticky='n')
        # Total pack voltage
        self.TPV_label = ttk.Label(
            self.data_frame, text='Total Pack Voltage:')
        self.TPV_label.grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.TPV_value = ttk.Label(
            self.data_frame, text=round(total_pack_voltage, 4))
        self.TPV_value.grid(row=0, column=1, padx=5, pady=5, sticky='')
        self.TPV_unit = ttk.Label(self.data_frame, text='V')
        self.TPV_unit.grid(row=0, column=2, padx=5, pady=5, sticky='w')
        # Average cell voltage
        self.ACV_label = ttk.Label(
            self.data_frame, text='Avg. Cell Voltage:')
        self.ACV_label.grid(row=1, column=0, padx=5, pady=5, sticky='e')
        fullpack_avg_cell_voltage = np.mean([np.mean(voltage)
                                             for voltage in all_cell_voltages])
        self.ACV_value = ttk.Label(
            self.data_frame, text=round(fullpack_avg_cell_voltage, 4))
        self.ACV_value.grid(row=1, column=1, padx=5, pady=5)
        self.ACV_unit = ttk.Label(self.data_frame, text='V')
        self.ACV_unit.grid(row=1, column=2, padx=5, pady=5)
        # Average cell temperature
        self.ACT_label = ttk.Label(
            self.data_frame, text='Avg. Cell Temp.:')
        self.ACT_label.grid(row=2, column=0, padx=10, pady=5, sticky='e')
        fullpack_avg_cell_temp = np.mean(
            [np.mean(temp) for temp in all_cell_temps])
        self.ACT_value = ttk.Label(
            self.data_frame, text=round(fullpack_avg_cell_temp, 4))
        self.ACT_value.grid(row=2, column=1, padx=5, pady=5)
        self.ACT_unit = ttk.Label(self.data_frame, text='°C')
        self.ACT_unit.grid(row=2, column=2, padx=5, pady=5)
        # Highest cell temperature
        max_cell_temps = []
        self.HCT_label = ttk.Label(
            self.data_frame, text='Highest Cell Temp.:')
        self.HCT_label.grid(row=3, column=0, padx=10, pady=5, sticky='e')
        for stack_index in range(stack_rows * stack_cols):
            for temp in range(temps):
                max_cell_temps.append(max(all_cell_temps[stack_index][temp]))
        self.HCT_value = ttk.Label(
            self.data_frame, text=round(max(max_cell_temps), 4))
        self.HCT_value.grid(row=3, column=1, padx=5, pady=5)
        self.HCT_unit = ttk.Label(self.data_frame, text='°C')
        self.HCT_unit.grid(row=3, column=2, padx=5, pady=5, sticky='w')
        # Average stack voltages
        self.ASV_frame = ttk.LabelFrame(
            self.d_n_s_frame, text='Average Stack Voltages', padding=(10, 5))
        self.ASV_frame.grid(row=1, column=0, padx=10, pady=5, sticky='nw')
        for stack_index in range(stack_rows * stack_cols):
            self.stack_label = ttk.Label(
                self.ASV_frame, text=f'Stack {stack_index + 1}:')
            self.stack_label.grid(row=stack_index, column=0,
                                  padx=5, pady=5, sticky='e')
            self.stack_value = ttk.Label(
                self.ASV_frame, text=round(avg_stack_voltages[stack_index], 4))
            self.stack_value.grid(row=stack_index, column=1, padx=5, pady=5)
            self.stack_unit = ttk.Label(self.ASV_frame, text='V')
            self.stack_unit.grid(row=stack_index, column=2, padx=5, pady=5)

        # Get the file name from the path
        file_name = self.file_path.split('/')[-1]
        # Update window title with file name
        self.root.title(f"BMS - {file_name}")


def main():
    root = ttk.Window(themename="vapor")
    # style=ttk.Style()
    # print(style.theme_names())
    BatteryManagementSystem(root)
    root.mainloop()


if __name__ == "__main__":
    main()
