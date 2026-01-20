import utils
from datetime import datetime
from read_entrata_csv import get_people
from auth import sf

# Make sure most recent csv is downloaded
available = utils.download_from_drive()
# Get people from most recent changed csv
if available:
    people = get_people(changed=False)
else:
    people = []

# Find a match
comparison_cols = [
    'Lessee_Name__c',
    'Start_Date__c',
]

parking_space_to_ref = utils.set_parking_spaces(sf)
lease_owner_to_ref = utils.set_lease_owners(sf)

# Get all leases from Salesforce
# Quarters clause can be added to filter to only The Quarters on Campus leases
def get_leases(quarters=False):
    if not quarters:
        return utils.query_table(
            sf, 
            'lease',
            f"WHERE End_Date__c >= {datetime.today().strftime('%Y-%m-%d')}"
        )
    
    return utils.query_table(
        sf,
        'lease', 
        f"WHERE Lease_Contract_Owner__r.name = 'The Quarters on Campus'\
        AND End_Date__c >= {datetime.now().strftime('%Y-%m-%d')}"
    )

# Creates a lookup of Entrata IDs to existing lease records
# Used to see if a record already exists in the system
def get_id_lookup(data):
    id_lookup = {}
    for record in data:
        entrata_id = record['Entrata_Id__c']
        if not entrata_id:
            continue
        
        if entrata_id not in id_lookup:
            id_lookup[entrata_id] = []

        id_lookup[entrata_id].append(record)

    return id_lookup

# Returns new records and potential problem records
# New records are those that do not exist in the system
# Problem records are those that have matching Entrata ID but differ in other fields
def get_new_records(id_lookup):
    new_records = []
    problems = []
    for person in people:
        entrata_id = person['Entrata_Id__c']
        # Entrata ID Not in the system - new Record
        if entrata_id not in id_lookup:
            new_records.append(person)
            continue

        records = id_lookup[entrata_id]
        
        for record in records:
            temp_problem = {col:person[col]==record[col] for col in comparison_cols if col in record}

            # Perfect match (Parking space and start date)
            if all(val for val in temp_problem.values()) \
                and parking_space_to_ref[person['Parking_Space__c']] == record['Parking_Space__c']:
                if not person['End_Date__c'] == record['End_Date__c']:
                    problems.append(person)
                    break
                else:
                    break
        else:
            new_records.append(person)

    return new_records, problems

# Creates a lookup of parking spaces to existing lease date ranges
def get_space_lookup(data):
    space_lookup = {}
    format_string = "%Y-%m-%d"
    for record in data:
        parking_space = record['Parking_Space__c']

        if parking_space not in space_lookup:
            space_lookup[parking_space] = []

        space_lookup[parking_space].append(
            (datetime.strptime(record['Start_Date__c'], format_string), 
             datetime.strptime(record['End_Date__c'], format_string))
        )

    return space_lookup

# Checks if a single lease record overlaps with existing leases
def is_overlapping(res_list, record):
    format_string = "%Y-%m-%d"
    record_start = datetime.strptime(record['Start_Date__c'], format_string)
    record_end = datetime.strptime(record['End_Date__c'], format_string)
    overlap = False

    for start, end in res_list:
        overlap |= (record_end <= end and record_end >= start) \
        or (record_start >= start and record_start <= end)

    return overlap

# Checks for overlapping leases in the new records
# If any overlaps are found, they are returned in the invalid list
def check_overlap(data, records):
    spaces = get_space_lookup(data)
    valid = []
    invalid = []
    for record in records:
        try:
            parking_space = parking_space_to_ref[record['Parking_Space__c']]
        except:
            parking_space = record['Parking_Space__c']
        
        if parking_space not in spaces:
            valid.append(record)
            continue

        if is_overlapping(spaces[parking_space], record):
            invalid.append(record)
        else:
            valid.append(record)

    return valid, invalid

# convert to valid object for upload
def convert_record(record):
    try:
        record['Monthly_Rate__c'] = float(record['Monthly_Rate__c'])
    except:
        return False, record

    # Convert to Salesforce IDs
    record['Lease_Contract_Owner__c'] = lease_owner_to_ref['The Quarters on Campus']
    record['Parking_Space__c'] = parking_space_to_ref[record['Parking_Space__c']]

    return True, record

# Add new lease records to Salesforce
# If any records fail to insert, they are returned in the failed list
# Prints the results of the insert operation
def add_records(records):
    to_insert = []
    failed = []
    for record in records:
        success, updated = convert_record(record)
        if success:
            to_insert.append(updated)
        else:
            failed.append(updated)

    # print([f"{col}: {type(val)}" for col, val in records[0].items()])
    # print(records[0])
    if to_insert:
        insert_results = sf.bulk2.Leases__c.insert(records=to_insert)
        print(insert_results)
        # If errors occurred, get failed records and dump into CSV
        if insert_results[0]['numberRecordsFailed'] > 0:
            job_id = insert_results[0]['job_id']
            sf.bulk2.Leases__c.get_failed_records(job_id, file=f'{job_id}_failed.csv')
    else:
        print('No records to insert.')

    return to_insert, failed

# Delete all leases for The Quarters on Campus
def delete_quarters():
    data = get_leases(quarters=True)
    utils.create_id_csv(data)
    utils.delete_leases(sf)
    exit()

# Only used to update Hardin House Records monthly rate to 0
def update_records():
    data = utils.query_table(sf, 'lease', where="WHERE Lease_Contract_Owner__r.name = 'Hardin House'")

    for record in data['records']:
        id = record['Id']
        sf.Leases__c.update(id, {'Monthly_Rate__c': 0.0})
        print(f'Updated record {id}.')

# If a problem record has changed end date, update it in Salesforce
# Return changed records to use for checking overlap with new adds
def update_changed(changed, records):
    lookup = {f'{r['Entrata_Id__c']}{r['Start_Date__c']}':r for r in changed}
    updated = []
    for record in records:
        try:
            r = lookup[f'{record['Entrata_Id__c']}{record['Start_Date__c']}']
            r['End_Date__c'] = record['End_Date__c']
            sf.Leases__c.update(r['Id'], {'End_Date__c': r['End_Date__c']})
            print(f'Updated record {r['Id']}.')
            updated.append(record)
        except KeyError:
            pass

    return updated

# Creates a lookup for to verify that SF records match parking spaces in 'people'
def get_people_lookup():
    lookup = {}
    for person in people:
        parking_space = parking_space_to_ref[person['Parking_Space__c']]
        id = f"{person['Entrata_Id__c']}{parking_space}{person['Start_Date__c']}{person['End_Date__c']}"
        lookup[id] = person

    return lookup

# Checks that none of the parking spaces have been moved around.
# Does not find the right match, just returns all records that do not match
def verify_sf_data(data):
    changed = []
    unchanged = []
    people_lookup = get_people_lookup()
    for record in data:
        if record['Entrata_Id__c'] is None:
            unchanged.append(record)
            continue

        id = f"{record['Entrata_Id__c']}{record['Parking_Space__c']}{record['Start_Date__c']}{record['End_Date__c']}"
        if id not in people_lookup:
            changed.append(record)
        else:
            unchanged.append(record)

    return changed, unchanged

# Authenticate salesforce
# Set up Lookups
# Get Lease data
# Get new potential lease records
# Check for overlaps
# Add valid records
# Create CSV logs
# TODO: Add command line arguments for different operations
def main():
    if not available:
        print("No new CSV available. Exiting.")
        return
    # Get Lease Data from Salesforce
    data = get_leases()['records']

    # Check that entrata id's in salesforce match parking spaces in 'people'
    changed, _ = verify_sf_data(data)
    id_lookup = get_id_lookup(data)
    new_records, problems = get_new_records(id_lookup)
    # Records with no monthly rate are not actually signed leases
    problems = [problem for problem in problems if problem['Monthly_Rate__c'] != '']
    # new_records = [record for record in new_records if record['Monthly_Rate__c'] != '']
    # If an update happened, add them to new records to check for overlaps and add
    # changed: sf data that recognizes something has changed
    # problems: csv data that differs from sf data
    # updated: csv data that has been updated to sf
    updated = update_changed(changed, problems)
    new_records.extend(updated)
    valid, overlapping = check_overlap(data, new_records)
    added, skipped = add_records(valid)

    # Data dumps
    utils.create_csv('overlapping', overlapping)
    utils.create_csv('skipped', skipped)
    utils.create_csv('added', added)
    utils.create_csv('updated', updated)
    utils.advance_logs()

if __name__ == "__main__":
    main()