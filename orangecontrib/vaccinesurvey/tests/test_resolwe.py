import unittest

from orangecontrib.vaccinesurvey import ResolweAPI


class ResolweTests(unittest.TestCase):

    def test_connection(self):
        username = 'admin'
        password = 'admin'
        url = 'http://127.0.0.1:8001'
        self.assertTrue(ResolweAPI(username, password, url))
