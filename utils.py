import csv
import os
import shutil
import datetime
import tables.lease as lease
import tables.parking as parking
import tables.contractor as contractor
import tables.pool as pool
from dotenv import load_dotenv

# Ease for queries
tables = {
    'parking': {
        'name': 'Parking_Space__c', 
        'columns': parking.parking_cols, 
        'object': parking.Parking_Space
    },
    'lease': {
        'name': 'Leases__c',
        'columns': lease.lease_cols,
        'object': lease.Lease
    },
    'contractor': {
        'name': 'Contractor__c',
        'columns': contractor.contractor_cols,
        'object': contractor.Contractor
    },
    'pool': {
        'name': 'Pooled_Lease__c',
        'columns': pool.pool_cols,
        'object': None
    }
}


# Generic function to query any table with any where clause       
def query_table(sf, table, where=""):
    name = tables[table]['name']
    cols = tables[table]['columns']

    return sf.query_all(f"SELECT {cols} FROM {name} {where}")

# Create a CSV file from a list of dictionaries
def create_csv(name, data, delete=False):
    if not data or not len(data):
        return
    
    csv_file = f'logs/{name}.csv'
    if delete and os.path.exists(csv_file):
        os.remove(csv_file)

    while os.path.exists(csv_file):
        csv_file = csv_file.replace('.csv', '(1).csv')

    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[col for col in data[0].keys()])
        writer.writeheader()
        writer.writerows(data)

# Create a CSV file with all IDs for deletion
def create_id_csv(data):
    csv_file = 'to_delete.csv'

    id_list = [{'Id': record['Id']} for record in data]

    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['Id'])
        writer.writeheader()
        writer.writerows(id_list)

# Delete leases from a CSV file containing IDs
def delete_leases(sf, csv_file='to_delete.csv'):
    job_id = sf.bulk2.Leases__c.delete(csv_file=csv_file)
    print(f'Delete Job ID: {job_id}')
    os.remove(csv_file)

# Lists columns for a given custom table
def list_cols(sf, obj_name):
    try:
        description = getattr(sf, obj_name).describe()

        print(f'Columns for custom table {obj_name}:')
        for field in description['fields']:
            #print(field)
            print(f'* {field['name']} (Type: {field['type']})')

    except Exception as e:
        print(f'Error accessing object {obj_name}: {e}')

# List all custom tables and their columns
def list_all(sf):
    for obj in ('Parking_Space', 'Leases', 'Contractor'):
        list_cols(sf, obj + '__c')


# Set parking space lookup
# Used for converting parking space names to Salesforce IDs
def set_parking_spaces(sf):
    result = {}
    data = query_table(sf, 'parking')['records']

    for record in data:
        result[record['Name']] = record['Id']

    return result

# Set lease owners lookup
# Used for converting names to Salesforce IDs
def set_lease_owners(sf):
    result = {}
    data = query_table(sf, 'contractor')['records']

    for record in data:
        result[record['Name']] = record['Id']

    return result

# Finds difference in entries between 2 csv files
# Outputs to logs/diffs/{diff_file.csv}
def log_csv_diff(old_file, new_file, diff_file):
    entries = {}
    entries_reverse = {}
    diffs = []
    with open(old_file, 'r', encoding='utf-8-sig') as f_old, open(new_file, 'r', encoding='utf-8-sig') as f_new:
        old_csv = csv.reader(f_old)
        new_csv = csv.reader(f_new)
        old_lines = iter(old_csv)
        new_lines = iter(new_csv)
        headerLine = next(old_lines)
        next(new_lines)

        for line in old_lines:
            line_dict = {header:val for header, val in zip(headerLine, line)}
            entries[line_dict['Entrata_Id__c']] = line_dict

        for line in new_lines:
            line_dict = {header:val for header, val in zip(headerLine, line)}
            entries_reverse[line_dict['Entrata_Id__c']] = line_dict

            if line_dict['Entrata_Id__c'] not in entries:
                line_dict['Change_Type'] = 'New Entry'
                diffs.append(line_dict)

        for key, value in entries.items():
            if key not in entries_reverse:
                value['Change_Type'] = 'Removed Entry'
                diffs.append(value)

    print(f'{diff_file}: Found {len(diffs)} new entries between {old_file} and {new_file}')
    create_csv(diff_file, diffs, delete=True)

# Helper for create_diffs
def get_matching_files(dir = "./logs"):
    for f in os.listdir(dir):
        if f.endswith("(1).csv"):
            yield f.replace("(1).csv", ".csv"), f

# Creates csvs with the difference between new and old csvs
# overlapping.csv compares to overlapping(1).csv
def create_diffs():
    for old, new in get_matching_files():
        log_csv_diff(f"./logs/{old}", f"./logs/{new}", f"diffs/{old.replace('.csv', '')}")

# Deletes old log files and renames (1).csv to .csv
def advance_logs():
    create_diffs()
    log_dir = 'logs'
    files = os.listdir(log_dir)
    for file in files:
        if file.endswith('(1).csv'):
            new_file = os.path.join(log_dir, file)
            old_file = new_file.replace('(1).csv', '.csv')
            os.rename(new_file, old_file)

# Gets most recent file from google drive folder
# "Most Recent" determined by filename date prefix YYYY-MM-DD
def download_from_drive():
    tgt_name = datetime.datetime.now().strftime("%Y-%m-%d") + "_Rentable Items Availability.csv"
    if os.path.exists(f'csvs/{tgt_name}'):
        print("Most recent file already downloaded.")
        return
    load_dotenv()
    drive_dir = os.getenv("DRIVE_DIR")
    file_list = os.listdir(drive_dir)
    file_list.sort(key=lambda x: x.split("_")[0])
    most_recent = file_list[-1]
    print(f'Added {most_recent}')
    shutil.copyfile(f'{drive_dir}/{most_recent}', f'csvs/{most_recent}')

if __name__ == "__main__":
    download_from_drive()