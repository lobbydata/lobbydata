from elixir import *
from database.lda.models import *
from database.bills.models import *
from database.tariffs.models import *
from sqlalchemy.sql import or_, and_
import database.general, database.lda.ix_utils, database.lda.db_utils
import re
import datetime



def lda_issue_search(queries):
    database.general.init_db()
    return database.lda.ix_utils.issue_search(
        queries,
        return_objects=True,
        make_phrase=True,
        case_sensitive=False
    )


def client_state_search(clientobject, searchAll=True, removeDC=True):

    """this function returns states associated with client excluding DC. It

    takes clientobject as an input.
    """

    if searchAll:
        reports = LobbyingReport.query.filter_by(client=clientobject)
    else:
        reports = LobbyingReport.query.filter_by(client=clientobject).filter_by(type='REGISTRATION')

    state = []
    if reports.count() > 0:
        for report in reports:
            state.append(report.client_state)

        state = list(set(state))
        if removeDC:
            state = filter(lambda a: a != u'DISTRICT OF COLUMBIA', state)
        state = filter(lambda a: a != u'UNDETERMINED', state)
        state = filter(lambda a: a != "", state)
        if state:
            state = state
    else:
        state = ''
    return state


def client_ppbstate_search(clientobject, searchAll=True, removeDC=True):

    """this function returns principal place of business states
    associated with client excluding DC. It takes clientobject as an input.
    """

    if searchAll:
        reports = LobbyingReport.query.filter_by(client=clientobject)
    else:
        reports = LobbyingReport.query.filter_by(client=clientobject).filter_by(type='REGISTRATION')

    state = []
    if reports.count() > 0:
        for report in reports:
            state.append(report.client_ppb_state)

        state = list(set(state))
        if removeDC:
            state = filter(lambda a: a != u'DISTRICT OF COLUMBIA', state)
        state = filter(lambda a: a != u'UNDETERMINED', state)
        state = filter(lambda a: a != "", state)
        if state:
            state = state
    else:
        state = ''
    return state


def client_naics_search(clientobject):
    """this function returns naics industry codes associated with client 
    takes clientobject as an input.
    """
    
    gvkey = clientobject.gvkey
    if gvkey: 
        compustat_data = CompustatFirmYearlyData.query.filter_by(gvkey=gvkey)
        naics = []
        for d in compustat_data:
            naics.append(d.naicsh)

        naics = list(set(naics))
        naics  = filter(lambda a: a != '', naics)
        if naics:
            naics = naics
    else:
            naics = ''
    return naics

    

def client_ppb_country_search(clientobject, searchAll=True, removeUSA=False):

    """this function returns countries associated with client. It

    takes clientobject as an input.
    """

    if searchAll:
        reports = LobbyingReport.query.filter_by(client=clientobject)
    else:
        reports = LobbyingReport.query.filter_by(client=clientobject).filter_by(type='REGISTRATION')

    state = []
    if reports.count() > 0:
        for report in reports:
            state.append(report.client_ppb_country)

        state = list(set(state))
        if removeUSA:
            state = filter(lambda a: a != u'USA', state)
        state = filter(lambda a: a != u'UNDETERMINED', state)
        state = filter(lambda a: a != "", state)
        if state:
            state = state
    else:
        state = ''
    return state


def exists_amendment(lobbyingreport):
    """ this function searches whether there exists amendment"""
    ## getting information
    client = lobbyingreport.client
    registrant = lobbyingreport.registrant
    year = lobbyingreport.year
    r_type = lobbyingreport.type
    r_period = lobbyingreport.period
    r_id = lobbyingreport.id
    received = lobbyingreport.received
    
    check = LobbyingReport.query.filter_by(client=client).filter_by(registrant=registrant).filter_by(year=year).filter_by(period=r_period)
    amendments = check.filter(LobbyingReport.id!=r_id)
    if amendments.count() > 0:
        return True
    else:
        return False


def get_amendment(lobbyingreport):
    """
    this function returns amendment for a given report
    if exists
    """
    ## getting information
    client = lobbyingreport.client
    registrant = lobbyingreport.registrant
    year = lobbyingreport.year
    r_type = lobbyingreport.type
    r_period = lobbyingreport.period
    r_id = lobbyingreport.id
    received = lobbyingreport.received
    
    check = LobbyingReport.query.filter_by(client=client).filter_by(registrant=registrant).filter_by(year=year).filter_by(period=r_period)
    amendments = check.filter(LobbyingReport.id!=r_id)
    if amendments.count() > 0:
        if amendments.count() == 1:
            return amendments[0]
        else:
            ## need to find latest amendments
            latest_sofar = received
            latest_index = 0
            for i, report in enumerate(amendments):
                amend_received = report.received
                diff = amend_received - latest_sofar
                time_diff = divmod(diff.total_seconds(), 60)
                if time_diff > 0:
                    latest_sofar = amend_received
                    latest_index = i
                else:
                    continue
            return amendments[latest_index]
    else:
        return None
