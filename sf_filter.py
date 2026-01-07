import argparse
from utils import query_table
from auth import sf
from dotenv import load_dotenv
from datetime import date

def parse_args():
    parser = argparse.ArgumentParser(
        description='Run the script starting from a specific month/year'
    )

    parser.add_argument(
        '-y',
        '--start-year',
        type=int,
        required=False,
        help='Start Year (e.g. 2025)',
    )

    parser.add_argument(
        '-m',
        '--start-month',
        type=int,
        choices=range(1,12),
        required=False,
        metavar='[1-12]',
        help='Start Month (e.g. 1 for January)',
    )

    return parser.parse_args()

# Move back 3 months and adjust year if needed
def get_previous_quarter(month, year):
    month = month - 3
    if month <= 0:
        month += 12
        year -= 1

    return month, year

# Gets each month in a quarter based on current date or provided date
# If no date provided, gets previous quarter relative to today
def get_quarter_dates(args=None):
    use_date = date.today()
    month, year = use_date.month, use_date.year

    if args.start_year and args.start_month:
        year = args.start_year
        month = (args.start_month - 1)// 3  * 3 + 1
    else:
        month = (month - 1)// 3  * 3 + 1
        month, year = get_previous_quarter(month, year)

    for i in range(3):
        yield f"{year}-{str(month + i).zfill(2)}-01"


def query_pool(dates):
    for d in dates:
        print("-----")
        print(f'Querying for date: {d}')
        where= f"WHERE Lease_Id__r.Start_Date__c <= {d} AND Lease_Id__r.End_Date__c >= {d}"
        result = query_table(
            sf,
            'pool',
            where
        )

        yield result

def main():
    args = parse_args()
    dates = list(get_quarter_dates(args))
    total_q = 0
    for result in query_pool(dates):
        print(f"Total Records Retrieved: {result['totalSize']}")
        payment_total = sum(record['TT15_Share_Amt__c'] for record in result['records'])
        print(f'Total Payment Amount: ${payment_total:,.2f}')
        total_q += payment_total

    print("=====")
    print(f'Total Payment Amount for Quarter: ${total_q:,.2f}')


if __name__ == "__main__":
    main()