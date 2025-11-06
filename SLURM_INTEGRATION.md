# SLURM Integration for Data_Bench and mstables

## Overview

This document describes the improved SLURM-compatible distributed computing system for Data_Bench and mstables, based on lessons learned from the Distribute_Computables project.

## Key Improvements

### 1. **True Multi-Machine Execution**
- **Before**: Jobs ran only on controller machine
- **After**: Jobs are distributed across available machines via SSH
- **Implementation**: `SLURMDistributedScheduler` with machine selection and remote execution

### 2. **SSH-Based Remote Execution**
- **Before**: Local execution only
- **After**: Remote execution via SSH with proper authentication
- **Implementation**: `_execute_remote_command()` method with SSH key support

### 3. **Resource Allocation**
- **Before**: No resource-based machine selection
- **After**: Machine selection based on CPU, memory, and GPU requirements
- **Implementation**: `_select_machine()` with resource-aware selection

### 4. **Job Monitoring**
- **Before**: Basic job status tracking
- **After**: Comprehensive job monitoring with stdout/stderr capture
- **Implementation**: Per-job output directories and status tracking

### 5. **Data_Bench Integration**
- **Before**: No Data_Bench integration
- **After**: High-level API for Data_Bench distributed processing
- **Implementation**: `DataBenchSLURM` class with batch processing support

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Data_Bench / mstables Application            │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              DataBenchSLURM (High-Level API)            │
│  • submit_data_processing_job()                         │
│  • submit_batch_processing()                           │
│  • submit_parallel_analysis()                            │
│  • wait_for_jobs()                                       │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│         SLURMDistributedScheduler (Core Engine)          │
│  • sbatch() - Submit jobs                               │
│  • squeue() - View queue                                │
│  • sinfo() - Cluster info                               │
│  • scancel() - Cancel jobs                              │
│  • sacct() - Job accounting                             │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Machine Resource Management                 │
│  • Machine discovery                                    │
│  • Status monitoring                                    │
│  • Resource allocation                                  │
│  • SSH connectivity                                     │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Distributed Execution Layer                 │
│  • SSH remote execution                                 │
│  • Output capture (stdout/stderr)                       │
│  • Job status tracking                                  │
│  • Error handling                                       │
└─────────────────────────────────────────────────────────┘
```

## Usage Examples

### Basic Job Submission

```python
from src.utils.data_bench_slurm import DataBenchSLURM

# Initialize
bench = DataBenchSLURM()

# Submit a data processing job
job_id = bench.submit_data_processing_job(
    script_path="scripts/process_data.py",
    partition="compute",
    cpus=4,
    memory="8G",
    time_limit="2:00:00"
)

# Wait for completion
results = bench.wait_for_jobs([job_id], timeout=3600)
print(f"Job {job_id} completed: {results[job_id]}")
```

### Batch Processing

```python
# Submit multiple files for processing
data_files = [
    "data/raw/file1.csv",
    "data/raw/file2.csv",
    "data/raw/file3.csv"
]

job_ids = bench.submit_batch_processing(
    data_files=data_files,
    processor="scripts/process_file.py",
    partition="compute",
    cpus_per_job=2,
    memory_per_job="4G"
)

# Wait for all jobs
results = bench.wait_for_jobs(job_ids, timeout=3600)
```

### Parallel Analysis

```python
# Submit parallel analysis for multiple symbols
symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

job_ids = bench.submit_parallel_analysis(
    symbols=symbols,
    analysis_type="backtest",
    partition="compute",
    cpus_per_job=4,
    memory_per_job="8G"
)

# Monitor progress
for job_id in job_ids:
    status = bench.get_job_status(job_id)
    print(f"Job {job_id}: {status['status']} on {status['assigned_machine']}")
```

### Command Line Interface

```bash
# Check cluster status
python src/infrastructure/slurm_distributed.py sinfo

# Submit a job
python src/infrastructure/slurm_distributed.py sbatch my_script.sh

# View job queue
python src/infrastructure/slurm_distributed.py squeue

# Cancel a job
python src/infrastructure/slurm_distributed.py scancel 1000

# View job history
python src/infrastructure/slurm_distributed.py sacct
```

## Configuration

### Machine Configuration

Create `config/fleet_config.json`:

```json
{
  "machines": {
    "5,1": {
      "hostname": "macpro.lan",
      "ip": "192.168.86.144",
      "cpus": 8,
      "memory_gb": 64,
      "gpu_available": true,
      "ssh_user": "owner",
      "ssh_key_path": "/path/to/ssh/key"
    },
    "7,1": {
      "hostname": "mac-pro.lan",
      "ip": "192.168.86.143",
      "cpus": 32,
      "memory_gb": 192,
      "gpu_available": true,
      "ssh_user": "xavier"
    }
  }
}
```

### SLURM Script Template

```bash
#!/bin/bash
#SBATCH --job-name=my_job
#SBATCH --partition=compute
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=2:00:00

# Your processing code here
python3 scripts/process_data.py
```

## Testing

### Run Tests

```bash
# Run SLURM distributed tests
pytest tests/multi_machine/test_slurm_distributed.py -v

# Run comprehensive multi-machine tests
pytest tests/multi_machine/ -v

# Run all tests
pytest tests/ -v
```

### Test Coverage

- ✅ Job submission and execution
- ✅ Multi-machine job distribution
- ✅ Remote execution via SSH
- ✅ Resource allocation
- ✅ Job monitoring and status tracking
- ✅ Job cancellation
- ✅ Cluster information
- ✅ Job accounting

## Integration with mstables

### Financial Data Processing

```python
from src.utils.data_bench_slurm import DataBenchSLURM

bench = DataBenchSLURM()

# Submit stock price import jobs
symbols = ["AAPL", "MSFT", "GOOGL"]
job_ids = bench.submit_parallel_analysis(
    symbols=symbols,
    analysis_type="import_prices",
    partition="compute",
    cpus_per_job=2,
    memory_per_job="4G"
)

# Wait for completion
results = bench.wait_for_jobs(job_ids)
```

### Backtesting

```python
# Submit parallel backtesting jobs
strategies = ["buy_and_hold", "momentum", "mean_reversion"]
job_ids = []

for strategy in strategies:
    job_id = bench.submit_data_processing_job(
        script_path=f"scripts/backtest_{strategy}.py",
        partition="compute",
        cpus=4,
        memory="8G",
        time_limit="4:00:00"
    )
    job_ids.append(job_id)

# Monitor progress
for job_id in job_ids:
    status = bench.get_job_status(job_id)
    print(f"{status['name']}: {status['status']}")
```

## Troubleshooting

### SSH Connection Issues

1. **Test SSH connectivity**:
   ```bash
   ssh -o ConnectTimeout=5 user@machine_ip "echo 'test'"
   ```

2. **Check SSH keys**:
   ```bash
   ssh-keygen -t rsa
   ssh-copy-id user@machine_ip
   ```

3. **Update machine configuration**:
   - Ensure correct IP addresses
   - Verify SSH user names
   - Add SSH key paths if needed

### Job Execution Issues

1. **Check job status**:
   ```python
   status = bench.get_job_status(job_id)
   print(status)
   ```

2. **View job output**:
   ```bash
   cat data/slurm_output/{job_id}/stdout.txt
   cat data/slurm_output/{job_id}/stderr.txt
   ```

3. **Check machine status**:
   ```python
   cluster_status = bench.get_cluster_status()
   print(cluster_status)
   ```

## Next Steps

1. **GPU Support**: Add GPU resource allocation and job scheduling
2. **Job Dependencies**: Implement job dependency chains
3. **Job Arrays**: Support SLURM job arrays for parallel tasks
4. **Monitoring Dashboard**: Create web-based monitoring dashboard
5. **Resource Limits**: Enforce CPU and memory limits per job
6. **Load Balancing**: Implement intelligent load balancing across machines

## References

- [SLURM Documentation](https://slurm.schedmd.com/documentation.html)
- [Distribute_Computables Project](../Distribute_Computables/)
- [mstables Multi-Machine Tests](../tests/multi_machine/)

