"""
SLURM-Compatible Distributed Computing System

Improved implementation for Data_Bench and mstables:
- True multi-machine job distribution
- SSH-based remote execution
- Resource allocation and monitoring
- Job dependencies and arrays
- Integration with fleet management

Based on lessons learned from Distribute_Computables project.
"""

import os
import sys
import json
import time
import subprocess
import threading
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import uuid
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SLURMJob:
    """SLURM-compatible job representation"""
    job_id: int
    name: str
    user: str
    status: str  # PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
    time_limit: str
    time_used: str
    partition: str
    nodes: int
    cpus: int
    memory: str
    command: str
    submit_time: str
    start_time: str
    end_time: str
    exit_code: Optional[int]
    node_list: str
    priority: int
    qos: str
    dependency: Optional[str]
    array_job_id: Optional[int]
    array_task_id: Optional[int]
    assigned_machine: Optional[str]
    stdout_path: Optional[str]
    stderr_path: Optional[str]


@dataclass
class MachineResource:
    """Machine resource information"""
    hostname: str
    ip: str
    cpus: int
    memory_gb: int
    gpu_available: bool
    status: str  # ONLINE, OFFLINE, BUSY
    current_jobs: int
    ssh_user: str
    ssh_key_path: Optional[str]


class SLURMDistributedScheduler:
    """SLURM-compatible distributed job scheduler"""
    
    def __init__(self, config_path: str = "config/fleet_config.json"):
        self.config_path = Path(config_path)
        self.machines = self._load_machine_config()
        self.jobs: Dict[int, SLURMJob] = {}
        self.job_counter = 1000
        self.job_lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # Partitions
        self.partitions = {
            "compute": {"default": True, "max_time": "7-00:00:00", "nodes": "ALL"},
            "debug": {"default": False, "max_time": "1-00:00:00", "nodes": "ALL"},
            "long": {"default": False, "max_time": "30-00:00:00", "nodes": "ALL"}
        }
        
        # Load existing jobs
        self._load_jobs()
        
        # Start job processor
        self._start_job_processor()
    
    def _load_machine_config(self) -> Dict[str, MachineResource]:
        """Load machine configuration from fleet config"""
        machines = {}
        
        # Default machines from mstables network setup
        default_machines = {
            '5,1': {
                'hostname': 'macpro.lan',
                'ip': '192.168.86.144',
                'cpus': 8,
                'memory_gb': 64,
                'gpu_available': True,
                'ssh_user': 'owner',
                'description': 'Mac Pro 5,1 with 64GB RAM, 2x4TB WD drives, GTX 6GB GPU'
            },
            '6,1': {
                'hostname': 'corns-mac-pro.lan',
                'ip': '192.168.86.133',
                'cpus': 12,
                'memory_gb': 32,
                'gpu_available': False,
                'ssh_user': 'owner',
                'description': 'Mac Pro 6,1 "trashcan"'
            },
            '7,1': {
                'hostname': 'mac-pro.lan',
                'ip': '192.168.86.143',
                'cpus': 32,
                'memory_gb': 192,
                'gpu_available': True,
                'ssh_user': 'xavier',
                'description': 'Mac Pro 7,1 (xavier)'
            },
            'macmini': {
                'hostname': 'corns-mac-pro-2.lan',
                'ip': '192.168.86.132',
                'cpus': 8,
                'memory_gb': 16,
                'gpu_available': False,
                'ssh_user': 'owner',
                'description': 'Mac mini'
            }
        }
        
        # Try to load from config file
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    if 'machines' in config:
                        default_machines.update(config['machines'])
            except Exception as e:
                logger.warning(f"Could not load config file: {e}")
        
        # Convert to MachineResource objects
        for machine_id, machine_info in default_machines.items():
            # Check machine status
            status = self._check_machine_status(
                machine_info['ip'],
                machine_info.get('ssh_user', 'xavier')
            )
            
            machines[machine_id] = MachineResource(
                hostname=machine_info['hostname'],
                ip=machine_info['ip'],
                cpus=machine_info['cpus'],
                memory_gb=machine_info['memory_gb'],
                gpu_available=machine_info.get('gpu_available', False),
                status=status,
                current_jobs=0,
                ssh_user=machine_info.get('ssh_user', 'xavier'),
                ssh_key_path=machine_info.get('ssh_key_path')
            )
        
        return machines
    
    def _check_machine_status(self, ip: str, user: str, timeout: int = 2) -> str:
        """Check if machine is online and accessible"""
        try:
            # Test SSH connection
            result = subprocess.run(
                ['ssh', '-o', 'ConnectTimeout=2', '-o', 'BatchMode=yes',
                 f'{user}@{ip}', 'echo "test"'],
                capture_output=True,
                timeout=timeout
            )
            return "ONLINE" if result.returncode == 0 else "OFFLINE"
        except:
            return "OFFLINE"
    
    def _load_jobs(self):
        """Load jobs from persistent storage"""
        jobs_file = Path("data/slurm_jobs.json")
        if jobs_file.exists():
            try:
                with open(jobs_file, 'r') as f:
                    jobs_data = json.load(f)
                    for job_data in jobs_data:
                        job = SLURMJob(**job_data)
                        self.jobs[job.job_id] = job
                        self.job_counter = max(self.job_counter, job.job_id + 1)
            except Exception as e:
                logger.warning(f"Could not load jobs: {e}")
    
    def _save_jobs(self):
        """Save jobs to persistent storage"""
        jobs_file = Path("data/slurm_jobs.json")
        jobs_file.parent.mkdir(parents=True, exist_ok=True)
        
        jobs_data = [asdict(job) for job in self.jobs.values()]
        with open(jobs_file, 'w') as f:
            json.dump(jobs_data, f, indent=2, default=str)
    
    def _start_job_processor(self):
        """Start background thread to process job queue"""
        def process_queue():
            while True:
                try:
                    # Find pending jobs
                    pending_jobs = [
                        job for job in self.jobs.values()
                        if job.status == "PENDING"
                    ]
                    
                    # Sort by priority and submit time
                    pending_jobs.sort(key=lambda x: (x.priority, x.submit_time))
                    
                    # Process jobs
                    for job in pending_jobs[:5]:  # Process up to 5 at a time
                        self._execute_job(job)
                    
                    time.sleep(1)  # Check every second
                except Exception as e:
                    logger.error(f"Error in job processor: {e}")
                    time.sleep(5)
        
        thread = threading.Thread(target=process_queue, daemon=True)
        thread.start()
    
    def _execute_job(self, job: SLURMJob):
        """Execute a job on an available machine"""
        # Find available machine
        machine = self._select_machine(job)
        if not machine:
            logger.warning(f"No available machine for job {job.job_id}")
            return
        
        # Update job status
        with self.job_lock:
            job.status = "RUNNING"
            job.start_time = datetime.now().isoformat()
            job.assigned_machine = machine.hostname
            job.node_list = machine.hostname
        
        # Update machine status
        machine.current_jobs += 1
        machine.status = "BUSY"
        
        # Execute job remotely
        def run_job():
            try:
                # Create output directories
                output_dir = Path(f"data/slurm_output/{job.job_id}")
                output_dir.mkdir(parents=True, exist_ok=True)
                job.stdout_path = str(output_dir / "stdout.txt")
                job.stderr_path = str(output_dir / "stderr.txt")
                
                # Execute command via SSH
                exit_code = self._execute_remote_command(
                    machine,
                    job.command,
                    job.stdout_path,
                    job.stderr_path
                )
                
                # Update job status
                with self.job_lock:
                    job.status = "COMPLETED" if exit_code == 0 else "FAILED"
                    job.end_time = datetime.now().isoformat()
                    job.exit_code = exit_code
                    
                    # Calculate time used
                    if job.start_time:
                        start = datetime.fromisoformat(job.start_time)
                        end = datetime.now()
                        duration = end - start
                        job.time_used = str(duration).split('.')[0]
                
                # Update machine status
                machine.current_jobs -= 1
                machine.status = "ONLINE" if machine.current_jobs == 0 else "BUSY"
                
                # Save jobs
                self._save_jobs()
                
            except Exception as e:
                logger.error(f"Error executing job {job.job_id}: {e}")
                with self.job_lock:
                    job.status = "FAILED"
                    job.end_time = datetime.now().isoformat()
                    job.exit_code = -1
                machine.current_jobs -= 1
                machine.status = "ONLINE"
                self._save_jobs()
        
        # Execute in thread pool
        self.executor.submit(run_job)
    
    def _select_machine(self, job: SLURMJob) -> Optional[MachineResource]:
        """Select best available machine for job"""
        # Filter available machines
        available = [
            m for m in self.machines.values()
            if m.status == "ONLINE" and m.current_jobs < 5  # Max 5 concurrent jobs
        ]
        
        if not available:
            return None
        
        # Select machine based on resources needed
        # For now, select machine with most available resources
        if job.cpus > 1:
            available.sort(key=lambda x: x.cpus, reverse=True)
        elif job.memory and "G" in job.memory:
            memory_gb = int(job.memory.replace("G", ""))
            available = [m for m in available if m.memory_gb >= memory_gb]
            if available:
                available.sort(key=lambda x: x.memory_gb, reverse=True)
        
        return available[0] if available else None
    
    def _execute_remote_command(self, machine: MachineResource, command: str,
                                stdout_path: str, stderr_path: str) -> int:
        """Execute command on remote machine via SSH"""
        try:
            # Build SSH command
            ssh_cmd = ['ssh', '-o', 'ConnectTimeout=10']
            
            if machine.ssh_key_path:
                ssh_cmd.extend(['-i', machine.ssh_key_path])
            
            ssh_cmd.append(f'{machine.ssh_user}@{machine.ip}')
            
            # Execute command
            with open(stdout_path, 'w') as stdout_file, \
                 open(stderr_path, 'w') as stderr_file:
                result = subprocess.run(
                    ssh_cmd + [command],
                    stdout=stdout_file,
                    stderr=stderr_file,
                    timeout=3600  # 1 hour timeout
                )
                return result.returncode
        except subprocess.TimeoutExpired:
            logger.error(f"Job timeout on {machine.hostname}")
            return -1
        except Exception as e:
            logger.error(f"Error executing remote command: {e}")
            return -1
    
    def sbatch(self, script_path: str, **options) -> int:
        """Submit a batch job (equivalent to sbatch)"""
        try:
            with open(script_path, 'r') as f:
                script_content = f.read()
            
            # Parse SLURM directives
            directives = self._parse_slurm_directives(script_content)
            
            # Extract command from script
            command = self._extract_command(script_content)
            
            # Create job
            with self.job_lock:
                job_id = self.job_counter
                self.job_counter += 1
            
            job = SLURMJob(
                job_id=job_id,
                name=directives.get('job-name', f"job_{job_id}"),
                user=os.getenv('USER', 'unknown'),
                status="PENDING",
                time_limit=directives.get('time', '7-00:00:00'),
                time_used="00:00:00",
                partition=directives.get('partition', 'compute'),
                nodes=int(directives.get('nodes', 1)),
                cpus=int(directives.get('cpus-per-task', 1)),
                memory=directives.get('mem', '1G'),
                command=command,
                submit_time=datetime.now().isoformat(),
                start_time="",
                end_time="",
                exit_code=None,
                node_list="",
                priority=int(directives.get('priority', 0)),
                qos=directives.get('qos', 'normal'),
                dependency=directives.get('dependency'),
                array_job_id=None,
                array_task_id=None,
                assigned_machine=None,
                stdout_path=None,
                stderr_path=None
            )
            
            with self.job_lock:
                self.jobs[job_id] = job
            
            self._save_jobs()
            
            logger.info(f"Submitted batch job {job_id}")
            return job_id
            
        except Exception as e:
            logger.error(f"Error submitting job: {e}")
            return -1
    
    def _parse_slurm_directives(self, script_content: str) -> Dict[str, str]:
        """Parse SLURM directives from script"""
        directives = {}
        lines = script_content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('#SBATCH'):
                parts = line.split()
                if len(parts) >= 2:
                    directive = parts[1]
                    if directive.startswith('--'):
                        directive = directive[2:]
                        if len(parts) >= 3:
                            value = parts[2]
                            directives[directive] = value
        
        return directives
    
    def _extract_command(self, script_content: str) -> str:
        """Extract command from SLURM script"""
        lines = script_content.split('\n')
        command_lines = []
        in_command = False
        
        for line in lines:
            line = line.strip()
            if not line.startswith('#') and line:
                in_command = True
                command_lines.append(line)
            elif in_command and line.startswith('#'):
                continue
        
        return '\n'.join(command_lines) if command_lines else script_content
    
    def squeue(self, **options) -> List[SLURMJob]:
        """Show job queue (equivalent to squeue)"""
        with self.job_lock:
            jobs = [job for job in self.jobs.values()
                   if job.status in ["PENDING", "RUNNING"]]
        return jobs
    
    def sinfo(self, **options) -> Dict[str, Any]:
        """Show cluster information (equivalent to sinfo)"""
        # Update machine statuses
        for machine in self.machines.values():
            machine.status = self._check_machine_status(machine.ip, machine.ssh_user)
        
        # Build partition info
        partitions = {}
        for partition_name, partition_config in self.partitions.items():
            online_machines = [
                m for m in self.machines.values()
                if m.status == "ONLINE"
            ]
            
            partitions[partition_name] = {
                "avail": "up",
                "timelimit": partition_config['max_time'],
                "nodes": len(online_machines),
                "state": "idle" if all(m.current_jobs == 0 for m in online_machines) else "mixed",
                "nodelist": ",".join([m.hostname for m in online_machines])
            }
        
        return {
            "partitions": partitions,
            "machines": {k: {
                "hostname": m.hostname,
                "ip": m.ip,
                "cpus": m.cpus,
                "memory_gb": m.memory_gb,
                "status": m.status,
                "current_jobs": m.current_jobs
            } for k, m in self.machines.items()},
            "timestamp": datetime.now().isoformat()
        }
    
    def scancel(self, job_id: int) -> bool:
        """Cancel a job (equivalent to scancel)"""
        with self.job_lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                if job.status in ["PENDING", "RUNNING"]:
                    job.status = "CANCELLED"
                    job.end_time = datetime.now().isoformat()
                    self._save_jobs()
                    logger.info(f"Job {job_id} cancelled")
                    return True
        return False
    
    def sacct(self, **options) -> List[SLURMJob]:
        """Show accounting data (equivalent to sacct)"""
        with self.job_lock:
            jobs = [
                job for job in self.jobs.values()
                if job.status in ["COMPLETED", "FAILED", "CANCELLED"]
            ]
        return jobs


def main():
    """Main CLI interface"""
    if len(sys.argv) < 2:
        print("Usage: python slurm_distributed.py <command> [options]")
        print("Commands: sbatch, squeue, sinfo, scancel, sacct")
        sys.exit(1)
    
    command = sys.argv[1]
    scheduler = SLURMDistributedScheduler()
    
    if command == "sbatch":
        if len(sys.argv) < 3:
            print("Usage: sbatch <script>")
            sys.exit(1)
        script_path = sys.argv[2]
        job_id = scheduler.sbatch(script_path)
        if job_id > 0:
            print(f"Submitted batch job {job_id}")
        else:
            print("Job submission failed")
            sys.exit(1)
    
    elif command == "squeue":
        jobs = scheduler.squeue()
        print("JOBID PARTITION     NAME     USER    STATE       TIME TIME_LIMIT  NODE NODELIST(REASON)")
        print("----- ---------- ---------- -------- ---------- ------ ---------- ---- ------------------")
        for job in jobs:
            print(f"{job.job_id:5d} {job.partition:10s} {job.name:9s} {job.user:8s} {job.status:10s} {job.time_used:6s} {job.time_limit:10s} {job.nodes:4d} {job.node_list}")
    
    elif command == "sinfo":
        info = scheduler.sinfo()
        print("PARTITION AVAIL  TIMELIMIT  NODES  STATE NODELIST")
        print("---------- -----  ----------  -----  ----- --------")
        for partition, details in info.get('partitions', {}).items():
            print(f"{partition:10s} {details['avail']:5s} {details['timelimit']:10s} {details['nodes']:6d} {details['state']:6s} {details['nodelist']}")
        print("\nMachines:")
        for machine_id, machine_info in info.get('machines', {}).items():
            print(f"  {machine_info['hostname']:20s} {machine_info['ip']:15s} {machine_info['status']:8s} {machine_info['current_jobs']:2d} jobs")
    
    elif command == "scancel":
        if len(sys.argv) < 3:
            print("Usage: scancel <job_id>")
            sys.exit(1)
        job_id = int(sys.argv[2])
        if scheduler.scancel(job_id):
            print(f"Job {job_id} cancelled")
        else:
            print(f"Failed to cancel job {job_id}")
            sys.exit(1)
    
    elif command == "sacct":
        jobs = scheduler.sacct()
        print("JobID    JobName  Partition    Account  AllocCPUS      State ExitCode")
        print("--------- -------- ---------- ---------- ---------- ---------- --------")
        for job in jobs:
            print(f"{job.job_id:9d} {job.name:8s} {job.partition:10s} {job.user:9s} {job.cpus:10d} {job.status:10s} {job.exit_code or 'N/A':8s}")
    
    else:
        print(f"Unknown command: {command}")
        print("Available commands: sbatch, squeue, sinfo, scancel, sacct")
        sys.exit(1)


if __name__ == "__main__":
    main()

