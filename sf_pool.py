import utils
from tables.pool import pool_cols
from tables.lease import lease_cols
from auth import sf


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
# spaces['Contractor_Name__c'] == the id stored in available_to_add
# Choose leases that are not in the pool:
# Choose ones owned by the Quarters on Campus
def choose_to_add(leases, pool, amount):
    pool_lease_ids = set(r['Lease_ID__r']['Id'] for r in pool)
    lease_ids = set(r['Id'] for r in leases)
    available_to_add = lease_ids - pool_lease_ids
    print(len(available_to_add), len(pool_lease_ids), len(lease_ids))

    spaces = utils.query_table(sf, 'parking')['records']
    print(spaces[0])
    print(list(available_to_add)[0])

    return []



quarter = 3
year = 2025

pool = get_pool_from_quarter(quarter, year)
leases = get_leases_from_quarter(quarter, year)

print(leases[:5])
print(leases[-5:])
print(len(pool))

choose_to_add(leases, pool, 20)

# for record in pool:
#     print(f'{record["Lease_ID__r"]["Start_Date__c"]}: {record["Lease_ID__r"]["Lessee_Name__c"]}')

