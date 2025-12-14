import json
import re
import sys
import argparse

def parse_size(size_str):
    """
    Parses a size string (e.g., '1.08GB', '36.68MB') into bytes.
    """
    if not size_str:
        return 0.0
    
    units = {
        'B': 1,
        'KB': 1000,
        'MB': 1000**2,
        'GB': 1000**3,
        'TB': 1000**4,
    }
    
    # Regex to capture number and unit
    # wrk output often has no space between number and unit, e.g. "1.08GB"
    match = re.match(r'^([\d\.]+)([a-zA-Z]+)$', size_str.strip())
    if match:
        value, unit = match.groups()
        # Use binary units (1024 base) as per wrk implementation
        binary_units = {
            'B': 1,
            'KB': 1024,
            'MB': 1024**2,
            'GB': 1024**3,
            'TB': 1024**4,
        }
        return float(value) * binary_units.get(unit.upper(), 1)
        
    return 0.0

def parse_time(time_str):
    """
    Parses time string (e.g. '2.28ms', '30.06s') into milliseconds.
    """
    if not time_str:
        return 0.0
        
    units = {
        'us': 0.001,
        'ms': 1,
        's': 1000,
        'm': 60 * 1000,
        'h': 60 * 60 * 1000,
    }
    
    match = re.match(r'^([\d\.]+)([a-zA-Z]+)$', time_str.strip())
    if match:
        value, unit = match.groups()
        return float(value) * units.get(unit, 1)
    return 0.0

def parse_wrk(content):
    lines = content.splitlines()
    # wrk doesn't explicitly output its version in the result, so we leave it unknown or infer from first line
    version = "wrk (unknown version)"
    
    plot_data = {}
    table_data = {}
    
    # Config
    # Line 1: Running 30s test @ http://nginx-server/
    # Line 2:   4 threads and 100 connections
    threads_match = re.search(r'(\d+) threads and (\d+) connections', content)
    if threads_match:
        table_data['threads'] = int(threads_match.group(1))
        table_data['connections'] = int(threads_match.group(2))
        
    # Thread Stats
    #     Latency     2.28ms    1.51ms  28.90ms   74.61%
    #     Req/Sec    11.34k     1.26k   18.05k    71.42%
    latency_match = re.search(r'Latency\s+([\d\.]+[a-z]+)\s+([\d\.]+[a-z]+)\s+([\d\.]+[a-z]+)', content)
    if latency_match:
        plot_data['latency_avg_ms'] = parse_time(latency_match.group(1))
        table_data['latency_stdev_ms'] = parse_time(latency_match.group(2))
        table_data['latency_max_ms'] = parse_time(latency_match.group(3))
        
    # Totals
    # 1355387 requests in 30.06s, 1.08GB read
    totals_match = re.search(r'(\d+) requests in ([\d\.]+[a-z]+), ([\d\.]+[a-zA-Z]+) read', content)
    if totals_match:
        table_data['total_requests'] = int(totals_match.group(1))
        table_data['total_duration_ms'] = parse_time(totals_match.group(2))
        table_data['total_read_bytes'] = parse_size(totals_match.group(3))
        
    # Socket errors (optional)
    # Socket errors: connect 0, read 0, write 0, timeout 0
    errors_match = re.search(r'Socket errors: connect (\d+), read (\d+), write (\d+), timeout (\d+)', content)
    if errors_match:
        table_data['errors_connect'] = int(errors_match.group(1))
        table_data['errors_read'] = int(errors_match.group(2))
        table_data['errors_write'] = int(errors_match.group(3))
        table_data['errors_timeout'] = int(errors_match.group(4))
        
    # Main Metrics
    # Requests/sec:  45094.76
    # Transfer/sec:     36.68MB
    req_sec_match = re.search(r'Requests/sec:\s+([\d\.]+)', content)
    if req_sec_match:
        plot_data['requests_per_sec'] = float(req_sec_match.group(1))
        
    transfer_sec_match = re.search(r'Transfer/sec:\s+([\d\.]+[a-zA-Z]+)', content)
    if transfer_sec_match:
        # Transfer/sec usually has unit attached like "36.68MB"
        plot_data['transfer_per_sec_bytes'] = parse_size(transfer_sec_match.group(1))

    return {
        "version": version,
        "plot": plot_data,
        "table": table_data
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse wrk results to JSON.")
    parser.add_argument("input_file", help="Path to the wrk output file")
    parser.add_argument("--output", help="Path to output JSON file (optional)")
    
    args = parser.parse_args()
    
    try:
        with open(args.input_file, 'r') as f:
            content = f.read()
            
        result = parse_wrk(content)
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
        else:
            print(json.dumps(result, indent=2))
            
    except FileNotFoundError:
        print(f"Error: File not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)
