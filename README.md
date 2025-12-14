# Docker Storage Driver Benchmark Suite (PMA)

Automated benchmarking of Docker storage drivers across different filesystems (ext4, xfs, btrfs, zfs) using containerized workloads.

## Features

- **Multi-Filesystem Support**: Automated formatting and mounting of `ext4`, `xfs`, `btrfs`, and `zfs`.
- **Docker Integration**: Dynamic configuration of Docker storage drivers (`overlay2`, `btrfs`, `zfs`).
- **Comprehensive Benchmarks**: Includes FIO, Sysbench, Pgbench, Web server benchmarks (wrk), and more.
- **System Monitoring**: Real-time tracking of CPU, RAM, Disk I/O (iostat), and Docker container stats.
- **Automated Reporting**: Aggregates results into JSON and uploads them to a central dashboard.

## Project Structure

```
pma/
├── main.yaml              # Main Ansible playbook entry point
├── prepare_system.sh      # System initialization script (Ubuntu)
├── tasks/                 # Modular Ansible task definitions
├── vars/                  # Configuration variables
└── scripts/               # Python scripts for parsing and aggregation
```

## System Preparation

Before running benchmarks, the system must be prepared (dependencies, Docker, Python environment).

### 1. Run Preparation Script
This script installs Docker, Ansible, and required system tools. It is designed for Ubuntu.

```bash
sudo ./prepare_system.sh [optional_venv_path]
```
> **Note**: The default virtual environment path is `/opt/ansible_venv`.

### 2. Activate Virtual Environment
```bash
source /opt/ansible_venv/bin/activate
```

## Configuration (`vars/`)

All benchmark parameters are defined in the `vars/` directory:

- **`filesystems.yaml`**: filesystems to test and their specific mount options.
- **`container_workloads.yaml`**: Definitions of containerized benchmarks (images, commands, iterations).
- **`default_monitoring.yaml`**: Configuration for `iostat` and `docker stats`.
- **`paths.yaml`**: System paths (log directory, target device/partition).

## Usage

To start the benchmark suite, run the main playbook:

```bash
ansible-playbook main.yaml -K
```
*The `-K` flag prompts for the `sudo` password, which is required for filesystem operations and Docker control.*

## Scripts & Automation

### Python Parsers (`scripts/`)
These tools translate raw command output into structured JSON for the dashboard:
- **`aggregate_results.py`**: Main aggregator that collects logs and generates `aggregated_report.json`.
- **`parse_*.py`**: Specialized parsers for specific tools (e.g., `parse_fio.py`, `parse_iostat.py`).

### Ansible Tasks (`tasks/`)
The workflow is modularized into specific tasks:
- **Initialization**: `collect_system_info.yaml`
- **Filesystem Lifecycle**: `format_storage.yaml`, `mount_storage.yaml`, `storage_cleanup.yaml`
- **Docker Control**: `configure_docker.yaml`
- **Workload Execution**: `run_workloads.yaml`, `start_monitoring.yaml`

## Process Flow

The execution starts with `main.yaml` and proceeds as follows:

1.  **Initialization**:
    *   Loads variables from `vars/`.
    *   Ensures the base log directory exists.
    *   (Optional) Collects system information (`tasks/collect_system_info.yaml`).

2.  **Filesystem Loop** (`tasks/process_filesystem.yaml`):
    *   Iterates through each filesystem defined in `vars/filesystems.yaml`.
    *   **Stop Docker**: Stops the Docker service to allow storage manipulation (`tasks/docker_control.yaml`).
    *   **Cleanup**: Removes any existing storage configuration (`tasks/storage_cleanup.yaml`).
    *   **Format**: Formats the partition with the target filesystem (`tasks/format_storage.yaml`).
    *   **Mount**: Mounts the partition (`tasks/mount_storage.yaml`).
    *   **Configure Docker**: Updates `daemon.json` with the storage driver (`tasks/configure_docker.yaml`).
    *   **Start Docker**: Starts Docker with the new storage configuration (`tasks/docker_control.yaml`).
    *   **Run Workloads** (`tasks/run_workloads.yaml`):
        *   Creates result directories.
        *   Pulls required Docker images.
        *   **Workload Loop** (`tasks/run_workload_loop.yaml`):
            *   Iterates through each workload in `vars/container_workloads.yaml`.
            *   **Iteration Loop** (`tasks/run_iteration_tasks.yaml`):
                *   Runs the workload for the specified number of iterations.
                *   Cleans up Docker system (prune) and drops caches before each run.
                *   **Execution**:
                    *   **Single Container**: Uses `tasks/run_single_workload.yaml`.
                    *   **Multi-Container**: Uses `tasks/run_multi_container_workload.yaml` (starts app -> waits -> runs workload -> stops app).
                *   **Monitoring**: Starts and stops monitoring tools (`tasks/start_monitoring.yaml`, `tasks/stop_monitoring.yaml`) around the workload execution.
    *   **Stop Docker**: Stops Docker after testing (`tasks/docker_control.yaml`).
    *   **Final Cleanup**: Unmounts and wipes the partition (`tasks/storage_cleanup.yaml`).

3.  **Aggregation** :
    *   Aggregates results using a Python script (`tasks/aggregate_results.yaml`).

4.  **Upload**:
    *   **Archive Config**: Archives the `vars/` directory into `config.zip` to preserve the run configuration.
    *   **Upload Results**: Uploads both the aggregated report (`aggregated_report.json`) and the configuration archive (`config.zip`) to the web server.


## Task Descriptions

### `tasks/`

| File | Description |
| :--- | :--- |
| `collect_system_info.yaml` | Collects system details (uname, lsblk, sysctl, mounts, cpu, memory) into text files. |
| `configure_docker.yaml` | Configures `/etc/docker/daemon.json` with the specified storage driver. |
| `docker_control.yaml` | Manages the Docker service state (start/stop). |
| `format_storage.yaml` | Formats the target partition with the specified filesystem (ext4, xfs, btrfs, zfs). |
| `mount_storage.yaml` | Mounts the formatted partition to the configured mount point. |
| `process_filesystem.yaml` | Orchestrates the full lifecycle for testing a single filesystem (format -> configure -> test -> cleanup). |
| `reinit_storage.yaml` | Re-initializes storage (stop Docker, wipe, format, mount, configure, start) between runs. |
| `run_iteration_tasks.yaml` | Manages a single iteration of a workload, including cleanup and choosing the execution method. |
| `run_multi_container_workload.yaml` | Handles workloads requiring two containers (App + Workload Generator), ensuring proper startup order and monitoring. |
| `run_single_workload.yaml` | Handles workloads running in a single container. |
| `run_workload_lifecycle.yaml` | Manages the full lifecycle for a single workload, triggering the execution loop. |
| `run_workload_loop.yaml` | Loops through the defined number of benchmark runs for a specific workload. |
| `run_workloads.yaml` | Main entry point for running all configured workloads on the current filesystem. |
| `start_monitoring.yaml` | Starts background monitoring processes (iostat, docker stats, etc.) and records their PIDs. |
| `stop_monitoring.yaml` | Stops the background monitoring processes using the recorded PIDs. |
| `storage_cleanup.yaml` | Unmounts storage, destroys ZFS pools, and wipes partition signatures. |