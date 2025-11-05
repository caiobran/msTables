"""
Trader Workstation Integration Module

This module provides integration with Interactive Brokers Trader Workstation (TWS)
for paper trading and live trading capabilities.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
from ib_insync import *  # Interactive Brokers API

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/tws_integration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('TWSIntegration')

class TWSIntegration:
    """
    A class for integrating with Interactive Brokers Trader Workstation.
    """
    
    def __init__(self, 
                 host: str = '127.0.0.1',
                 port: int = 7497,  # 7497 for TWS, 4001 for Gateway
                 client_id: int = 1,
                 paper_trading: bool = True):
        """
        Initialize TWS integration.
        
        Parameters
        ----------
        host : str
            TWS/Gateway host
        port : int
            TWS/Gateway port
        client_id : int
            Client ID for the connection
        paper_trading : bool
            Whether to use paper trading
        """
        self.host = host
        self.port = port
        self.client_id = client_id
        self.paper_trading = paper_trading
        self.logger = logger
        
        # Create necessary directories
        Path('data/logs').mkdir(parents=True, exist_ok=True)
        Path('data/trading').mkdir(parents=True, exist_ok=True)
        
        # Initialize IB connection
        self.ib = IB()
        
    def connect(self) -> bool:
        """
        Connect to TWS/Gateway.
        
        Returns
        -------
        bool
            Whether connection was successful
        """
        try:
            self.ib.connect(
                host=self.host,
                port=self.port,
                clientId=self.client_id,
                readonly=False
            )
            self.logger.info("Connected to TWS/Gateway")
            return True
        except Exception as e:
            self.logger.error(f"Error connecting to TWS/Gateway: {e}")
            return False
            
    def disconnect(self):
        """Disconnect from TWS/Gateway."""
        try:
            self.ib.disconnect()
            self.logger.info("Disconnected from TWS/Gateway")
        except Exception as e:
            self.logger.error(f"Error disconnecting from TWS/Gateway: {e}")
            
    def create_contract(self, 
                       symbol: str,
                       sec_type: str = 'STK',
                       exchange: str = 'SMART',
                       currency: str = 'USD') -> Contract:
        """
        Create an IB contract.
        
        Parameters
        ----------
        symbol : str
            Symbol to trade
        sec_type : str
            Security type
        exchange : str
            Exchange
        currency : str
            Currency
            
        Returns
        -------
        Contract
            IB contract object
        """
        contract = Stock(symbol, exchange, currency)
        return contract
        
    def place_order(self,
                   contract: Contract,
                   action: str,
                   quantity: int,
                   order_type: str = 'MKT',
                   price: float = None,
                   stop_price: float = None,
                   take_profit_price: float = None) -> Trade:
        """
        Place an order through TWS.
        
        Parameters
        ----------
        contract : Contract
            IB contract object
        action : str
            'BUY' or 'SELL'
        quantity : int
            Number of shares
        order_type : str
            Order type (MKT, LMT, etc.)
        price : float
            Limit price (for limit orders)
        stop_price : float
            Stop price (for stop orders)
        take_profit_price : float
            Take profit price (for bracket orders)
            
        Returns
        -------
        Trade
            IB trade object
        """
        try:
            # Create order
            if order_type == 'MKT':
                order = MarketOrder(action, quantity)
            elif order_type == 'LMT':
                order = LimitOrder(action, quantity, price)
            elif order_type == 'STP':
                order = StopOrder(action, quantity, stop_price)
            elif order_type == 'BRK':
                # Create bracket order
                parent = LimitOrder(action, quantity, price)
                stop = StopOrder('SELL' if action == 'BUY' else 'BUY',
                               quantity, stop_price)
                take_profit = LimitOrder('SELL' if action == 'BUY' else 'BUY',
                                       quantity, take_profit_price)
                order = BracketOrder(parent, take_profit, stop)
            else:
                raise ValueError(f"Unsupported order type: {order_type}")
            
            # Place order
            trade = self.ib.placeOrder(contract, order)
            self.logger.info(f"Placed {order_type} order for {symbol}: {action} {quantity}")
            
            return trade
            
        except Exception as e:
            self.logger.error(f"Error placing order: {e}")
            return None
            
    def get_account_summary(self) -> Dict:
        """
        Get account summary from TWS.
        
        Returns
        -------
        Dict
            Account summary information
        """
        try:
            account = self.ib.accountSummary()
            summary = {
                'NetLiquidation': next((v.value for v in account if v.tag == 'NetLiquidation'), None),
                'TotalCashValue': next((v.value for v in account if v.tag == 'TotalCashValue'), None),
                'BuyingPower': next((v.value for v in account if v.tag == 'BuyingPower'), None),
                'EquityWithLoanValue': next((v.value for v in account if v.tag == 'EquityWithLoanValue'), None),
                'AvailableFunds': next((v.value for v in account if v.tag == 'AvailableFunds'), None)
            }
            return summary
        except Exception as e:
            self.logger.error(f"Error getting account summary: {e}")
            return {}
            
    def get_positions(self) -> List[Dict]:
        """
        Get current positions from TWS.
        
        Returns
        -------
        List[Dict]
            List of current positions
        """
        try:
            positions = self.ib.positions()
            return [{
                'symbol': p.contract.symbol,
                'quantity': p.position,
                'avg_cost': p.avgCost
            } for p in positions]
        except Exception as e:
            self.logger.error(f"Error getting positions: {e}")
            return []
            
    def execute_trading_signals(self,
                              signals: Dict[str, Dict],
                              max_position_size: float = 0.1):
        """
        Execute trading signals through TWS.
        
        Parameters
        ----------
        signals : Dict[str, Dict]
            Dictionary of trading signals
        max_position_size : float
            Maximum position size as fraction of portfolio
        """
        try:
            # Get account summary
            account = self.get_account_summary()
            portfolio_value = float(account.get('NetLiquidation', 0))
            
            # Get current positions
            positions = {p['symbol']: p for p in self.get_positions()}
            
            for symbol, signal in signals.items():
                if signal['action'] == 'HOLD':
                    continue
                    
                # Calculate position size
                max_position = portfolio_value * max_position_size
                current_price = float(self.ib.reqMktData(
                    self.create_contract(symbol)
                ).last)
                
                quantity = int(max_position / current_price)
                
                # Check if we already have a position
                current_position = positions.get(symbol, {}).get('quantity', 0)
                
                if signal['action'] == 'BUY' and current_position <= 0:
                    # Place buy order
                    self.place_order(
                        contract=self.create_contract(symbol),
                        action='BUY',
                        quantity=quantity,
                        order_type='BRK',
                        price=signal['target_price'],
                        stop_price=signal['stop_loss'],
                        take_profit_price=signal['take_profit']
                    )
                elif signal['action'] == 'SELL' and current_position >= 0:
                    # Place sell order
                    self.place_order(
                        contract=self.create_contract(symbol),
                        action='SELL',
                        quantity=abs(current_position),
                        order_type='BRK',
                        price=signal['target_price'],
                        stop_price=signal['stop_loss'],
                        take_profit_price=signal['take_profit']
                    )
                    
        except Exception as e:
            self.logger.error(f"Error executing trading signals: {e}")
            
    def monitor_trades(self):
        """Monitor and log trade execution."""
        try:
            while True:
                # Get open trades
                trades = self.ib.trades()
                
                for trade in trades:
                    if trade.isActive():
                        self.logger.info(
                            f"Active trade: {trade.contract.symbol} "
                            f"{trade.order.action} {trade.order.totalQuantity} "
                            f"Status: {trade.orderStatus.status}"
                        )
                        
                # Sleep for a bit
                self.ib.sleep(1)
                
        except Exception as e:
            self.logger.error(f"Error monitoring trades: {e}")
            
    def save_trading_results(self,
                           output_file: str = 'data/trading/trading_results.json'):
        """
        Save trading results to file.
        
        Parameters
        ----------
        output_file : str
            Path to save results
        """
        try:
            results = {
                'timestamp': datetime.now().isoformat(),
                'account_summary': self.get_account_summary(),
                'positions': self.get_positions(),
                'trades': [{
                    'symbol': t.contract.symbol,
                    'action': t.order.action,
                    'quantity': t.order.totalQuantity,
                    'price': t.orderStatus.avgFillPrice,
                    'status': t.orderStatus.status,
                    'timestamp': t.orderStatus.completedTime
                } for t in self.ib.trades()]
            }
            
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=4)
                
            self.logger.info(f"Trading results saved to {output_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving trading results: {e}")

def main():
    """Example usage of TWS integration."""
    # Initialize TWS integration
    tws = TWSIntegration(paper_trading=True)
    
    # Connect to TWS
    if tws.connect():
        try:
            # Load trading signals
            with open('data/predictions/overnight_analysis.json', 'r') as f:
                analysis = json.load(f)
                signals = analysis['signals']
            
            # Execute signals
            tws.execute_trading_signals(signals)
            
            # Monitor trades
            tws.monitor_trades()
            
        finally:
            # Save results and disconnect
            tws.save_trading_results()
            tws.disconnect()

if __name__ == '__main__':
    main() 