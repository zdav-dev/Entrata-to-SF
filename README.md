# Entrata to SF
Code to connect Entrata system to Salesforce database

## utils
 - Helper functions for sf_add.py

# read_entrata_csv.py
 - Creates a dictionary of people for entry into salesforce

## sf_add.py
 - Finds, compares, adds, and checks for deletion of entries in salesforce database
 - Creates log files with any potential issues for human review
 - includes a few example functions for future reference on sf functionality


## sf_filter.py
 - Future use for customizing report filters rather than making a new report each month
 

## FAQ

## Why would you ever build it like this? Surely there's a better way?
I don't have access to Entrata's API, so I had to use their basic reports.

There is no unique key in Entrata that would also be unique in Salesforce,
so checks have to be done comparing multiple columns to find a match

## How much of the 'leases' database is being pulled each time?
This is run 1x in the morning, and there is a maximum of:
933 (spaces) * 4 (terms per year) * 2 (years) = 7464 entries that could match a query.