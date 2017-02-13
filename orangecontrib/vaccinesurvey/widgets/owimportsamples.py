"""Import samples widget"""
import requests


from AnyQt.QtWidgets import QLineEdit
from AnyQt.QtWidgets import QSizePolicy as Policy

from Orange.data import Table
from Orange.widgets.widget import OWWidget
from Orange.widgets import gui, settings
from Orange.widgets.utils.concurrent import ThreadExecutor, Task
from ..resolwe import ResolweAPI, to_orange_table, ResolweCredentialsException, ResolweServerException

error_red = 'QWidget { background-color:#FFCCCC;}'


class OWImportSamples(OWWidget):
    name = "Import Samples"
    icon = "icons/import.svg"
    want_main_area = False
    resizing_enabled = False
    priority = 1
    outputs = [("Data", Table)]

    username = settings.Setting('')
    password = settings.Setting('')
    selected_server = settings.Setting(0)
    combo_items = settings.Setting([])

    def __init__(self):
        super().__init__()
        self.res = None
        self.data = None
        self._datatask = None
        self._executor = ThreadExecutor()

        """Choose server"""
        box = gui.widgetBox(self.controlArea, 'Server')
        box.setSizePolicy(Policy.Minimum, Policy.Fixed)
        self.servers = gui.comboBox(box, self, "selected_server", editable=True,
                                    items=self.combo_items, callback=self.on_server_changed)

        """set credentials"""
        box = gui.widgetBox(self.controlArea, 'Credentials')
        box.setSizePolicy(Policy.Minimum, Policy.Fixed)

        self.name_field = gui.lineEdit(box, self, "username", "Username:", labelWidth=100,
                                       controlWidth=200, orientation='horizontal', callback=self.auth_changed)
        self.pass_field = gui.lineEdit(box, self, "password", "Password:", labelWidth=100,
                                       controlWidth=200, orientation='horizontal', callback=self.auth_changed)

        self.pass_field.setEchoMode(QLineEdit.Password)

        """display info"""
        box = gui.vBox(self.controlArea, "Info")
        box.setSizePolicy(Policy.Minimum, Policy.Fixed)
        self.info = gui.widgetLabel(box, 'No data loaded.')

        gui.rubber(self.controlArea)
        self.auth_set()

        if self.username and self.password:
            self.connect()

    def _update_info(self, error_msg=None):
        if not error_msg:
            if self._datatask is not None:
                if not self._datatask.future().done():
                    self.info.setText('Retrieving data...')
            if self.data:
                self.info.setText('{} samples loaded.'.format(len(self.data)))
        else:
            self.info.setText(error_msg)

    def _handle_styles(self, login=False, server=False):
        if login:
            self.name_field.setFocus()
            self.name_field.setStyleSheet(error_red)
            self.pass_field.setStyleSheet(error_red)
        elif server:
            self.servers.setFocus()
            self.servers.setStyleSheet(error_red)

    def _reset_styles(self):
        self.pass_field.setStyleSheet('')
        self.name_field.setStyleSheet('')
        self.servers.setStyleSheet('')

    def on_server_changed(self):
        if self.servers.itemText(self.selected_server) != '':
            if self.username and self.password:
                self.connect()
            elif not self.username:
                self.name_field.setFocus()
                self.name_field.setStyleSheet(error_red)
            elif not self.password:
                self.pass_field.setFocus()
                self.pass_field.setStyleSheet(error_red)
        else:
            self._handle_styles(server=True)

    def auth_set(self):
        self.pass_field.setDisabled(not self.username)
        self.pass_field.setFocus()

    def auth_changed(self):
        self._reset_styles()
        self.auth_set()
        self.connect()

    def get_data(self):
        return self.res.get_samples()

    def commit(self):
        try:
            self.data = self._datatask.result()
        except requests.exceptions.ConnectionError:
            self._update_info(error_msg='Error while connecting to the server!')
            self.data = None
        finally:
            self._datatask = None

        self._update_info()
        if self.data:
            self.send("Data", to_orange_table(self.data))

    def connect(self):
        self.res = None
        if self.username and self.password:
            self._reset_styles()

            """Store widget settings (Login)"""
            self.combo_items = [self.servers.itemText(i) for i in range(self.servers.count())]
            self.selected_server = self.servers.currentIndex()

            try:
                self.res = ResolweAPI(self.username, self.password, self.servers.itemText(self.selected_server))
            except (ResolweCredentialsException, ResolweServerException, Exception) as e:
                self.data = None
                error_name = type(e).__name__

                if error_name == 'ResolweCredentialsException':
                    self._update_info(error_msg=str(e))
                    self._handle_styles(login=True)
                elif error_name == 'ResolweServerException' or error_name == 'MissingSchema':
                    self._update_info(error_msg=str(e))
                    self._handle_styles(server=True)
                else:
                    self._update_info(error_msg=str(e))

            if self.res:
                self._datatask = Task(function=self.get_data)
                self._datatask.finished.connect(self.commit)
                self._executor.submit(self._datatask)
                self._update_info()

    def onDeleteWidget(self):
        super().onDeleteWidget()
        self._executor.shutdown(wait=False)
