from collections import defaultdict, Counter
from typing import List, Dict, Any
from datetime import datetime
import json
from .search_models import TdnetSearchEntry

class TDnetAnalyzer:
    """Analyzer for TDnet results"""

    @staticmethod
    def load_results(json_file):
        """Load results from JSON file"""
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Handle both list of entries and object with 'entries' key
            if isinstance(data, list):
                return data
            return data.get('entries', [])

    @staticmethod
    def analyze_by_company(results: List[Dict]):
        """Analyze activity by company"""
        print("\n" + "="*80)
        print("ANALYSIS 1: COMPANY ACTIVITY")
        print("="*80)

        company_activity = defaultdict(int)
        for result in results:
            name = result.get('company_name') or result.get('company')
            if name:
                company_activity[name] += 1

        # Sort by activity
        sorted_companies = sorted(company_activity.items(), key=lambda x: x[1], reverse=True)

        print(f"\nTop 15 Most Active Companies (by announcement count):")
        print("-"*80)
        print(f"{'Rank':<5} {'Company Name':<40} {'Announcements':<15}")
        print("-"*80)

        for i, (company, count) in enumerate(sorted_companies[:15], 1):
            print(f"{i:<5} {company:<40} {count:<15}")

    @staticmethod
    def analyze_by_date(results: List[Dict]):
        """Analyze trends over time"""
        print("\n" + "="*80)
        print("ANALYSIS 2: TEMPORAL TRENDS")
        print("="*80)

        daily_counts = defaultdict(int)
        for result in results:
            if 'datetime' in result:
                date = result['datetime'].split()[0]
                daily_counts[date] += 1
            elif 'date' in result:
                d = result['date']
                if isinstance(d, (datetime, date)):
                    d = d.strftime('%Y-%m-%d')
                daily_counts[str(d)] += 1

        # Sort by date
        sorted_dates = sorted(daily_counts.items())

        print(f"\nAnnouncements by Date:")
        print("-"*80)
        print(f"{'Date':<15} {'Count':<10} {'Trend':<50}")
        print("-"*80)

        for date_str, count in sorted_dates[-14:]:  # Last 14 days
            bar = "█" * (count // 2)
            print(f"{date_str:<15} {count:<10} {bar}")

    @staticmethod
    def analyze_by_stock_code(results: List[Dict]):
        """Analyze by stock code"""
        print("\n" + "="*80)
        print("ANALYSIS 3: STOCK CODE DISTRIBUTION")
        print("="*80)

        code_activity = defaultdict(int)
        code_to_company = {}
        
        for result in results:
            code = result.get('stock_code')
            if code:
                code_activity[code] += 1
                if 'company_name' in result:
                    code_to_company[code] = result['company_name']

        sorted_codes = sorted(code_activity.items(), key=lambda x: x[1], reverse=True)

        print(f"\nTop 10 Stock Codes by Announcement Frequency:")
        print("-"*80)
        print(f"{'Stock Code':<15} {'Company':<40} {'Count':<10}")
        print("-"*80)

        for code, count in sorted_codes[:10]:
            company = code_to_company.get(code, 'N/A')
            print(f"{code:<15} {company:<40} {count:<10}")

    @staticmethod
    def analyze_announcement_types(results: List[Dict]):
        """Analyze types of announcements"""
        print("\n" + "="*80)
        print("ANALYSIS 4: ANNOUNCEMENT TYPES")
        print("="*80)

        # Categorize by keywords in title
        categories = {
            'Warrant/Stock Option': 0,
            'Convertible Bond': 0,
            'Common Stock': 0,
            'Treasury Stock': 0,
            'Capital Partnership': 0,
            'Other': 0
        }

        for result in results:
            title = result.get('title', '').lower()
            if '新株予約権' in title or 'warrant' in title.lower():
                categories['Warrant/Stock Option'] += 1
            elif '転換社債' in title or 'convertible' in title.lower():
                categories['Convertible Bond'] += 1
            elif '新株式' in title and '資本' in title:
                categories['Capital Partnership'] += 1
            elif '新株式' in title:
                categories['Common Stock'] += 1
            elif '自己株式' in title or 'treasury' in title.lower():
                categories['Treasury Stock'] += 1
            else:
                categories['Other'] += 1

        print(f"\nAnnouncement Type Distribution:")
        print("-"*80)
        print(f"{'Type':<30} {'Count':<10} {'Percentage':<15}")
        print("-"*80)

        total = sum(categories.values())
        for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total * 100) if total > 0 else 0
            print(f"{category:<30} {count:<10} {percentage:>6.1f}%")

    @staticmethod
    def generate_portfolio_insights(results: List[Dict]):
        """Generate insights for portfolio managers"""
        print("\n" + "="*80)
        print("PORTFOLIO MANAGER INSIGHTS")
        print("="*80)

        if not results:
            print("No results to analyze.")
            return

        print(f"\nDataset Overview:")
        print(f"  • Total announcements: {len(results)}")
        companies = set(r.get('company_name') for r in results if r.get('company_name'))
        print(f"  • Unique companies: {len(companies)}")
