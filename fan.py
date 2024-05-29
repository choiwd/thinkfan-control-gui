#!/usr/bin/python3
import tkinter as tk
import subprocess
from time import sleep, time
from threading import Thread

import re

core_info = re.compile(r'Core \d+:\s+\+(\d+.\d+).C')

temperature_list : list[float] = []

avg = lambda x : sum(x)/len(x)

refresh_rate = 0.5

last_setting = None

def make_columns(x: list, total_width: int) -> list:
    l = (len(x) + 1) // 2
    new_list = []
    for i in range(l):
        item = x[i] + (total_width//2 - len(x[i]))*' ' + x[l + i]
        item += (total_width - len(item))*' '
        new_list.append(item)
    return new_list

def get_info() -> list[str]:
    info_lines = subprocess.check_output("sensors").decode("utf-8").split("\n")
    result : list[str] = []
    temp_list = []
    count = 0
    for i in info_lines:
        core = core_info.search(i)
        if core is not None:
            result.append("Core %d: " % count + core.group(1))
            temp_list.append(float(core.group(1)))
            count += 1
        if "fan" in i:
            result.append("Fan: " + i.split(":")[-1].strip())
    
    global temperature_list
    temperature_list = temp_list
    result = make_columns(result, 30)
    result.append(f'Highest: +{max(temp_list)}°C')
    result.append(f'Average: +{round(avg(temp_list), 1)}°C')
    return result

def set_speed(speed : str) -> str:
    """
    Set speed of fan by changing level at /proc/acpi/ibm/fan
    speed: 0-7, auto, disengaged, full-speed
    """
    global last_setting
    last_setting = speed
    print("set level to %r" % speed)
    return subprocess.check_output(
        'echo level {0} | sudo tee "/proc/acpi/ibm/fan"'.format(speed),
        shell=True
    ).decode()

def change_speed(speed : float, inc : float, min_speed : int, max_speed : int, allow_full_speed : bool = False) -> int:
    new_speed = speed + inc
    if new_speed <= min_speed:
        new_speed = min_speed
    if new_speed >= max_speed:
        if allow_full_speed:
            new_speed = max_speed
        else:
            new_speed = max_speed - 1
    return int(new_speed)

class MainApplication(tk.Frame):
    
    speeds = {0 : '0', 1 : '1', 2 : '2', 3 : '3', 4 : '4', 5 : '5', 6 : '6', 7 : '7', 8 : 'full-speed'}

    def __init__(self, parent, *args, **kwargs):
        
        self.policy = None

        self.current_speed = 5
        self.last_time_above_max = time()
        self.last_time_below_max = time()
        
        self.last_error = 0
        self.error_acc = 0
        self.PIDSignal = 5

        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.parent.minsize(width=100, height=100)

        main_label = tk.Label(parent, text="")
        main_label.grid(row=0, column=0)

        row1 = tk.Frame()
        row1.grid()
        for i in range(8):
            tk.Button(row1, text=str(i), command=lambda x=i: self.set_speed_button(str(x))).grid(
                row=0, column=i + 1
            )

        row2 = tk.Frame()
        row2.grid()

        tk.Button(row2, text="Auto", command=lambda: self.set_speed_button("auto")).grid(
            row=0, column=0
        )
        tk.Button(row2, text="Full", command=lambda: self.set_speed_button("full-speed")).grid(
            row=0, column=1
        )
        tk.Button(row2, text="Custom auto", command=lambda: self.enable_custom_auto()).grid(
            row=0, column=3
        )
        tk.Button(row2, text="Shitty PID", command=lambda: self.enable_sPID()).grid(
            row=0, column=4
        )

        def display_loop():
            while True:
                sleep(refresh_rate)
                if self.policy:
                    self.policy()
                main_label["text"] = "\n".join(get_info()) + f'\nLast setting : {last_setting}'

        Thread(target=display_loop).start()

    def _clear_state(self) -> None:
        self.policy = None
        self.last_error = 0
        self.error_acc = 0
        self.PIDSignal = 5

    def set_speed_button(self, speed : str) -> str:
        self._clear_state()
        return set_speed(speed)
    
    def enable_custom_auto(self) -> None:
        self._clear_state()
        self.policy = self.custom_auto
    
    def enable_sPID(self) -> None:
        self._clear_state()
        self.policy = self.shitty_PID
    
    def custom_auto(self, max_temp : float = 60, min_speed : int = 2, max_speed : int = 8, allow_full_speed : bool = False, delay_upwards : float = 3, delay_downwards : float = 5) -> str:
        
        if avg(temperature_list) >= max_temp:
            self.last_time_above_max = time()
            if time() - self.last_time_below_max > delay_upwards:
                self.current_speed = change_speed(self.current_speed, +1, min_speed, max_speed)
                self.last_time_below_max = time()
        else:
            self.last_time_below_max = time()
            if time() - self.last_time_above_max > delay_downwards:
                self.current_speed = change_speed(self.current_speed, -1, min_speed, max_speed)
                self.last_time_above_max = time()
        
        return set_speed(speed=MainApplication.speeds[self.current_speed])

    def shitty_PID(self, target : float = 65, min_speed : int = 2, max_speed : int = 6, allow_full_speed : bool = False) -> str:
        kP = 0.8
        kD = 0
        kI = 0.05
        
        error = avg(temperature_list) - target
        error_deriv = (error - self.last_error)/refresh_rate
        self.error_acc += (error + self.last_error)*refresh_rate/2
        self.error_acc = min(max(0.0, self.error_acc), (max_speed / kI) * 1.25 )
        
        self.PIDSignal = kP * error + kD * error_deriv + kI * self.error_acc
        self.PIDSignal = max(self.PIDSignal, float(min_speed))

        output_signal = change_speed(0, self.PIDSignal, min_speed, max_speed)
        self.current_speed = output_signal

        print(f'PIDSignal: {self.PIDSignal:.2f}, PK: {kP * error:.2f}, PI: {kI * self.error_acc:.2f}, error: {error:.2f}, error_deriv {error_deriv:.2f}, error_acc: {self.error_acc:.2f}')
        
        return set_speed(speed=MainApplication.speeds[self.current_speed])

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Thinkfan Control")
    MainApplication(root).grid()
    try:
        root.mainloop()
    finally:
        sleep(2)
        set_speed('auto')
