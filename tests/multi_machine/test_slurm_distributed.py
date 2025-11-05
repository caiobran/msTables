"""
SLURM Distributed Computing Tests

Tests for SLURM-compatible distributed computing system:
- Job submission and execution
- Multi-machine job distribution
- Remote execution via SSH
- Resource allocation
- Job monitoring
"""

import pytest
import time
from pathlib import Path
from datetime import datetime
import tempfile
import json

from src.infrastructure.slurm_distributed import (
    SLURMDistributedScheduler, SLURMJob, MachineResource
)


@pytest.fixture
def temp_config():
    """Create temporary config file"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config = {
            "machines": {
                "test_machine": {
                    "hostname": "test-host",
                    "ip": "127.0.0.1",
                    "cpus": 4,
                    "memory_gb": 8,
                    "gpu_available": False,
                    "ssh_user": "testuser"
                }
            }
        }
        json.dump(config, f)
        config_path = f.name
    
    yield config_path
    
    # Cleanup
    Path(config_path).unlink(missing_ok=True)


class TestSLURMScheduler:
    """Test SLURM scheduler initialization"""
    
    def test_scheduler_initialization(self, temp_config):
        """Test scheduler initialization"""
        scheduler = SLURMDistributedScheduler(config_path=temp_config)
        assert scheduler is not None
        assert scheduler.machines is not None
        assert len(scheduler.machines) > 0
    
    def test_machine_loading(self, temp_config):
        """Test machine configuration loading"""
        scheduler = SLURMDistributedScheduler(config_path=temp_config)
        
        # Check default machines loaded
        assert '5,1' in scheduler.machines or '7,1' in scheduler.machines or 'test_machine' in scheduler.machines
    
    def test_partition_configuration(self, temp_config):
        """Test partition configuration"""
        scheduler = SLURMDistributedScheduler(config_path=temp_config)
        
        assert 'compute' in scheduler.partitions
        assert 'debug' in scheduler.partitions
        assert 'long' in scheduler.partitions


class TestSLURMJobSubmission:
    """Test SLURM job submission"""
    
    def test_sbatch_job_submission(self, temp_config):
        """Test submitting a batch job"""
        scheduler = SLURMDistributedScheduler(config_path=temp_config)
        
        # Create test script
        script_content = """#!/bin/bash
#SBATCH --job-name=test_job
#SBATCH --partition=compute
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:05:00

echo "Hello from SLURM job!"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(script_content)
            script_path = f.name
        
        try:
            job_id = scheduler.sbatch(script_path)
            assert job_id > 0
            assert job_id in scheduler.jobs
            
            job = scheduler.jobs[job_id]
            assert job.name == "test_job"
            assert job.partition == "compute"
            assert job.status == "PENDING"
        finally:
            Path(script_path).unlink(missing_ok=True)
    
    def test_parse_slurm_directives(self, temp_config):
        """Test parsing SLURM directives"""
        scheduler = SLURMDistributedScheduler(config_path=temp_config)
        
        script = """#!/bin/bash
#SBATCH --job-name=my_job
#SBATCH --partition=debug
#SBATCH --nodes=2
#SBATCH --cpus-per-task=4
#SBATCH --time=1:00:00
#SBATCH --mem=8G

echo "Hello"
"""
        
        directives = scheduler._parse_slurm_directives(script)
        
        assert directives['job-name'] == "my_job"
        assert directives['partition'] == "debug"
        assert directives['nodes'] == "2"
        assert directives['cpus-per-task'] == "4"
        assert directives['time'] == "1:00:00"
        assert directives['mem'] == "8G"
    
    def test_extract_command(self, temp_config):
        """Test extracting command from script"""
        scheduler = SLURMDistributedScheduler(config_path=temp_config)
        
        script = """#!/bin/bash
#SBATCH --job-name=test

echo "Hello"
date
"""
        
        command = scheduler._extract_command(script)
        
        assert "echo" in command
        assert "date" in command
        assert "#SBATCH" not in command


class TestSLURMJobQueue:
    """Test SLURM job queue operations"""
    
    def test_squeue_empty(self, temp_config):
        """Test empty job queue"""
        scheduler = SLURMDistributedScheduler(config_path=temp_config)
        
        jobs = scheduler.squeue()
        assert isinstance(jobs, list)
    
    def test_squeue_with_jobs(self, temp_config):
        """Test job queue with jobs"""
        scheduler = SLURMDistributedScheduler(config_path=temp_config)
        
        # Create test job
        script_content = """#!/bin/bash
#SBATCH --job-name=test
echo "test"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(script_content)
            script_path = f.name
        
        try:
            job_id = scheduler.sbatch(script_path)
            jobs = scheduler.squeue()
            
            assert len(jobs) > 0
            assert any(job.job_id == job_id for job in jobs)
        finally:
            Path(script_path).unlink(missing_ok=True)
    
    def test_scancel_job(self, temp_config):
        """Test cancelling a job"""
        scheduler = SLURMDistributedScheduler(config_path=temp_config)
        
        # Create test job
        script_content = """#!/bin/bash
#SBATCH --job-name=test
echo "test"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(script_content)
            script_path = f.name
        
        try:
            job_id = scheduler.sbatch(script_path)
            
            # Cancel job
            result = scheduler.scancel(job_id)
            assert result is True
            
            # Verify job is cancelled
            job = scheduler.jobs[job_id]
            assert job.status == "CANCELLED"
        finally:
            Path(script_path).unlink(missing_ok=True)


class TestSLURMClusterInfo:
    """Test SLURM cluster information"""
    
    def test_sinfo_partitions(self, temp_config):
        """Test cluster partition information"""
        scheduler = SLURMDistributedScheduler(config_path=temp_config)
        
        info = scheduler.sinfo()
        
        assert 'partitions' in info
        assert 'compute' in info['partitions']
        assert 'debug' in info['partitions']
        assert 'long' in info['partitions']
    
    def test_sinfo_machines(self, temp_config):
        """Test cluster machine information"""
        scheduler = SLURMDistributedScheduler(config_path=temp_config)
        
        info = scheduler.sinfo()
        
        assert 'machines' in info
        assert len(info['machines']) > 0
    
    def test_machine_status_check(self, temp_config):
        """Test machine status checking"""
        scheduler = SLURMDistributedScheduler(config_path=temp_config)
        
        # Test status check (will be OFFLINE for non-existent machines)
        status = scheduler._check_machine_status("127.0.0.1", "testuser")
        assert status in ["ONLINE", "OFFLINE"]


class TestSLURMJobAccounting:
    """Test SLURM job accounting"""
    
    def test_sacct_empty(self, temp_config):
        """Test empty job accounting"""
        scheduler = SLURMDistributedScheduler(config_path=temp_config)
        
        jobs = scheduler.sacct()
        assert isinstance(jobs, list)
    
    def test_sacct_with_completed_jobs(self, temp_config):
        """Test job accounting with completed jobs"""
        scheduler = SLURMDistributedScheduler(config_path=temp_config)
        
        # Create and mark job as completed
        job = SLURMJob(
            job_id=1000,
            name="test_job",
            user="testuser",
            status="COMPLETED",
            time_limit="1:00:00",
            time_used="00:05:00",
            partition="compute",
            nodes=1,
            cpus=1,
            memory="1G",
            command="echo test",
            submit_time=datetime.now().isoformat(),
            start_time=datetime.now().isoformat(),
            end_time=datetime.now().isoformat(),
            exit_code=0,
            node_list="test-host",
            priority=0,
            qos="normal",
            dependency=None,
            array_job_id=None,
            array_task_id=None,
            assigned_machine="test-host",
            stdout_path=None,
            stderr_path=None
        )
        
        scheduler.jobs[1000] = job
        
        jobs = scheduler.sacct()
        
        assert len(jobs) > 0
        assert any(job.job_id == 1000 for job in jobs)


class TestSLURMMachineSelection:
    """Test machine selection for jobs"""
    
    def test_select_machine(self, temp_config):
        """Test selecting machine for job"""
        scheduler = SLURMDistributedScheduler(config_path=temp_config)
        
        # Create job
        job = SLURMJob(
            job_id=1000,
            name="test",
            user="testuser",
            status="PENDING",
            time_limit="1:00:00",
            time_used="00:00:00",
            partition="compute",
            nodes=1,
            cpus=1,
            memory="1G",
            command="echo test",
            submit_time=datetime.now().isoformat(),
            start_time="",
            end_time="",
            exit_code=None,
            node_list="",
            priority=0,
            qos="normal",
            dependency=None,
            array_job_id=None,
            array_task_id=None,
            assigned_machine=None,
            stdout_path=None,
            stderr_path=None
        )
        
        machine = scheduler._select_machine(job)
        
        # May be None if no machines are online
        assert machine is None or isinstance(machine, MachineResource)


class TestSLURMRemoteExecution:
    """Test remote job execution"""
    
    @pytest.mark.skip(reason="Requires SSH access to test machines")
    def test_execute_remote_command(self, temp_config):
        """Test executing command on remote machine"""
        scheduler = SLURMDistributedScheduler(config_path=temp_config)
        
        # Find online machine
        machine = None
        for m in scheduler.machines.values():
            if m.status == "ONLINE":
                machine = m
                break
        
        if not machine:
            pytest.skip("No online machines available")
        
        # Test remote execution
        exit_code = scheduler._execute_remote_command(
            machine,
            "echo 'test'",
            "/tmp/stdout.txt",
            "/tmp/stderr.txt"
        )
        
        # Should succeed or fail gracefully
        assert exit_code is not None

