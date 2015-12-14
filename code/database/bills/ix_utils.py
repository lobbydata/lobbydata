import sys, os, shutil
import itertools
import string
import datetime
import xml_utils
from .. import general
from path import path
from whoosh.index import create_in, open_dir
from whoosh.qparser import QueryParser, PhrasePlugin
from whoosh.fields import *
import whoosh.query
from database.bills.models import Bill

if general.TEST_MODE:
    SUMMARY_INDEX_DIR = general.TESTS_DIR / 'test_summary_index'
else:
    SUMMARY_INDEX_DIR = general.DATA_DIR / 'database' / 'summary_index'

def get_summary_index():
    return open_dir(SUMMARY_INDEX_DIR)

def create_summary_index():
    schema = Schema(id=ID(stored=True), summary=TEXT)
    
    if SUMMARY_INDEX_DIR.exists():
        shutil.rmtree(SUMMARY_INDEX_DIR)
    os.mkdir(SUMMARY_INDEX_DIR)

    ix = create_in(SUMMARY_INDEX_DIR, schema)
    writer = ix.writer()

    print "*** Creating index of summary texts"
    for b in Bill.query.yield_per(10):
        writer.add_document(
            id=b.id,
            summary=b.summary
        )
    print ""

    writer.commit()

def summary_search(queries_list, return_objects=False, make_phrase=False):
    queries = [unicode(q).replace("\'", "").replace('\"', '')
               for q in queries_list]

    if make_phrase:
        queries = ["\"" + q + "\"" for q in queries]

    create_summary_index()
    ix = get_summary_index()
    parser = QueryParser("summary", schema=ix.schema)
    parser.add_plugin(PhrasePlugin())

    with ix.searcher() as searcher:
        parsed_queries = [parser.parse(q) for q in queries]
        total_query = whoosh.query.Or(parsed_queries)

        results = searcher.search(total_query, limit=None)
        if return_objects:
            return [Bill.query.get(b['id']) for b in results]
        else:
            return [b['id'] for b in results]
