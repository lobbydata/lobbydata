from elixir import *
from database.firms.models import CompustatFirmYearlyData

class Lobbyist(Entity):
    using_options(shortnames=True, tablename='lobbyists')

    name = Field(Unicode(140), primary_key=True)
    official_position = Field(Unicode(250))
    reports = ManyToMany('LobbyingReport')

    def __repr__(self):
        return '<Lobbyist "%s">' % self.name

class LobbyingIssue(Entity):
    using_options(shortnames=True, tablename='lobbying_issues')

    code = Field(Unicode(140), primary_key=True)

    def __repr__(self):
        return '<Issue "%s">' % self.code

class LobbyingSpecificIssue(Entity):
    using_options(shortnames=True, tablename='lobbying_specific_issues')

    text = Field(UnicodeText)
    issue = ManyToOne('LobbyingIssue')
    report = ManyToOne('LobbyingReport')
    bills_by_number = ManyToMany('Bill', inverse='specific_issues_by_number')
    bills_by_title = ManyToMany('Bill', inverse='specific_issues_by_title')

    def __repr__(self):
        return u'<SpecificIssue ' + str(self.id) + u'>'

class LobbyingClient(Entity):
    using_options(shortnames=True, tablename='lda_clients')

    id = Field(Integer)
    name = Field(Unicode(250), primary_key=True)
    description = Field(UnicodeText)
    country = Field(Unicode(250))
    ppb_country = Field(Unicode(250))
    state = Field(Unicode(250))
    ppb_state = Field(Unicode(250))
    self_filer = Field(Boolean)
    is_state_or_local_gov = Field(Boolean)
    is_tradeassoc = Field(Boolean)

    compustat_score = Field(Integer)
    compustat_key = Field(Unicode(40))
    compustat_name = Field(Unicode(250))

    osiris_score = Field(Integer)
    osiris_key = Field(Unicode(40))
    osiris_name = Field(Unicode(250))

    orbis_score = Field(Integer)
    orbis_key = Field(Unicode(40))
    orbis_name = Field(Unicode(250))
    orbis_guo_key = Field(Unicode(40))
    orbis_guo_name = Field(Unicode(250))

    bvdid = Field(Unicode(40))
    gvkey = Field(Unicode(40))
    guo_bvdid = Field(Unicode(40))
    ticker = Field(Unicode(40))
    isin = Field(Unicode(40))
    naics = Field(Unicode(40))

    industry = ManyToOne("Industry")


    def __repr__(self):
        return '<Client "%s">' % self.name

class LobbyingRegistrant(Entity):
    using_options(shortnames=True, tablename='lobbying_registrants')

    id = Field(Integer)
    name = Field(Unicode(250), primary_key=True)
    address = Field(UnicodeText)
    country = Field(Unicode(250))
    ppb_country = Field(Unicode(250))
    description = Field(UnicodeText)

    def __repr__(self):
        return '<Registrant "%s">' % self.name

class GovernmentEntity(Entity):
    using_options(shortnames=True, tablename='government_entities')

    name = Field(Unicode(140), primary_key=True)
    reports = ManyToMany('LobbyingReport')

    def __repr__(self):
        return '<GovernmentEntity "%s">' % self.name

class ForeignEntity(Entity):
    using_options(shortnames=True, tablename='foreign_entities')

    name = Field(Unicode(140), primary_key=True)
    country = Field(Unicode(140))
    ppb_country = Field(Unicode(140))
    reports = ManyToMany('LobbyingReport')

    def __repr__(self):
        return '<ForeignEntity "%s">' % self.name

class ForeignEntityRelationship(Entity):
    using_options(shortnames=True, tablename='foreign_entity_relationships')

    foreign_entity = ManyToOne('ForeignEntity')
    lobbying_report = ManyToOne('LobbyingReport')
    contribution = Field(Integer)
    ownership = Field(Integer)

class AffiliatedOrg(Entity):
    using_options(shortnames=True, tablename='affiliated_orgs')

    name = Field(Unicode(140), primary_key=True)
    country = Field(Unicode(140))
    ppb_country = Field(Unicode(140))    
    reports = ManyToMany('LobbyingReport')

    def __repr__(self):
        return '<AffiliatedOrg "%s">' % self.name

class LobbyingReport(Entity):
    using_options(shortnames=True, tablename='lobbying_reports')

    id = Field(Unicode(60), primary_key=True)
    year = Field(Integer)
    received = Field(DateTime)
    amount = Field(Integer)
    type = Field(Unicode(60))
    period = Field(Unicode(80))
    xml_file = Field(Unicode(80))

    client = ManyToOne('LobbyingClient')
    client_state = Field(Unicode(60))
    client_ppb_state = Field(Unicode(60))
    client_ppb_country = Field(Unicode(60))
    self_filer = Field(Boolean)
    registrant = ManyToOne('LobbyingRegistrant')

    lobbyists = ManyToMany('Lobbyist')
    issues = ManyToMany('LobbyingIssue')
    gov_entities = ManyToMany('GovernmentEntity')
    affiliated_orgs = ManyToMany('AffiliatedOrg')
    foreign_entities = ManyToMany('ForeignEntity')

    def client_compustat_data(self, score_cutoff=0):
        if self.client.compustat_score < score_cutoff:
            return None

        if self.client.gvkey:
            gvkey = self.client.gvkey
        else: gvkey = self.client.compustat_key
        year = int(self.year)

        return CompustatFirmYearlyData.query.filter_by(gvkey=gvkey, year=year).first()

    def client_data_row(self, score_cutoff=0):
        yearly_data = self.client_compustat_data(score_cutoff=score_cutoff)
        
        if yearly_data is None:
            return None

        return [self.client.compustat_name] + yearly_data.financial_row()
