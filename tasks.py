import os
from auth import sf
from utils import create_id_csv, delete_leases

"""
Used just to clean up Tasks --
Tasks are more selectively added now, so only needed once
"""


def delete_tasks():
    csv_file = "tasks_to_delete.csv"
    job_id = sf.bulk2.Task.delete(csv_file=csv_file)
    print(f'Delete Job ID: {job_id}')
    os.remove(csv_file)

def delete_creation():
    soql_query = "SELECT Id, Subject, ActivityDate, Status FROM Task LIMIT 100"

    results = sf.query_all(soql_query)

    #print(ids)
    file = "tasks_to_delete.csv"
    create_id_csv(results['records'][:-1], csv_file=file)
    #delete_leases(sf, csv_file=file)

# Uncomment to delete all but the most recent task
# delete_creation()
# delete_tasks()