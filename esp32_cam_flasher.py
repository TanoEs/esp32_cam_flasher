#!/usr/bin/env python3
import sys
import glob
import os
import esptool
import serial
import time

# Change this to wherever you keep your firmware directories
BASE_FIRMWARE_DIR = os.getcwd()

def list_serial_ports():
    """Return a list of available serial ports on Windows, macOS, or Linux."""
    if sys.platform.startswith('win'):
        ports = [f'COM{i+1}' for i in range(256)]
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        ports = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')

    available = []
    for port in ports:
        try:
            with open(port):
                pass
            available.append(port)
        except Exception:
            continue
    return available

def choose_port():
    ports = list_serial_ports()
    if not ports:
        print("No serial ports found! Plug in your ESP32-CAM and try again.")
        sys.exit(1)
    if len(ports) == 1:
        print(f"Auto-detected port: {ports[0]}")
        return ports[0]
    print("Available serial ports:")
    for idx, p in enumerate(ports, start=1):
        print(f"  {idx}: {p}")
    choice = input("Select port number: ")
    try:
        return ports[int(choice) - 1]
    except Exception:
        print("Invalid selection.")
        sys.exit(1)

def flash(project_dir, port):
    """Erase flash and write bootloader, partition, and firmware bins."""
    boot  = os.path.join(project_dir, "bootloader.bin")
    parts = os.path.join(project_dir, "partitions.bin")
    app   = os.path.join(project_dir, "firmware.bin")

    for path in (boot, parts, app):
        if not os.path.isfile(path):
            print(f"Error: '{os.path.basename(path)}' not found in {project_dir}")
            sys.exit(1)

    print("Erasing flash…")
    esptool.main(['--chip','esp32','--port',port,'erase_flash'])

    print("Writing binaries:")
    print(f"  0x1000    {os.path.basename(boot)}")
    print(f"  0x8000    {os.path.basename(parts)}")
    print(f"  0x10000   {os.path.basename(app)}")
    esptool.main([
        '--chip','esp32','--port',port,
        'write_flash',
        '0x1000',  boot,
        '0x8000',  parts,
        '0x10000', app
    ])
    print("Flash complete!")

  
def serial_monitor(port, baudrate=115200):
    """Open a serial monitor on the specified port."""
    print(f"\nStarting serial monitor on {port} (baudrate {baudrate})")
    print("Press Ctrl+C to exit.\n")
    try:
        with serial.Serial(port, baudrate, timeout=1) as ser:

            ser.setDTR(False)
            ser.setRTS(False)
            time.sleep(2)  # Wait for ESP32 to reset after flash
            while True:
                if ser.in_waiting:
                    output = ser.read(ser.in_waiting).decode(errors='ignore')
                    print(output, end='', flush=True)
    except KeyboardInterrupt:
        print("\nSerial monitor stopped.")
    except Exception as e:
        print(f"Error: {e}")
      
def main():
    try:
        print("🔧 Welcome to the ESP32-CAM Flasher Tool!")
        print("This tool flashes your ESP32-CAM with bootloader, partitions, and firmware.\n")

        if len(sys.argv) == 2:
            project_name = sys.argv[1]
        else:
            project_name = input("Enter the name of the project folder (with .bin files): ").strip()

        project_dir = os.path.join(BASE_FIRMWARE_DIR, project_name)

        if not os.path.isdir(project_dir):
            print(f"❌ Error: project directory '{project_dir}' does not exist.")
            input("Press Enter to exit...")
            sys.exit(1)

        port = choose_port()
        flash(project_dir, port)

        answer = input("Launch serial monitor? [Y/n] (optionally: 'Y <baud_rate>'): ").strip().lower()
        if answer.startswith('y'):
            parts = answer.split()
            baudrate = 115200
            if len(parts) > 1:
                try:
                    baudrate = int(parts[1])
                except ValueError:
                    print("Invalid baud rate. Using default 115200.")
            serial_monitor(port, baudrate)

    except Exception as e:
        print(f"\n❌ An unexpected error occurred:\n{e}")
    finally:
        input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
