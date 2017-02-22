"""Resolwe API"""
import datetime
from collections import OrderedDict

import requests
from resdk import Resolwe
from Orange.data import ContinuousVariable, StringVariable, TimeVariable, DiscreteVariable, Domain, Table


DATA = [
    ['sex', {'type': DiscreteVariable}],
    ['entry_date', {'type': TimeVariable}],
    ['birth_date', {'type': TimeVariable}],
    ['village_code', {'type': DiscreteVariable}],
    ['latitude', {'type': ContinuousVariable, 'group': 'location'}],
    ['longitude', {'type': ContinuousVariable, 'group': 'location'}],
    ['ethnicity', {'type': DiscreteVariable}],
    ['fever', {'type': DiscreteVariable}],
    ['antimalaria_treatment', {'type': DiscreteVariable}],
    ['hospital_visit', {'type': DiscreteVariable}],
    ['vomit', {'type': DiscreteVariable}],
    ['cough', {'type': DiscreteVariable}],
    ['diarrhoea', {'type': DiscreteVariable}],
    ['bednet', {'type': DiscreteVariable}],
    ['body_temp', {'type': ContinuousVariable}],
    ['ama1', {'type': ContinuousVariable, 'group': 'immunological_data'}],
    ['msp1', {'type': ContinuousVariable, 'group': 'immunological_data'}],
    ['msp2', {'type': ContinuousVariable, 'group': 'immunological_data'}],
    ['nanp', {'type': ContinuousVariable, 'group': 'immunological_data'}],
    ['total_ige', {'type': ContinuousVariable, 'group': 'immunological_data'}],
]
METAS = [
    ['study_code', {'type': StringVariable}],
]


def _parse_sample_descriptor(descriptor):
    """Return a list of values from sample descriptor."""
    data = []
    for var in DATA:
        value = None  # Prevent assigning previous value if current one is missing
        if 'group' in var[1]:
            if descriptor.get(var[1]['group'], None):
                value = descriptor[var[1]['group']][var[0]]
        else:
            value = descriptor.get(var[0], None)

        # Format discrete and time variables:
        if value is not None and var[1]['type'] in [DiscreteVariable, TimeVariable] and not isinstance(value, bool):
            value = str(value)

        data.append(value)

    metas = [descriptor.get(var[0], None) for var in METAS]
    return data + metas


def to_orange_table(samples):
    """Parse data from samples to Orange.data.Table"""
    #  Create table and fill it with sample data:
    table = []
    for sample in samples:
        table.append(_parse_sample_descriptor(sample.descriptor['sample']))

    #  Create domain (header in table):
    header = [var[1]['type'].make(var[0]) for var in DATA]

    # It is necessary to provide all possible values for dicrete variable with
    # Iterate through all discrete variables in header:
    for head_, i in [(var, i) for i, (var, dat) in enumerate(zip(header, DATA)) if dat[1]['type'] == DiscreteVariable]:
        # Provide all possible values for discrete_var:
        head_.values = list(set([sample[i] for sample in table]))

    metas = [var[1]['type'].make(var[0]) for var in METAS]
    return Table(Domain(header, metas=metas), table)


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
