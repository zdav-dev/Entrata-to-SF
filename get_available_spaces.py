from auth import sf
from utils import query_table
import argparse
from datetime import date as dt_date
from datetime import timedelta
from functools import cmp_to_key

def parse_args():
    parser = argparse.ArgumentParser(
        description='Filter available parking spaces at a given date'
    )

    parser.add_argument(
        '-d',
        '--date',
        type=str,
        required=False,
        help="YYYY-MM-DD"
    )

    parser.add_argument(
        '-f',
        '--future',
        action='store_true',
        help='Runs for 2026-08-31'
    )

    parser.add_argument(
        '-p',
        '--print-amount',
        type=int,
        required=False,
        help='Number of available spaces to print per building (default 10)',
        default=10
    )

    parser.add_argument(
        '-a',
        '--all',
        action='store_true',
        help='Use all buildings'
    )

    return parser.parse_args()

def get_date(args):
    date_year, date_month = dt_date.today().year, dt_date.today().month

    if args.future:
        if dt_date.today().month >= 8:
            date_year += 1 
        date_month = 8
    elif args.date:
        y, m, _ = args.date.split('-')
        date_year, date_month = int(y), int(m)

    return date_of_last_day_of_month(date_year, date_month)


def date_of_last_day_of_month(year, month):
    if month == 12:
        return dt_date(year, month, 31).strftime("%Y-%m-%d")
    else:
        first_of_next_month = dt_date(year, month + 1, 1)
        last_day = first_of_next_month - timedelta(days=1)
        return last_day.strftime("%Y-%m-%d")

def query_date(d):
    where= f"WHERE Start_Date__c <= {d} AND End_Date__c >= {d}"
    try:
        results = query_table(sf, 'lease', where)['records']
    except Exception as e:
        return set()

    return set((r['Parking_Space__c'] for r in results))

# Returns every available parking space for each building on a given date
def get_open_spaces(d):
    leased_spaces = query_date(d)
    next_lease_date = get_all_leases_after(d)
    spaces = query_table(sf, 'parking')['records']

    buildings = {'NU':[], 'GR':[], 'KN':[]}

    for space in spaces:
        if space['Id'] not in leased_spaces:
            if space['Id'] not in next_lease_date:
                buildings[space['Building__c']].append((space['Contractor_Name__r']['Name'], space['Name'], "OPEN"))
            else:
                buildings[space['Building__c']].append((space['Contractor_Name__r']['Name'], space['Name'],next_lease_date[space['Id']]['Start_Date__c']))

    return buildings

def get_all_leases_after(d):
    where= f"WHERE Start_Date__c >= {d}"
    try:
        results = query_table(sf, 'lease', where)['records']
    except Exception as e:
        return {}

    return {r['Parking_Space__c']: r for r in results}

l = {'T':0, '2':1, 'H':2, 'C':3}
# To sort contractors
# 1. item[2] == 'OPEN' comes first
# 2. item[0][0] according to l dict
# 3. date comparison of item[2]
# 4. item[1] stays in same relative order
def comparator(item1, item2):
    if item1[2] == 'OPEN' and item2[2] == 'OPEN':
        return l[item1[0][0]] - l[item2[0][0]]
    
    # OPEN comes first
    if item1[2] == 'OPEN':
        return -1
    
    if item2[2] == 'OPEN':
        return 1
    
    diff = l[item1[0][0]] - l[item2[0][0]]
    if diff == 0:
        return 2*int(item1[2] > item2[2])-1
    else: 
        return diff


def main():
    args = parse_args()
    date = get_date(args)

    print(f'Available parking spaces for date: {date}')
    print('===================')

    if args.all:
        buildings = ['NU', 'GR', 'KN']
    else:
        buildings = ['KN']
        
    for key, val in get_open_spaces(date).items():
        if key not in buildings:
            continue

        print(f'Building: {key}')
        print('-------------------')
        s = sorted(val, key=cmp_to_key(comparator))
        for space, _ in zip(s, range(0, args.print_amount)):
            print(space)

        if len(val) > args.print_amount:
            print(f'... and {len(val) - args.print_amount} more')
        print('-------------------')


if __name__ == '__main__':
    main()