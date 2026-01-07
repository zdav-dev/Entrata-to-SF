# Entrata to SF
This project is to add existing data from one system (Entrata) into another (Salesforce)
The work being done is for managing a parking garage, which has 933 spaces in total, and 4 different contractors leasing out spaces.
Only 'Quarters' manages the spaces through Entrata, and the other contractors pay Quarters for x amount of spots
The goal is to take all information from Entrata, and merge it into Salesforce along with contractor data to better track leases and payments over time.

# About the Database

## Tables
There are 3 tables - Leases, Contractors, and Parking Spaces

## Parking Spaces
 - A list of what spaces there are in the parking garage, and which contractor owns it

## Contractors
 - General information about each contractor

## Leases
 - Assigned space, lease term, lessee name, contact info, etc.
 - Eventually, this will be populated through leads from SF, and through Entrata
 - This project will sync data and parking space assignment between the two systems


# About the files

## utils.py
 - Helper functions for sf_add.py

## read_entrata_csv.py
 - Creates a dictionary of people for entry into salesforce

## sf_add.py
 - Finds, compares, adds, and checks for deletion of entries in salesforce database
 - Creates log files with any potential issues for human review
 - includes a few example functions for future reference on sf functionality
 
## sf_filter.py
 - Future use for customizing report filters rather than making a new report each month


# FAQ

## Why would you ever build it like this? Surely there's a better way?
I don't have access to Entrata's API, so I had to use their basic reports.

There is no unique key in Entrata that would also be unique in Salesforce,
so checks have to be done comparing multiple columns to find a match

## How much of the 'leases' database is being pulled each time?
This is run 1x in the morning, and there is a maximum of:
933 (spaces) * 4 (terms per year) * 2 (years) = 7464 entries that could match a query.