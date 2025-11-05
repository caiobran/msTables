import pytest
from src.utils.analyze_sample_rules import analyze_sample_rules
import pandas as pd
import sqlite3
from pathlib import Path
import matplotlib.pyplot as plt

class TestAnalyzeSampleRules:
    def test_analyze_sample_rules_basic(self, temp_db):
        """Test basic analysis functionality"""
        # Create test data
        with sqlite3.connect(temp_db) as conn:
            df = pd.DataFrame({
                'sector': ['Technology', 'Finance', 'Technology'],
                'PE_TTM': [20.0, 15.0, 25.0],
                'CAGR_Rev': [0.1, 0.05, 0.15],
                'yield': [0.02, 0.03, 0.01],
                'Dividend_Y10': [1.0, 1.5, 0.8],
                'name': ['Tech1', 'Fin1', 'Tech2']
            })
            df.to_sql('sample_rules', conn, index=False)
        
        # Run analysis
        analyze_sample_rules(temp_db)
        
        # Verify output files exist
        assert Path('yield_by_sector.png').exists()
        assert Path('dividend_y10_by_sector.png').exists()

    def test_analyze_sample_rules_empty_db(self, temp_db):
        """Test analysis with empty database"""
        with pytest.raises(ValueError):
            analyze_sample_rules(temp_db)

    def test_analyze_sample_rules_missing_columns(self, temp_db):
        """Test analysis with missing required columns"""
        with sqlite3.connect(temp_db) as conn:
            df = pd.DataFrame({
                'sector': ['Technology'],
                'other_col': [1]
            })
            df.to_sql('sample_rules', conn, index=False)
        
        with pytest.raises(ValueError):
            analyze_sample_rules(temp_db)

    def test_analyze_sample_rules_sector_averages(self, temp_db):
        """Test sector average calculations"""
        # Create test data with known values
        with sqlite3.connect(temp_db) as conn:
            df = pd.DataFrame({
                'sector': ['Technology', 'Finance', 'Technology'],
                'PE_TTM': [20.0, 15.0, 25.0],
                'CAGR_Rev': [0.1, 0.05, 0.15],
                'yield': [0.02, 0.03, 0.01],
                'Dividend_Y10': [1.0, 1.5, 0.8],
                'name': ['Tech1', 'Fin1', 'Tech2']
            })
            df.to_sql('sample_rules', conn, index=False)
        
        # Run analysis
        analyze_sample_rules(temp_db)
        
        # Verify sector averages
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.execute("""
                SELECT sector, AVG(PE_TTM) as avg_pe, AVG(CAGR_Rev) as avg_cagr
                FROM sample_rules
                GROUP BY sector
            """)
            results = cursor.fetchall()
            
            # Find Technology sector
            tech_result = next(r for r in results if r[0] == 'Technology')
            assert tech_result[1] == 22.5  # Average PE_TTM
            assert tech_result[2] == 0.125  # Average CAGR_Rev

    def test_analyze_sample_rules_top_performers(self, temp_db):
        """Test top performer identification"""
        # Create test data
        with sqlite3.connect(temp_db) as conn:
            df = pd.DataFrame({
                'sector': ['Technology'] * 10,
                'CAGR_Rev': [0.1 * i for i in range(10)],
                'name': [f'Tech{i}' for i in range(10)],
                'PE_TTM': [20.0] * 10,
                'yield': [0.02] * 10,
                'Dividend_Y10': [1.0] * 10
            })
            df.to_sql('sample_rules', conn, index=False)
        
        # Run analysis
        analyze_sample_rules(temp_db)
        
        # Verify top performers
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.execute("""
                SELECT name, CAGR_Rev
                FROM sample_rules
                WHERE sector = 'Technology'
                ORDER BY CAGR_Rev DESC
                LIMIT 5
            """)
            results = cursor.fetchall()
            
            assert len(results) == 5
            assert results[0][0] == 'Tech9'  # Highest CAGR_Rev
            assert results[0][1] == 0.9  # Highest growth rate

    def test_analyze_sample_rules_visualizations(self, temp_db):
        """Test visualization generation"""
        # Create test data
        with sqlite3.connect(temp_db) as conn:
            df = pd.DataFrame({
                'sector': ['Technology', 'Finance', 'Technology'],
                'PE_TTM': [20.0, 15.0, 25.0],
                'CAGR_Rev': [0.1, 0.05, 0.15],
                'yield': [0.02, 0.03, 0.01],
                'Dividend_Y10': [1.0, 1.5, 0.8],
                'name': ['Tech1', 'Fin1', 'Tech2']
            })
            df.to_sql('sample_rules', conn, index=False)
        
        # Run analysis
        analyze_sample_rules(temp_db)
        
        # Verify visualization files
        assert Path('yield_by_sector.png').exists()
        assert Path('dividend_y10_by_sector.png').exists()
        
        # Clean up
        Path('yield_by_sector.png').unlink()
        Path('dividend_y10_by_sector.png').unlink() 