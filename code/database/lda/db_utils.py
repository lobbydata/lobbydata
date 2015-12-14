import string
import re, os, csv
import numpy as np
from nltk.tokenize import PunktWordTokenizer
from nltk.corpus import stopwords

from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

import json
import hashlib
#from ../.. import f

import xml_utils, ix_utils
from models import *
from database.bills.models import Bill
from .. import general
from collections import defaultdict
from database.matching.new_match_names import *
from database.matching.base_list_scorer import get_scorer

RESULTS_DIR = general.DATA_DIR / 'database' / ''



def get_or_create_model(model, data, primary_key):
    try:
        obj = model.query.get(data[primary_key])
        if obj is None: obj = model(**data)
    except Exception as e: obj = model(**data)
    return obj

def make_get_or_create(model, primary_key):
    def f(data):
        return get_or_create_model(model, data, primary_key)
    return f

get_or_create_lobbyist = make_get_or_create(Lobbyist, 'name')
get_or_create_gov_entity = make_get_or_create(GovernmentEntity, 'name')
get_or_create_registrant = make_get_or_create(LobbyingRegistrant, 'name')
get_or_create_client = make_get_or_create(LobbyingClient, 'name')
get_or_create_affiliated_org = make_get_or_create(AffiliatedOrg, 'name')

bill_regex = r'((HR|((H|S)(((CON|C)|J)?RES)?))[0-9]{1,5})'
multi_bill_regex = r'((HR|((H|S)(((CON|C)|J)?RES)?))[0-9]{1,5})'
tkzr = PunktWordTokenizer()
valid_tokens = [
    # u'H', # Do not include to avoid Congressional hearing conflict
    u'HR',
    u'S',
    u'CON',
    u'RES',
    # u'C',
    # u'J',
    u'CONRES',
    u'CRES',
    u'JRES',
    u'HCONRES',
    u'HCRES',
    u'HJRES',
    u'SCONRES',
    u'SCRES',
    u'SJRES'
]

def bill_search_tokenize(s):
    # Preliminary tokenization of text
    tokens = tkzr.tokenize(s) 
    
    # Split on '/' character
    tokens = [
        t
        for token in tokens
        for t in token.split('/')
    ]

    tokens = [
        token
        for token in tokens
        if len(token) > 0
    ]

    # Remove tokens starting with apostrophe
    tokens = [
        token
        for token in tokens
        if token[0] != "'"
    ]

    # Remove punctuation from all tokens except dashes, and capitalize
    remove_punctuation_map = dict(
        (ord(char), None) for char in string.punctuation if char != '-'
    )
    tokens = [
        unicode(t).translate(remove_punctuation_map).upper() for t in tokens
    ]

    def split_dash(s):
        return re.split('(-)', s)
    
    # Split tokens on dashes, keeping the dashes
    tokens = [
        t for token in tokens for t in split_dash(token)
    ]

    def split_number(s):
        match = re.search(r'\d+$', s)
        if match is None:
            return [s]
        else:
            nums = match.group()
            return [s[:-len(nums)], nums]

    # Split tokens ending in numbers
    tokens = [
        t for token in tokens for t in split_number(token)
    ]

    # Remove blank tokens
    tokens = [t for t in tokens if len(t) > 0]

    return tokens

def find_lone_bills(tokens):
    d = {
        (i, i+1) : [t1 + t2]
        for i, (t1, t2, t3) in enumerate(zip(tokens, tokens[1:], tokens[2:]))
        if t1 in valid_tokens and t2.isdigit() and t3 != '-' and t3.upper() != 'TO'
    }

    # Handle match at end of string
    if len(tokens) > 2:
        t1 = tokens[-2]
        t2 = tokens[-1]
        if t1 in valid_tokens and t2.isdigit():
            d[(len(tokens) - 2, len(tokens) - 1)] = [t1 + t2]
            
    return d

def find_num_range_bills(tokens):
    zipped_list = zip(tokens, tokens[1:], tokens[2:], tokens[3:], tokens[4:], tokens[5:])

    # TODO: possible match at end of string where last 4 tokens form a range?
    return {
        (i, i+3) : [t1 + str(j) for j in range(int(t2), int(t4) + 1)]
        for i, (t1, t2, t3, t4, t5, t6) in enumerate(zipped_list)
        if t1 in valid_tokens and t2.isdigit() and t3 == '-' and \
        t4.isdigit() and not (t5 == '-' and t6.isdigit()) and \
        int(t2) < int(t4) and int(t4) - int(t2) <= 20 # Range is proper and not too small
    }

def find_text_range_bills(tokens):
    zipped_list = zip(tokens, tokens[1:], tokens[2:], tokens[3:], tokens[4:], tokens[5:])

    def tokens_test(t1, t2, t3, t4, t5, t6):
        has_linkers = (t1 == 'FROM') and (t4 == 'TO')
        first_is_bill = (t2 in valid_tokens and t3.isdigit())
        second_is_bill = (t5 in valid_tokens and t6.isdigit())
        same_type = (t2 == t5)

        return has_linkers and first_is_bill and second_is_bill and same_type

    return {
        (i, i+5) : [t2 + str(j) for j in range(int(t3), int(t6) + 1)]
        for i, (t1, t2, t3, t4, t5, t6) in enumerate(zipped_list)
        if tokens_test(t1, t2, t3, t4, t5, t6)
    }

def find_bills(tokens):
    d = {}
    
    d.update(find_lone_bills(tokens))
    d.update(find_num_range_bills(tokens))
    d.update(find_text_range_bills(tokens))

    # Get the bill ranges, sorted by first position
    bill_ranges = sorted(d.keys(), key=lambda t: t[0])

    if len(bill_ranges) == 0:
        return {}

    text_sections = [
        tokens[t1[1] + 1:t2[0]]
        for t1, t2 in zip(bill_ranges, bill_ranges[1:])
    ]

    # Fill out text sections list at the ends if necessary
    first_bill_start = bill_ranges[0][0]
    last_bill_end = bill_ranges[-1][1]
    num_tokens = len(tokens)

    if first_bill_start > 0:
        text_sections.insert(0, tokens[0:first_bill_start])
    else:
        text_sections.insert(0, [])
        
    if last_bill_end < num_tokens - 1:
        text_sections.append(tokens[last_bill_end+1:num_tokens])
    else:
        text_sections.append([])

    # To each bill, associate the text tokens from either side of it (if a bill is
    # repeated, it will get all of the associated texts).
    bill_texts_dict = defaultdict(list)
    for i, b in enumerate(bill_ranges):
        bills = d[b]
        for bill in bills:
            bill_texts_dict[bill] += text_sections[i] + text_sections[i+1]

    ret = {
        k: " ".join(v)
        for k, v in bill_texts_dict.items()
    }

    return ret

def find_top_match_index(texts, context):
    tfidf_vectorizer = TfidfVectorizer(stop_words = stopwords.words('english'), min_df=1)
    # Hack to avoid empty vocabulary -- is this bad?
    tfidf_matrix_train = tfidf_vectorizer.fit_transform(['aaaaaa', context] + texts)
    
    c = cosine_similarity(tfidf_matrix_train[0:1], tfidf_matrix_train[1:])[0]

    return np.argmax(c)

def find_top_match_bill(bill_number, context, start_congress, report, changes, n=3):
    """
    Returns the bill having the given bill number, among those in the n congresses
    preceding start_congress, that has the highest textual similarity (in its CRS
    summary) to the context text.
    """
    candidate_congresses = [start_congress - i for i in range(n)]

    # print "--", bill_number, "--", context, "--", start_congress
    
    candidate_bills = [b for b in [
        Bill.query.get(str(c) + '_' + bill_number) for c in candidate_congresses
        ] if b is not None]

    # check for mininputted numbers
    prefix = bill_number.rstrip('0123456789')
    given = int(bill_number[len(prefix):])
    possibles = [prefix+str(given+1), prefix+str(abs(given-1)),
        prefix+str(given+10), prefix+str(abs(given-10)),
        prefix+str(given+100), prefix+str(abs(given-100))]

    """possibles = [prefix+str(given+1), prefix+str(given-1), 
        prefix+str(given+10), prefix+str(given-10), 
        prefix+str(given+100), prefix+str(given-100)]"""

    number_misinputs = [b for b in [
        Bill.query.get(str(start_congress) + '_' + p) for p in possibles
        ] if b is not None]

    all_candidate_bills = candidate_bills + number_misinputs

    bill_texts = [b.summary for b in all_candidate_bills]

    if len(candidate_bills) == 0:
        return None

    i = find_top_match_index(bill_texts, context)


    if i is not 0:
        report_year = ""
        if report.year:
            report_year = report.year

        report_client = ""
        if report.client:
            report_client = report.client.name

        report_type = ""
        if report.type:
            report_type = report.type

        change = [candidate_bills[0].get_session_type_number(), str(report_year), report_client, report_type, candidate_bills[i].get_session_type_number()]
        changes.append(change)


    return candidate_bills[i]

def find_range_bill_numbers(s):
    tokens = bill_search_tokenize(s)

    num_range_bills = find_num_range_bills(tokens)
    text_range_bills = find_text_range_bills(tokens)

    return (num_range_bills, text_range_bills)

def get_or_create_issue(i, report):
    i_args = i.copy()
    i_args.pop('specific_issue', None)
    i_obj = get_or_create_model(LobbyingIssue, i_args, 'code')
    if i['specific_issue'] is not None:
        LobbyingSpecificIssue(
            text = i['specific_issue'],
            issue = i_obj,
            report = report,
            bills_by_number = [],
            bills_by_title = []
        )

    return i_obj

def add_specific_issue_bills_by_title():
    general.init_db()

    lower = 0
    upper = 200000

    print "*** Identifying specific issues by bill title"
    for i, b in enumerate(Bill.query.yield_per(10)):
        if i >= upper:
            break
        if i >= lower:
            print "    Bill", "#" + str(i)
            specific_issues = ix_utils.get_bill_specific_issues_by_titles(b)
            b.specific_issues_by_title = specific_issues

    general.close_db(write=True)
    
def log_specific_issue_bill_ranges():
    general.init_db()

    filename = (general.OUTPUT_DIR / 'LOG_bill_ranges.txt').abspath()
    if os.path.exists(filename):
        os.remove(filename)
    f = open(filename, 'w+')
    writer = csv.writer(f, delimiter="\t")
    writer.writerow(["specific_issue_id", "report_id", "numerical_range_bills", "textual_range_bills", "specific_issue_text"])

    print "*** Identifying specific issues by bill number"
    for i, s in enumerate(LobbyingSpecificIssue.query.yield_per(10)):
        print "    Specific Issue", "#" + str(i)
        num_range_bills, text_range_bills = find_range_bill_numbers(s.text)
        if len(num_range_bills) > 0 or len(text_range_bills) > 0:
            writer.writerow(
                [str(s.id), str(s.report.id), ",".join(num_range_bills), ",".join(text_range_bills), general.clean_string(s.text.encode('utf8'))]
            )
    print ""

    f.close()

    general.close_db(write=False)

def add_client_unique_names():
    general.init_db()

    random.seed(10)
    prefix = get_prefix('list_scorer')
    scorer = get_scorer('list_scorer')

    libs = {}
    for lib_name, config_entries in LIBS_CONFIG.iteritems():
        libs[lib_name] = LibSet(config_entries, do_parts=True)

    # Load subsidiary data: this part superseded by Orbis GUO data
    # subdata = LibSet(SUBDATA_CONFIG, do_parts=True)
    # Load GUO data as a dictionary
    GUOdfile = csv.reader(open(os.path.join(general.DATA_DIR, 'orbis/GUOdata.csv')))
    GUOdata, skip = {}, GUOdfile.next()
    for line in GUOdfile: GUOdata[line[2]] = (line[3],line[4])
    
    matcher = MatcherCtx(scorer, libs, prefix)
    for i, c in enumerate(LobbyingClient.query.yield_per(10)):
        print "    Specific Issue", "#" + str(i)
        name = c.name
        print "Matching LDA client  ", name
        

        attempt =  matcher.match(name, 'tradeassoc')[0]
        if attempt: 
            print "in tradeassoc, matched ", attempt
            c.is_tradeassoc = True
        else: 
            print ' no matches in tradeassoc'

            attempt = matcher.match(name,'compustat')
            attempt_tuple = attempt[0]
            attempt_match = attempt[1]
            if attempt_tuple:
                print "in compustat, matched  ", attempt_tuple
                c.compustat_score = int(attempt_tuple[1])
                c.compustat_key = str(attempt_tuple[0])
                c.compustat_name = str(attempt_match)
            else: print 'no matches in compustat'

            attempt = matcher.match(name,'orbis')
            attempt_tuple = attempt[0]
            attempt_match = attempt[1]
            if attempt_tuple:
                print "in orbis, matched  ", attempt_tuple
                c.orbis_score = int(attempt_tuple[1])
                c.orbis_key = str(attempt_tuple[0])
                c.orbis_name = str(attempt_match)
                link_to_GUO_patch(c, GUOdata)
            else: print 'no matches in orbis'

            attempt = matcher.match(name,'osiris')
            attempt_tuple = attempt[0]
            attempt_match = attempt[1]
            if attempt_tuple:
                print "in osiris, matched  ", attempt_tuple
                c.osiris_score = int(attempt_tuple[1])
                c.osiris_key = str(attempt_tuple[0])
                c.osiris_name = str(attempt_match)
            else: 
                print 'no matches in osiris'

# unsuccessful match, have user verify
# this part temporarily deactivated
#        elif attempt_match:
#            choice_string = "Please choose the right match, or \'0\' for no match:\n"
#
#            i = 1
#            for match in attempt_match:
#                choice_string += " " + match + "\n"
#
#            choice = raw_input(choice_string)
#
#            try:
#                choice = int(choice)
#                if choice != 0:
#                    try:
#                        chosen_tuple = attempt_match[choice-1]
#                        if chosen_tuple[0] == 'compustat':
#                            c.compustat_score = int(chosen_tuple[3])
#                            c.compustat_key = str(chosen_tuple[1])
#                            c.compustat_name = str(chosen_tuple[2])
#                        elif chosen_tuple[0] == 'osiris':
#                            c.osiris_score = int(chosen_tuple[3])
#                            c.osiris_key = str(chosen_tuple[1])
#                            c.osiris_name = str(chosen_tuple[2])
#                    except:
#                        print "chosen index out of bounds...\n"
#            except:
#                print "invalid input\n"
        
    general.close_db(write=True)

def add_bvdid():
    general.init_db()
    # also adds ISIN / gvKey (where available)

    # Load Amatches.csv
    Amatches_data = csv.reader(open(os.path.join(general.DATA_DIR, 'compustat', 'Amatch_gvkeys.csv')))
    toInsert_bvdid, skip = {}, Amatches_data.next()
    toInsert_isin, toInsert_gvKey = {}, {}
    for line in Amatches_data: 
        toInsert_bvdid[line[0]] = line[2]
        if line[4] not in ["Unlisted", "", "NA", None]: toInsert_isin[line[0]] = line[4]
        if line[6] not in ["NA", "", None]: toInsert_gvKey[line[0]] = line[6]
    # Insert bvdids into database
    for i, c in enumerate(LobbyingClient.query.yield_per(10)):
        print "    Specific Issue", "#" + str(i)
        name = c.name
        print "for LDA client  ", name
    
        if name in toInsert_bvdid.keys(): c.bvdid = toInsert_bvdid[name]
        if name in toInsert_isin.keys(): c.isin = toInsert_isin[name]
        if name in toInsert_gvKey.keys(): c.gvkey = toInsert_gvKey[name]
    general.close_db(write=True)


def add_bvdid_gvkey():
    general.init_db()
    # also adds ISIN / gvKey (where available)

    # Load Amatches.csv
    Amatches_data = csv.reader(open(os.path.join(general.DATA_DIR, 'newclients', 'LobbyingClient_data.csv')))
    toInsert_bvdid, skip = {}, Amatches_data.next()
    toInsert_isin, toInsert_gvKey = {}, {}
    toInsert_ticker, toInsert_guo_bvdid = {}, {}
    toInsert_naics = {}

    for line in Amatches_data:
        toInsert_bvdid[line[0]] = line[1]
        if line[2] not in ["NA", "", None]: toInsert_gvKey[line[0]] = line[2]
        if line[3] not in ["NA", "", None]: toInsert_guo_bvdid[line[0]] = line[3]
        if line[4] not in ["NA", "", None]: toInsert_ticker[line[0]] = line[4]
        if line[5] not in ["Unlisted", "", "NA", None]: toInsert_isin[line[0]] = line[5]
        if line[6] not in ["NA", "", None]: toInsert_naics[line[0]] = line[6]
    # Insert bvdids into database
    for i, c in enumerate(LobbyingClient.query.yield_per(10)):
        name = c.name
        print "for LDA client  ", name

        if name in toInsert_bvdid.keys(): c.bvdid = toInsert_bvdid[name]
        if name in toInsert_gvKey.keys(): c.gvkey = toInsert_gvKey[name]; print toInsert_gvKey[name]
        if name in toInsert_guo_bvdid.keys(): c.guo_bvdid = toInsert_guo_bvdid[name]
        if name in toInsert_ticker.keys(): c.ticker = toInsert_ticker[name]
        if name in toInsert_isin.keys(): c.isin = toInsert_isin[name]
        if name in toInsert_naics.keys(): c.naics = toInsert_naics[name]
    general.close_db(write=True)

# def add_findata():
    # general.init_db()

    #Load Amatches.csv
    # costat_data = csv.reader(open(os.path.join(general.DATA_DIR, 'compustat', 'compustat_all_cleaned.csv')))
    # osiris_data = csv.reader(open(os.path.join(general.DATA_DIR, 'osiris', 'osiris.csv')))
    
    # for i, c in enumerate(LobbyingClient.query.yield_per(10)):
        # print "    Specific Issue", "#" + str(i)
        # name = c.name
        # print "for LDA client  ", name
        # if c.bvdid is not None: 
#            bah humbug.
    # general.close_db(write=True)

    
def link_to_GUO_patch(client, GUOdata):
    # Helper function to replace add GUO info to orbis matches
    # Should only be called from within add_client_unique_names
    
    try:
        GUOtuple = GUOdata[client.orbis_key]
        client.orbis_GUO_key = GUOtuple[0]
        client.orbis_GUO_name = GUOtuple[1]
        print "Linked to GUO"
    except KeyError:
        print "No GUO data found"
    
def add_specific_issue_bills_by_number():
    general.init_db()


    changes = []

    print "*** Identifying specific issues by bill number"
    for i, s in enumerate(LobbyingSpecificIssue.query.yield_per(10)):
        # print "    Specific Issue", "#" + str(i)

        title_bills = s.bills_by_title
        title_bill_numbers = [b.get_number() for b in title_bills]
        
        year = int(s.report.year)
        session = (year - 1)/2 - 893

        tokens = bill_search_tokenize(s.text)
        bill_contexts_dict = find_bills(tokens)


        unfiltered_bills = [
            find_top_match_bill(bill_number, context, session, s.report, changes)
            for bill_number, context in bill_contexts_dict.items()
            if not bill_number in title_bill_numbers
        ]

        final_bills = list(set([b for b in unfiltered_bills if b is not None]))

        for b in unfiltered_bills:
            if b is not None:
                if b.session != session:
                    naive_bill = Bill.query.get(str(session) + '_' + b.get_number())

                    if naive_bill is not None:
                        print "NAIVE CANDIDATE BILL     ", naive_bill.id + ": " + naive_bill.titles[0].text
                    else:
                        print "NAIVE CANDIDATE BILL     ", "Session", str(session), "; Not in database"
                    
                    print "REPLACEMENT BILL         ", b.id + ": " + b.titles[0].text
                    print "CLIENT                   ", s.report.client.name
                                    
                    print "SPECIFIC ISSUE TEXT"
                    print s.text
                    print "\n---------\n"

        s.bills_by_number = final_bills
    print ""

    changes_file = RESULTS_DIR / "bill_number_changes.txt"
    with open(changes_file, "w+") as ch_file:
        ch_file.write("original_bill_number\treport_year\treport_client\treport_type\tnew_bill_number\n")

        for change in changes:
            ch_file.write(change[0]+"\t"+change[1]+"\t"+change[2]+"\t"+change[3]+"\t"+change[4]+"\n")

    general.close_db(write=True)

def add_specific_issue_bills():
    add_specific_issue_bills_by_title()
    add_specific_issue_bills_by_number()

def get_or_create_foreign_entity(f, report):
    f_args = f.copy()
    f_args.pop('contribution', None)
    f_args.pop('ownership', None)
    f_obj = get_or_create_model(ForeignEntity, f_args, 'name')
    ForeignEntityRelationship(
        foreign_entity = f_obj,
        lobbying_report = report,
        contribution = f['contribution'],
        ownership = f['ownership']
    )

    return f_obj

def create_report(f):
    report = LobbyingReport(
        id = f['id'],
        year = f['year'],
        received = f['received'],
        amount = f['amount'],
        type = f['type'],
        period = f['period'],
        xml_file = f['xml_file'],
        client = get_or_create_client(f['client']),
        client_state = f['client_state'],
        client_ppb_state = f['client_ppb_state'],
        client_ppb_country = f['client_ppb_country'],
        self_filer = f['self_filer'],
        registrant = get_or_create_registrant(f['registrant']),
        lobbyists = list(set([
                    get_or_create_lobbyist(l) for l in f['lobbyists']
        ])),
        affiliated_orgs = list(set([
                    get_or_create_affiliated_org(a) for a in f['affiliated_orgs']
        ])),
        gov_entities = list(set([
                    get_or_create_gov_entity(g) for g in f['gov_entities']
        ]))
    )

    report.issues = list(set([
                get_or_create_issue(i, report) for i in f['issues']
    ]))

    report.foreign_entities = list(set([
                get_or_create_foreign_entity(entity, report)
                for entity in f['foreign_entities']
    ]))

    return report

# def write_file_to_db(filename):
#     general.init_db()

#     filings = xml_utils.parse_file(filename)
#     for f in filings:
#         create_report(f)

#     general.close_db(write=True)


def date_handler(obj):
    return obj.isoformat() if hasattr(obj, 'isoformat') else obj


_GLOBAL_SEEN_FILING_IDS_SET = set()


def to_hash(obj):
    input_str = str(obj['id'])
    h = hashlib.md5()
    h.update(input_str)
    return h.digest()


# ideally we would want to reorganize a little bit so that this global
# object is instead managed by whatever function is calling
# write_file_to_db

def write_file_to_db(filename):
    general.init_db()
    filings = xml_utils.parse_file(filename)

    for f in filings:
        f_hash = to_hash(f)

        if f_hash not in _GLOBAL_SEEN_FILING_IDS_SET:
            create_report(f)
            _GLOBAL_SEEN_FILING_IDS_SET.add(f_hash)

    general.close_db(write=True)


# def write_file_to_db(filename):
#     general.init_db()

#     filings = xml_utils.parse_file(filename)
#     seen_filing_hashes = set()
#     for f in filings:
#         f_hash_str = to_hash(f)

#         if f_hash_str not in seen_filing_hashes:
#             create_report(f)
#             seen_filing_hashes.add(f_hash_str)

#     general.close_db(write=True)


def clear_lda_db():
    general.init_db()

    # Drop secondary tables of reports
    for prop in ["lobbyists", "issues", "gov_entities", "affiliated_orgs",
                 "foreign_entities"]:
        table = LobbyingReport.mapper.get_property(prop).secondary
        table.drop(metadata.bind)

    # Clear primary data
    Lobbyist.query.delete()
    LobbyingSpecificIssue.query.delete()
    LobbyingIssue.query.delete()
    LobbyingClient.query.delete()
    LobbyingRegistrant.query.delete()
    GovernmentEntity.query.delete()
    ForeignEntityRelationship.query.delete()
    ForeignEntity.query.delete()
    AffiliatedOrg.query.delete()
    LobbyingReport.query.delete()
    
    general.close_db(write=True)
