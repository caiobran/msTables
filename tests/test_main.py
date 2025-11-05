import pytest
from src.main import main
import pandas as pd
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock

class TestMain:
    def test_main_basic(self, temp_db, sample_csv):
        """Test basic main functionality"""
        with patch('src.main.Deduplicator') as mock_deduplicator:
            # Mock deduplicator
            mock_dedup = MagicMock()
            mock_deduplicator.return_value = mock_dedup
            
            # Run main
            main()
            
            # Verify deduplicator was called
            mock_deduplicator.assert_called_once()
            mock_dedup.run.assert_called_once()

    def test_main_error_handling(self, temp_db):
        """Test error handling in main"""
        with patch('src.main.Deduplicator') as mock_deduplicator:
            # Mock deduplicator to raise an exception
            mock_dedup = MagicMock()
            mock_dedup.run.side_effect = Exception("Test error")
            mock_deduplicator.return_value = mock_dedup
            
            # Run main and verify it handles the error
            main()
            
            # Verify deduplicator was called
            mock_deduplicator.assert_called_once()
            mock_dedup.run.assert_called_once()

    def test_main_file_processing(self, temp_db, sample_csv):
        """Test file processing in main"""
        with patch('src.main.Deduplicator') as mock_deduplicator:
            # Mock deduplicator
            mock_dedup = MagicMock()
            mock_deduplicator.return_value = mock_dedup
            
            # Run main
            main()
            
            # Verify file paths were processed
            assert mock_dedup.file_paths is not None
            assert len(mock_dedup.file_paths) > 0

    def test_main_database_connection(self, temp_db):
        """Test database connection in main"""
        with patch('src.main.Deduplicator') as mock_deduplicator:
            # Mock deduplicator
            mock_dedup = MagicMock()
            mock_deduplicator.return_value = mock_dedup
            
            # Run main
            main()
            
            # Verify database path was passed correctly
            mock_deduplicator.assert_called_once()
            args, kwargs = mock_deduplicator.call_args
            assert 'db_path' in kwargs
            assert kwargs['db_path'] == 'data/mstables.sqlite'

    def test_main_logging(self, temp_db):
        """Test logging in main"""
        with patch('src.main.Deduplicator') as mock_deduplicator, \
             patch('src.main.logging') as mock_logging:
            # Mock deduplicator
            mock_dedup = MagicMock()
            mock_deduplicator.return_value = mock_dedup
            
            # Run main
            main()
            
            # Verify logging was set up
            mock_logging.basicConfig.assert_called_once()
            assert mock_logging.INFO in mock_logging.basicConfig.call_args[1]['level']

    def test_main_cleanup(self, temp_db):
        """Test cleanup in main"""
        with patch('src.main.Deduplicator') as mock_deduplicator:
            # Mock deduplicator
            mock_dedup = MagicMock()
            mock_deduplicator.return_value = mock_dedup
            
            # Run main
            main()
            
            # Verify cleanup was performed
            mock_dedup.cleanup.assert_called_once() 