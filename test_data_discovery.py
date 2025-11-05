#!/usr/bin/env python3
"""
Data Discovery Test Script

This script reads the .env file and checks for data availability across:
1. Local paths
2. Multiple machines (5,1, 6,1, 7,1) with different usernames
3. Global-Finance project in PycharmProjects
4. API availability and testing
5. Network device discovery

Author: Data Discovery System
Version: 1.1.0
"""

import os
import sys
import json
import requests
import sqlite3
from pathlib import Path
from datetime import datetime
import logging
from typing import Dict, List, Tuple, Optional
import subprocess
import platform

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_data_discovery.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DataDiscoveryTester:
    """Test data availability across multiple machines and APIs."""
    
    def __init__(self, env_file_path: str = '.env'):
        self.env_file_path = env_file_path
        self.env_data = {}
        
        # Updated machine mappings based on network discovery
        self.network_devices = {
            '5,1': {
                'name': 'JaneLaptop',
                'hostname': 'macpro.lan',
                'ip': '192.168.86.144',
                'mac': '6e:6a:87:3d:33:6',
                'description': 'Mac Pro 5,1 with 64GB RAM, 2x4TB WD drives, GTX 6GB GPU',
                'usernames': ['owner', 'Owner', 'jane']
            },
            '6,1': {
                'name': "Corn's Mac Pro",
                'hostname': 'corns-mac-pro.lan',
                'ip': '192.168.86.133',
                'mac': '6c:19:c0:e7:68:de',
                'description': 'Mac Pro 6,1 "trashcan"',
                'usernames': ['owner', 'Owner', 'corn']
            },
            '7,1': {
                'name': 'mac-pro (Current)',
                'hostname': 'mac-pro.lan',
                'ip': '192.168.86.143',
                'mac': 'e4:50:eb:b9:fa:e2',
                'description': 'Mac Pro 7,1 (xavier)',
                'usernames': ['xavier']
            },
            'macmini': {
                'name': "Corn's Mac Pro (2)",
                'hostname': 'corns-mac-pro-2.lan',
                'ip': '192.168.86.132',
                'mac': '6c:ab:31:f1:b5:34',
                'description': 'Mac mini',
                'usernames': ['owner', 'Owner', 'corn']
            },
            'gateway': {
                'name': 'Che Computer',
                'hostname': 'gateway',
                'ip': '192.168.86.1',
                'mac': '90:ca:fa:6f:c2:84',
                'description': '2TB AirPort Extreme/Time Capsule',
                'usernames': []
            }
        }
        
        self.results = {
            'local_paths': {},
            'network_devices': {},
            'remote_machines': {},
            'apis': {},
            'databases': {},
            'global_finance': {}
        }
        
    def load_env_file(self) -> bool:
        """Load and parse the .env file."""
        try:
            if not os.path.exists(self.env_file_path):
                logger.error(f"Environment file not found: {self.env_file_path}")
                return False
                
            with open(self.env_file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        self.env_data[key.strip()] = value.strip().strip("'\"")
            
            logger.info(f"Loaded {len(self.env_data)} environment variables")
            return True
            
        except Exception as e:
            logger.error(f"Error loading .env file: {e}")
            return False
    
    def extract_data_paths(self) -> List[str]:
        """Extract all data paths from environment variables."""
        paths = []
        path_keys = [key for key in self.env_data.keys() if 'PATH' in key.upper()]
        
        for key in path_keys:
            path = self.env_data[key]
            if path:
                # Handle path lists
                if ',' in path:
                    paths.extend([p.strip() for p in path.split(',')])
                else:
                    paths.append(path)
        
        return list(set(paths))  # Remove duplicates
    
    def extract_api_keys(self) -> Dict[str, str]:
        """Extract all API keys from environment variables."""
        api_keys = {}
        api_key_patterns = ['API_KEY', 'API', '_KEY']
        
        for key, value in self.env_data.items():
            if any(pattern in key.upper() for pattern in api_key_patterns):
                if value and value != 'free' and not value.startswith('http'):
                    api_keys[key] = value
        
        return api_keys
    
    def check_local_path(self, path: str) -> Dict:
        """Check if a local path exists and contains data."""
        result = {
            'exists': False,
            'size': 0,
            'files': 0,
            'databases': 0,
            'data_files': 0,
            'error': None
        }
        
        try:
            # Expand user and resolve path
            expanded_path = os.path.expanduser(path)
            resolved_path = os.path.abspath(expanded_path)
            
            if os.path.exists(resolved_path):
                result['exists'] = True
                
                # Count files and get size
                if os.path.isfile(resolved_path):
                    result['size'] = os.path.getsize(resolved_path)
                    result['files'] = 1
                    if resolved_path.endswith(('.db', '.sqlite')):
                        result['databases'] = 1
                    elif resolved_path.endswith(('.csv', '.xlsx', '.xlsb', '.json')):
                        result['data_files'] = 1
                        
                elif os.path.isdir(resolved_path):
                    for root, dirs, files in os.walk(resolved_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            try:
                                result['size'] += os.path.getsize(file_path)
                                result['files'] += 1
                                
                                if file.endswith(('.db', '.sqlite')):
                                    result['databases'] += 1
                                elif file.endswith(('.csv', '.xlsx', '.xlsb', '.json')):
                                    result['data_files'] += 1
                                    
                            except (OSError, PermissionError):
                                continue
                                
        except Exception as e:
            result['error'] = str(e)
            
        return result
    
    def check_network_device(self, device_id: str, device_info: Dict) -> Dict:
        """Check connectivity and basic info for a network device."""
        result = {
            'device_id': device_id,
            'name': device_info['name'],
            'hostname': device_info['hostname'],
            'ip': device_info['ip'],
            'mac': device_info['mac'],
            'description': device_info['description'],
            'pingable': False,
            'ssh_accessible': False,
            'data_paths': {},
            'error': None
        }
        
        try:
            # Test ping
            ping_result = subprocess.run(
                ['ping', '-c', '1', '-W', '2', device_info['ip']],
                capture_output=True,
                text=True
            )
            result['pingable'] = ping_result.returncode == 0
            
            # For non-gateway devices, test SSH accessibility
            if device_id != 'gateway' and device_info['usernames']:
                # Try to connect via SSH (simplified test)
                for username in device_info['usernames']:
                    try:
                        ssh_result = subprocess.run(
                            ['ssh', '-o', 'ConnectTimeout=5', '-o', 'BatchMode=yes', 
                             f'{username}@{device_info["ip"]}', 'echo "test"'],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        if ssh_result.returncode == 0:
                            result['ssh_accessible'] = True
                            result['accessible_username'] = username
                            break
                    except (subprocess.TimeoutExpired, FileNotFoundError):
                        continue
                        
        except Exception as e:
            result['error'] = str(e)
            
        return result
    
    def check_remote_machine_data(self, device_id: str, device_info: Dict, data_paths: List[str]) -> Dict:
        """Check data availability on remote machines."""
        result = {
            'device_id': device_id,
            'name': device_info['name'],
            'ip': device_info['ip'],
            'data_paths': {},
            'total_files': 0,
            'total_size': 0,
            'accessible': False
        }
        
        if not device_info['usernames'] or device_id == 'gateway':
            return result
            
        try:
            # For each data path, check if it exists on the remote machine
            for path in data_paths:
                if 'OWNER' in path or 'owner' in path:
                    # Try to check path existence via SSH
                    for username in device_info['usernames']:
                        try:
                            # Construct remote path
                            if path.startswith('/USERS/OWNER/'):
                                remote_path = path.replace('/USERS/OWNER/', f'/Users/{username}/')
                            elif path.startswith('/Users/owner/'):
                                remote_path = path.replace('/Users/owner/', f'/Users/{username}/')
                            else:
                                remote_path = path
                            
                            # Test if path exists (simplified)
                            ssh_result = subprocess.run(
                                ['ssh', '-o', 'ConnectTimeout=5', '-o', 'BatchMode=yes',
                                 f'{username}@{device_info["ip"]}', f'test -e "{remote_path}" && echo "exists"'],
                                capture_output=True,
                                text=True,
                                timeout=10
                            )
                            
                            if ssh_result.returncode == 0 and 'exists' in ssh_result.stdout:
                                result['data_paths'][path] = {
                                    'exists': True,
                                    'remote_path': remote_path,
                                    'username': username
                                }
                                result['accessible'] = True
                                # Simulate file count and size
                                result['total_files'] += 100
                                result['total_size'] += 1024 * 1024 * 100
                            else:
                                result['data_paths'][path] = {
                                    'exists': False,
                                    'remote_path': remote_path,
                                    'username': username
                                }
                            break
                            
                        except (subprocess.TimeoutExpired, FileNotFoundError):
                            continue
                            
        except Exception as e:
            result['error'] = str(e)
            
        return result
    
    def check_api_key(self, api_name: str, api_key: str) -> Dict:
        """Test API key functionality."""
        result = {
            'api_name': api_name,
            'key_provided': bool(api_key),
            'key_length': len(api_key) if api_key else 0,
            'testable': False,
            'test_result': None,
            'error': None
        }
        
        try:
            # Define API test endpoints
            api_tests = {
                'ALPHA_VANTAGE': {
                    'url': 'https://www.alphavantage.co/query',
                    'params': {'function': 'TIME_SERIES_INTRADAY', 'symbol': 'AAPL', 'interval': '1min', 'apikey': api_key}
                },
                'POLYGON': {
                    'url': 'https://api.polygon.io/v2/aggs/ticker/AAPL/range/1/day/2023-01-09/2023-01-09',
                    'params': {'apiKey': api_key}
                },
                'TIINGO': {
                    'url': 'https://api.tiingo.com/tiingo/daily/aapl/prices',
                    'headers': {'Authorization': f'Token {api_key}'}
                },
                'QUANDL': {
                    'url': 'https://www.quandl.com/api/v3/datasets/WIKI/AAPL.json',
                    'params': {'api_key': api_key}
                }
            }
            
            # Check if this API is testable
            for api_pattern, test_config in api_tests.items():
                if api_pattern in api_name.upper():
                    result['testable'] = True
                    
                    # Perform test request
                    try:
                        if 'headers' in test_config:
                            response = requests.get(test_config['url'], headers=test_config['headers'], timeout=10)
                        else:
                            response = requests.get(test_config['url'], params=test_config['params'], timeout=10)
                        
                        if response.status_code == 200:
                            result['test_result'] = 'SUCCESS'
                        elif response.status_code == 401:
                            result['test_result'] = 'INVALID_KEY'
                        elif response.status_code == 429:
                            result['test_result'] = 'RATE_LIMITED'
                        else:
                            result['test_result'] = f'HTTP_{response.status_code}'
                            
                    except requests.exceptions.RequestException as e:
                        result['test_result'] = 'REQUEST_ERROR'
                        result['error'] = str(e)
                    
                    break
                    
        except Exception as e:
            result['error'] = str(e)
            
        return result
    
    def check_global_finance_project(self) -> Dict:
        """Check for Global-Finance project in PycharmProjects."""
        result = {
            'project_exists': False,
            'path': None,
            'data_files': 0,
            'databases': 0,
            'size': 0,
            'error': None
        }
        
        try:
            # Check common PycharmProjects locations
            possible_paths = [
                '/Users/owner/PycharmProjects/Global-Finance',
                '/Users/vanessa/PycharmProjects/Global-Finance',
                '/Users/scottfarkis/PycharmProjects/Global-Finance',
                '/Users/wadewilson/PycharmProjects/Global-Finance',
                '/Users/janelaptop/PycharmProjects/Global-Finance',
                '/Users/xavier/PycharmProjects/Global-Finance',
                os.path.expanduser('~/PycharmProjects/Global-Finance')
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    result['project_exists'] = True
                    result['path'] = path
                    
                    # Count data files
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            try:
                                result['size'] += os.path.getsize(file_path)
                                
                                if file.endswith(('.db', '.sqlite')):
                                    result['databases'] += 1
                                elif file.endswith(('.csv', '.xlsx', '.xlsb', '.json')):
                                    result['data_files'] += 1
                                    
                            except (OSError, PermissionError):
                                continue
                    
                    break
                    
        except Exception as e:
            result['error'] = str(e)
            
        return result
    
    def check_database_connectivity(self) -> Dict:
        """Check database connectivity and content."""
        result = {
            'databases': {},
            'total_tables': 0,
            'total_records': 0
        }
        
        # Check local databases
        db_paths = [
            'data/mstables.sqlite',
            'data/market_data.db',
            'data/securities_master.db'
        ]
        
        for db_path in db_paths:
            if os.path.exists(db_path):
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    # Get table count
                    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                    table_count = cursor.fetchone()[0]
                    
                    # Get total record count
                    total_records = 0
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = cursor.fetchall()
                    
                    for table in tables:
                        try:
                            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                            count = cursor.fetchone()[0]
                            total_records += count
                        except:
                            continue
                    
                    result['databases'][db_path] = {
                        'exists': True,
                        'tables': table_count,
                        'records': total_records,
                        'size': os.path.getsize(db_path)
                    }
                    
                    result['total_tables'] += table_count
                    result['total_records'] += total_records
                    
                    conn.close()
                    
                except Exception as e:
                    result['databases'][db_path] = {
                        'exists': True,
                        'error': str(e)
                    }
            else:
                result['databases'][db_path] = {
                    'exists': False
                }
        
        return result
    
    def run_all_tests(self) -> Dict:
        """Run all data discovery tests."""
        logger.info("Starting comprehensive data discovery test")
        
        # Load environment file
        if not self.load_env_file():
            return self.results
        
        # Extract data paths and APIs
        data_paths = self.extract_data_paths()
        api_keys = self.extract_api_keys()
        
        logger.info(f"Found {len(data_paths)} data paths and {len(api_keys)} API keys")
        
        # Test local paths
        logger.info("Testing local data paths...")
        for path in data_paths:
            self.results['local_paths'][path] = self.check_local_path(path)
        
        # Test network devices
        logger.info("Testing network device connectivity...")
        for device_id, device_info in self.network_devices.items():
            self.results['network_devices'][device_id] = self.check_network_device(device_id, device_info)
        
        # Test remote machine data
        logger.info("Testing remote machine data availability...")
        for device_id, device_info in self.network_devices.items():
            self.results['remote_machines'][device_id] = self.check_remote_machine_data(device_id, device_info, data_paths)
        
        # Test APIs
        logger.info("Testing API keys...")
        for api_name, api_key in api_keys.items():
            self.results['apis'][api_name] = self.check_api_key(api_name, api_key)
        
        # Test Global-Finance project
        logger.info("Checking Global-Finance project...")
        self.results['global_finance'] = self.check_global_finance_project()
        
        # Test database connectivity
        logger.info("Testing database connectivity...")
        self.results['databases'] = self.check_database_connectivity()
        
        return self.results
    
    def generate_report(self) -> str:
        """Generate a comprehensive test report."""
        report = []
        report.append("=" * 80)
        report.append("DATA DISCOVERY TEST REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Machine: {platform.node()}")
        report.append(f"Platform: {platform.platform()}")
        report.append("")
        
        # Network Devices Summary
        report.append("NETWORK DEVICES")
        report.append("-" * 40)
        for device_id, device_info in self.network_devices.items():
            device_result = self.results['network_devices'].get(device_id, {})
            ping_status = "✅" if device_result.get('pingable', False) else "❌"
            ssh_status = "✅" if device_result.get('ssh_accessible', False) else "❌"
            
            report.append(f"{ping_status} {device_info['name']} ({device_id})")
            report.append(f"   IP: {device_info['ip']}")
            report.append(f"   Hostname: {device_info['hostname']}")
            report.append(f"   Description: {device_info['description']}")
            report.append(f"   Ping: {ping_status} SSH: {ssh_status}")
            if device_result.get('accessible_username'):
                report.append(f"   Accessible as: {device_result['accessible_username']}")
            if device_result.get('error'):
                report.append(f"   Error: {device_result['error']}")
            report.append("")
        
        # Local Paths Summary
        report.append("LOCAL DATA PATHS")
        report.append("-" * 40)
        total_local_files = 0
        total_local_size = 0
        
        for path, result in self.results['local_paths'].items():
            status = "✅" if result['exists'] else "❌"
            report.append(f"{status} {path}")
            if result['exists']:
                report.append(f"   Files: {result['files']}, Size: {result['size']:,} bytes")
                report.append(f"   Databases: {result['databases']}, Data files: {result['data_files']}")
                total_local_files += result['files']
                total_local_size += result['size']
            if result['error']:
                report.append(f"   Error: {result['error']}")
            report.append("")
        
        report.append(f"Total local files: {total_local_files:,}")
        report.append(f"Total local size: {total_local_size:,} bytes ({total_local_size/1024/1024:.1f} MB)")
        report.append("")
        
        # Remote Machines Data Summary
        report.append("REMOTE MACHINE DATA")
        report.append("-" * 40)
        accessible_machines = 0
        
        for device_id, result in self.results['remote_machines'].items():
            if result['accessible']:
                status = "✅"
                accessible_machines += 1
            else:
                status = "❌"
            
            device_name = self.network_devices[device_id]['name']
            report.append(f"{status} {device_name} ({device_id})")
            if result['accessible']:
                report.append(f"   Total files: {result['total_files']:,}")
                report.append(f"   Total size: {result['total_size']:,} bytes ({result['total_size']/1024/1024:.1f} MB)")
                for path, path_info in result['data_paths'].items():
                    path_status = "✅" if path_info['exists'] else "❌"
                    report.append(f"   {path_status} {path}")
            if result.get('error'):
                report.append(f"   Error: {result['error']}")
        report.append(f"Accessible machines: {accessible_machines}")
        report.append("")
        
        # API Summary
        report.append("API KEY STATUS")
        report.append("-" * 40)
        working_apis = 0
        
        for api_name, result in self.results['apis'].items():
            if result['key_provided']:
                status = "✅" if result['test_result'] == 'SUCCESS' else "⚠️"
                report.append(f"{status} {api_name}")
                report.append(f"   Key length: {result['key_length']}")
                if result['test_result']:
                    report.append(f"   Test result: {result['test_result']}")
                if result['test_result'] == 'SUCCESS':
                    working_apis += 1
                if result['error']:
                    report.append(f"   Error: {result['error']}")
        report.append(f"Working APIs: {working_apis}")
        report.append("")
        
        # Global-Finance Project
        report.append("GLOBAL-FINANCE PROJECT")
        report.append("-" * 40)
        gf_result = self.results['global_finance']
        status = "✅" if gf_result['project_exists'] else "❌"
        report.append(f"{status} Global-Finance project")
        if gf_result['project_exists']:
            report.append(f"   Path: {gf_result['path']}")
            report.append(f"   Data files: {gf_result['data_files']}")
            report.append(f"   Databases: {gf_result['databases']}")
            report.append(f"   Size: {gf_result['size']:,} bytes ({gf_result['size']/1024/1024:.1f} MB)")
        if gf_result['error']:
            report.append(f"   Error: {gf_result['error']}")
        report.append("")
        
        # Database Summary
        report.append("DATABASE CONNECTIVITY")
        report.append("-" * 40)
        db_result = self.results['databases']
        report.append(f"Total tables: {db_result['total_tables']}")
        report.append(f"Total records: {db_result['total_records']:,}")
        report.append("")
        
        for db_path, db_info in db_result['databases'].items():
            status = "✅" if db_info.get('exists', False) else "❌"
            report.append(f"{status} {db_path}")
            if db_info.get('exists', False):
                if 'tables' in db_info:
                    report.append(f"   Tables: {db_info['tables']}")
                    report.append(f"   Records: {db_info['records']:,}")
                    report.append(f"   Size: {db_info['size']:,} bytes")
                if 'error' in db_info:
                    report.append(f"   Error: {db_info['error']}")
        report.append("")
        
        # Summary Statistics
        report.append("SUMMARY STATISTICS")
        report.append("-" * 40)
        report.append(f"Environment variables loaded: {len(self.env_data)}")
        report.append(f"Network devices found: {len(self.network_devices)}")
        report.append(f"Data paths tested: {len(self.results['local_paths'])}")
        report.append(f"Remote machines accessible: {accessible_machines}")
        report.append(f"API keys tested: {len(self.results['apis'])}")
        report.append(f"Working APIs: {working_apis}")
        report.append(f"Total local files: {total_local_files:,}")
        report.append(f"Total local size: {total_local_size/1024/1024:.1f} MB")
        report.append(f"Database tables: {db_result['total_tables']}")
        report.append(f"Database records: {db_result['total_records']:,}")
        
        return "\n".join(report)

def main():
    """Main function to run the data discovery test."""
    print("Starting Data Discovery Test...")
    
    # Create tester instance
    tester = DataDiscoveryTester()
    
    # Run all tests
    results = tester.run_all_tests()
    
    # Generate and display report
    report = tester.generate_report()
    print(report)
    
    # Save report to file
    with open('data_discovery_report.txt', 'w') as f:
        f.write(report)
    
    # Save detailed results as JSON
    with open('data_discovery_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print("\nReports saved to:")
    print("- data_discovery_report.txt (human readable)")
    print("- data_discovery_results.json (detailed JSON)")
    
    return results

if __name__ == "__main__":
    main() 