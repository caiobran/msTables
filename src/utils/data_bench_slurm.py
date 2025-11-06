"""
Data_Bench SLURM Integration

Integration layer for Data_Bench to use SLURM-compatible distributed computing.
Provides high-level interface for distributed financial data processing.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
import logging

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.infrastructure.slurm_distributed import SLURMDistributedScheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataBenchSLURM:
    """Data_Bench integration with SLURM distributed computing"""
    
    def __init__(self, config_path: str = "config/fleet_config.json"):
        """Initialize Data_Bench SLURM integration"""
        self.scheduler = SLURMDistributedScheduler(config_path=config_path)
        self.job_templates = {}
    
    def submit_data_processing_job(self, script_path: str, 
                                   partition: str = "compute",
                                   cpus: int = 1,
                                   memory: str = "4G",
                                   time_limit: str = "1:00:00") -> int:
        """
        Submit a data processing job
        
        Args:
            script_path: Path to processing script
            partition: SLURM partition (compute, debug, long)
            cpus: Number of CPUs
            memory: Memory requirement (e.g., "4G", "8G")
            time_limit: Time limit (e.g., "1:00:00")
        
        Returns:
            Job ID
        """
        # Create SLURM script wrapper
        slurm_script = self._create_slurm_script(
            script_path,
            partition=partition,
            cpus=cpus,
            memory=memory,
            time_limit=time_limit
        )
        
        # Submit job
        job_id = self.scheduler.sbatch(slurm_script)
        logger.info(f"Submitted data processing job {job_id}")
        return job_id
    
    def submit_batch_processing(self, data_files: List[str],
                               processor: Callable,
                               partition: str = "compute",
                               cpus_per_job: int = 1,
                               memory_per_job: str = "4G") -> List[int]:
        """
        Submit batch processing jobs for multiple files
        
        Args:
            data_files: List of data file paths to process
            processor: Processing function or script path
            partition: SLURM partition
            cpus_per_job: CPUs per job
            memory_per_job: Memory per job
        
        Returns:
            List of job IDs
        """
        job_ids = []
        
        for data_file in data_files:
            # Create processing script for this file
            script_content = self._create_processing_script(data_file, processor)
            
            # Save script
            script_path = Path(f"data/slurm_scripts/process_{Path(data_file).stem}.sh")
            script_path.parent.mkdir(parents=True, exist_ok=True)
            script_path.write_text(script_content)
            
            # Submit job
            job_id = self.submit_data_processing_job(
                str(script_path),
                partition=partition,
                cpus=cpus_per_job,
                memory=memory_per_job
            )
            job_ids.append(job_id)
        
        logger.info(f"Submitted {len(job_ids)} batch processing jobs")
        return job_ids
    
    def submit_parallel_analysis(self, symbols: List[str],
                                 analysis_type: str = "backtest",
                                 partition: str = "compute",
                                 cpus_per_job: int = 2,
                                 memory_per_job: str = "8G") -> List[int]:
        """
        Submit parallel analysis jobs for multiple symbols
        
        Args:
            symbols: List of stock symbols to analyze
            analysis_type: Type of analysis (backtest, prediction, etc.)
            partition: SLURM partition
            cpus_per_job: CPUs per job
            memory_per_job: Memory per job
        
        Returns:
            List of job IDs
        """
        job_ids = []
        
        for symbol in symbols:
            # Create analysis script
            script_content = f"""#!/bin/bash
#SBATCH --job-name={analysis_type}_{symbol}
#SBATCH --partition={partition}
#SBATCH --cpus-per-task={cpus_per_job}
#SBATCH --mem={memory_per_job}
#SBATCH --time=2:00:00

python3 -c "
from src.analysis.market_analyzer import MarketAnalyzer
from src.analysis.market_predictor import MarketPredictor
from src.backtesting.advanced_backtester import AdvancedBacktester

symbol = '{symbol}'
analysis_type = '{analysis_type}'

if analysis_type == 'backtest':
    backtester = AdvancedBacktester()
    results = backtester.run_backtest(symbol)
    print(f'Backtest results for {{symbol}}: {{results}}')
elif analysis_type == 'prediction':
    predictor = MarketPredictor()
    prediction = predictor.predict(symbol)
    print(f'Prediction for {{symbol}}: {{prediction}}')
else:
    analyzer = MarketAnalyzer()
    analysis = analyzer.analyze(symbol)
    print(f'Analysis for {{symbol}}: {{analysis}}')
"
"""
            
            # Save script
            script_path = Path(f"data/slurm_scripts/{analysis_type}_{symbol}.sh")
            script_path.parent.mkdir(parents=True, exist_ok=True)
            script_path.write_text(script_content)
            
            # Submit job
            job_id = self.scheduler.sbatch(str(script_path))
            job_ids.append(job_id)
        
        logger.info(f"Submitted {len(job_ids)} parallel analysis jobs")
        return job_ids
    
    def wait_for_jobs(self, job_ids: List[int], timeout: Optional[int] = None) -> Dict[int, bool]:
        """
        Wait for jobs to complete
        
        Args:
            job_ids: List of job IDs to wait for
            timeout: Optional timeout in seconds
        
        Returns:
            Dictionary mapping job_id to success status
        """
        import time
        start_time = time.time()
        results = {}
        
        while job_ids:
            # Check job status
            for job_id in job_ids[:]:
                job = self.scheduler.jobs.get(job_id)
                if job:
                    if job.status == "COMPLETED":
                        results[job_id] = job.exit_code == 0
                        job_ids.remove(job_id)
                    elif job.status == "FAILED":
                        results[job_id] = False
                        job_ids.remove(job_id)
                    elif job.status == "CANCELLED":
                        results[job_id] = False
                        job_ids.remove(job_id)
            
            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                logger.warning(f"Timeout waiting for jobs: {job_ids}")
                for job_id in job_ids:
                    results[job_id] = False
                break
            
            if job_ids:
                time.sleep(1)
        
        return results
    
    def get_job_status(self, job_id: int) -> Dict[str, Any]:
        """Get status of a job"""
        job = self.scheduler.jobs.get(job_id)
        if not job:
            return {"status": "NOT_FOUND"}
        
        return {
            "job_id": job.job_id,
            "name": job.name,
            "status": job.status,
            "assigned_machine": job.assigned_machine,
            "start_time": job.start_time,
            "end_time": job.end_time,
            "time_used": job.time_used,
            "exit_code": job.exit_code,
            "stdout_path": job.stdout_path,
            "stderr_path": job.stderr_path
        }
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get cluster status information"""
        return self.scheduler.sinfo()
    
    def _create_slurm_script(self, script_path: str, **kwargs) -> str:
        """Create SLURM script wrapper"""
        script_content = f"""#!/bin/bash
#SBATCH --job-name=data_processing
#SBATCH --partition={kwargs.get('partition', 'compute')}
#SBATCH --cpus-per-task={kwargs.get('cpus', 1)}
#SBATCH --mem={kwargs.get('memory', '4G')}
#SBATCH --time={kwargs.get('time_limit', '1:00:00')}

# Execute the processing script
{Path(script_path).read_text()}
"""
        
        # Save script
        slurm_script_path = Path(f"data/slurm_scripts/wrapper_{Path(script_path).stem}.sh")
        slurm_script_path.parent.mkdir(parents=True, exist_ok=True)
        slurm_script_path.write_text(script_content)
        
        return str(slurm_script_path)
    
    def _create_processing_script(self, data_file: str, processor: Callable) -> str:
        """Create processing script for a data file"""
        if isinstance(processor, str):
            # Processor is a script path
            return f"""#!/bin/bash
# Process {data_file}
python3 {processor} {data_file}
"""
        else:
            # Processor is a function - create Python script
            # This is a simplified version - in practice, you'd serialize the function
            return f"""#!/bin/bash
# Process {data_file}
python3 -c "
import sys
sys.path.append('src')
from src.utils.data_processor import process_file
process_file('{data_file}')
"
"""


def main():
    """Example usage"""
    bench = DataBenchSLURM()
    
    # Check cluster status
    status = bench.get_cluster_status()
    print("Cluster Status:")
    print(f"  Machines: {len(status['machines'])}")
    print(f"  Partitions: {list(status['partitions'].keys())}")
    
    # Submit a test job
    test_script = """#!/bin/bash
echo "Hello from Data_Bench SLURM!"
date
"""
    
    script_path = Path("data/slurm_scripts/test.sh")
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(test_script)
    
    job_id = bench.submit_data_processing_job(str(script_path))
    print(f"Submitted job {job_id}")
    
    # Wait for completion
    results = bench.wait_for_jobs([job_id], timeout=60)
    print(f"Job {job_id} completed: {results[job_id]}")


if __name__ == "__main__":
    main()

