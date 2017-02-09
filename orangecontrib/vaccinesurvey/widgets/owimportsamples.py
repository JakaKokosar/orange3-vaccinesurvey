"""Import samples widget"""
from AnyQt.QtWidgets import QLineEdit
from AnyQt.QtWidgets import QSizePolicy as Policy

from Orange.data import Table
from Orange.widgets.widget import OWWidget, Msg
from Orange.widgets import gui, settings
from ..resolwe import ResolweAPI, to_orange_table


class OWImportSamples(OWWidget):
    name = "Import Samples"
    icon = "icons/import.svg"
    want_main_area = False
    resizing_enabled = False
    priority = 1
    outputs = [("Data", Table)]

    username = settings.Setting('')
    password = settings.Setting('')

    def __init__(self):
        super().__init__()
        self.res = None
        self.server = 'http://127.0.0.1:8001'

        box = gui.widgetBox(self.controlArea, 'Login')
        box.setSizePolicy(Policy.Minimum, Policy.Fixed)

        self.name_field = gui.lineEdit(box, self, "username", "Username:", labelWidth=100,
                                       controlWidth=200, orientation='horizontal', callback=self.auth_changed)
        self.pass_field = gui.lineEdit(box, self, "password", "Password:", labelWidth=100,
                                       controlWidth=200, orientation='horizontal', callback=self.auth_changed)

        self.pass_field.setEchoMode(QLineEdit.Password)

        box = gui.vBox(self.controlArea, "Info")
        box.setSizePolicy(Policy.Minimum, Policy.Fixed)
        self.info = gui.widgetLabel(box, 'No data loaded.')

        gui.rubber(self.controlArea)
        self.auth_set()

        if self.username and self.password:
            self.connect()

    def auth_set(self):
        self.pass_field.setDisabled(not self.username)

    def auth_changed(self):
        self.auth_set()
        self.connect()

    def connect(self):
        self.res = None
        if self.username and self.password:
            try:
                self.res = ResolweAPI(self.username, self.password, self.server)
            except Exception as e:
                self.info.setText(e.args[0])

            if self.res:
                samples = self.res.get_samples()
                self.info.setText('{} samples loaded.'.format(len(samples)))
                self.send("Data", to_orange_table(samples))
