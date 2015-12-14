import sys, os, errno
import itertools
import string
from collections import Counter
import datetime
from database.lda.ix_utils import issue_search

from models import *
import xml_utils
from .. import general
from bs4 import BeautifulSoup

def db_get_or_create_term(t):
    t_obj = Term.query.filter_by(name=t).first()
    if t_obj is None:
        t_obj = Term(name=t)
    return t_obj

def db_get_or_create_committee(c):
    c_obj = Committee.query.filter_by(name=c).first()
    if c_obj is None:
        c_obj = Committee(name=c)
    return c_obj

def db_create_bill_title(t, parent_bill):
    return BillTitle(
        text=t['text'],
        type=t['type'],
        as_field=t['as_field'],
        bill=parent_bill
    )

def db_get_or_create_person(p):
    p_obj = Person.query.filter_by(id=p['id']).first()
    if p_obj is None:
        return Person(**p)
    else:
        return p_obj

def db_create_bill(b):
    terms = [db_get_or_create_term(t) for t in b['terms']]
    committees = [db_get_or_create_committee(c) for c in b['committees']]

    bill_obj = Bill(
        id = b['id'],
        session = b['session'],
        type = b['type'],
        number = b['number'],
        introduced = b['introduced'],
        summary = b['summary'],
        terms = terms,
        committees = committees,
	billtext = "",
        related = [],
        titles = []
    )
    text = xml_utils.get_bill_text(b['session'], b['type'].lower(), b['number'])
    if text != "":
	print "Bill Text Found: " + str(b['session']) + "_"+ str(b['type']) + str(b['number'])
    bill_obj.billtext = text
    titles = [db_create_bill_title(t, bill_obj) for t in b['titles']]
    bill_obj.titles = titles

    return bill_obj

def write_db():
    general.init_db()
    
    print "*** Writing XML bills to database"
    for session_num in general.CONGRESSES:
        s = str(session_num)
    
        sys.stdout.write('    Writing congress ' +  s +  '...')
        sys.stdout.flush()

        for f in xml_utils.files_of_session(s):
            b = db_create_bill(xml_utils.bill_of_file(f))
    
        print 'done'    
    print ""

    general.close_db(write=True)

def write_db_people():
    general.init_db()

    print "*** Writing XML people to database"
    for session_num in general.CONGRESSES_PEOPLE:
        s = str(session_num)
    
        sys.stdout.write('    Writing congress ' +  s +  '...')
        sys.stdout.flush()

        f = xml_utils.people_file_of_session(s)

        xml_people = xml_utils.xml_people_of_file(f)
        for x in xml_people:
            p = xml_utils.parse_person(x)
            db_get_or_create_person(p)

        print 'done'    
    print ""

    general.close_db(write=True)

def write_db_sponsors():
    general.init_db()
    
    print "*** Writing bill sponsors and cosponsors to database"
    for session_num in general.CONGRESSES:
        s = str(session_num)
    
        sys.stdout.write('    Writing congress ' +  s +  '...')
        sys.stdout.flush()

        for filename in xml_utils.files_of_session(s):
            with open(filename) as f:
                soup = BeautifulSoup(f.read())
                xml_bill = soup.bill

                bill_id = unicode(xml_utils.id_of_xml_bill(xml_bill))
                bill_obj = Bill.query.get(bill_id)

                xml_sponsor = xml_bill.find('sponsor')
                if (xml_sponsor is not None) and (bill_obj is not None):
                    sponsor_id = xml_sponsor.get('id', None)
                    if sponsor_id is not None:
                        sponsor_obj = Person.query.filter_by(
                            id=int(sponsor_id)
                        ).first()
                        bill_obj.sponsor = sponsor_obj

                xml_cosponsors = xml_bill.cosponsors.find_all('cosponsor')
                cosponsor_objs = list(set([
                    Person.query.filter_by(id=x['id']).first()
                    for x in xml_cosponsors
                ]))
                if bill_obj is not None:
                    bill_obj.cosponsors = cosponsor_objs
        print 'done'    
    print ""

    general.close_db(write=True)

def write_db_top_term():
    general.init_db()
    
    print "*** Writing bill top terms to database"
    for session_num in general.CONGRESSES:
        s = str(session_num)
    
        sys.stdout.write('    Writing congress ' +  s +  '...')
        sys.stdout.flush()

        for filename in xml_utils.files_of_session(s):
            with open(filename) as f:
                soup = BeautifulSoup(f.read())
                xml_bill = soup.bill

                bill_id = unicode(xml_utils.id_of_xml_bill(xml_bill))
                bill_obj = Bill.query.get(bill_id)

                xml_top_term = xml_bill.subjects.find('term')
                if (xml_top_term is not None) and (bill_obj is not None):
                    top_term = xml_top_term['name']
                    top_term_obj = Term.query.filter_by(name=top_term) \
                        .first()
                    bill_obj.top_term = top_term_obj
        print 'done'    
    print ""

    general.close_db(write=True)


def write_db_top_terms(max_terms=2):
    general.init_db()
    
    print "*** Writing bill top terms to database"
    for session_num in general.CONGRESSES:
        s = str(session_num)
    
        sys.stdout.write('    Writing congress ' +  s +  '...')
        sys.stdout.flush()

        for filename in xml_utils.files_of_session(s):
            with open(filename) as f:
                soup = BeautifulSoup(f.read())
                xml_bill = soup.bill

                bill_id = unicode(xml_utils.id_of_xml_bill(xml_bill))
                bill_obj = Bill.query.get(bill_id)

                xml_terms = xml_bill.subjects.find_all('term')

                if (bill_obj is not None) and (xml_terms is not None):
                    num_terms = min(len(xml_terms), max_terms)

                    top_terms = []
                    for i in range(num_terms):
                        term_name = xml_terms[i]['name']
                        term_object = Term.query.filter_by(name=term_name).first()
                        if term_object is not None:
                            top_terms.append(term_object)

                    bill_obj.top_terms = top_terms
        print 'done'    
    print ""

    general.close_db(write=True)


def write_db_related_bills():
    general.init_db()

    print "*** Writing related bills relations to database"
    for session_num in general.CONGRESSES:

        s = str(session_num)
    
        sys.stdout.write('    Writing congress ' +  s +  '...')
        sys.stdout.flush()

        for f in xml_utils.files_of_session(s):
            b = xml_utils.bill_of_file(f)
            b_obj = Bill.query.filter_by(id=b['id']).first()
            for r_id in b['related']:
                r_obj = Bill.query.filter_by(id=r_id).first()
                b_obj.related_bills.append(r_obj)
    
        print 'done'
    print ""

    general.close_db(write=True)

def add_specific_issues_by_title():
    general.init_db()

    print "*** Searching for bill titles in specific issues"
    i = 0
    for b in Bill.query.yield_per(10):
        i += 1
        print i, ":", b.title

        spec_issues = issue_search(
            b.title,
            return_objects=True,
            make_phrase=True
        )

        for s in spec_issues:
            if s not in b.specific_issues:
                b.specific_issues.append(s)

    general.close_db(write=True)

def clear_bills_db():
    general.init_db()

    # Drop secondary tables of Bill
    for prop in ["related_bills", "committees", "terms",
                 "specific_issues_by_title", "specific_issues_by_number",
                 "cosponsors"]:
        table = Bill.mapper.get_property(prop).secondary
        table.drop(metadata.bind)
    
    # Clear primary data
    Person.query.delete()
    Bill.query.delete()
    Committee.query.delete()
    Term.query.delete()
    BillTitle.query.delete()
    
    general.close_db(write=True)

def expand_query_by_related_bills(q):
    related_query = Bill.query.join(
        q.subquery(),
        Bill.related_bills
    )

    return q.union(related_query)
