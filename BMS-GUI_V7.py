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
import serial
import mplcursors
import threading


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


# GLOBAL VARIABLES
serial_values = ['0.0' for _ in range(108)]  # Placeholder for serial data
serial_running = False


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


def check_status(value, lower, upper):
    """ Checks the status of a value against lower and upper limits.

        :param value: The value to check.
        :param lower: The lower limit.
        :param upper: The upper limit.
        :returns: A string indicating the colour in hex format
    """
    value = float(value)
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
        self.root.title("ORI BMS")
        self.root.iconbitmap('icon.ico')

        notebook = ttk.Notebook(self.root)  # Notebook for tabs
        notebook.pack(expand=True, fill='both', padx=10,
                      pady=10)

        # Create tabs for different functionalities
        self.create_settings_tab(notebook)
        # self.create_overview_tab(notebook)
        self.create_voltages_tab(notebook)
        # self.create_temps_tab(notebook)
        self.root.geometry("1450x700")
        self.serial_values = serial_values

    def start_serial_read(self):
        # Open serial port and start thread
        port = self.port_var.get()
        try:
            self.serial_port = serial.Serial(port, DEFAULT_BAUD, timeout=1)
            self.serial_running = True
            self.serial_thread = threading.Thread(
                target=self.read_serial_data, daemon=True)
            self.serial_thread.start()
        except Exception as e:
            print(f"Error opening serial port: {e}")

    def read_serial_data(self):
        while self.serial_running:
            try:
                line = self.serial_port.readline().decode('utf-8').rstrip()
                if line:
                    values = line.split(', ')
                    for i, val in enumerate(values):
                        if i < len(self.serial_values):
                            self.root.after(
                                0, self.serial_values.__setitem__, i, val)
            except Exception as e:
                print(f"Serial read error: {e}")

    def create_settings_tab(self, notebook):
        """ Creates the settings tab with input fields for comm settings. """

        settings_tab = ttk.Frame(notebook)
        notebook.add(settings_tab, text='Settings')

        # Communication Settings Frame
        comm_frame = ttk.LabelFrame(
            settings_tab, text='Communication Settings', padding=(10, 5))
        comm_frame.grid(row=0, column=0, padx=10, pady=5)
        port_label = ttk.Label(comm_frame, text='Serial Port:')
        port_label.grid(row=0, column=0, padx=5, pady=5)
        self.port_var = StringVar()
        port_option = ttk.OptionMenu(comm_frame, self.port_var, '')
        port_option.grid(row=0, column=1, padx=5, pady=5)

        def update_ports():
            def worker():
                self.port_var.set('Scanning...')
                ports = serial_ports()

                def update_menu():
                    menu = port_option['menu']
                    menu.delete(0, 'end')
                    if ports:
                        for port in ports:
                            menu.add_command(
                                label=port, command=lambda value=port: self.port_var.set(value))
                        self.port_var.set(ports[0])
                        self.confirm_button.config(state='enabled')
                    else:
                        menu.add_command(
                            label='No ports found', command=lambda: self.port_var.set('No ports found'))
                        self.port_var.set('No ports found')
                        self.confirm_button.config(state='disabled')
                self.root.after(0, update_menu)
            threading.Thread(target=worker, daemon=True).start()

        update_ports()

        refresh_button = ttk.Button(
            comm_frame, text='Refresh', command=update_ports)
        refresh_button.grid(row=0, column=2, padx=5, pady=5)
        baudrate_label = ttk.Label(comm_frame, text='Baud Rate:')
        baudrate_label.grid(row=1, column=0, padx=5, pady=5)
        bauds = ['300', '600', '750', '1200', '2400', '4800', '9600', '19200', '28800', '31250', '38400',
                 '57600', '74880', '115200', '230400', '250000', '460800', '500000', '921600', '1000000', '2000000']
        self.baud_var = StringVar(value=DEFAULT_BAUD)
        baudrate_option = ttk.OptionMenu(
            comm_frame, self.baud_var, DEFAULT_BAUD, *bauds)
        baudrate_option.grid(row=1, column=1, padx=5, pady=5)

        # Confirm Settings Button
        self.confirm_button = ttk.Button(
            settings_tab, text='Confirm & Launch', command=self.confirm_settings)
        # Disabled until a port is found
        self.confirm_button.config(state='disabled')
        self.confirm_button.grid(
            row=2, column=0, columnspan=2, padx=10, pady=5)

    def create_overview_tab(self, notebook):
        """ Creates the overview tab with summary information. """

        overview_tab = ttk.Frame(notebook)
        notebook.add(overview_tab, text='Overview')

        # --- Add vertical and horizontal scrollbars using Canvas ---
        overview_view_frame = ttk.Frame(
            overview_tab, padding=(10, 5))
        overview_view_frame.pack(padx=10, pady=5, fill=BOTH, expand=True)

        # Canvas for scrollable content
        o_canvas = Canvas(overview_view_frame, borderwidth=0)
        o_canvas.pack(side=LEFT, fill=BOTH, expand=True)

        # Vertical scrollbar
        o_scrollbar = ttk.Scrollbar(
            overview_view_frame, orient=VERTICAL, command=o_canvas.yview)
        o_scrollbar.pack(side=RIGHT, fill=Y)
        o_canvas.configure(yscrollcommand=o_scrollbar.set)

        # Horizontal scrollbar
        o_hscrollbar = ttk.Scrollbar(
            overview_view_frame, orient=HORIZONTAL, command=o_canvas.xview)
        o_hscrollbar.pack(side=BOTTOM, fill=X)
        o_canvas.configure(xscrollcommand=o_hscrollbar.set)

        # Frame inside canvas for actual content
        overview_frame = ttk.Frame(o_canvas)
        o_canvas.create_window(
            (0, 0), window=overview_frame, anchor='nw')

        # Make the canvas scrollable
        def on_frame_configure(event):
            o_canvas.configure(scrollregion=o_canvas.bbox('all'))
            o_canvas.xview_moveto(0)
            o_canvas.yview_moveto(0)
        overview_frame.bind('<Configure>', on_frame_configure)

        # CAN
        can_frame = ttk.LabelFrame(
            overview_frame, padding=(10, 5), text='CAN Status')
        can_frame.grid(row=0, column=1, padx=10, pady=5, sticky='nw')
        can_status_label = ttk.Label(can_frame, text='Initialization status: ')
        can_status_label.grid(row=0, column=0, padx=5, pady=5, sticky='e')
        data_sent_label = ttk.Label(can_frame, text='Data status: ')
        data_sent_label.grid(row=1, column=0, padx=5, pady=5, sticky='e')
        can_status = ttk.Label(can_frame, text='-')
        can_status.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        data_sent = ttk.Label(can_frame, text='-')
        data_sent.grid(row=1, column=1, padx=5, pady=5, sticky='w')

        # Charging
        charger_status = serial_values[0]
        charging_frame = ttk.LabelFrame(
            overview_frame, padding=(10, 5), text='Charging Status')
        charging_frame.grid(row=0, column=0, padx=10, pady=5, sticky='nw')
        charger_status_label = ttk.Label(
            charging_frame, text='Charger status: ')
        charger_status_label.grid(row=0, column=0, padx=5, pady=5, sticky='e')
        charging_status_label = ttk.Label(
            charging_frame, text="Charging status: ")
        charging_status_label.grid(row=1, column=0, padx=5, pady=5, sticky='e')
        charger_status_val = ttk.Label(charging_frame, text='-')
        charger_status_val.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        charging_status_val = ttk.Label(charging_frame, text="-")
        charging_status_val.grid(row=1, column=1, padx=5, pady=5, sticky='w')

        # Min/Max Voltages
        voltage_frame = ttk.LabelFrame(
            overview_frame, padding=(10, 5), text='Voltage Status')
        voltage_frame.grid(row=1, column=0, padx=10, pady=5, sticky='nw')
        min_voltage_label = ttk.Label(voltage_frame, text="Min Voltage: ")
        min_voltage_label.grid(row=0, column=0, padx=5, pady=5, sticky='e')
        max_voltage_label = ttk.Label(voltage_frame, text="Max Voltage: ")
        max_voltage_label.grid(row=1, column=0, padx=5, pady=5, sticky='e')
        min_voltage = ttk.Label(voltage_frame, text="-")
        min_voltage.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        max_voltage = ttk.Label(voltage_frame, text="-")
        max_voltage.grid(row=1, column=1, padx=5, pady=5, sticky='w')

        # Min/Max Temperatures
        temp_frame = ttk.LabelFrame(
            overview_frame, padding=(10, 5), text='Temperature Status')
        temp_frame.grid(row=1, column=1, padx=10, pady=5, sticky='nw')
        min_temp_label = ttk.Label(temp_frame, text="Min Temperature: ")
        min_temp_label.grid(row=0, column=0, padx=5, pady=5)
        max_temp_label = ttk.Label(temp_frame, text="Max Temperature: ")
        max_temp_label.grid(row=1, column=0, padx=5, pady=5)
        min_temp = ttk.Label(temp_frame, text="-")
        min_temp.grid(row=0, column=1, padx=5, pady=5)
        max_temp = ttk.Label(temp_frame, text="-")
        max_temp.grid(row=1, column=1, padx=5, pady=5)

        # LV Data
        lv_frame = ttk.LabelFrame(
            overview_frame, padding=(10, 5), text='LV Data')
        lv_frame.grid(row=2, column=0, padx=10, pady=5, sticky='nw')
        air_p_label = ttk.Label(lv_frame, text='air_p')
        air_p_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')
        air_p_value = ttk.Label(lv_frame, text='0')
        air_p_value.grid(row=0, column=1, padx=5, pady=5, sticky='w')

        aux_p_label1 = ttk.Label(lv_frame, text='aux_p')
        aux_p_label1.grid(row=1, column=0, padx=5, pady=5, sticky='w')
        aux_p_value1 = ttk.Label(lv_frame, text='0')
        aux_p_value1.grid(row=1, column=1, padx=5, pady=5, sticky='w')

        aux_p_label2 = ttk.Label(lv_frame, text='aux_p')
        aux_p_label2.grid(row=2, column=0, padx=5, pady=5, sticky='w')
        aux_p_value2 = ttk.Label(lv_frame, text='0')
        aux_p_value2.grid(row=2, column=1, padx=5, pady=5, sticky='w')

        aux_n_label = ttk.Label(lv_frame, text='aux_n')
        aux_n_label.grid(row=3, column=0, padx=5, pady=5, sticky='w')
        aux_n_value = ttk.Label(lv_frame, text='0')
        aux_n_value.grid(row=3, column=1, padx=5, pady=5, sticky='w')

        pcr_5v_label = ttk.Label(lv_frame, text='pcr_5v')
        pcr_5v_label.grid(row=4, column=0, padx=5, pady=5, sticky='w')
        pcr_5v_value = ttk.Label(lv_frame, text='0')
        pcr_5v_value.grid(row=4, column=1, padx=5, pady=5, sticky='w')

        pcr_aux_in_label = ttk.Label(lv_frame, text='pcr_aux_in')
        pcr_aux_in_label.grid(row=5, column=0, padx=5, pady=5, sticky='w')
        pcr_aux_in_value = ttk.Label(lv_frame, text='0')
        pcr_aux_in_value.grid(row=5, column=1, padx=5, pady=5, sticky='w')

        vs_bat_label = ttk.Label(lv_frame, text='vs_bat')
        vs_bat_label.grid(row=6, column=0, padx=5, pady=5, sticky='w')
        vs_bat_value = ttk.Label(lv_frame, text='0')
        vs_bat_value.grid(row=6, column=1, padx=5, pady=5, sticky='w')

        ss_final_label = ttk.Label(lv_frame, text='ss_final')
        ss_final_label.grid(row=7, column=0, padx=5, pady=5, sticky='w')
        ss_final_value = ttk.Label(lv_frame, text='0')
        ss_final_value.grid(row=7, column=1, padx=5, pady=5, sticky='w')

        green_in_label = ttk.Label(lv_frame, text='green_in')
        green_in_label.grid(row=8, column=0, padx=5, pady=5, sticky='w')
        green_in_value = ttk.Label(lv_frame, text='0')
        green_in_value.grid(row=8, column=1, padx=5, pady=5, sticky='w')

        green_out_label = ttk.Label(lv_frame, text='green_out')
        green_out_label.grid(row=9, column=0, padx=5, pady=5, sticky='w')
        green_out_value = ttk.Label(lv_frame, text='0')
        green_out_value.grid(row=9, column=1, padx=5, pady=5, sticky='w')

        vs_bat_voltage_label = ttk.Label(lv_frame, text='vs_bat_voltage')
        vs_bat_voltage_label.grid(row=10, column=0, padx=5, pady=5, sticky='w')
        vs_bat_voltage_value = ttk.Label(lv_frame, text='0')
        vs_bat_voltage_value.grid(row=10, column=1, padx=5, pady=5, sticky='w')

        vs_hv_voltage_label = ttk.Label(lv_frame, text='vs_hv_voltage')
        vs_hv_voltage_label.grid(row=11, column=0, padx=5, pady=5, sticky='w')
        vs_hv_voltage_value = ttk.Label(lv_frame, text='0')
        vs_hv_voltage_value.grid(row=11, column=1, padx=5, pady=5, sticky='w')

        pcr_done_label = ttk.Label(lv_frame, text='pcr_done')
        pcr_done_label.grid(row=12, column=0, padx=5, pady=5, sticky='w')
        pcr_done_value = ttk.Label(lv_frame, text='0')
        pcr_done_value.grid(row=12, column=1, padx=5, pady=5, sticky='w')

        v_check_label = ttk.Label(lv_frame, text='v_check')
        v_check_label.grid(row=13, column=0, padx=5, pady=5, sticky='w')
        v_check_value = ttk.Label(lv_frame, text='0')
        v_check_value.grid(row=13, column=1, padx=5, pady=5, sticky='w')

        t_check_label = ttk.Label(lv_frame, text='t_check')
        t_check_label.grid(row=14, column=0, padx=5, pady=5, sticky='w')
        t_check_value = ttk.Label(lv_frame, text='0')
        t_check_value.grid(row=14, column=1, padx=5, pady=5, sticky='w')

        k2_label = ttk.Label(lv_frame, text='k2')
        k2_label.grid(row=15, column=0, padx=5, pady=5, sticky='w')
        k2_value = ttk.Label(lv_frame, text='0')
        k2_value.grid(row=15, column=1, padx=5, pady=5, sticky='w')

        k1_label = ttk.Label(lv_frame, text='k1')
        k1_label.grid(row=16, column=0, padx=5, pady=5, sticky='w')
        k1_value = ttk.Label(lv_frame, text='0')
        k1_value.grid(row=16, column=1, padx=5, pady=5, sticky='w')

    def create_voltages_tab(self, notebook):
        """ Creates the voltages tab. """

        voltages_tab = ttk.Frame(notebook)
        notebook.add(voltages_tab, text='Voltages')

        # Create voltages structure
        voltages_view_frame = ttk.Frame(
            voltages_tab, padding=(10, 5))
        voltages_view_frame.pack(fill=BOTH, expand=True)

        # Use a Canvas to enable scrolling
        v_canvas = Canvas(voltages_view_frame, xscrollcommand=None)
        v_canvas.pack(side=LEFT, fill=BOTH, expand=True)

        # Vertical scrollbar
        v_scrollbar = ttk.Scrollbar(
            voltages_view_frame, orient=VERTICAL, command=v_canvas.yview)
        v_scrollbar.pack(side=RIGHT, fill=Y)
        v_canvas.configure(yscrollcommand=v_scrollbar.set)

        # Horizontal scrollbar
        v_hscrollbar = ttk.Scrollbar(
            voltages_view_frame, orient=HORIZONTAL, command=v_canvas.xview)
        v_hscrollbar.pack(side=BOTTOM, fill=X)
        v_canvas.configure(xscrollcommand=v_hscrollbar.set)

        voltages_frame = ttk.Frame(v_canvas)
        v_canvas.create_window(
            (0, 0), window=voltages_frame, anchor='nw')

        # Make the canvas scrollable
        def on_frame_configure(event):
            v_canvas.configure(scrollregion=v_canvas.bbox('all'))
            v_canvas.xview_moveto(0)
            v_canvas.yview_moveto(0)
        voltages_frame.bind('<Configure>', on_frame_configure)

        for row in range(DEFAULT_STACK_ROWS):
            for col in range(DEFAULT_STACK_COLS):
                stack_index = row * DEFAULT_STACK_COLS + col
                stack_frame = ttk.LabelFrame(
                    voltages_frame, text=f'Stack {stack_index + 1}')
                stack_frame.grid(row=row, column=col,
                                 padx=10, pady=5, sticky='nw')

                for cell in range(DEFAULT_CELLS):
                    # Cell voltages with plot buttons
                    # Extracting cell voltage from serial values
                    cell_voltage = serial_values[stack_index *
                                                 DEFAULT_CELLS + cell]
                    cell_label = ttk.Label(
                        stack_frame, text=f'Cell {cell + 1}')
                    cell_label.grid(row=cell, column=0, padx=5, pady=5)
                    cell_voltage_label = ttk.Label(
                        stack_frame, textvariable=StringVar(value=cell_voltage), bootstyle=check_status(cell_voltage, DEFAULT_UV, DEFAULT_OV))
                    cell_voltage_label.grid(row=cell, column=1, padx=5, pady=5)
                    voltage_unit = ttk.Label(stack_frame, text='V')
                    voltage_unit.grid(row=cell, column=2, padx=5, pady=5)

                stack_voltage = 0.0
                stack_voltage_label = ttk.Label(
                    stack_frame, text=f'Stack voltage: {stack_voltage}')
                stack_voltage_label.grid(
                    row=DEFAULT_CELLS + 1, column=0, padx=5, pady=5, columnspan=2)

    def create_temps_tab(self, notebook):
        """ Creates the temperatures tab. """

        temps_tab = ttk.Frame(notebook)
        notebook.add(temps_tab, text='Temperatures')

        # Create temperatures structure
        temps_view_frame = ttk.Frame(temps_tab, padding=(10, 5))
        temps_view_frame.pack(fill=BOTH, expand=True)

        # Use a Canvas to enable scrolling
        t_canvas = Canvas(temps_view_frame, xscrollcommand=None)
        t_canvas.pack(side=LEFT, fill=BOTH, expand=True)

        # Vertical scrollbar
        t_scrollbar = ttk.Scrollbar(
            temps_view_frame, orient=VERTICAL, command=t_canvas.yview)
        t_scrollbar.pack(side=RIGHT, fill=Y)
        t_canvas.configure(yscrollcommand=t_scrollbar.set)

        # Horizontal scrollbar
        t_hscrollbar = ttk.Scrollbar(
            temps_view_frame, orient=HORIZONTAL, command=t_canvas.xview)
        t_hscrollbar.pack(side=BOTTOM, fill=X)
        t_canvas.configure(xscrollcommand=t_hscrollbar.set)

        temps_frame = ttk.Frame(t_canvas)
        t_canvas.create_window(
            (0, 0), window=temps_frame, anchor='nw')

        # Make the canvas scrollable
        def on_frame_configure(event):
            t_canvas.configure(scrollregion=t_canvas.bbox('all'))
            t_canvas.xview_moveto(0)
            t_canvas.yview_moveto(0)
        temps_frame.bind('<Configure>', on_frame_configure)

        for row in range(DEFAULT_STACK_ROWS):
            for col in range(DEFAULT_STACK_COLS):
                stack_index = row * DEFAULT_STACK_COLS + col
                stack_frame = ttk.LabelFrame(
                    temps_frame, text=f'Stack {stack_index + 1}')
                stack_frame.grid(row=row, column=col,
                                 padx=5, pady=5, sticky='nw')

                for temp in range(DEFAULT_TEMPS):
                    # Cell temperatures with plot buttons
                    temp_button = ttk.Label(
                        stack_frame, text=f'Temp. {temp + 1}')
                    temp_button.grid(row=temp, column=0, padx=5, pady=5)
                    cell_temp = 0.0
                    temp_value = ttk.Label(stack_frame, textvariable=StringVar(
                        value=cell_temp), bootstyle=check_status(cell_temp, DEFAULT_UT, DEFAULT_OT))
                    temp_value.grid(row=temp, column=1, padx=5, pady=5)
                    temp_unit = ttk.Label(stack_frame, text='°C')
                    temp_unit.grid(row=temp, column=2, padx=5, pady=5)

    def confirm_settings(self):
        """ Confirms the settings and launches the main application. """
        self.title = f"ORI BMS - {self.port_var.get()} @ {self.baud_var.get()} baud"
        self.start_serial_read()


def main():
    root = ttk.Window(themename="vapor")
    # style=ttk.Style()
    # print(style.theme_names())
    BatteryManagementSystem(root)
    root.mainloop()


if __name__ == "__main__":
    main()
