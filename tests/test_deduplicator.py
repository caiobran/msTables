import pytest
from src.utils.deduplicator import Deduplicator
from pathlib import Path
import pandas as pd
import sqlite3

class TestDeduplicator:
    def test_init(self, temp_db):
        """Test Deduplicator initialization"""
        deduplicator = Deduplicator(db_path=temp_db)
        assert deduplicator.db_path == temp_db
        assert deduplicator.file_paths == []

    def test_init_db(self, temp_db):
        """Test database initialization"""
        deduplicator = Deduplicator(db_path=temp_db)
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='deleted_files'")
            assert cursor.fetchone() is not None

    def test_compute_blake2_hash(self, temp_db, sample_csv):
        """Test BLAKE2 hash computation"""
        deduplicator = Deduplicator(db_path=temp_db)
        hash_value = deduplicator.compute_blake2_hash(Path(sample_csv))
        assert isinstance(hash_value, str)
        assert len(hash_value) == 128  # BLAKE2b produces 128-character hex string

    def test_is_file_deleted(self, temp_db):
        """Test file deletion tracking"""
        deduplicator = Deduplicator(db_path=temp_db)
        # Test with non-existent hash
        assert not deduplicator.is_file_deleted("nonexistent_hash")
        
        # Test with existing hash
        with sqlite3.connect(temp_db) as conn:
            conn.execute("""
                INSERT INTO deleted_files (file_path, file_hash, file_size, deleted_at)
                VALUES (?, ?, ?, ?)
            """, ("test.txt", "test_hash", 100, "2024-01-01"))
        assert deduplicator.is_file_deleted("test_hash")

    def test_get_next_sequence(self, temp_db):
        """Test sequence number generation"""
        deduplicator = Deduplicator(db_path=temp_db)
        # Test first sequence
        assert deduplicator.get_next_sequence() == 1
        
        # Test subsequent sequences
        with sqlite3.connect(temp_db) as conn:
            conn.execute("""
                INSERT INTO deleted_files 
                (file_path, file_hash, file_size, deleted_at, sequence_number)
                VALUES (?, ?, ?, ?, ?)
            """, ("test.txt", "test_hash", 100, "2024-01-01", 1))
        assert deduplicator.get_next_sequence() == 2

    def test_log_deleted_file(self, temp_db, sample_csv):
        """Test file deletion logging"""
        deduplicator = Deduplicator(db_path=temp_db)
        file_path = Path(sample_csv)
        file_hash = deduplicator.compute_blake2_hash(file_path)
        
        deduplicator.log_deleted_file(file_path, file_hash, "test reason")
        
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.execute("SELECT * FROM deleted_files WHERE file_hash = ?", (file_hash,))
            row = cursor.fetchone()
            assert row is not None
            assert row[1] == str(file_path)  # file_path
            assert row[2] == file_hash       # file_hash
            assert row[5] == "test reason"   # reason

    def test_verify_data_in_db(self, temp_db, sample_csv):
        """Test data verification"""
        deduplicator = Deduplicator(db_path=temp_db)
        
        # Test with empty database
        assert not deduplicator.verify_data_in_db(Path(sample_csv))
        
        # Test with matching data
        df = pd.read_csv(sample_csv)
        with sqlite3.connect(temp_db) as conn:
            df.to_sql('tiingo_prices', conn, index=False)
        assert deduplicator.verify_data_in_db(Path(sample_csv))

    def test_process_file(self, temp_db, sample_csv):
        """Test file processing"""
        deduplicator = Deduplicator(db_path=temp_db)
        
        # Test with non-existent file
        deduplicator.process_file(Path("nonexistent.csv"))
        
        # Test with existing file
        deduplicator.process_file(Path(sample_csv))
        assert Path(sample_csv).exists()  # File should still exist as data is new

    def test_run(self, temp_db, sample_csv):
        """Test full deduplication process"""
        deduplicator = Deduplicator(db_path=temp_db, file_paths=[sample_csv])
        deduplicator.run() 