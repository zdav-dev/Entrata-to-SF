import os
import csv
from datetime import datetime

class Person:
    attr_conversion = {
        'Parking_Space__c': 'parking_space',
        'Entrata_Id__c': 'e_id',
        'Start_Date__c': 'start',
        'End_Date__c': 'end',
        'Lessee_Name__c': 'name',
        'Email__c': 'email',
        'Pass_Number__c': 'pass_num',
        'Monthly_Rate__c': 'monthly_rate',
        'Lease_Contract_Owner__c': 'contractor',
        'Is_Resident__c': 'is_resident'
    }

    def __init__(self, data):
        self.parking_space = data['Parking_Space__c']
        self.e_id = data['Entrata_Id__c']
        self.start = data['Start_Date__c']
        self.end = data['End_Date__c']
        self.name = data['Lessee_Name__c'].strip()
        self.email = data['Email__c'].strip()
        self.pass_num = data['Pass_Number__c']
        self.monthly_rate = data['Monthly_Rate__c']
        self.is_resident = data['Is_Resident__c']
        self.contractor = None

    def __setitem__(self, key, value):
        if key in Person.attr_conversion:
            object.__setattr__(self, Person.attr_conversion[key], value)


    def __getitem__(self, key):
        if key in Person.attr_conversion:
            return object.__getattribute__(self, Person.attr_conversion[key])
        else:
            return None
        
    def __str__(self):
        return f"{self.name} ({self.email}): {self.start} - {self.end} in {self.parking_space}"
    
    def keys(self):
        return Person.attr_conversion.keys()
    
    def get(self, key, default_val=None):
        result = self.__getitem__(key)
        if not result:
            return default_val
        
        return result

current_cols = {
    'Inventory Name': 'Parking_Space__c', 
    'Current Reservation - Rate': 'Monthly_Rate__c', 
    'Current Reservation - Reserved By': 'Lessee_Name__c',
    'Current Reservation - Email': 'Email__c',
    'Current Reservation - Reservation Dates': 'Dates',
    'Current Reservation - Lease Id': 'Entrata_Id__c',
    'Current Reservation - Move Out Date': 'Moveout'
}

future_cols = {
    'Inventory Name': 'Parking_Space__c',
    'Future Reservation - Rate': 'Monthly_Rate__c', 
    'Future Reservation - Reserved By': 'Lessee_Name__c',
    'Future Reservation - Email': 'Email__c', 
    'Future Reservation - Reservation Dates': 'Dates',
    'Future Reservation - Lease Id': 'Entrata_Id__c'
}

# Most recently created file in csvs directory
def get_most_recent(changed=False):
    if changed:
        return 'csvs/changed.csv'
    
    data_path = 'csvs'
    tgt_name = datetime.now().strftime("%Y-%m-%d") + "_Rentable Items Availability.csv"
    return os.path.join(data_path, tgt_name)

# Split each line in the csv into current and future reservations
# Datetime format YYYY-MM-DD is comparable with >= as a string
# Takes the pass number from the lessee name if it exists (Last #1234, First)
# Only returns people with valid emails and end dates in the future
def split_line(headerLine, line):
    line_dict = {header:val for header, val in zip(headerLine, line)}
    current_person = {current_cols[col]:line_dict[col] for col in current_cols}
    future_person = {future_cols[col]:line_dict[col] for col in future_cols}
    result = []
    if len(current_person['Email__c']) > 3:
        result.append(current_person)
        if current_person['Moveout'] and len(current_person['Moveout']) > 0:
            current_person['Dates'] = f'{current_person['Dates'].split("-")[0]} - {str(current_person['Moveout'])}'
        del current_person['Moveout']
    
    if len(future_person['Email__c']) > 3:
        result.append(future_person)

    for person in result:
        start, end = person['Dates'].split("-")
        person['Start_Date__c'] = datetime.strptime(start.strip(), "%m/%d/%Y").strftime("%Y-%m-%d")
        person['End_Date__c'] = datetime.strptime(end.strip(), "%m/%d/%Y").strftime("%Y-%m-%d")
        del person['Dates']
        try:
            last, first = person['Lessee_Name__c'].split(", ")
            first_split = first.split("(")
            if len(first_split) > 1:
                person['Is_Resident__c'] = True
            else:
                person['Is_Resident__c'] = False
            first = first_split[0].strip()
        except ValueError:
            first = person['Lessee_Name__c']
            last = ""
        pass_num = ""
        if '#' in last:
            last, pass_num = last.split("#")
            last = last.strip()
            pass_num = pass_num.strip()

        
        person['Lessee_Name__c'] = f'{first} {last}'
        person['Pass_Number__c'] = pass_num.split("/")[0].strip()

    dates = [i for i in result if i['End_Date__c'] >= datetime.now().strftime("%Y-%m-%d")]
    return dates

# Read CSV and return list of people dictionaries
#
# Each person will have:
# 'Parking_Space__c', 'Monthly_Rate__c', 'Lessee_Name__c', 
# 'Email__c', 'Start_Date__c', 'End_Date__c', 
# 'Entrata_Id__c', 'Pass_Number__c'
#
# __c indicates custom Salesforce field
def read_csv(f):
    temp_people = []
    with open(f, mode = 'r', encoding='utf-8-sig') as file:
        csvFile = csv.reader(file)
        lines = iter(csvFile)
        headerLine = next(lines)
        for line in lines:
            temp_people.extend(split_line(headerLine, line))
    
    people = [Person(p) for p in temp_people]
    return people

def get_people(changed=False):
    return read_csv(get_most_recent(changed=changed))

def main():
    people = get_people()

if __name__ == "__main__":
    main()