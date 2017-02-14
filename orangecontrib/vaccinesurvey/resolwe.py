"""Resolwe api"""
import requests
import datetime


from resdk import Resolwe
from Orange.data import ContinuousVariable, StringVariable, TimeVariable, DiscreteVariable, Domain, Table


IMMUNOLOGICAL_DATA = [('Ama1', 'ama1'), ('Msp1', 'msp1'), ('Msp2', 'msp2'),
                      ('Nanp', 'nanp'), ('Total ige', 'total_ige')]

DATE = [('Birth date', 'birth_date'), ('Entry Date', 'entry_date')]
METAS = [('Study code', 'study_code')]
DISCRETE = [('Sex', 'sex'), ('Ethnicity', 'ethnicity'), ('Village Code', 'village_code')]


def _add_discrete_value(variable, val):
    """ Checks if item is in values. If its not it will add it """
    if val not in variable.values:
        variable.add_value(val)


def to_orange_table(samples):
    #  Create variables
    immuno_data = [ContinuousVariable.make(var[0]) for var in IMMUNOLOGICAL_DATA]
    discrete_vars = [DiscreteVariable.make(var[0]) for var in DISCRETE]   # we add values later
    date_vars = [TimeVariable.make(var[0]) for var in DATE]
    #  Create metas
    meta_attrs = [StringVariable.make(meta[0]) for meta in METAS]

    #  Parse sample descriptor
    def _parse_descriptor(descriptor):
        """ return a list of values from sample descriptor """
        metas = [descriptor[value[1]] for value in METAS]
        immuno_data = [descriptor['immunological_data'][value[1]] for value in IMMUNOLOGICAL_DATA]
        discrete_data = [str(descriptor[value[1]]) for value in DISCRETE]
        date_data = [str(datetime.datetime.strptime(descriptor[value[1]], "%Y-%m-%d").date()) for value in DATE
                     if descriptor[value[1]]]

        # add all possible values from descriptor to discrete variables
        for value in DISCRETE:
            [_add_discrete_value(var,  str(descriptor[value[1]])) for var in discrete_vars if var.name == value[0]]

        return immuno_data + discrete_data + date_data + metas

    #  Create table
    table = []
    for sample in samples:
        table.append(_parse_descriptor(sample.descriptor['sample']))
    #  Create domain
    domain = Domain(immuno_data + discrete_vars + date_vars, metas=meta_attrs)

    return Table(domain, table)


class ResolweAPI(object):

    def __init__(self, user, password, url):
        try:
            self._res = Resolwe(user, password, url)
        except requests.exceptions.InvalidURL as e:
            raise ResolweServerException(e)
        except ValueError as e:  # TODO: is there a better way? resdk returns only ValueError
            msg = str(e)
            if msg == 'Response HTTP status code 400. Invalid credentials?':
                raise ResolweCredentialsException(msg)
            elif msg == 'Server not accessible on {}. Wrong url?'.format(url):
                raise ResolweServerException(msg)
            else:
                raise

    def get_samples(self):
        return self._res.sample.filter(descriptor_schema__slug='sample-vaccinesurvey')


class ResolweCredentialsException(Exception):
    """Invalid credentials?"""


class ResolweServerException(Exception):
    """Wrong url?"""
