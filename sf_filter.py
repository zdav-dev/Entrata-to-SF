import argparse
# import csv
from utils import query_table
from auth import sf
from datetime import date as datetimedate
from datetime import datetime
from utils import create_csv

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

    parser.add_argument(
        '-o',
        '--output-file',
        type=str,
        required=False,
        help='Output file name (will add .csv extension if not provided)',
    )

    parser.add_argument(
        '-s',
        '--save-records',
        action='store_true',
        help='Save individual records to CSV files'
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
def get_quarter_dates(args):
    use_date = datetimedate.today()
    month, year = use_date.month, use_date.year

    if args.start_year and args.start_month:
        year = args.start_year
        month = (args.start_month - 1)// 3  * 3 + 1
    else:
        month = (month - 1)// 3  * 3 + 1
        month, year = get_previous_quarter(month, year)

    if args.start_year and not args.start_month:
        for m in range(1, 13):
            yield f"{args.start_year}-{str(m).zfill(2)}-01"
    else:
        for i in range(3):
            yield f"{year}-{str(month + i).zfill(2)}-01"

def query_date(d):
    where= f"WHERE Lease_Id__r.Start_Date__c <= {d} AND Lease_Id__r.End_Date__c >= {d}"
    return query_table(sf, 'pool', where)

def query_pool(dates):
    for d in dates:
        print("-----")
        print(f'Querying for date: {d}')
        result = query_date(d)
        yield result, d

def output(csv_file, records):
    output_file = create_csv(csv_file, records, logs=False)
    if output_file:
        print(f'Output written to {output_file}.')

def save_records(csv_file, records, save_records_flag):
    if not save_records_flag:
        return
    
    to_save = []
    for record in records:
        to_save.append({
            'Id': record['Id'],
            'Lease_Id': record['Lease_ID__r']['Id'],
            'Rate': record['Lease_ID__r']['Monthly_Rate__c'],
            'TT15_Percent': record['TT15_Share__c'],
            'TT15_Share_Amt': record['TT15_Share_Amt__c'],
        })
    output_file = create_csv(csv_file, to_save, logs=False)
    if output_file:
        print(f'Records saved to {output_file}.')

# def read_from_file(csv_file):
#     records = []
#     with open(csv_file, 'r', encoding='utf-8-sig') as f:
#         file = csv.reader(f)
#         header = next(file)
#         for line in file:
#             temp = {col: val for col, val in zip(header, line)}
#             record = {'Id': temp['Lease_Id'],
#                       'Rate': temp['Rate']}
#             records.append(record)

    
#     return records

# def target_amount(amt, csv_file):
#     records = read_from_file(csv_file)
#     total = sum(float(record['TT15_Share_Amt']) for record in records)
#     print(f'Target Amount: {amt}, Total from File: {total}')
#     diff = total - amt
#     print(f'Difference: {diff}')
#     exit()
#     i = 0
#     while total >= amt and i < len(records):
#         record = records[i]
#         record['Rate'] -= 10.00
#         record['TT15_Share_Amt'] = round(record['Rate'] * float(record['TT15_Percent']) / 100, 2)
#         total -= record['TT15_Share_Amt']
#         i += 1

def main():
    args = parse_args()
    dates = list(get_quarter_dates(args))
    base_tt15_amount = 85.00
    #target_amount()
    #get_total_from_file(f'pool_{dates[0]}.csv')
    #exit()
    #read_from_file(f'pool_{dates[0]}.csv')
    output_dicts = []
    total_q = 0
    for result, date in query_pool(dates):
        years_added = (datetime.strptime(date, "%Y-%m-%d").date() - datetimedate(2017, 2, 1)).days // 365 // 5
        start_extra = base_tt15_amount
        for _ in range(years_added):
            start_extra *= 1.10
            start_extra = round(start_extra, 4)

        tt15_extra = start_extra * 25
        print(f'Adding extra ${tt15_extra:,.2f}')
        payment_total = round(sum(record['TT15_Share_Amt__c'] for record in result['records'])+ tt15_extra, 2)
        output_dicts.append({'Date': date, '# Leases in Pool': result['totalSize'], 'TT15 Payment': payment_total})
        total_q += payment_total

        print(f"Total Records Retrieved: {result['totalSize']}")
        print(f'Total Payment Amount: ${payment_total:,.2f}')
        save_records(f'pool_{date}.csv', result['records'], args.save_records)

    print("=====")
    print(f'Total Payment Amount for {dates[0]} through {dates[-1]}: ${total_q:,.2f}')
    print("=====")

    output(args.output_file, output_dicts)


if __name__ == "__main__":
    main()