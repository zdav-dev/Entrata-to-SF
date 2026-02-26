pool_cols = ', '.join(['Id', 'TT15_Share__c', 'TT15_Share_Amt__c', 'Lease_Id__r.Monthly_Rate__c', 'Lease_Id__r.Id', 'Lease_Id__r.Lessee_Name__c', 'Lease_Id__r.Start_Date__c', 'Lease_Id__r.End_Date__c', 'Lease_Id__r.Pool_Quarter__c'])

class Pooled_Lease():
    def __init__(self, oDict):
        self.id = oDict['Id']
        self.share = oDict['TT15_Share__c']
        self.share_amt = oDict['TT15_Share_Amt__c']
        self.lease_rate = oDict['Lease_Id__r.Monthly_Rate__c']
        self.lease_start = oDict['Lease_Id__r.Start_Date__c']
        self.lease_end = oDict['Lease_Id__r.End_Date__c']
        self.pool_quarter = oDict['Lease_Id__r.Pool_Quarter__c']

    def __str__(self):
        return f'Pooled Lease ID: {self.id} - Share: {self.share} ({self.share_amt}), Lease Rate: {self.lease_rate} from {self.lease_start} to {self.lease_end}'