import sys, os, shutil
from .. import general
import db_utils
import ix_utils

BILLS_XML_DIR = general.DATA_DIR / 'bills' / 'xml'

def get_xml_people():
    print "*** Downloading XML people"
    for session in general.CONGRESSES_PEOPLE:
        s = str(session)

        sys.stdout.write('    Downloading congress ' + s + '...')
        sys.stdout.flush()

        session_dir = BILLS_XML_DIR / s
        cmd = 'rsync -avz --delete --delete-excluded govtrack.us::govtrackdata/us/' + s + '/people.xml ' + str(session_dir.abspath())
        os.system(cmd)
        print 'done'
    print ""

def get_xml_bills():
    if BILLS_XML_DIR.exists():
        shutil.rmtree(BILLS_XML_DIR)
    os.makedirs(BILLS_XML_DIR)

    print "*** Downloading XML bills"
    for session in general.CONGRESSES:
        s = str(session)

        sys.stdout.write('    Downloading congress ' + s + '...')
        sys.stdout.flush()

        session_dir = BILLS_XML_DIR / s
        os.mkdir(session_dir)
        cmd = 'rsync -avz --delete --delete-excluded govtrack.us::govtrackdata/us/' + s + '/bills ' + str(session_dir.abspath())
        print cmd
        os.system(cmd)
        print 'done'
    print ""

def main():
    # Download XML bills
    get_xml_bills()
    # Clear database
    db_utils.clear_bills_db()
    # Write basic data
    db_utils.write_db()
    # Write top terms
    db_utils.write_db_top_term()
    db_utils.write_db_top_terms()

    # Download XML people
    get_xml_people()
    db_utils.write_db_people()
    db_utils.write_db_sponsors()

    # Write related bills data
    db_utils.write_db_related_bills()
    # Create text index of summaries
    ix_utils.create_summary_index()

if __name__ == '__main__':
    main()
