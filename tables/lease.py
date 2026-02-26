lease_cols = ', '.join(['Id', 'Entrata_Id__c', 'Email__c', 'Start_Date__c', 'End_Date__c', 'Parking_Space__c', 'Lessee_Name__c', 'Monthly_Rate__c', 'Pool_Quarter__c', 'Is_Resident__c', 'Lease_Contract_Owner__c', 'Parking_Space__r.name', 'Lease_Contract_Owner__r.name'])

class Lease():
    def __init__(self, oDict):
        self.id = oDict['Id']
        self.email = oDict['Email__c']
        self.start = oDict['Start_Date__c']
        self.end = oDict['End_Date__c']
        self.parking_space_ref = oDict['Parking_Space__c']
        self.person = oDict['Lessee_Name__c']
        self.rate = oDict['Monthly_Rate__c']
        self.is_resident = oDict['Is_Resident__c']
        self.lease_owner = oDict['Lease_Contract_Owner__c']

    def __str__(self):
        return f'Parking Space Reference: {self.parking_space_ref} - {self.start}/{self.end}, {self.person} - {self.email}'
