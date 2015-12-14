import sys, os, shutil
import itertools
import string
from .. import general
from path import path
from whoosh.index import create_in, open_dir
from whoosh.qparser import QueryParser, PhrasePlugin
from whoosh.fields import *
import whoosh.analysis
import whoosh.query
from models import LobbyingSpecificIssue
from database.bills.models import Bill, BillTitle

if general.TEST_MODE:
    DATABASE_DIR = general.TESTS_DIR
else:
    DATABASE_DIR = general.DATA_DIR / 'database'

CASE_SEN_ISSUE_INDEX_DIR = DATABASE_DIR / 'case_sen_specific_issue_index'
CASE_INSEN_ISSUE_INDEX_DIR = DATABASE_DIR / 'case_insen_specific_issue_index'

def get_issue_index(case_sensitive=False):
    if case_sensitive:
        return open_dir(CASE_SEN_ISSUE_INDEX_DIR)
    else:
        return open_dir(CASE_INSEN_ISSUE_INDEX_DIR)

def create_issue_index():
    sen_ana = whoosh.analysis.RegexTokenizer()

    schema1 = Schema(id=ID(stored=True), text=TEXT(analyzer=sen_ana))
    schema2 = Schema(id=ID(stored=True), text=TEXT)

    if CASE_SEN_ISSUE_INDEX_DIR.exists():
        shutil.rmtree(CASE_SEN_ISSUE_INDEX_DIR)
    os.mkdir(CASE_SEN_ISSUE_INDEX_DIR)

    if CASE_INSEN_ISSUE_INDEX_DIR.exists():
        shutil.rmtree(CASE_INSEN_ISSUE_INDEX_DIR)
    os.mkdir(CASE_INSEN_ISSUE_INDEX_DIR)

    sen_ix = create_in(CASE_SEN_ISSUE_INDEX_DIR, schema1)
    sen_writer = sen_ix.writer()

    insen_ix = create_in(CASE_INSEN_ISSUE_INDEX_DIR, schema2)
    insen_writer = insen_ix.writer()

    general.init_db()

    print "*** Creating index of specific issue texts"
    for i, s in enumerate(LobbyingSpecificIssue.query.yield_per(10)):
        print "    ", "SpecificIssue #" + str(i)
        insen_writer.add_document(
            id=unicode(s.id),
            text=unicode(s.text)
        )
        sen_writer.add_document(
            id=unicode(s.id),
            text=unicode(s.text)
        )
    print ""

    general.close_db(write=False)

    sen_writer.commit()
    insen_writer.commit()

def issue_search(queries_list, return_objects=False, make_phrase=False,
                 case_sensitive=False):
    # Remove quotation marks
    queries = [q.replace("'", "").replace('"', '') for q in queries_list]

    if make_phrase:
        queries = ["\"" + q + "\"" for q in queries]

    ix = get_issue_index(case_sensitive=case_sensitive)
    parser = QueryParser("text", schema=ix.schema)
    parser.add_plugin(PhrasePlugin())
    
    with ix.searcher() as searcher:
        parsed_queries = [parser.parse(q) for q in queries]
        q = whoosh.query.Or(parsed_queries)
        results = searcher.search(q, limit=None)
        # print "   -", len(results), "results"
        if return_objects:
            return [LobbyingSpecificIssue.query.get(int(i['id']))
                    for i in results]
        else:
            return [i['id'] for i in results]

def get_bill_specific_issues_by_titles(bill):
    title_texts = [t.text for t in bill.titles]
    specific_issues = issue_search(title_texts,
                                   make_phrase=True,
                                   return_objects=True,
                                   case_sensitive=True)
    return specific_issues
