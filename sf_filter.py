import os
import json
from auth import sf
from dotenv import load_dotenv
from datetime import date

load_dotenv()
report_id = os.getenv("REPORT_ID")
report_url = f'/analytics/reports/{report_id}/instances'

def get_last_quarter_dates():
    today = date.today()
    current_quarter_month = (today.month-1)//3*3 + 1
    last_quarter_start_month = current_quarter_month - 3
    last_quarter_year = today.year
    if last_quarter_start_month <= 0:
        last_quarter_start_month += 12
        last_quarter_year -= 1

    for i in range(3):
        yield f"{last_quarter_year}-{str(last_quarter_start_month + i).zfill(2)}-01"

def get_filter(start_date):
    custom_filter = {
        "reportMetadata": {
            "reportFilters": [
                {
                    "column": "Start_Date__c",
                    "operator": "lessThan",
                    "value": start_date
                },
                {
                    "column": "End_Date__c",
                    "operator": "greaterThan",
                    "value": start_date
                }
            ]
        }
    }
    return custom_filter



def main():
    for date in get_last_quarter_dates():
        filter = get_filter(date)
        response = sf.rest_post(report_url, data=json.dumps(filter))
        report_rows = response['factMap']['T!T']['rows']
        print(f"Report for {date}: {len(report_rows)} records found.")
        print(report_rows)



if __name__ == "__main__":
    main()