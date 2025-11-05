import pandas as pd
import numpy as np
import sqlite3
import json
import sys
import re
import os
from src import fetch
from src import parse
from typing import List, Dict, Optional, Union
from .utils.yahoo_finance_reference import get_exchange_suffix, get_data_provider, get_exchange_info

class DataFrames():
    """Class for handling and merging financial data from various sources."""

    db_file = '../db/mstables.sqlite'  # Standard db file name

    def __init__(self, file = db_file):
        """Initialize DataFrames with database file."""
        msg = 'Creating initial DataFrames objects from file {}...\n'
        print(msg.format(file))

        # Load exchange information
        self.exchange_info = {market: (suffix, delay) for _, market, suffix, delay, _ in get_exchange_info()}
        
        # Create database connection
        conn = sqlite3.connect(file)
        
        # Load tables
        self.master0 = pd.read_sql('SELECT * FROM Master', conn)
        self.tickers = pd.read_sql('SELECT * FROM Tickers', conn)
        self.companies = pd.read_sql('SELECT * FROM Companies', conn)
        self.exchanges = pd.read_sql('SELECT * FROM Exchanges', conn)
        self.industries = pd.read_sql('SELECT * FROM Industries', conn)
        self.sectors = pd.read_sql('SELECT * FROM Sectors', conn)
        self.countries = pd.read_sql('SELECT * FROM Countries', conn)
        self.securitytypes = pd.read_sql('SELECT * FROM SecurityTypes', conn)
        self.stocktypes = pd.read_sql('SELECT * FROM StockTypes', conn)
        self.styles = pd.read_sql('SELECT * FROM Styles', conn)
        self.currencies = pd.read_sql('SELECT * FROM Currencies', conn)
        self.timerefs = pd.read_sql('SELECT * FROM TimeRefs', conn)
        
        # Add exchange suffixes and data providers
        self.exchanges['suffix'] = self.exchanges['exchange_sym'].apply(
            lambda x: self.exchange_info.get(x, ('', ''))[0] if x in self.exchange_info else '')
        self.exchanges['data_provider'] = self.exchanges['exchange_sym'].apply(
            lambda x: get_data_provider('us_equities' if x in ['Nasdaq Stock Exchange', 'New York Stock Exchange'] 
                                      else 'international_charts'))
        
        # Merge Tables
        self.master = (self.master0
        # Ticker Symbols
         .merge(self.tickers, left_on='ticker_id', right_on='id')
         .drop(['id'], axis=1)
        # Company / Security Name
         .merge(self.companies, left_on='company_id', right_on='id')
         .drop(['id', 'company_id'], axis=1)
        # Exchanges
         .merge(self.exchanges, left_on='exchange_id', right_on='id')
         .drop(['id'], axis=1)
        # Industries
         .merge(self.industries, left_on='industry_id', right_on='id')
         .drop(['id', 'industry_id'], axis=1)
        # Sectors
         .merge(self.sectors, left_on='sector_id', right_on='id')
         .drop(['id', 'sector_id'], axis=1)
        # Countries
         .merge(self.countries, left_on='country_id', right_on='id')
         .drop(['id', 'country_id'], axis=1)
        # Security Types
         .merge(self.securitytypes, left_on='security_type_id', right_on='id')
         .drop(['id', 'security_type_id'], axis=1)
        # Stock Types
         .merge(self.stocktypes, left_on='stock_type_id', right_on='id')
         .drop(['id', 'stock_type_id'], axis=1)
        # Stock Style Types
         .merge(self.styles, left_on='style_id', right_on='id')
         .drop(['id', 'style_id'], axis=1)
        # Quote Header Info
         .merge(self.quoteheader(), on=['ticker_id', 'exchange_id'])
         .rename(columns={'fpe':'PE_Forward'})
        # Currency
         .merge(self.currencies, left_on='currency_id', right_on='id')
         .drop(['id', 'currency_id'], axis=1)
        # Fiscal Year End
         .merge(self.timerefs, left_on='fyend_id', right_on='id')
         .drop(['fyend_id'], axis=1)
         .rename(columns={'dates':'fy_end'})
        )
        
        # Add full symbols with exchange suffixes
        self.master['full_symbol'] = self.master.apply(
            lambda row: f"{row['ticker']}{row['suffix']}" if row['suffix'] != 'N/A' else row['ticker'], axis=1)
        
        # Change date columns to TimeFrames
        self.master['fy_end'] = pd.to_datetime(self.master['fy_end'])
        self.master['update_date'] = pd.to_datetime(self.master['update_date'])
        self.master['lastdate'] = pd.to_datetime(self.master['lastdate'])
        self.master['_52wk_hi'] = self.master['_52wk_hi'].astype('float')
        self.master['_52wk_lo'] = self.master['_52wk_lo'].astype('float')
        self.master['lastprice'] = self.master['lastprice'].astype('float')
        self.master['openprice'] = self.master['openprice'].astype('float')

        print('\nInitial DataFrames created successfully.')

    def quoteheader(self):
        return self.table('MSheader')

    def valuation(self):
        # Create DataFrame
        val = self.table('MSvaluation')

        # Rename column headers with actual year values
        yrs = val.iloc[0, 2:13].replace(self.timerefs['dates']).to_dict()
        cols = val.columns[:13].values.tolist() + list(map(
            lambda col: ''.join([col[:3], yrs[col[3:]]]), val.columns[13:]))
        val.columns = cols

        # Resize and reorder columns
        val = val.set_index(['exchange_id', 'ticker_id']).iloc[:, 11:]

        return val


    def keyratios(self):
        keyr = self.table('MSfinancials')
        yr_cols = ['Y0', 'Y1', 'Y2', 'Y3', 'Y4', 'Y5', 'Y6',
            'Y7', 'Y8', 'Y9', 'Y10']
        keyr = self.get_yrcolumns(keyr, yr_cols)
        keyr[yr_cols[:-1]] = keyr[yr_cols[:-1]].astype('datetime64')

        return keyr


    def finhealth(self):
        finan = self.table('MSratio_financial')
        yr_cols = [col for col in finan.columns if col.startswith('fh_Y')]
        finan = self.get_yrcolumns(finan, yr_cols)
        finan[yr_cols[:-1]] = finan[yr_cols[:-1]].astype('datetime64')

        return finan


    def profitability(self):
        profit= self.table('MSratio_profitability')
        yr_cols = [col for col in profit.columns if col.startswith('pr_Y')]
        profit = self.get_yrcolumns(profit, yr_cols)
        profit[yr_cols[:-1]] = profit[yr_cols[:-1]].astype('datetime64')

        return profit


    def growth(self):
        growth = self.table('MSratio_growth')
        yr_cols = [col for col in growth.columns if col.startswith('gr_Y')]
        growth = self.get_yrcolumns(growth, yr_cols)
        growth[yr_cols[:-1]] = growth[yr_cols[:-1]].astype('datetime64')

        return growth


    def cfhealth(self):
        cfhealth = self.table('MSratio_cashflow')
        yr_cols = [col for col in cfhealth.columns if col.startswith('cf_Y')]
        cfhealth = self.get_yrcolumns(cfhealth, yr_cols)
        cfhealth[yr_cols[:-1]] = cfhealth[yr_cols[:-1]].astype('datetime64')

        return cfhealth


    def efficiency(self):
        effic = self.table('MSratio_efficiency')
        yr_cols = [col for col in effic.columns if col.startswith('ef_Y')]
        effic = self.get_yrcolumns(effic, yr_cols)
        effic[yr_cols[:-1]] = effic[yr_cols[:-1]].astype('datetime64')

        return effic

    # Income Statement - Annual
    def annualIS(self):
        rep_is_yr = self.table('MSreport_is_yr')
        yr_cols = [col for col in rep_is_yr.columns
                    if col.startswith('Year_Y')]
        rep_is_yr = self.get_yrcolumns(rep_is_yr, yr_cols)
        rep_is_yr[yr_cols[:-1]] = rep_is_yr[yr_cols[:-1]].astype('datetime64')

        return rep_is_yr

    # Income Statement - Quarterly
    def quarterlyIS(self):
        rep_is_qt = self.table('MSreport_is_qt')
        yr_cols = [col for col in rep_is_qt.columns
                    if col.startswith('Year_Y')]
        rep_is_qt = self.get_yrcolumns(rep_is_qt, yr_cols)
        rep_is_qt[yr_cols[:-1]] = rep_is_qt[yr_cols[:-1]].astype('datetime64')

        return rep_is_qt

    # Balance Sheet - Annual
    def annualBS(self):
        rep_bs_yr = self.table('MSreport_bs_yr')
        yr_cols = [col for col in rep_bs_yr.columns
                    if col.startswith('Year_Y')]
        rep_bs_yr = self.get_yrcolumns(rep_bs_yr, yr_cols)
        rep_bs_yr[yr_cols[:-1]] = rep_bs_yr[yr_cols[:-1]].astype('datetime64')

        return rep_bs_yr

    # Balance Sheet - Quarterly
    def quarterlyBS(self):
        rep_bs_qt = self.table('MSreport_bs_qt')
        yr_cols = [col for col in rep_bs_qt.columns
                    if col.startswith('Year_Y')]
        rep_bs_qt = self.get_yrcolumns(rep_bs_qt, yr_cols)
        rep_bs_qt[yr_cols[:-1]] = rep_bs_qt[yr_cols[:-1]].astype('datetime64')

        return rep_bs_qt

    # Cashflow Statement - Annual
    def annualCF(self):
        rep_cf_yr = self.table('MSreport_cf_yr')
        yr_cols = [col for col in rep_cf_yr.columns
                    if col.startswith('Year_Y')]
        rep_cf_yr = self.get_yrcolumns(rep_cf_yr, yr_cols)
        rep_cf_yr[yr_cols[:-1]] = rep_cf_yr[yr_cols[:-1]].astype('datetime64')

        return rep_cf_yr

    # Cashflow Statement - Quarterly
    def quarterlyCF(self):
        rep_cf_qt = self.table('MSreport_cf_qt')
        yr_cols = [col for col in rep_cf_qt.columns
                    if col.startswith('Year_Y')]
        rep_cf_qt = self.get_yrcolumns(rep_cf_qt, yr_cols)
        rep_cf_qt[yr_cols[:-1]] = rep_cf_qt[yr_cols[:-1]].astype('datetime64')

        return rep_cf_qt

    # 10yr Price History
    def priceHistory(self):

        return self.table('MSpricehistory')


    def insider_trades(self):
        df_insiders = self.table('Insiders', False)
        df_tradetypes = self.table('TransactionType', False)
        df_trades = self.table('InsiderTransactions', False)
        df_trades['date'] = pd.to_datetime(df_trades['date'])
        df = (df_trades
            .merge(df_insiders, left_on='name_id', right_on='id')
            .drop(['id', 'name_id'], axis=1)
            .merge(df_tradetypes, left_on='transaction_id', right_on='id')
            .drop(['id', 'transaction_id'], axis=1)
            )
        return df


    def get_yrcolumns(self, df, cols):
        for yr in cols:
            df = (df.merge(self.timerefs, left_on=yr, right_on='id')
                .drop(yr, axis=1).rename(columns={'dates':yr}))

        return df


    def table(self, tbl, prnt = False):
        self.cur.execute('SELECT * FROM {}'.format(tbl))
        cols = list(zip(*self.cur.description))[0]

        try:
            if prnt == True:
                msg = '\t- DataFrame \'df.{}\' ...'
                print(msg.format(tbl.lower()))
            return pd.DataFrame(self.cur.fetchall(), columns=cols)
        except:
            raise


    def __del__(self):
        self.cur.close()
        self.conn.close()
