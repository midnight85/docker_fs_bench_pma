import json
import sys
import argparse

def parse_fio(content):
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON content"}

    version = data.get("fio version", "unknown")
    
    # FIO job aggregation
    # Currently assumes single job or takes the first job as representative.
    
    jobs = data.get("jobs", [])
    if not jobs:
        return {"error": "No jobs found in FIO result"}

    # Initialize aggregators
    total_read_iops = 0.0
    total_write_iops = 0.0
    total_read_bw = 0.0
    total_write_bw = 0.0
    
    # Use first job metrics as representative for latency
    # Aggregating latency across multiple jobs requires weighted averages
    job = jobs[0]
    
    plot_data = {}
    table_data = {}
    
    # Job Options (Context)
    options = job.get("job options", {})
    table_data["job_name"] = job.get("jobname")
    table_data["rw_mode"] = options.get("rw")
    table_data["bs"] = options.get("bs")
    table_data["ioengine"] = options.get("ioengine")
    table_data["iodepth"] = options.get("iodepth", "1") # Default if not set, though usually it is
    
    # Read Stats
    read_stats = job.get("read", {})
    read_io_bytes = read_stats.get("io_bytes", 0)
    
    if read_io_bytes > 0:
        plot_data["read_iops"] = read_stats.get("iops", 0.0)
        # bw_bytes represents bandwidth in bytes/sec
        plot_data["read_bw_bytes"] = read_stats.get("bw_bytes", 0.0)
        
        plot_data["read_lat_ns_mean"] = read_stats.get("lat_ns", {}).get("mean", 0.0)
        
        table_data["read_io_bytes"] = read_io_bytes
        table_data["read_lat_ns_min"] = read_stats.get("lat_ns", {}).get("min", 0)
        table_data["read_lat_ns_max"] = read_stats.get("lat_ns", {}).get("max", 0)
        
        # Percentiles (clat_ns usually has percentiles)
        clat_ns = read_stats.get("clat_ns", {})
        percentiles = clat_ns.get("percentile", {})
        if "95.000000" in percentiles:
            table_data["read_lat_ns_p95"] = percentiles["95.000000"]
        if "99.000000" in percentiles:
            table_data["read_lat_ns_p99"] = percentiles["99.000000"]

    # Write Stats
    write_stats = job.get("write", {})
    write_io_bytes = write_stats.get("io_bytes", 0)
    
    if write_io_bytes > 0:
        plot_data["write_iops"] = write_stats.get("iops", 0.0)
        plot_data["write_bw_bytes"] = write_stats.get("bw_bytes", 0.0)
        plot_data["write_lat_ns_mean"] = write_stats.get("lat_ns", {}).get("mean", 0.0)
        
        table_data["write_io_bytes"] = write_io_bytes
        table_data["write_lat_ns_min"] = write_stats.get("lat_ns", {}).get("min", 0)
        table_data["write_lat_ns_max"] = write_stats.get("lat_ns", {}).get("max", 0)
        
        # Percentiles
        clat_ns = write_stats.get("clat_ns", {})
        percentiles = clat_ns.get("percentile", {})
        if "95.000000" in percentiles:
            table_data["write_lat_ns_p95"] = percentiles["95.000000"]
        if "99.000000" in percentiles:
            table_data["write_lat_ns_p99"] = percentiles["99.000000"]

    # General
    table_data["error"] = job.get("error", 0)

    return {
        "version": version,
        "plot": plot_data,
        "table": table_data
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse fio JSON results.")
    parser.add_argument("input_file", help="Path to the fio json output file")
    parser.add_argument("--output", help="Path to output JSON file (optional)")
    
    args = parser.parse_args()
    
    try:
        with open(args.input_file, 'r') as f:
            content = f.read()
            
        result = parse_fio(content)
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
        else:
            print(json.dumps(result, indent=2))
            
    except FileNotFoundError:
        print(f"Error: File not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)
