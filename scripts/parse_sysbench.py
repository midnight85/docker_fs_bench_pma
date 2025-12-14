import json
import re
import sys
import argparse

def parse_sysbench(content):
    lines = content.splitlines()
    version = lines[0].strip() if lines else "unknown"
    
    plot_data = {}
    table_data = {}
    
    # Transactions per second
    tps_match = re.search(r'transactions:\s+(\d+)\s+\(([\d\.]+) per sec\.\)', content)
    if tps_match:
        table_data['total_transactions'] = int(tps_match.group(1))
        plot_data['tps'] = float(tps_match.group(2))
        
    # Queries per second
    qps_match = re.search(r'queries:\s+(\d+)\s+\(([\d\.]+) per sec\.\)', content)
    if qps_match:
        table_data['total_queries'] = int(qps_match.group(1))
        plot_data['qps'] = float(qps_match.group(2))

    # Errors and Reconnects
    errors_match = re.search(r'ignored errors:\s+(\d+)', content)
    if errors_match:
        table_data['ignored_errors'] = int(errors_match.group(1))
        
    reconnects_match = re.search(r'reconnects:\s+(\d+)', content)
    if reconnects_match:
        table_data['reconnects'] = int(reconnects_match.group(1))
        
    # Latency
    # Latency Breakdown
    latency_match = re.search(r'Latency \(ms\):\s+min:\s+([\d\.]+)\s+avg:\s+([\d\.]+)\s+max:\s+([\d\.]+)\s+95th percentile:\s+([\d\.]+)', content)
    
    if not latency_match:
        # Fallback to individual searches
        min_match = re.search(r'min:\s+([\d\.]+)', content)
        avg_match = re.search(r'avg:\s+([\d\.]+)', content)
        max_match = re.search(r'max:\s+([\d\.]+)', content)
        p95_match = re.search(r'95th percentile:\s+([\d\.]+)', content)
        
        if min_match: table_data['latency_min'] = float(min_match.group(1))
        if avg_match: plot_data['latency_avg'] = float(avg_match.group(1))
        if max_match: table_data['latency_max'] = float(max_match.group(1))
        if p95_match: plot_data['latency_p95'] = float(p95_match.group(1))
    else:
        table_data['latency_min'] = float(latency_match.group(1))
        plot_data['latency_avg'] = float(latency_match.group(2))
        table_data['latency_max'] = float(latency_match.group(3))
        plot_data['latency_p95'] = float(latency_match.group(4))
        
    # General stats
    time_match = re.search(r'total time:\s+([\d\.]+)s', content)
    if time_match:
        table_data['total_time_sec'] = float(time_match.group(1))

    return {
        "version": version,
        "plot": plot_data,
        "table": table_data
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse sysbench results to JSON.")
    parser.add_argument("input_file", help="Path to the sysbench output file")
    parser.add_argument("--output", help="Path to output JSON file (optional)")
    
    args = parser.parse_args()
    
    try:
        with open(args.input_file, 'r') as f:
            content = f.read()
            
        result = parse_sysbench(content)
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
        else:
            print(json.dumps(result, indent=2))
            
    except FileNotFoundError:
        print(f"Error: File not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)
