import sys, os
from bs4 import BeautifulSoup
import itertools
import string
import datetime
from .. import general
from collections import Counter
import urllib2
from urllib2 import Request
from StringIO import StringIO
import re
BILLS_DIR = general.DATA_DIR / 'bills'

# Dictionary converting govtracker.us bill types to the appropriate prefixes.
BILL_TYPE_TO_PREFIX = {
    'h' : 'HR',
    'hr' : 'HRES',
    'hj' : 'HJRES',
    'hc' : 'HCONRES',
    's' : 'S',
    'sr' : 'SRES',
    'sj' : 'SJRES',
    'sc' : 'SCONRES'
    }

# Returns the id of a parsed XML bill, formatted to match the way that the
# ids are formatted in the bills_classify.csv file.
def id_of_xml_bill(bill):
    prefix = bill['type']
    if prefix in BILL_TYPE_TO_PREFIX:
        prefix = BILL_TYPE_TO_PREFIX[prefix]
    else:
        # If the type is not found in the dictionary (which should not happen),
        # we just capitalize it and proceed.
        prefix = prefix.upper()
    return bill['session'] + '_' + prefix + bill['number']

def parse_title(tag):
    ret = {}

    if 'type' not in tag:
        ret['type'] = None
    else:
        ret['type'] = tag['type']

    if 'as' not in tag:
        ret['as_field'] = None
    else:
        ret['as_field'] = tag['as']

    ret['text'] = unicode(tag.string)

    return ret

def parse_person(tag):
    ret = {
        'id': int(tag['id']),
        'firstname': unicode(tag['firstname']),
        'lastname': unicode(tag['lastname']),
        'gender': unicode(tag.get('gender', '')),
        'religion': unicode(tag.get('religion', ''))
    }

    if tag.get('birthday', None) is not None:
        ret['birthday'] = datetime.datetime.strptime(
            tag['birthday'], '%Y-%m-%d'
        )
    else:
        ret['birthday'] = None

    roles = tag.find_all('role')
    if len(roles) > 0:
        ret['title'] = roles[0].get('type', '')
        ret['state'] = roles[0].get('state', '')
        ret['party'] = roles[0].get('party', '')
        ret['district'] = int(roles[0].get('district', '0'))
    else:
        ret['party'] = ''
        ret['title'] = unicode(tag.get(['title'], ''))
        ret['district'] = int(tag.get('district', '0')),
        ret['state'] = unicode(tag.get('state', '')),

    return ret

def xml_people_of_file(filename):
    with open(filename) as f:
        soup = BeautifulSoup(f.read())
        return soup.people.find_all('person')

# Parses an XML file containing a bill using BeautifulSoup, returning a
# dictionary of the data that we will use.
def bill_of_file(filename):
    with open(filename) as f:
        soup = BeautifulSoup(f.read())
        bill = soup.bill
        
        title_tags = bill.titles.find_all('title')

        b = {
            'id' : unicode(id_of_xml_bill(bill)),
            'number' : bill['number'],
            'session' : bill['session'],
            'type' : BILL_TYPE_TO_PREFIX[bill['type']],
            'titles' : [parse_title(t) for t in title_tags],
            'introduced' : datetime.datetime.strptime(
                bill.introduced['datetime'].split('T')[0],
                '%Y-%m-%d'
            ),
            'terms' : list(set([
                        unicode(t['name'])
                        for t in bill.subjects.find_all('term')])),
            'committees' : list(set([
                        unicode(c['name'])
                        for c in bill.committees.find_all('committee')])),
            'subcommittees' : list(set([
                        c.get('subcommittee')
                        for c in bill.committees.find_all('committee')
                    if c.get('subcommittee')])),
            'related' : list(set([
                        unicode(id_of_xml_bill(b))
                        for b in bill.relatedbills.find_all('bill')
                    ]))
            }

        if bill.summary is not None:
            b['summary'] = unicode(bill.summary.string)
        else:
            b['summary'] = u''

        return b

def clean_text(string):
    ''' Returns the string without non ASCII characters and without \n or \r or \t'''
    stripped = []

    for c in string:
        if 0 < ord(c) < 127 and c != "\r" and c != "\t" and c != "\n":
            stripped.append(c)

    z =  ''.join(stripped).strip()
    return re.sub(r'\s+', ' ',z)

def get_bill_text(session, t, number): 
        poss = ["eh", "rds", "ih", "enr", "is", "ats", "es"]
        bill_text = ""
        for x in poss:
                try:
                        url = "https://www.govtrack.us/data/congress/" + str(session) + "/bills/" + str(t) + "/" + str(t) + str(number) + "/text-versions/" + x + "/document.txt"
                        bill_text = urllib2.urlopen(Request(url)).read()
                        if bill_text != "":
                                break
                except:
                        pass
	cleanbilltext = clean_text(bill_text)
	#print cleanbilltext
        return cleanbilltext

def people_file_of_session(session):
    return BILLS_DIR / 'xml' / str(session) / 'people.xml'

def files_of_session(session):
    base_path = BILLS_DIR / 'xml' / str(session) / 'bills'
    return base_path.files('*.xml')

# Gets the list of all parsed bills for a given session.
def bills_of_session(session):
    base_path = BILLS_DIR / 'xml' / str(session) / 'bills'
    xml_files = base_path.files('*.xml')
    return [bill_of_file(f) for f in xml_files]

#print get_bill_text(113, "sconres", 14)
