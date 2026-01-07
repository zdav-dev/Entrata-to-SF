import os
import csv
from datetime import datetime

current_cols = {
    'Inventory Name': 'Parking_Space__c', 
    'Current Reservation - Rate': 'Monthly_Rate__c', 
    'Current Reservation - Reserved By': 'Lessee_Name__c',
    'Current Reservation - Email': 'Email__c',
    'Current Reservation - Reservation Dates': 'Dates',
    'Current Reservation - Lease Id': 'Entrata_Id__c'
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
def get_most_recent():
    data_path = 'csvs'
    files = os.listdir(data_path)
    files.sort(key=lambda x: os.path.getctime(os.path.join(data_path, x)))
    return os.path.join(data_path, files[-1])

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
    
    if len(future_person['Email__c']) > 3:
        result.append(future_person)

    for person in result:
        start, end = person['Dates'].split("-")
        person['Start_Date__c'] = datetime.strptime(start.strip(), "%m/%d/%Y").strftime("%Y-%m-%d")
        person['End_Date__c'] = datetime.strptime(end.strip(), "%m/%d/%Y").strftime("%Y-%m-%d")
        del person['Dates']

        last, first = person['Lessee_Name__c'].split(", ")
        first = first.split("(")[0].strip()
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
    people = []
    with open(f, mode = 'r', encoding='utf-8-sig') as file:
        csvFile = csv.reader(file)
        lines = iter(csvFile)
        headerLine = next(lines)
        for line in lines:
            people.extend(split_line(headerLine, line))

    return people


people = read_csv(get_most_recent())