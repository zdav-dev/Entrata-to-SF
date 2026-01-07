contractor_cols = ", ".join(['Id', 'Name'])

class Contractor():
    def __init__(self, oDict):
        self.id = oDict['Id']
        self.name = oDict['Name']

    def __str__(self):
        return f"Contractor: {self.name}"