#!/usr/bin/env python3
import os
import json
import subprocess
import statistics
import sys
from collections import defaultdict

# Configuration
RESULTS_DIR = "results"
OUTPUT_FILE = os.path.join(RESULTS_DIR, "aggregated_report.json")
SCRIPTS_DIR = "scripts"
SYSTEM_INFO_DIR = os.path.join(RESULTS_DIR, "system_info")

def load_system_info():
    """Load system metadata from the system_info directory."""
    metadata_file = os.path.join(SYSTEM_INFO_DIR, "system_metadata.json")
    if os.path.exists(metadata_file):
        try:
            with open(metadata_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load system metadata: {e}", file=sys.stderr)
    return {}

# Map benchmark directory names (prefixes) to parser scripts
PARSER_MAP = {
    "sysbench-oltp": "parse_sysbench.py",
    "postgres-pgbench": "parse_pgbench.py",
    "webserver-bench": "parse_wrk.py",
    "fio-": "parse_fio.py" # Prefix match for fio
}

def get_parser_for_benchmark(benchmark_name):
    for key, script in PARSER_MAP.items():
        if benchmark_name.startswith(key):
            return os.path.join(SCRIPTS_DIR, script)
    return None

def run_parser(script_path, input_file):
    try:
        result = subprocess.run(
            [sys.executable, script_path, input_file],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_path} on {input_file}: {e.stderr}", file=sys.stderr)
        return None
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {script_path} on {input_file}", file=sys.stderr)
        return None

def calculate_average(scalar_lists):
    """
    Aggregates a dictionary of lists of scalars into mean values.
    Input: {'tps': [100, 110, 105], 'latency': [1.1, 1.2, 1.1]}
    Output: {'tps': 105.0, 'latency': 1.13}
    """
    aggregated = {}
    for metric, values in scalar_lists.items():
        # Filter out None or non-numeric values just in case
        valid_values = [v for v in values if isinstance(v, (int, float))]
        
        if not valid_values:
            continue
            
        if len(valid_values) > 1:
            mean = statistics.mean(valid_values)
            aggregated[metric] = round(mean, 4)
        else:
            aggregated[metric] = valid_values[0]
            
    return aggregated


def aggregate_table_data(table_lists):
    """
    Aggregates table data. 
    For numeric values, calculates the mean.
    For non-numeric values (strings), takes the first value (assuming they are identical across runs).
    """
    aggregated = {}
    for key, values in table_lists.items():
        # Check type
        if not values:
            continue
        
        if isinstance(values[0], (int, float)):
             valid_values = [v for v in values if isinstance(v, (int, float))]
             if valid_values:
                 aggregated[key] = round(statistics.mean(valid_values), 4)
        else:
            # Strings or other: just take the first one for now
            aggregated[key] = values[0]
    return aggregated

def main():
    if not os.path.exists(RESULTS_DIR):
        print(f"Results directory {RESULTS_DIR} not found.")
        sys.exit(1)

    # Structure: report[benchmark][filesystem] = { ... }
    report = defaultdict(lambda: defaultdict(dict))
    

    
    # helper for defaultdict
    def data_container():
        return {
            'metrics_plot': defaultdict(list),
            'metrics_table': defaultdict(list),
            'monitoring_plot': defaultdict(list),
            'monitoring_table': defaultdict(list),
            'docker_plot': defaultdict(list),
            'docker_table': defaultdict(list)
        }

    temp_data = defaultdict(lambda: defaultdict(data_container))
    
    # Storage for representative run (run_1) time series
    rep_data = defaultdict(lambda: defaultdict(dict))

    # Walk through results directory
    for benchmark in os.listdir(RESULTS_DIR):
        benchmark_path = os.path.join(RESULTS_DIR, benchmark)
        if not os.path.isdir(benchmark_path):
            continue
            
        parser_script = get_parser_for_benchmark(benchmark)
        if not parser_script:
            print(f"Skipping {benchmark}: No parser mapped.")
            continue
            
        print(f"Processing {benchmark}...")
        
        for filesystem in os.listdir(benchmark_path):
            fs_path = os.path.join(benchmark_path, filesystem)
            if not os.path.isdir(fs_path):
                continue
                
            for run in os.listdir(fs_path):
                run_path = os.path.join(fs_path, run)
                if not os.path.isdir(run_path):
                    continue
                
                # Identify input files
                workload_file = os.path.join(run_path, "results.txt")
                if "fio-" in benchmark:
                    workload_file = os.path.join(run_path, "result.json")
                
                docker_stats_file = os.path.join(run_path, "docker_stats.jsonl")
                iostat_file = os.path.join(run_path, "iostat.json")
                
                # 1. Parse Workload (Benchmarks) -> Metrics
                if os.path.exists(workload_file):
                    data = run_parser(parser_script, workload_file)
                    if data:
                        if "plot" in data:
                            for k, v in data["plot"].items():
                                temp_data[benchmark][filesystem]['metrics_plot'][k].append(v)
                        if "table" in data:
                            for k, v in data["table"].items():
                                temp_data[benchmark][filesystem]['metrics_table'][k].append(v)

                # 2. Parse Docker Stats -> Monitoring
                if os.path.exists(docker_stats_file):
                    data = run_parser(os.path.join(SCRIPTS_DIR, "parse_docker_stats.py"), docker_stats_file)
                    if data:
                        # Docker parser returns 'plot' (scalars) and 'series' (time series)
                        # Store separately to use simple aggregation (no _mean/_stddev)
                        if "plot" in data:
                            for k, v in data["plot"].items():
                                temp_data[benchmark][filesystem]['docker_plot'][k].append(v)
                                temp_data[benchmark][filesystem]['docker_table'][k].append(v)
                        
                        if run == "run_1" and "series" in data:
                            rep_data[benchmark][filesystem]['docker_stats_series'] = data["series"]

                # 3. Parse IOStat -> Monitoring
                if os.path.exists(iostat_file):
                    data = run_parser(os.path.join(SCRIPTS_DIR, "parse_iostat.py"), iostat_file)
                    if data:
                        # IOstat returns 'plot' (time series) and 'table' (scalars/averages)
                        if "table" in data:
                            for k, v in data["table"].items():
                                temp_data[benchmark][filesystem]['monitoring_plot'][k].append(v) # Treat avg stats as plot scalars
                                temp_data[benchmark][filesystem]['monitoring_table'][k].append(v)
                        
                        if run == "run_1" and "plot" in data:
                             rep_data[benchmark][filesystem]['iostat_series'] = data["plot"]

    # Final Aggregation
    print("Aggregating results...")
    for benchmark, fs_dict in temp_data.items():
        for filesystem, data_container in fs_dict.items():
            
            # Aggregate Benchmark Metrics
            metrics = {
                "plot": calculate_average(data_container['metrics_plot']),
                "table": aggregate_table_data(data_container['metrics_table'])
            }
            
            # Aggregate Docker metrics
            docker_metrics = {
                "plot": calculate_average(data_container['docker_plot']),
                "table": aggregate_table_data(data_container['docker_table']),
                "series": rep_data[benchmark][filesystem].get('docker_stats_series', {})
            }
            
            # Aggregate IOStat metrics
            iostat_metrics = {
                "plot": calculate_average(data_container['monitoring_plot']),
                "table": aggregate_table_data(data_container['monitoring_table']),
                "series": rep_data[benchmark][filesystem].get('iostat_series', {})
            }
            
            # Restructured monitoring with separate docker_stats and iostat sections
            monitoring = {
                "docker_stats": docker_metrics,
                "iostat": iostat_metrics
            }
            
            final_entry = {
                "metrics": metrics,
                "monitoring": monitoring
            }
            
            report[benchmark][filesystem] = final_entry
    # Load system information
    print("Loading system information...")
    system_info = load_system_info()

    # Write output with structure: {system_info: {}, data: {}}
    output = {
        "system_info": system_info,
        "data": dict(report)
    }
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"Aggregation complete. Report saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
