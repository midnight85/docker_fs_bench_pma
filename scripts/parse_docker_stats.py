import json
import re
import sys
import argparse

def parse_size(size_str):
    """
    Parses a size string (e.g., '72.1MB', '5.33kB', '126B') into bytes.
    Returns 0 if the string is invalid or empty.
    """
    if not size_str or size_str == '--':
        return 0.0
    
    units = {
        'B': 1,
        'kB': 1000,
        'MB': 1000**2,
        'GB': 1000**3,
        'TB': 1000**4,
        'KiB': 1024,
        'MiB': 1024**2,
        'GiB': 1024**3,
        'TiB': 1024**4,
    }
    
    # Regex to capture number and unit
    match = re.match(r'^([\d\.]+)([a-zA-Z]+)$', size_str.strip())
    if match:
        value, unit = match.groups()
        return float(value) * units.get(unit, 1)
    
    # Fallback for just numbers (assumed bytes) or unknown formats
    try:
        return float(size_str)
    except ValueError:
        return 0.0

def parse_docker_stats(file_path):
    data = {
        "cpu_perc": [],
        "mem_usage_bytes": [],
        "mem_limit_bytes": [],
        "block_read_bytes": [],
        "block_write_bytes": [],
        "net_rx_bytes": [],
        "net_tx_bytes": []
    }
    
    try:
        with open(file_path, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Parse CPU
                cpu_str = entry.get("CPUPerc", "0%").replace("%", "")
                try:
                    data["cpu_perc"].append(float(cpu_str))
                except ValueError:
                    data["cpu_perc"].append(0.0)

                # Parse Memory
                # Format: "420.9MiB / 7.755GiB"
                mem_str = entry.get("MemUsage", "0B / 0B")
                if " / " in mem_str:
                    used_str, limit_str = mem_str.split(" / ")
                    data["mem_usage_bytes"].append(parse_size(used_str))
                    data["mem_limit_bytes"].append(parse_size(limit_str))
                else:
                    data["mem_usage_bytes"].append(parse_size(mem_str))
                    data["mem_limit_bytes"].append(0.0)

                # Parse Block IO
                # Format: "72.1MB / 252MB"
                block_str = entry.get("BlockIO", "0B / 0B")
                if " / " in block_str:
                    read_str, write_str = block_str.split(" / ")
                    data["block_read_bytes"].append(parse_size(read_str))
                    data["block_write_bytes"].append(parse_size(write_str))
                else:
                    data["block_read_bytes"].append(0.0)
                    data["block_write_bytes"].append(0.0)

                # Parse Net IO
                # Format: "5.33kB / 126B"
                net_str = entry.get("NetIO", "0B / 0B")
                if " / " in net_str:
                    rx_str, tx_str = net_str.split(" / ")
                    data["net_rx_bytes"].append(parse_size(rx_str))
                    data["net_tx_bytes"].append(parse_size(tx_str))
                else:
                    data["net_rx_bytes"].append(0.0)
                    data["net_tx_bytes"].append(0.0)

    except FileNotFoundError:
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    # Calculate Summary Statistics
    plot_data = {}
    
    # CPU & Memory: Use average values with simple names
    if data["cpu_perc"]:
        plot_data["cpu_perc"] = round(sum(data["cpu_perc"]) / len(data["cpu_perc"]), 2)
    else:
        plot_data["cpu_perc"] = 0.0
        
    if data["mem_usage_bytes"]:
        plot_data["mem_usage_bytes"] = round(sum(data["mem_usage_bytes"]) / len(data["mem_usage_bytes"]), 2)
    else:
        plot_data["mem_usage_bytes"] = 0.0

    # Block & Net IO: Total (Last Value) - use simple names
    plot_data["block_read_bytes"] = data["block_read_bytes"][-1] if data["block_read_bytes"] else 0.0
    plot_data["block_write_bytes"] = data["block_write_bytes"][-1] if data["block_write_bytes"] else 0.0
    # Keep network stats but simplified
    plot_data["net_rx_bytes"] = data["net_rx_bytes"][-1] if data["net_rx_bytes"] else 0.0
    plot_data["net_tx_bytes"] = data["net_tx_bytes"][-1] if data["net_tx_bytes"] else 0.0

    # Return structure
    # 'plot' contains scalar metrics for charts/tables
    # 'series' contains raw time series data
    return {
        "plot": plot_data,
        "series": data 
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse docker_stats.jsonl to JSON for Plotly.")
    parser.add_argument("input_file", help="Path to the docker_stats.jsonl file")
    parser.add_argument("--output", help="Path to output JSON file (optional, prints to stdout if not set)")
    
    args = parser.parse_args()
    
    parsed_data = parse_docker_stats(args.input_file)
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(parsed_data, f, indent=2)
    else:
        print(json.dumps(parsed_data, indent=2))
