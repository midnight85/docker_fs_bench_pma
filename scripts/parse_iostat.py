#!/usr/bin/env python3
"""
Parse iostat JSON log files into structured format for analysis.
Output format tailored for Plotly.js visualization and summary tables.
"""

import json
import sys
import argparse
from typing import Dict, List, Any
import statistics
import re


def parse_single_json_object(content: str) -> Dict[str, Any]:
    """
    Parse single JSON object format from iostat -o JSON output.
    Structure: {"sysstat": {"hosts": [{"statistics": [...]}]}}
    """
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse JSON: {e}", file=sys.stderr)
        return {"version": "unknown", "plot": {}, "table": {}}
    
    # Data structures for Plotly (lists)
    plot_data = {
        "timestamp": [],
        # CPU metrics
        "cpu_user": [],
        "cpu_system": [],
        "cpu_iowait": [],
        "cpu_idle": [],
    }
    
    # Temporary storage for calculating averages for Table
    table_stats = {
        "cpu_user": [],
        "cpu_system": [],
        "cpu_iowait": [],
        "cpu_idle": [],
    }
    device_table_stats = {}
    
    version_info = "unknown"
    
    # Extract sysstat data
    if "sysstat" not in data:
        return {"version": version_info, "plot": plot_data, "table": {}}
    
    hosts = data["sysstat"].get("hosts", [])
    if not hosts:
        return {"version": version_info, "plot": plot_data, "table": {}}
    
    host = hosts[0]
    
    # Extract version info
    version_info = f"{host.get('sysname', 'Linux')} {host.get('release', '')} ({host.get('nodename', '')}) {host.get('machine', '')}"
    
    # Process statistics
    statistics_list = host.get("statistics", [])
    if not statistics_list:
        return {"version": version_info, "plot": plot_data, "table": {}}
    
    for idx, stat_entry in enumerate(statistics_list):
        # Extract CPU stats
        cpu_stats = stat_entry.get("avg-cpu", {})
        
        # Create timestamp - use index as we don't have precise timestamps
        timestamp = idx
        
        # Add CPU metrics to plot data
        plot_data["timestamp"].append(timestamp)
        plot_data["cpu_user"].append(cpu_stats.get("user", 0.0))
        plot_data["cpu_system"].append(cpu_stats.get("system", 0.0))
        plot_data["cpu_iowait"].append(cpu_stats.get("iowait", 0.0))
        plot_data["cpu_idle"].append(cpu_stats.get("idle", 0.0))
        
        # Add to table stats
        table_stats["cpu_user"].append(cpu_stats.get("user", 0.0))
        table_stats["cpu_system"].append(cpu_stats.get("system", 0.0))
        table_stats["cpu_iowait"].append(cpu_stats.get("iowait", 0.0))
        table_stats["cpu_idle"].append(cpu_stats.get("idle", 0.0))
        
        # Extract disk stats
        # IMPORTANT: Some filesystems (ZFS) create partitions, so iostat returns
        # multiple devices (e.g., vdb, vdb1, vdb9). We only want the main device.
        disk_list = stat_entry.get("disk", [])
        
        # Find the main disk device (without partition number suffix)
        # Strategy: Pick the device name that is shortest (base device)
        #           or explicitly filter out numbered partitions
        main_disk = None
        main_disk_name = None
        
        for disk_entry in disk_list:
            dev_name = disk_entry.get("disk_device", "")
            # Skip devices with numbers at the end (partitions like vdb1, vdb9)
            if re.search(r'\d+$', dev_name):
                continue
            # This is the base device
            main_disk = disk_entry
            main_disk_name = dev_name
            break
        
        # If we found the main disk, process it
        if main_disk:
            dev_name = main_disk_name
            disk_stats = main_disk
            
            # Extract only the specified metrics
            parsed_metrics = {
                # --- DISK (IOPS) ---
                "read_iops": disk_stats.get("r/s", 0.0),
                "write_iops": disk_stats.get("w/s", 0.0),
                
                # --- DISK (Throughput) ---
                "read_kbps": disk_stats.get("rkB/s", 0.0),
                "write_kbps": disk_stats.get("wkB/s", 0.0),
                
                # --- DISK (Latency & Load) ---
                "read_await": disk_stats.get("r_await", 0.0),
                "write_await": disk_stats.get("w_await", 0.0),
                "util": disk_stats.get("util", 0.0)
            }
            
            # Add to plot data
            for metric_name, metric_value in parsed_metrics.items():
                key = f"{dev_name}_{metric_name}"
                if key not in plot_data:
                    plot_data[key] = []
                
                # Ensure the list has the same length as timestamps
                while len(plot_data[key]) < len(plot_data["timestamp"]) - 1:
                    plot_data[key].append(0.0)
                
                plot_data[key].append(metric_value)
            
            # Add to table stats
            if dev_name not in device_table_stats:
                device_table_stats[dev_name] = {k: [] for k in parsed_metrics.keys()}
            
            for metric_name, metric_value in parsed_metrics.items():
                device_table_stats[dev_name][metric_name].append(metric_value)
    
    # Ensure all list lengths in plot_data match timestamp length
    ts_len = len(plot_data["timestamp"])
    for k in plot_data:
        if k == "timestamp":
            continue
        while len(plot_data[k]) < ts_len:
            plot_data[k].append(0.0)
    
    # Compute Table Data (Averages)
    table_data = {}
    
    # CPU Stats - averages only
    for k, v in table_stats.items():
        if v:
            table_data[f"{k}_avg"] = round(statistics.mean(v), 2)
    
    # Device Stats - averages only
    for dev, stats in device_table_stats.items():
        for metric, values in stats.items():
            if values:
                table_data[f"{dev}_{metric}_avg"] = round(statistics.mean(values), 2)
    
    return {
        "version": version_info,
        "plot": plot_data,
        "table": table_data
    }


def parse_iostat(content: str) -> Dict[str, Any]:
    """
    Parse iostat JSON log content and return structured data.
    Takes raw content (possibly incomplete JSON) and returns dict for Plotly.
    """
    if not content.strip():
        return {"version": "unknown", "plot": {}, "table": {}}
    
    return parse_single_json_object(content)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse iostat JSON logs to structured JSON for Plotly.")
    parser.add_argument("input_file", help="Path to input iostat JSON log")
    parser.add_argument("--output", help="Path to output JSON")
    
    args = parser.parse_args()
    
    try:
        with open(args.input_file, 'r') as f:
            content = f.read()
        
        result = parse_iostat(content)
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
        else:
            print(json.dumps(result, indent=2))
    
    except FileNotFoundError:
        print(f"Error: File not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)
