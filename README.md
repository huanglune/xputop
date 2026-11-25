# xputop (`kunlun-xputop`)

**An interactive Kunlunxin-XPU process viewer and beyond, the one-stop solution for XPU process management.**

[![PyPI](https://img.shields.io/pypi/v/kunlun-xputop?label=PyPI%20%7C%20kunlun-xputop)](https://pypi.org/project/kunlun-xputop/)
[![Python Versions](https://img.shields.io/pypi/pyversions/kunlun-xputop)](https://pypi.org/project/kunlun-xputop/)
[![License](https://img.shields.io/badge/License-Apache--2.0%20AND%20GPL--3.0-blue.svg)](#license)

`xputop` (published on PyPI as **`kunlun-xputop`**) is a native port of [`nvitop`](https://github.com/XuehaiPan/nvitop) for **Kunlunxin (昆仑芯) XPU** accelerators (such as **Kunlunxin P800 OAM / KL3**, R200, R300, RG800, etc.).

Unlike NVIDIA NVML wrappers that break when `torch_xmlir` / `libbkcl.so` performs symbol rewriting at Python startup, `xputop` binds directly to Kunlunxin's native **XPU Management Library (`libxpuml.so.1`)** via `ctypes` — requiring **zero `nvidia-ml-py` dependency** and providing first-class support for Kunlunxin-specific metrics such as **L3 Memory (96 MiB)**, **XPU-RT Version**, and **KLRM Driver Version**.

---

## Preview

```text
╒═════════════════════════════════════════════════════════════════════════════╕
│ XPUTOP 1.7.2           Driver Version: 515.58          XPU-RT Version: 10.2 │
├───────────────────────────────┬──────────────────────┬──────────────────────┤
│ XPU  Name        Persistence-M│ Bus-Id        Disp.A │ Volatile Uncorr. ECC │
│ Fan  Temp  Perf  Pwr:Usage/Cap│         Memory-Usage │ XPU-Util  Compute M. │
╞═══════════════════════════════╪══════════════════════╪══════════════════════╪═══════════════════════╤════════════════════════╕
│   0  P800 OAM             N/A │ 00000000:03:00.0 N/A │                    0 │ MEM: █████████▌ 79.6% │ L3M: ▎ 2.00MiB    2.1% │
│ N/A   60C  N/A    387W / 400W │  76.45GiB / 96.00GiB │     80%      Default │ UTL: █████████▋ 80%   │ PWR: ████████████▋ 97% │
├───────────────────────────────┼──────────────────────┼──────────────────────┼───────────────────────┼────────────────────────┤
│   1  P800 OAM             N/A │ 00000000:16:00.0 N/A │                    0 │ MEM: ▏ 660.0MiB  0.7% │ L3M: ▏ 0B         0.0% │
│ N/A   60C  N/A    383W / 400W │  660.0MiB / 96.00GiB │     81%      Default │ UTL: █████████▊ 81%   │ PWR: ████████████▌ 96% │
╘═══════════════════════════════╧══════════════════════╧══════════════════════╧═══════════════════════╧════════════════════════╛
[ CPU: █▉ 2.4%                                                         UPTIME: 231.1 days ]  ( Load Average:  9.61 10.09 10.64 )
[ MEM: ████▍ 5.6%                                                          USED: 74.36GiB ]  [ SWP: ▏ 0.0%                     ]

╒══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╕
│ Processes:                                                                                               root@TENCENT64.site │
│ XPU     PID      USER  XPU-MEM SM% GMBW%  CPU%  MEM%        TIME  COMMAND                                                    │
╞══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╡
│   0  559664 C    root 32.00MiB N/A   N/A   0.0   0.2  210.2 days  VLLM::Worker_TP0                                           │
│   0  559665 C    root 75.84GiB N/A   N/A 211.9   0.2  210.2 days  VLLM::Worker_TP1                                           │
╘══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╛
```

---

## Highlights

- **Zero NVML Dependency (`xputop.api.libxpuml`)**: Pure `ctypes` bindings against Kunlunxin's `/usr/lib/x86_64-linux-gnu/libxpuml.so.1`. Works out-of-the-box in environments with `torch_xmlir`, `vllm_xpu`, and `xtorch_ops`.
- **Kunlunxin-Specific Telemetry**:
  - **Global HBM Memory** (`memory_used`, `memory_total`, `memory_percent`, `memory_usage`)
  - **L3 Cache / Memory** (`l3_memory_used`, `l3_memory_total`, `l3_memory_percent`, `l3_memory_usage`, rendered as `L3M` bar in wide mode)
  - **XPU Utilization**, **Cluster / CDNN Clocks**, **Power Draw / Limit**, **Temperature**, **ECC Errors**, and **PCIe Link Generation/Width**
  - **Driver Version (`515.58`)**, **KLRM Version (`5.0.21.45`)**, and **XPU-RT Version (`10.2`)**
- **Interactive Curses Monitor (`xputop`)**:
  - Switch between `auto` / `full` / `compact` display modes (`a` / `f` / `c`)
  - Live historical utilization graphs for XPU memory, XPU compute utilization, host CPU, and host RAM
  - Process tree view (`t`), environment variable inspector (`e`), per-process metric history (`Enter`), and process signal actions (`I` / `T` / `K`)
- **Device Selection Tool (`xpusel`)**:
  - Filter and sort available XPUs by free memory and utilization for `CUDA_VISIBLE_DEVICES` / `XPU_VISIBLE_DEVICES`.
- **Drop-In Python API**:
  - Compatible with `nvitop` APIs (`from xputop import Device, GpuProcess, HostProcess, take_snapshots, ResourceMetricCollector, select_devices`).

---

## Installation & Quick Start

### 1. Run Directly with `uvx` (No Install Needed)

If you have [`uv`](https://docs.astral.sh/uv/) installed, you can launch `xputop` immediately without installing it into your current environment:

```bash
# Run via the package's default entrypoint
uvx kunlun-xputop

# Or explicitly invoke `xputop` / `xpusel` from `kunlun-xputop`
uvx --from kunlun-xputop xputop
uvx --from kunlun-xputop xpusel
```

### 2. Install as a Global CLI Tool via `uv tool` or `pipx`

```bash
uv tool install kunlun-xputop
# Now `xputop`, `xpusel`, and `kunlun-xputop` are on your PATH:
xputop
```

### 3. Install via `pip` / `uv pip`

```bash
pip install --upgrade kunlun-xputop
# or in a Kunlunxin PyTorch environment (using --no-deps if you want to avoid touching vendor packages):
uv pip install kunlun-xputop
```

### 4. Install from Source

```bash
git clone https://github.com/huanglune/xputop.git
cd xputop
pip install -e .
```

---

## Command-Line Usage

### Interactive Monitor (`xputop`)

```bash
# Start interactive TUI monitor (default when running in a TTY)
xputop

# Specify display mode: auto, full, or compact
xputop -m full
xputop -m compact

# Print status once and exit
xputop -1

# Print once with wide bar charts (MEM, L3M, UTL, PWR)
COLUMNS=128 xputop -1

# Filter by XPU device indices or user
xputop -o 0 1 2 3
xputop -u root
```

#### Interactive Keybindings

| Key | Action |
|---|---|
| `a` / `f` / `c` | Switch between **Auto**, **Full**, and **Compact** display modes |
| `h` / `?` | Open help screen |
| `q` | Quit current screen / `xputop` |
| `t` | Toggle process tree view screen |
| `e` | Inspect environment variables of the selected process |
| `Enter` | View live historical metrics of the selected process |
| `Space` | Tag / untag current process |
| `Ctrl-C` / `I`, `T`, `K` | Send `SIGINT` (Interrupt), `SIGTERM` (Terminate), or `SIGKILL` (Kill) to selected process |
| `o` + `n`/`p`/`u`/`g`/`s`/`c`/`m`/`t` | Sort processes by XPU-ID, PID, USER, XPU-MEM, SM%, CPU%, MEM%, or TIME |
| `,` / `.` / `/` | Select sort column / invert sort order |

### XPU Device Selector (`xpusel`)

```bash
# List available XPU indices sorted by lowest load
xpusel

# Select 2 XPUs with at least 50 GiB free memory
export CUDA_VISIBLE_DEVICES="$(xpusel --min-count 2 --min-free-memory 50GiB)"
```

---

## Python API Usage

### Query Device & L3 Memory Status

```python
from xputop import Device, GpuProcess, take_snapshots, select_devices

print(f'Driver Version: {Device.driver_version()}')
print(f'KLRM Version  : {Device.klrm_version()}')
print(f'XPU-RT Version: {Device.xpurt_version()}')
print(f'Device Count  : {Device.count()}')

for device in Device.all():
    with device.oneshot():
        print(
            f'XPU {device.index} ({device.name()}, {device.bus_id()}): '
            f'MEM={device.memory_usage()} ({device.memory_percent()}%), '
            f'L3={device.l3_memory_usage()} ({device.l3_memory_percent()}%), '
            f'UTL={device.gpu_utilization()}%, '
            f'TEMP={device.temperature()}C, '
            f'PWR={device.power_status()}'
        )
        for pid, proc in device.processes().items():
            print(f'  PID {pid} ({proc.username()}): {proc.gpu_memory_human()} - {proc.command()}')
```

### Take Snapshots & Select Free XPUs

```python
from xputop import select_devices, take_snapshots

# Select up to 4 XPUs with >= 80 GiB free memory and <= 30% utilization
free_xpus = select_devices(
    format='index',
    min_count=2,
    max_count=4,
    min_free_memory='80GiB',
    max_gpu_utilization=30,
)
print('Selected XPUs:', free_xpus)

# Take a point-in-time snapshot of all devices and XPU processes
device_snapshots, process_snapshots = take_snapshots()
```

---

## Environment Variables

- `XPUML_LIBRARY_PATH`: Custom path to `libxpuml.so.1` if installed in a non-standard directory (searched by default in `/usr/lib/x86_64-linux-gnu/libxpuml.so.1`, `/usr/lib64/libxpuml.so.1`, `/usr/local/xpu/lib64/libxpuml.so.1`, and `$CONDA_PREFIX/xcudart/lib/libxpuml.so.1`).
- `XPUTOP_MONITOR_MODE`: Comma-separated default monitor options (e.g., `full,colorful,light,readonly`).

---

## Acknowledgments & License

`xputop` is ported from [XuehaiPan/nvitop](https://github.com/XuehaiPan/nvitop) and inspired by [youyve/nputop](https://github.com/youyve/nputop).

- The API package under `xputop/api` is licensed under the **Apache License, Version 2.0**.
- The TUI and full distribution are licensed under the **GNU General Public License v3.0 (GPL-3.0-only)**.
