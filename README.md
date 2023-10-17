# Thinkpad Fan Control GUI

![Screenshot](https://i.imgur.com/UXII1Mg.png)

This is an application for controlling fan speed on IBM/Lenovo ThinkPads.

It can also monitor CPU temp and fan RPM.

It is written for Linux only. For windows, see http://www.almico.com/speedfan.php   

## How it Works?
 + Parses `sensors` command to show CPU temp and fan RPM
 + Modifies `/proc/acpi/ibm/fan` to change fan speed

## Dependencies
`sudo apt install lm-sensors python3 python3-tk`

## Setup
+ Open this file, using command -- `sudo nano /etc/modprobe.d/thinkpad_acpi.conf` 
+ Add line `options thinkpad_acpi fan_control=1`
+ Reboot. 
+ `python3 fan.py`

( Add `sudo` to modify speed )

---

Note: You are required to have the Linux kernel with `thinkpad-acpi` patch. (Ubuntu, Solus and a few others already seem to have this)

## New Features

Compared to the original code, this fork adds 3 additional lines in the GUI (Highest, Average and Last setting) and adds 2 new (EXPERIMENTAL) controllers:

1. A custom auto, that regulates the fans when they cross a threshold;
2. [Recommended] A very simple implementation of a PID.

However, **USE IT AT YOUR OWN RISK**.

Under no circumstance shall I have any liability to you for any loss or damage of any kind incurred as a result of the use of this application!
