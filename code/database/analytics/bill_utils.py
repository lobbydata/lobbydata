from elixir import *
from database.bills.models import *
from database.tariffs.models import *
from sqlalchemy.sql import or_, and_
import database.general, database.bills.ix_utils, database.bills.db_utils
import re

def get_lobbied_info(terms):
    pass   
     

def bill_is_lobbied(b, use_number=True, use_title=True,
                    issue_codes=None):
    # Get object if necessary
    if isinstance(b, basestring):
        b = Bill.query.get(b)

    issues = set()
    if use_number:
        issues = issues | set(b.specific_issues_by_number)
    if use_title:
        issues = issues | set(b.specific_issues_by_title)

    if issue_codes is not None:
        issues = [i for i in issues if i.issue.code in issue_codes]

    return (len(issues) > 0)

def bill_number_of_reports(b):
    if isinstance(b, basestring):
        b = Bill.query.get(b)

    reports_by_title = [s.report for s in b.specific_issues_by_title]
    reports_by_number = [s.report for s in b.specific_issues_by_number]

    return len(set(reports_by_number) | set(reports_by_title))

def bill_unique_clients(b):
    if isinstance(b, basestring):
        b = Bill.query.get(b)

    reports_by_title = [s.report for s in b.specific_issues_by_title]
    reports_by_number = [s.report for s in b.specific_issues_by_number]
    all_reports = list(set(reports_by_number) | set(reports_by_title))

    def reduced_name(client):
        if client.compustat_name is not None:
            return client.compustat_name
        else:
            return client.name

    return list(set([r.client for r in all_reports]))

def bill_clients(b):
    if isinstance(b, basestring):
        b = Bill.query.get(b)

    reports_by_title = [s.report for s in b.specific_issues_by_title]
    reports_by_number = [s.report for s in b.specific_issues_by_number]
    all_reports = list(set(reports_by_number) | set(reports_by_title))

    return list(set([r.client for r in all_reports]))

def bill_summary_search(queries):
    database.general.init_db()
    return database.bills.ix_utils.summary_search(
        queries,
        make_phrase=True,
        return_objects=True
    )

def bill_terms_any(terms):
    database.general.init_db()
    return Bill.query.filter(
        Bill.terms.any(Term.name.in_(terms))
    ).all()

def bill_terms_all(terms):
    database.general.init_db()
    q = Bill.query
    for t in terms:
        q = q.filter(Bill.terms.any(Term.name == t))

    return q.all()

def bill_top_term_any(terms):
    database.general.init_db()
    return Bill.query.filter(
        Bill.top_term.has(Term.name.in_(terms))
    ).all()

def bill_top_terms_any(terms):
    database.general.init_db()
    return Bill.query.filter(
        Bill.top_terms.any(Term.name.in_(terms))
    ).all()

def bill_sets_union(set_list):
    return list(set.union(*[set(s) for s in set_list]))

def bill_sets_intersect(set_list):
    return list(set.intersection(*[set(s) for s in set_list]))

def bill_set_ids(bill_set):
    return [b.id for b in bill_set]
    
def bill_set_compustat_keys(bill_set):
    return [b.compustat_key for b in bill_set]

def bill_set_osiris_keys(bill_set):
    return [b.osiris_key for b in bill_set]

# converts all whitespace with regex to single space
def clean_whitespace(s):
    return re.sub('\s+', ' ', s)

def strip_commas(s):
    return re.sub(',', ' ', s)


def reduced_name(client):
    if client.compustat_name is not None:
        return client.compustat_name
    else:
        return client.name

def output_lobbied_trade_bills(bills, out_file):
    lobbied = 0
    with open(out_file, "w+") as results:
        results.write("bill\tis_lobbied\tcompustat_keys\tosiris_keys\tbill_title\tbill_summary\n")
        for bill in bills:
            row = bill.get_session_type_number() + "\t"
            print row

            if bill_is_lobbied(bill):
                row += "1\t"
                lobbied += 1

                clients = bill_unique_clients(bill)
                
                compustat_keys = ""
                try:
                    compustat_keys = ','.join([client.compustat_key for client in clients])
                except:
                    pass
                row = row + compustat_keys + "\t"

                osiris_keys = ""
                try:
                    osiris_keys = ','.join([client.osiris_key for client in clients])
                except:
                    pass
                row = row + osiris_keys + "\t"

            else:
                # try misc tariff bill info                                                                    
                misc = TariffReport.query.filter_by(session=bill.session). \
                       filter_by(bill_type=bill.type).filter_by(bill_number=bill.number).first()

                if misc is not None:
                    lobbied += 1
                    print "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
                    row = row + "1\t"

                    if misc.interested_entity.compustat_key:
                        row = row + misc.interested_entity.compustat_key + "\t"
                    else:
                        row = row + "\t"

                    if misc.interested_entity.osiris_key:
                        row = row + misc.interested_entity.osiris_key + "\t"
                    else:
                        row = row + "\t"
                
                else:
                    row = row + "0\t" + "\t" + "\t"

            # append bill title and summary
            row = row + clean_whitespace(bill.titles[0].text) + "\t" + clean_whitespace(bill.summary) + "\n"

            results.write(row.encode('utf-8'))

    print "Number of trade bills: " + str(len(bills))
    print "Number lobbied: " + str(lobbied)
    print "Percent of trade bills lobbied: " + str(float(lobbied)/float(len(bills)))
