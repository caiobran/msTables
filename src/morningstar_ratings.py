#!/usr/bin/env python

"""
Morningstar Rating Criteria and Formulas

This module documents the known criteria and formulas used by Morningstar for their proprietary ratings.
These are based on publicly available information and may not reflect Morningstar's current methodology.

Note: Morningstar's exact formulas are proprietary and not publicly disclosed.
This is a best-effort compilation of known criteria based on public sources.
"""

MORNINGSTAR_RATINGS = {
    # Star Rating (1-5 stars)
    'star_rating': {
        'description': 'Morningstar's proprietary star rating system for funds and stocks',
        'criteria': [
            'Risk-adjusted returns relative to peers',
            'Historical performance consistency',
            'Expense ratios and costs',
            'Manager tenure and stability',
            'Portfolio turnover',
            'Tax efficiency'
        ],
        'formula': 'Proprietary - Not publicly disclosed'
    },

    # Economic Moat Rating
    'economic_moat': {
        'description': 'Assessment of a company's competitive advantages and ability to maintain them',
        'criteria': [
            'Network effects',
            'Intangible assets (brands, patents, licenses)',
            'Cost advantages',
            'Switching costs',
            'Efficient scale'
        ],
        'formula': 'Proprietary - Not publicly disclosed'
    },

    # Fair Value Estimate
    'fair_value': {
        'description': 'Morningstar's estimate of a stock's intrinsic value',
        'criteria': [
            'Discounted cash flow analysis',
            'Historical financial performance',
            'Industry and competitive analysis',
            'Management quality and strategy',
            'Economic conditions and outlook'
        ],
        'formula': 'Proprietary - Not publicly disclosed'
    },

    # Uncertainty Rating
    'uncertainty': {
        'description': 'Assessment of the reliability of Morningstar's fair value estimate',
        'criteria': [
            'Business model stability',
            'Financial leverage',
            'Revenue predictability',
            'Operating leverage',
            'Macroeconomic sensitivity'
        ],
        'formula': 'Proprietary - Not publicly disclosed'
    },

    # Stewardship Rating
    'stewardship': {
        'description': 'Evaluation of management's capital allocation and corporate governance',
        'criteria': [
            'Capital allocation history',
            'Shareholder alignment',
            'Corporate governance practices',
            'Financial transparency',
            'Management compensation'
        ],
        'formula': 'Proprietary - Not publicly disclosed'
    },

    # Financial Health Rating
    'financial_health': {
        'description': 'Assessment of a company's financial stability and strength',
        'criteria': [
            'Debt levels and coverage ratios',
            'Cash flow stability',
            'Profitability margins',
            'Working capital management',
            'Asset utilization'
        ],
        'formula': 'Proprietary - Not publicly disclosed'
    },

    # Growth Rating
    'growth': {
        'description': 'Evaluation of a company's growth prospects and execution',
        'criteria': [
            'Revenue growth rates',
            'Earnings growth',
            'Market share expansion',
            'New product development',
            'Geographic expansion'
        ],
        'formula': 'Proprietary - Not publicly disclosed'
    },

    # Profitability Rating
    'profitability': {
        'description': 'Assessment of a company's ability to generate profits',
        'criteria': [
            'Operating margins',
            'Return on equity (ROE)',
            'Return on assets (ROA)',
            'Return on invested capital (ROIC)',
            'Gross margins'
        ],
        'formula': 'Proprietary - Not publicly disclosed'
    },

    # Efficiency Rating
    'efficiency': {
        'description': 'Evaluation of how well a company utilizes its resources',
        'criteria': [
            'Asset turnover',
            'Inventory turnover',
            'Days sales outstanding (DSO)',
            'Days inventory outstanding (DIO)',
            'Days payable outstanding (DPO)'
        ],
        'formula': 'Proprietary - Not publicly disclosed'
    },

    # Cash Flow Health Rating
    'cash_flow_health': {
        'description': 'Assessment of a company's cash flow generation and management',
        'criteria': [
            'Operating cash flow',
            'Free cash flow',
            'Cash conversion cycle',
            'Capital expenditure requirements',
            'Dividend coverage'
        ],
        'formula': 'Proprietary - Not publicly disclosed'
    }
}

# Example usage:
if __name__ == '__main__':
    for rating, details in MORNINGSTAR_RATINGS.items():
        print(f"\n{rating.upper()}:")
        print(f"Description: {details['description']}")
        print("Criteria:")
        for criterion in details['criteria']:
            print(f"  - {criterion}")
        print(f"Formula: {details['formula']}") 