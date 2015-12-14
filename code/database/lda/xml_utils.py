from bs4 import BeautifulSoup
import dateutil.parser

def parse_lobbyist(tag):
    ret = {}

    ret['name'] = tag['lobbyistname']
    if tag['officialposition'] == 'N/A':
        ret['official_position'] = None
    else:
        ret['official_position'] = tag['officialposition']
        
    return ret

def parse_government_entity(tag):
    return {
        'name': tag['goventityname']
        }

def parse_foreign_entity(tag):
    ret =  {
        'name': tag['foreignentityname'],
        'country': tag['foreignentitycountry'],
        'ppb_country': tag['foreignentityppbcountry']
        }

    if tag['foreignentitycontribution'] == '':
        ret['contribution'] = None
    else:
        ret['contribution'] = int(tag['foreignentitycontribution'])

    if tag['foreignentityownershippercentage'] == '':
        ret['ownership'] = None
    else:
        ret['ownership'] = int(tag['foreignentityownershippercentage'])

    return ret

def parse_affiliated_org(tag):
    return {
        'name': tag['affiliatedorgname'],
        'country': tag['affiliatedorgcountry'],
        'ppb_country': tag['affiliatedorgppbccountry'] # sic
        }

def parse_issue(tag):
    ret = {}

    ret['code'] = tag['code']
    if tag['specificissue'] == '':
        ret['specific_issue'] = None
    else:
        ret['specific_issue'] = tag['specificissue']

    return ret

def parse_client(tag):
    ret = {}

    ret['id'] = int(tag['clientid'])
    ret['name'] = tag['clientname']
    ret['country'] = tag['clientcountry']
    ret['ppb_country'] = tag['clientppbcountry']
    ret['state'] = tag['clientstate']
    ret['ppb_state'] = tag['clientppbstate']
    ret['description'] = tag['generaldescription']
    ret['is_state_or_local_gov'] = (tag['isstateorlocalgov'] == 'TRUE')
    ret['self_filer'] = (tag['selffiler'] == 'TRUE')

    return ret

def parse_registrant(tag):
    ret = {}

    ret['id'] = int(tag['registrantid'])
    ret['name'] = tag['registrantname']
    ret['address'] = None
    if 'address' in tag:
        ret['address'] = tag['address']
    ret['country'] = tag['registrantcountry']
    ret['ppb_country'] = tag['registrantppbcountry']
    ret['description'] = tag['generaldescription']

    return ret
    
def parse_filing(tag, filename=""):
    ret = {}

    ret['id'] = tag['id']
    ret['period'] = tag['period']
    if tag['amount'] == '':
        ret['amount'] = None
    else:
        ret['amount'] = int(tag['amount'])
    ret['type'] = tag['type']
    ret['year'] = int(tag['year'])
    ret['received'] = dateutil.parser.parse(tag['received'])

    ret['xml_file'] = filename
    
    client_parsed = parse_client(tag.client)
    ret['client'] = client_parsed
    ret['client_state'] = client_parsed['state']
    ret['client_ppb_state'] = client_parsed['ppb_state']
    ret['client_ppb_country'] = client_parsed['ppb_country']
    ret['self_filer'] = client_parsed['self_filer']
    ret['registrant'] = parse_registrant(tag.registrant)

    if tag.lobbyists is None:
        ret['lobbyists'] = []
    else:
        ret['lobbyists'] = [parse_lobbyist(l) for l in tag.lobbyists]

    if tag.issues is None:
        ret['issues'] = []
    else:
        ret['issues'] = [parse_issue(l) for l in tag.issues]
        
    if tag.governmententities is None:
        ret['gov_entities'] = []
    else:
        ret['gov_entities'] = [parse_government_entity(g) 
                               for g in tag.governmententities]
        
    if tag.foreignentities is None:
        ret['foreign_entities'] = []
    else:
        ret['foreign_entities'] = [parse_foreign_entity(f)
                                   for f in tag.foreignentities]

    if tag.affiliatedorgs is None:
        ret['affiliated_orgs'] = []
    else:
        ret['affiliated_orgs'] = [parse_affiliated_org(l) for l in tag.affiliatedorgs]
                                   
    return ret                                   

def parse_file(filename):
    with open(filename) as f:
        soup = BeautifulSoup(f.read())
        filings = soup.publicfilings.find_all('filing')
        return [parse_filing(filing, filename=filename)
                for filing in filings]

def print_filing(f):
    for k in f:
        print k, ":", str(f[k])

