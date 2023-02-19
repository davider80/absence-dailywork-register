#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import json
import datetime
import pandas as pd
import argparse, textwrap
import yaml
from requests_hawk import HawkAuth

ABSENCE_URL = "https://app.absence.io"
DATA_FILE = "data.yml"
daysofweek=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

def readdata(file):
  with open(r"%s" % file) as file:
    return yaml.full_load(file)

def sendwork(day, id, key, typeofwork, starthour='08:00', endhour='16:00'):

  hawk_auth = HawkAuth(id=id, key=key)
  response = requests.get("%s/api/v2/users/%s" % (ABSENCE_URL, id), auth=hawk_auth)
  if response.status_code != 200:
    print("Fail connecting to: %s, with id: %s and key: %s" % (ABSENCE_URL, id, key))
    exit(1)

  response = requests.get("%s/api/v2/users/%s" % (ABSENCE_URL, id), auth=hawk_auth)
  if response.status_code != 200:
    print("Fail connecting to: %s, with id: %s and key: %s" % (ABSENCE_URL, id, key))
    exit(1)

  headers = {
      'Content-Type': "application/json",
  }
  

  #Check if an absence exists that day
  data_get_absences = {
    "skip": 0,
    "limit": 50,
    "filter": {
      "assignedToId": "%s" % id,
      "start": {"$lte" : "%sT00:00:00.000Z" % (day)},
      "end": {"$gte": "%sT00:00:00.000Z" % (day)}, 
    }
  }

  resp = requests.post("%s/api/v2/absences" % ABSENCE_URL, auth=hawk_auth ,data=json.dumps(data_get_absences), headers=headers)

  absences = json.loads(resp.text)

  if(absences["count"] == 0):

    data_create_entry = {
      "userId": "%s" % id,
      "start": "%sT%s:00.000Z" % (day, starthour),
      "end": "%sT%s:00.000Z" % (day, endhour),
      "timezoneName": "CET",
      "timezone": "+0000",
      "type": "%s" % typeofwork
    }

    print(day+": write work time entry")
    resp = requests.post("%s/api/v2/timespans/create" % ABSENCE_URL, auth=hawk_auth ,data=json.dumps(data_create_entry), headers=headers)

  else:
    print(day+": skipped because of holiday")

def week_array(date):
    start_date = date + datetime.timedelta(-date.weekday(), weeks=-1)
    end_date = start_date+datetime.timedelta(days=5)
    return pd.date_range(start_date, end_date , freq='B')

def year_array(date):
    start_date = date
    end_date = datetime.date(date.year,12,31)

    if start_date > datetime.date.today():
      start_date = datetime.date.today()

    if end_date > datetime.date.today():
      end_date = datetime.date.today()

    return pd.date_range(start_date, end_date, freq='B')


def parse_arguments():
    """Parse the commandline arguments"""
    parser = argparse.ArgumentParser(
        add_help=True,
        usage='%(prog)s [OPTIONS]',
        formatter_class=argparse.RawTextHelpFormatter,
        description="Fill in daily work in Absence.io. It is always filling the whole week before as it is running or it has been specified \n\n \
        - Days of the week can be excluded by means of:\n \
            - Argument -e. This option has preference over the data.yml file. \n \
            - data.yml file \n\n \
        - Use the data.yml to customize your inputs \n \
              id: id from abscense.io \n \
              key: key from absence.io \n \
              starthour: Hour string to fill in as your start hour. Format: 'XX:YY' \n \
              endhour: Hour string to fill in as your end hour. Format: 'XX:YY' \n \
              typeofwork: Type of daily register. Allowed value: work \n \
              skipdays: List of the days to be excluded. Format: [Monday,Wednesday] \n \
        ")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--day',
        '-d',
        dest='day',
        help='Specify a date to fill the previous week of this day with this format: YYYY-MM-dd',
        type=str)
    group.add_argument(
        '--week',
        '-w',
        dest='week',
        action="store_true",
        help='Used to fill in the whole previous week. Use to be croned in your computer')
    group.add_argument(
        '--year',
        '-y',
        dest='year',
        help='Used to fill in the year, starting from day with this format: YYYY-MM-dd. Use with caution',
        type=str)
    parser.add_argument(
      "--exclusion",
      "-e",
      dest='exclusion',
      help='Specify the days of the week that should not be filled \n \
           Example: absence.py -w -e "Monday Friday"',
      default="file")
    return parser.parse_args()

def Convert(string):
  excludedDays = list(string.split(" "))
  return excludedDays

def main():
  args = parse_arguments()
  data = readdata(DATA_FILE)

  if args.year:
    date_range = year_array(datetime.date(int(args.year[:4]), int(args.year[5:7]), int(args.year[8:])))

  else:
    if args.week:
      today_obj = datetime.date.today()
      date_range = week_array(today_obj)

    else:
      date_range = week_array(datetime.date(int(args.day[:4]), int(args.day[5:7]), int(args.day[8:])))

  excludedDays = Convert(args.exclusion)
  
  if "file" in excludedDays:
    excludedDays = data['skipdays']

  bankHolidays = data['bankholidays']

  for d in date_range:
      if d.strftime('%d.%m.%Y') not in bankHolidays:
        if d.strftime('%A') not in excludedDays:
          sendwork(day="%s" % d.strftime('%Y-%m-%d'),
                 id=data['id'],
                 key=data['key'],
                 typeofwork=data['typeofwork'],
                 starthour=str(data['starthour']),
                 endhour=str(data['endhour']))
      else:
        print(d.strftime('%Y-%m-%d')+": skipped because of bank holiday")

if __name__ == '__main__':
    main()
