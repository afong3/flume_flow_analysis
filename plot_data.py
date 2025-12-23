import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.dates import DateFormatter

# =====================
# Configuration
# =====================
CSV_FILE = "flow_log.csv"
OUTPUT_PDF = "flow_report.pdf"
ROLLING_WINDOW_SECONDS = 10

# =====================
# Load and prepare data
# =====================
df = pd.read_csv(CSV_FILE)
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values("timestamp")

targets = sorted(df["target_flow"].unique())

# =====================
# Create PDF report
# =====================
with PdfPages(OUTPUT_PDF) as pdf:

    for target in targets:
        sub = df[df["target_flow"] == target].copy()
        sub = sub.set_index("timestamp")

        rolling = sub["flow_ls"].rolling(
            f"{ROLLING_WINDOW_SECONDS}s"
        ).mean()

        mean_flow = sub["flow_ls"].mean()
        std_flow = sub["flow_ls"].std()

        fig, ax = plt.subplots(figsize=(11, 7))

        # Raw flow
        ax.plot(
            sub.index,
            sub["flow_ls"],
            alpha=0.35,
            label="Raw Flow"
        )

        # Rolling average
        ax.plot(
            sub.index,
            rolling,
            linewidth=2.5,
            label=f"{ROLLING_WINDOW_SECONDS}s Rolling Avg"
        )

        # Mean flow
        ax.axhline(
            mean_flow,
            linestyle=":",
            linewidth=2.5,
            label=f"Mean Flow = {mean_flow:.3f} l/s (σ = {std_flow:.3f})"
        )

        # Target flow
        ax.axhline(
            target,
            linestyle="--",
            linewidth=2.5,
            label=f"Target Flow = {target} l/s"
        )

        # =====================
        # Formatting
        # =====================
        ax.set_title(
            f"Flow Performance — Target {target} l/s",
            fontsize=16,
            pad=12
        )
        ax.set_xlabel("Time", fontsize=12)
        ax.set_ylabel("Flow (l/s)", fontsize=12)

        # Legend locked to bottom-right
        ax.legend(
            loc="lower right",
            fontsize=10,
            framealpha=0.9
        )

        ax.grid(True)
        ax.xaxis.set_major_formatter(DateFormatter("%H:%M:%S"))

        fig.autofmt_xdate()
        fig.tight_layout()

        pdf.savefig(fig)
        plt.close(fig)

print(f"PDF report written to: {OUTPUT_PDF}")
