"""Resolwe api"""
from resdk import Resolwe
from Orange.data import ContinuousVariable, StringVariable, Domain, Table


DATA = [
        ('Ama1', 'ama1'),
        ('Msp1', 'msp1'),
        ('Msp2', 'msp2'),
        ('Nanp', 'nanp'),
        ('Total ige', 'total_ige')]
METAS = [
        ('Study code', 'study_code'),
        ('Birth date', 'birth_date'),
        ('Sex', 'sex'),
        ('Ethnicity', 'ethnicity'),
        ('Entry Date', 'entry_date'),
        ('Village Code', 'village_code')]


def _parse_descriptor(descriptor):
    metas = [descriptor[value[1]] for value in METAS if type(descriptor[value[1]]) is not dict]
    data = [descriptor['immunological_data'][value[1]] for value in DATA]
    return data + metas


def to_orange_table(samples):
    variables = [ContinuousVariable.make(var[0]) for var in DATA]
    meta_attrs = [StringVariable.make(meta[0]) for meta in METAS]
    domain = Domain(variables, metas=meta_attrs)
    table = []

    for sample in samples:
        table.append(_parse_descriptor(sample.descriptor['sample']))

    return Table(domain, table)


class ResolweAPI(object):

    def __init__(self, user, password, url):
        self._res = Resolwe(user, password, url)
        self.aut = self._res.auth

    def get_samples(self):
        return self._res.sample.filter(descriptor_schema__slug='sample-vaccinesurvey')
