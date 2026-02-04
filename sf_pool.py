import utils
from tables.pool import pool_cols
from tables.lease import lease_cols
from auth import sf
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description='Manage leases and pooled leases.')
    parser.add_argument('-q', '--quarter', type=int, required=False, help='Quarter number (1-4)')
    parser.add_argument('-y', '--year', type=int, required=False, help='Year (e.g., 2024)')
    parser.add_argument('-t', '--target', type=int, required=True, help='Number of leases to total in the pool')
    return parser.parse_args()

def get_dates_from_quarter(quarter, year):
    begin_date = f"{year}-{'%02d' % ((quarter - 1) * 3 + 1)}-01"
    last_date = f"{year}-{'%02d' % ((quarter - 1) * 3 + 3)}-02"
    return begin_date, last_date
    
def get_leases_from_quarter(quarter, year):
    begin_date, last_date = get_dates_from_quarter(quarter, year)
    where = f"WHERE Start_Date__c <= {last_date} AND Start_Date__c >= {begin_date} AND Lease_Contract_Owner__r.name = 'The Quarters on Campus'"

    return utils.query_table(sf, 'lease', where)['records']

def get_pool_from_quarter(quarter, year):
    begin_date, last_date = get_dates_from_quarter(quarter, year)
    print(begin_date, last_date)
    where = f"WHERE Lease_Id__r.Start_Date__c <= {last_date} AND Lease_Id__r.Start_Date__c >= {begin_date}"

    return utils.query_table(sf, 'pool', where)['records']


# Choose lease Ids to add to the pool based on amount needed
def choose_to_add(leases, pool, amount):
    pool_lease_ids = set(r['Lease_ID__r']['Id'] for r in pool)
    lease_ids = set(r['Id'] for r in leases)
    available_to_add = lease_ids - pool_lease_ids

    where = f"WHERE Contractor_Name__r.name = 'The Quarters on Campus' AND Building__c = 'KN'"
    spaces = set(s['Name'] for s in utils.query_table(sf, 'parking', where)['records'])
    lease_lookup = {r['Id']: r for r in leases if r['Id'] in available_to_add and r['Parking_Space__r']['Name'] in spaces}
    result = []
    for space in available_to_add:
        if space in lease_lookup:
            result.append(lease_lookup[space])

        if len(result) == amount:
            break

    return result

def main():
    args = parse_args()
    if args.quarter and args.quarter not in [1, 2, 3, 4]:
        print('Quarter must be between 1 and 4.')
        return
    
    if args.year and args.year < 2025:
        print('Year must be 2025 or later.')
        return
    
    if args.quarter and args.year:
        quarter = args.quarter
        year = args.year
    else:
        quarter = 3
        year = 2025

    pool = get_pool_from_quarter(quarter, year)
    
    if args.target <= len(pool):
        print(f'Pool already has {len(pool)} leases, which meets or exceeds the target of {args.target}. No leases to add.')
        return

    leases = get_leases_from_quarter(quarter, year)
    leases_to_add = choose_to_add(leases, pool, args.target - len(pool))
    
    print(f'Adding {len(leases_to_add)} leases to the pool for Q{quarter} {year}.')
    print(leases_to_add[0])
    print(pool[0])

if __name__ == '__main__':
    main()
