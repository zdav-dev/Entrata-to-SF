import utils
from tables.pool import pool_cols
from tables.lease import lease_cols
from auth import sf
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description='Manage leases and pooled leases.')
    parser.add_argument('-q', '--quarter', type=int, required=False, help='Quarter number (1-4)')
    parser.add_argument('-y', '--year', type=int, required=False, help='Year (e.g., 2024)')
    parser.add_argument('-t', '--target', type=int, required=False, help='Number of leases to total in the pool')
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

    if not len(available_to_add):
        print('No available leases to add to the pool.')
        return []

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

def update_lease_pool_date(leases_to_add, pool_quarter, pool_year):
    to_update = []
    for lease in leases_to_add:
        record = {
            'Id': lease['Id'],
            'Pool_Quarter__c': f'Q{pool_quarter} {pool_year}'
        }
        to_update.append(record)

    return utils.update_table(sf, to_update, table='Lease__c')

def add_to_pool(leases_to_add, share_percent, quarter, year):
    to_insert = []
    for lease in leases_to_add:
        record = {
            'Lease_ID__c': lease['Id'],
            'TT15_Share__c': share_percent,
        }
        to_insert.append(record)

    result = utils.insert_to_table(sf, to_insert, table='Pooled_Lease__c')
    update_lease_pool_date(leases_to_add, quarter, year)
    return result

def add_from_target(pool, target, quarter, year):
    if target <= len(pool):
        print(f'Pool already has {len(pool)} leases, which meets or exceeds the target of {target}. No leases to add.')
        return

    leases = get_leases_from_quarter(quarter, year)
    leases_to_add = choose_to_add(leases, pool, target - len(pool))
    
    print(f'Adding {len(leases_to_add)} leases to the pool for Q{quarter} {year}.')
    share_percent = pool[0]['TT15_Share__c']

    cont = input(f'Proceed to add leases with TT15 Share Amount of {share_percent*100}%? (y/n): ')
    if cont.lower() != 'y':
        print('Operation cancelled.')
        return
    
    return add_to_pool(leases_to_add, share_percent, quarter, year)


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

    if not pool:
        print(f'No leases found in the pool for Q{quarter} {year}.')
        return
    
    if args.target:
        add_from_target(pool, args.target, quarter, year)
        return
    
    print(f'Leases in the pool for Q{quarter} {year}: {len(pool)}')
    print(f'Percentage for each lease: {pool[0]["TT15_Share__c"]*100}%')
    
if __name__ == '__main__':
    main()
