#!/usr/bin/env python3

import os
import logging


class ds18b20:
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.device_file = f"/sys/bus/w1/devices/{device_id}"
        self.temperature:float = 0.0
        
    def read_file(self, file_name: str) -> str:
        try:
            with open(self.device_file + "/" + file_name, "r") as f:
                return f.read()
        except FileNotFoundError:
            return None

    def read_temperature(self) -> float:
        temp_string = self.read_file("temperature")
        if temp_string is not None:
            self.temperature = float(temp_string) / 1000.0
            return self.temperature
        
    def __str__(self) -> str:
        return f"Device ID: {self.device_id}, Temperature: {self.temperature:.2f} °C"
    
        
def list_devices() -> list:
    try:
        devices = os.listdir("/sys/bus/w1/devices/")
    except FileNotFoundError:
        logging.debug("1-Wire bus not found.")
        return []

    device_ids = [ds18b20(dev) for dev in devices if dev.startswith("28-")]
    for device_id in device_ids:
        device = ds18b20(device_id)
    return device_ids


if __name__ == "__main__":
    print("1-Wire Devices Found:")
    for device in list_devices():
        device.read_temperature()
        print(device)