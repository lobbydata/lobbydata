import db_utils, ix_utils
from .. import general

def main():
    db_utils.clear_lda_db()

    tests_dir = general.ROOT_DIR / 'tests'
    for f in tests_dir.files('filing*.xml'):
        db_utils.write_file_to_db(f)

    # Create index of issue texts
    ix_utils.create_issue_index()
    # Add bills <-> specific issues correspondences
    db_utils.add_specific_issue_bills()
            
if __name__ == '__main__':
    main()
