from elixir import *
from database.lda.models import *

class Person(Entity):
    using_options(shortnames=True, tablename='people')

    id = Field(Integer, primary_key=True)
    firstname = Field(Unicode(120))
    lastname = Field(Unicode(120))
    state = Field(Unicode(2))
    gender = Field(Unicode(1))
    district = Field(Integer)
    religion = Field(Unicode(120))
    birthday = Field(DateTime)
    party = Field(Unicode(120))
    title = Field(Unicode(120))
    def get_name(self):
        return self.firstname + " " + self.lastname
    def __repr__(self):
        return '<Person (%s) "%s">' % (self.id, self.firstname + ' ' + self.lastname)

class BillTitle(Entity):
    using_options(shortnames=True, tablename='bill_titles')

    bill = ManyToOne('Bill')
    text = Field(UnicodeText)
    type = Field(Unicode(30))
    as_field = Field(Unicode(30))

class Bill(Entity):
    using_options(shortnames=True, tablename='bills1')

    id = Field(Unicode(30), primary_key=True)
    session = Field(Integer)
    type = Field(Unicode(30))
    number = Field(Integer)
    introduced = Field(DateTime)
    summary = Field(UnicodeText)
    billtext = Field(UnicodeText)    

    sponsor_id = Field(Integer, colname='sponsor')
    sponsor = ManyToOne('Person', field=sponsor_id)
    cosponsors = ManyToMany('Person')

    related_bills = ManyToMany('Bill')
    committees = ManyToMany('Committee')
    terms = ManyToMany('Term')
    top_term_id = Field(Integer, colname='top_term')
    top_term = ManyToOne('Term', field=top_term_id)
    top_terms = ManyToMany('Term')

    titles = OneToMany('BillTitle')

    specific_issues_by_title = ManyToMany('LobbyingSpecificIssue')
    specific_issues_by_number = ManyToMany('LobbyingSpecificIssue')
   
    def get_session_type_number(self):
        return str(self.session) + "_" + self.type + str(self.number)

    def get_number(self):
        return self.type + str(self.number)

    def __repr__(self):
        return '<Bill (%s) "%s">' % (self.id, self.titles[0].text)

class Committee(Entity):
    using_options(shortnames=True, tablename='committees')

    name = Field(Unicode(120))
    bills = ManyToMany('Bill')

    def __repr__(self):
        return '<Committee "%s">' % self.name

    def __init__(self, name):
        self.name = name

class Term(Entity):
    using_options(shortnames=True, tablename='terms')

    name = Field(Unicode(120))
    bills = ManyToMany('Bill', inverse='terms')
    bills_top = ManyToMany('Bill', inverse='top_terms')

    def __repr__(self):
        return '<Term "%s">' % self.name

    def __init__(self, name):
        self.name = name
