import serial
import csv
import threading
import re
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import time

# =====================
# Configuration
# =====================
SERIAL_PORT = "COM4"
BAUD_RATE = 9600          # adjust if required
TIMEOUT = 1
CSV_FILE = "flow_log.csv"

# =====================
# Regex patterns
# =====================
UP_DN_Q_RE = re.compile(r"UP:(?P<up>[\d.]+),DN:(?P<dn>[\d.]+),Q=(?P<q>\d+)")
FLOW_RE = re.compile(r"FLOW:\s*(?P<flow>[\d.]+)")
VEL_RE = re.compile(r"VEL:\s*(?P<vel>[\d.]+)")
FVEL_RE = re.compile(r"FVEL:\s*(?P<fvel>[\d.]+)")

# =====================
# Control flags
# =====================
stop_logging = threading.Event()

# =====================
# CSV setup
# =====================
def init_csv():
    exists = Path(CSV_FILE).exists()
    f = open(CSV_FILE, "a", newline="")
    writer = csv.writer(f)

    if not exists:
        writer.writerow([
            "timestamp",
            "target_flow",
            "up",
            "down",
            "q",
            "flow_ls",
            "velocity_ms",
            "fvel_ms"
        ])

    return f, writer

# =====================
# Parse measurement block
# =====================
def parse_block(lines, target_flow):
    timestamp = up = down = q = flow = vel = fvel = None

    for line in lines:
        if re.match(r"\d{2}-\d{2}-\d{2}", line):
            timestamp = datetime.strptime(line, "%d-%m-%y %H:%M:%S")

        if (m := UP_DN_Q_RE.search(line)):
            up = float(m.group("up"))
            down = float(m.group("dn"))
            q = int(m.group("q"))

        if (m := FLOW_RE.search(line)):
            flow = float(m.group("flow"))

        if (m := VEL_RE.search(line)):
            vel = float(m.group("vel"))

        if (m := FVEL_RE.search(line)):
            fvel = float(m.group("fvel"))

    if None in (timestamp, up, down, q, flow, vel, fvel):
        return None

    return (
        timestamp,
        [
            timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            target_flow,
            up,
            down,
            q,
            flow,
            vel,
            fvel
        ],
        flow
    )

# =====================
# Serial logging thread
# =====================
def log_data(target_flow, flow_values, time_values):
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT)
    csv_file, csv_writer = init_csv()
    buffer = []

    try:
        while not stop_logging.is_set():
            line = ser.readline().decode(errors="ignore").strip()
            if not line:
                continue

            buffer.append(line)

            if line.startswith("FVEL"):
                parsed = parse_block(buffer, target_flow)
                buffer.clear()

                if parsed:
                    timestamp, csv_row, flow = parsed
                    csv_writer.writerow(csv_row)
                    csv_file.flush()

                    flow_values.append(flow)
                    time_values.append(timestamp)

    finally:
        ser.close()
        csv_file.close()

# =====================
# Plotting
# =====================
def live_plot(target_flow, flow_values, time_values):
    fig, ax = plt.subplots()

    ax.set_title("Live Flow Rate")
    ax.set_xlabel("Time")
    ax.set_ylabel("Flow (l/s)")

    target_line = ax.axhline(
        target_flow,
        linestyle="--",
        linewidth=2,
        label=f"Target Flow = {target_flow} l/s"
    )

    measured_line, = ax.plot([], [], label="Measured Flow")

    ax.legend()
    ax.grid(True)

    def update(frame):
        if not time_values:
            return measured_line,

        x = time_values
        y = flow_values

        measured_line.set_data(x, y)
        ax.relim()
        ax.autoscale_view()

        fig.autofmt_xdate()
        return measured_line,

    ani = animation.FuncAnimation(fig, update, interval=500)

    plt.show()   # blocks until closed
    plt.close(fig)

# =====================
# Stop listener
# =====================
def wait_for_stop():
    while True:
        if input().strip().lower() == "stop":
            stop_logging.set()
            break

# =====================
# Main loop
# =====================
def main():
    print("\nFlow Meter Logger with Live Plot\n")

    while True:
        try:
            target = float(input("Enter target flow rate (l/s): "))
        except ValueError:
            print("Invalid number.\n")
            continue

        stop_logging.clear()
        flow_values = []
        time_values = []

        reader = threading.Thread(
            target=log_data,
            args=(target, flow_values, time_values),
            daemon=True
        )
        reader.start()

        print("\nLogging... Type 'stop' and press Enter to stop.\n")

        stopper = threading.Thread(target=wait_for_stop, daemon=True)
        stopper.start()

        live_plot(target, flow_values, time_values)

        stop_logging.set()
        reader.join()

        choice = input("Log another target? (y/n): ").strip().lower()
        if choice != "y":
            break

    print("Program exited.")

# =====================
if __name__ == "__main__":
    main()
