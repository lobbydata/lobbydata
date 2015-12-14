import db_utils, ix_utils
import urllib
import string, re
import os
import shutil, zipfile
from .. import general
from bs4 import BeautifulSoup

BASE_DIR = general.DATA_DIR / 'lda' / 'xml'
ZIPPED_DIR = BASE_DIR / 'zipped'
UNZIPPED_DIR = BASE_DIR / 'unzipped'

DOWNLOADS_URL = "http://www.senate.gov/legislative/Public_Disclosure/database_download.htm"

def get_zipped_data():
    if ZIPPED_DIR.exists():
        shutil.rmtree(ZIPPED_DIR)
    os.makedirs(ZIPPED_DIR)

    soup = BeautifulSoup(urllib.urlopen(DOWNLOADS_URL).read())

    links = [link['href'] for link in soup.findAll('a', href=True)]
        
    pattern = r'[0-9]{4}_[0-9]\.zip$'
    regex = re.compile(pattern)

    download_links = [
        link for link in links if regex.search(link) is not None
    ]

    for link in download_links:
        print "    Downloading", link
        filename = link.split("/")[-1]
        with open(ZIPPED_DIR / filename, 'wb') as f:
            f.write(urllib.urlopen(link).read())

def get_unzipped_data():
    if UNZIPPED_DIR.exists():
        shutil.rmtree(UNZIPPED_DIR)
    os.makedirs(UNZIPPED_DIR)

    zip_files = ZIPPED_DIR.files('*.zip')

    for z in zip_files:
        print "    Extracting", z
        zf = zipfile.ZipFile(z, 'r')
        unzip_dir = UNZIPPED_DIR / string.replace(z.name, '.zip', '')
        os.makedirs(unzip_dir)
        zf.extractall(unzip_dir)

def write_db():
    xml_dirs = UNZIPPED_DIR.dirs()

    for d in xml_dirs:
        xml_files = d.files('*.xml')
        for f in xml_files:
            print "    Loading", f
            db_utils.write_file_to_db(f)

def main():
    print "*** Getting raw LDA data"
    get_zipped_data()
    get_unzipped_data()
    print ""

    print "*** Loading LDA data into database"
    db_utils.clear_lda_db()
    write_db()
    print ""

    # Create index of issue texts
    ix_utils.create_issue_index()
    # Add bills <-> specific issues correspondences
    db_utils.add_specific_issue_bills_by_title()
    db_utils.add_specific_issue_bills_by_number()

    # Add uniqueified client name data
    db_utils.add_client_unique_names()
    # db_utils.add_bvdid()
    db_utils.add_bvdid_gvkey()
    
if __name__ == '__main__':
    main()
