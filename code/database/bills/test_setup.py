import db_utils
import xml_utils
import ix_utils
from .. import general
from models import *

def main():
    tests_dir = general.ROOT_DIR / 'tests'

    db_utils.clear_bills_db()

    general.init_db()

    # Load basic data
    for f in tests_dir.files('bill*.xml'):
        db_utils.db_create_bill(xml_utils.bill_of_file(f))

    # Add related bills
    for f in tests_dir.files('bill*.xml'):
        b = xml_utils.bill_of_file(f)
        b_obj = Bill.query.filter_by(id=b['id']).first()
        for r_id in b['related']:
            r_obj = Bill.query.filter_by(id=r_id).first()
            b_obj.related_bills.append(r_obj)

    general.close_db(write=True)

    # Create text index of summaries
    ix_utils.create_summary_index()

if __name__ == '__main__':
    main()
