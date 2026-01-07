parking_cols = ', '.join(['Id', 'Name', 'Contractor_Name__c'])

class Parking_Space():
    def __init__(self, oDict):
        self.id = oDict['Id']
        self.name = oDict['Name']
        self.contractor_ref = oDict['Contractor_Name__c']

    def __str__(self):
        return f'{self.name} - Contractor Reference: {self.contractor_ref}'