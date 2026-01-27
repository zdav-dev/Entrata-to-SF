import os
from auth import sf
import utils
from datetime import datetime
import get_available_spaces as sp
from functools import cmp_to_key
import argparse

class Task:
    def __init__(self, message):
        self.id = message['Id']
        self.parse_body(message['Description'])

    def parse_body(self, body):
        lines = body.split('\n')
        data = {}
        for line in lines:
            if ':' in line:
                key, val = line.split(':', 1)
                data[key.strip()] = val.strip()

        if 'From' in data:
            try:
                name, email = data['From'].split('<')
                self.email = email[:-1]
                self.name = name.strip()
            except ValueError:
                self.email = None
                self.name = None

        if 'Start Date' in data:
            self.start_date = data['Start Date']
        else:
            self.start_date = None

        if 'End Date' in data:
            self.end_date = data['End Date']
        else:
            self.end_date = None

        self.data = data
    
    def __str__(self):
        if self.is_valid():
            return f'{self.email}: {self.name} | {self.start_date} - {self.end_date}'
        
        return f"{self.id}: Invalid Task"

    def is_valid(self):
        return self.email and self.start_date and self.end_date
    
    def date_format(self, d):
        return datetime.strptime(d.strip(), "%m/%d/%Y").strftime("%Y-%m-%d")
    
    def get_obj(self):
        return {
            'Email__c': self.email,
            'Full_Name__c': self.name,
            'Start_Date__c': self.date_format(self.start_date),
            'End_Date__c': self.date_format(self.end_date)
        }

# Iterator that yields available spaces in order of buildings
# Uses get_avialable_spaces.py's comparator to order the spaces within each building
#
# 1. Yields from buildings in order KN, GR, NU
# 2. Yields 'OPEN' spaces from The Quarters on Campus first
# 3. All rejected spaces are added to 'Last Resort' building, which always returns
#    These spaces are in order of 1. and may or may not work.
# 
#
class SpaceIterator():
    def __init__(self, spaces, extra='Last Resort'):
        self.extra = extra
        self.spaces = {key: sorted(val, key=cmp_to_key(sp.space_comparator)) for key, val in spaces.items()}
        spaces[extra] = []
        self.buildings = iter(['KN', 'GR', 'NU', extra])
        self.current_building = next(self.buildings)
        self.index = 0

    def advance_building(self, last_resort=True):
        if last_resort:
            self.spaces[self.extra].extend(self.spaces[self.current_building][self.index:])
        self.index = 0
        self.current_building = next(self.buildings)
    
    def __iter__(self):
        return self
    
    # self.advance_building() will raise StopIteration when no spaces are left
    def __next__(self):
        while True:
            # Go through the current building's spaces
            # If no good options are left, add remaining spaces to 'last resort' and move to the next building
            # If on 'Last Resort', yield the next space always
            if self.index < len(self.spaces[self.current_building]):
                option = self.spaces[self.current_building][self.index]
                if (option[2] != "OPEN" or option[0] != "The Quarters on Campus") and self.current_building != self.extra:
                    self.advance_building(last_resort=True)
                    continue
                self.index += 1
                return option
            else:
                self.advance_building(last_resort=False)
            
# Prompts user to confirm task details
def confirm_task(t):
    print(t)
    exited = False
    confirm = input("Is this information correct? (y/n): ")
    while confirm.lower() != 'y':
        edit_str = set(c for c in input("Do you want to edit (n)ame, (e)mail, (s)tart date, en(d) date or e(x)it?\nEnter all that apply with no spaces\n> ").lower())
        if 'x' in edit_str:
            exited = True
            break
        if 'n' in edit_str:
            t.name = input("Enter Full Name:\n> ")
        if 'e' in edit_str:
            t.email = input("Enter Email:\n> ")
        if 's' in edit_str:
            t.start_date = input("Enter Start Date (MM/DD/YYYY):\n> ")
        if 'd' in edit_str:
            t.end_date = input("Enter End Date (MM/DD/YYYY):\n> ")
        
        print(t)
        confirm = input("Is this information correct? (y/n): ")

    if not exited:
        return t.get_obj()
    
    return None

# Pulls all Tasks from Salesforce and returns valid ones
def parse_tasks():
    soql_query = "SELECT Id, Subject, ActivityDate, Description, Status FROM Task LIMIT 100"
    results = sf.query_all(soql_query)['records']

    to_add = []
    to_delete = []
    for result in results:
        t = Task(result)
        if t.is_valid():
            if confirm_task(t):
                to_add.append(t.get_obj())
                to_delete.append(result)
        else:
            print(t)

    return to_add, to_delete

# Get Valid Tasks, add as Applicants, then delete the Tasks
def move_from_tasks():
    to_add, to_delete = parse_tasks()

    if to_add and to_delete:
        print("Adding Applicants:")
        for item in to_add:
            print(item)

        utils.insert_to_table(sf, to_add, table='Applicant__c')
        utils.create_id_csv(to_delete, csv_file='tasks_to_delete.csv')
        utils.delete_from_csv(sf, csv_file='tasks_to_delete.csv', table='Task')
    else:
        print("No valid tasks to process.")

# Raises StopIteration if no spaces left
# Confirms with user if space is not open or it's from a different contractor
def confirm_space(spiterator):
    accepted = False

    while not accepted:
        contractor, space, space_status = next(spiterator)
        if space_status != "OPEN" or contractor != "The Quarters on Campus":
            if contractor != "2215" or contractor != "The Quarters on Campus":
                continue

            cont = input(f'Space {space} is {space_status} and contractor is {contractor}. \
                         Do you want to add this space? (y/n/(e)xit):\n> ')
            match cont.lower():
                case 'e':
                    return None
                case 'n':
                    continue
                case 'y':
                    accepted = True
        else:
            accepted = True

    return space
    

# Assign parking spaces to each applicant
# Yields lists of IDs to delete and records to insert
# Each batch is grouped by move-in date
def assign_spaces(to_move):
    # Move-ins grouped by start month and year
    move_ins = {}
    for person in to_move:
        year, month, _ = person['Start_Date__c'].split("-")
        start = sp.date_of_last_day_of_month(int(year), int(month))
        if start not in move_ins:
            move_ins[start] = []

        move_ins[start].append(person)

    # Gets available spaces for each move-in date and assigns to applicants in group
    # Yields IDs to delete and records to insert
    # Does this so that sp.get_open_spaces() will update in-between each batch
    space_lookup = utils.set_parking_spaces(sf)
    contractor_lookup = utils.set_lease_owners(sf)
    for start, applicants in move_ins.items():
        result = []
        ids = []
        print(f'Finding spaces for move-ins on {start}...')
        spiterator = SpaceIterator(sp.get_open_spaces(start))
        for applicant in applicants:
            try:
                if not applicant['Pass_Number__c']:
                    print(f'No parking pass specified for {applicant["Full_Name__c"]}. Skipping.')
                    continue

                space = confirm_space(spiterator)
                if not space:
                    continue

                # Add Space, Contractor, and prepare ID for deletion
                applicant['Parking_Space__c'] = space_lookup[space]
                applicant['Lease_Contract_Owner__c'] = contractor_lookup["The Quarters on Campus"]
                ids.append({'Id': applicant['Id']})
                del applicant['Id']
                result.append(applicant)

            except StopIteration:
                print(f'Ran out of spaces on {applicant['Full_Name__c']} for date {start}.')
                break

        yield ids, result

# Move Applicants to Leases in Salesforce
# Queries Applicants with 'Paid' status and a monthly rate set
# Assigns a parking space to valid applicants and inserts as Leases
# Deletes moved Applicants from Salesforce
def move_from_applicants():
    soql_query = "SELECT Id, Start_Date__c, End_Date__c, Full_Name__c, Email__c, Status__c, Monthly_Rate__c, Pass_Number__c FROM Applicant__c LIMIT 100"
    results = sf.query_all(soql_query)['records']
    valid = [r for r in results if r['Status__c'] == 'Paid' and r['Monthly_Rate__c']]
    if not valid:
        print('No applicants to move.')
        return

    # Prepare records for lease insertion
    for applicant in valid:
        applicant['Lessee_Name__c'] = applicant['Full_Name__c']
        del applicant['Status__c']
        del applicant['Full_Name__c']
        del applicant['attributes']

    file = 'applicants_to_delete.csv'
    remove_ids = []
    for ids, move_in_list in assign_spaces(valid):
        if not move_in_list:
            continue

        date_val = datetime.strptime(move_in_list[0]['Start_Date__c'], "%Y-%m-%d").strftime("%B %Y")
        print(f'Moving in {len(move_in_list)} applicants for {date_val}...')
        result = utils.insert_to_table(sf, move_in_list, table='Leases__c')
        if not result:
            print('Error inserting leases. Aborting move-in.')
            continue

        remove_ids.extend(ids)

    if remove_ids:
        utils.create_id_csv(csv_file=file, id_list=remove_ids)
        utils.delete_from_csv(sf, csv_file=file, table='Applicant__c')
        print(f'{len(remove_ids)} Applicant{"s" if len(remove_ids) != 1 else ""} deleted.')

def parse_args():
    parser = argparse.ArgumentParser(
        description='Move applicants from Tasks to Applicants\nor from Applicants to Leases in SF'
    )

    parser.add_argument(
        '-t',
        '--tasks',
        action='store_true',
        help='Tasks to Applicants',
    )

    parser.add_argument(
        '-a',
        '--applicants',
        action='store_true',
        help='Applicants to Leases'
    )

    return parser.parse_args()

# Get Valid Tasks, add as Applicants, then delete the Tasks
def main():
    args = parse_args()
    if args.tasks:
        move_from_tasks()
    if args.applicants:
        move_from_applicants()

    if not args.tasks and not args.applicants:
        print("No action specified. Use -t to move from Tasks to Applicants or -a to move from Applicants to Leases.")

if __name__ == "__main__":
    main()
