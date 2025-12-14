import json
import re
import sys
import argparse

def parse_pgbench(content):
    lines = content.splitlines()
    version = lines[0].strip() if lines else "unknown"
    
    plot_data = {}
    table_data = {}
    
    # TPS
    tps_match = re.search(r'tps = ([\d\.]+)', content)
    if tps_match:
        plot_data['tps'] = float(tps_match.group(1))
        
    # Latency average
    lat_match = re.search(r'latency average = ([\d\.]+) ms', content)
    if lat_match:
        plot_data['latency_avg'] = float(lat_match.group(1))
        
    # Transactions processed
    trans_match = re.search(r'number of transactions actually processed: (\d+)', content)
    if trans_match:
        table_data['transactions_processed'] = int(trans_match.group(1))

    # Failed transactions
    failed_match = re.search(r'number of failed transactions: (\d+)', content)
    if failed_match:
        table_data['failed_transactions'] = int(failed_match.group(1))
        
    # Config / Context
    clients_match = re.search(r'number of clients: (\d+)', content)
    if clients_match:
        table_data['clients'] = int(clients_match.group(1))

    threads_match = re.search(r'number of threads: (\d+)', content)
    if threads_match:
        table_data['threads'] = int(threads_match.group(1))
        
    scale_match = re.search(r'scaling factor: (\d+)', content)
    if scale_match:
        table_data['scaling_factor'] = int(scale_match.group(1))

    return {
        "version": version,
        "plot": plot_data,
        "table": table_data
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse pgbench results to JSON.")
    parser.add_argument("input_file", help="Path to the pgbench output file")
    parser.add_argument("--output", help="Path to output JSON file (optional)")
    
    args = parser.parse_args()
    
    try:
        with open(args.input_file, 'r') as f:
            content = f.read()
            
        result = parse_pgbench(content)
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
        else:
            print(json.dumps(result, indent=2))
            
    except FileNotFoundError:
        print(f"Error: File not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)
