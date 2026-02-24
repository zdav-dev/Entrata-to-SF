import argparse
import os
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
        return output_file

# d is formatted as YYYY-MM-DD
def date_to_quarter(d):
    date_split = d.split("-")
    month = int(date_split[1])
    quarter = (month - 1) // 3 + 1
    return f"Q{quarter} {date_split[0]}"

def save_records(csv_file, records, save_records_flag):
    if not save_records_flag:
        return
    
    to_save = []
    for record in records:
        to_save.append({
            'Name': record['Lease_ID__r']['Lessee_Name__c'],
            'Start Date': record['Lease_ID__r']['Start_Date__c'],
            'End Date': record['Lease_ID__r']['End_Date__c'],
            'Rate': record['Lease_ID__r']['Monthly_Rate__c'],
            'TT15 Share Percent': record['TT15_Share__c'],
            'TT15 Share Amt': record['TT15_Share_Amt__c'],
            'Quarter Added to Pool': date_to_quarter(record['Lease_ID__r']['Start_Date__c'])
        })

    to_save.sort(key=lambda x: x['Start Date'])
    output_file = create_csv(csv_file, to_save, logs=False)
    if output_file:
        print(f'Records saved to {output_file}.')

    return output_file

def save_retail_info(txt_file, retail_additional, save_records_flag):
    if not save_records_flag:
        return

    with open(txt_file, 'w') as f:
        for date, years_added, start_extra in retail_additional:
            f.write(f"$85 increased by 10% for {years_added} five-year period{'s' if years_added != 1 else ''} for {date} \
from February 1st, 2017: ${start_extra:,.2f} x 25 spaces = ${start_extra * 25:,.2f}\n")
            
    return txt_file

def zip_files(file_list, zip_name):
    import zipfile
    with zipfile.ZipFile(zip_name, 'w') as zipf:
        for file in file_list:
            zipf.write(file)
            os.remove(file)
    print(f'Files zipped into {zip_name}.')

def main():
    args = parse_args()
    dates = list(get_quarter_dates(args))
    base_tt15_amount = 85.00
    #target_amount()
    #get_total_from_file(f'pool_{dates[0]}.csv')
    #exit()
    #read_from_file(f'pool_{dates[0]}.csv')
    output_dicts = []
    # retail_additional = []
    to_zip = []
    total_q = 0
    for result, date in query_pool(dates):
        # years_added = (datetime.strptime(date, "%Y-%m-%d").date() - datetimedate(2017, 2, 1)).days // 365 // 5
        # start_extra = base_tt15_amount
        # for _ in range(years_added):
        #     start_extra *= 1.10
        #     start_extra = round(start_extra, 4)

        # retail_additional.append((date, years_added, start_extra))

        # tt15_extra = start_extra * 25
        # print(f'Adding extra ${tt15_extra:,.2f}')
        payment_total = round(sum(record['TT15_Share_Amt__c'] for record in result['records']), 2)
        output_dicts.append({'Date': date, '# Leases in Pool': result['totalSize'], 'TT15 Payment': payment_total})
        total_q += payment_total

        print(f"Total Records Retrieved: {result['totalSize']}")
        print(f'Total Payment Amount: ${payment_total:,.2f}')
        f = save_records(f'pool_{date}.csv', result['records'], args.save_records)
        if f:
            to_zip.append(f)

    print("=====")
    print(f'Total Payment Amount for {dates[0]} through {dates[-1]}: ${total_q:,.2f}')
    print("=====")
    # f = save_retail_info(f'TT15_additional_{dates[0]}_{dates[-1]}.txt', retail_additional, args.save_records)
    if f:
        to_zip.append(f)

    f = output(args.output_file, output_dicts)
    if f:
        to_zip.append(f)

    if to_zip:
        zip_files(to_zip, f'TT15_reports_{dates[0]}_{dates[-1]}.zip')

if __name__ == "__main__":
    main()