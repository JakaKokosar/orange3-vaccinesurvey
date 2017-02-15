"""Import samples widget"""
import requests
import os
import requests_cache

from AnyQt.QtWidgets import QLineEdit
from AnyQt.QtWidgets import QSizePolicy as Policy
from AnyQt.QtCore import pyqtSignal

from Orange.misc import environ
from Orange.data import Table
from Orange.widgets.widget import OWWidget
from Orange.widgets import gui, settings
from Orange.widgets.utils.concurrent import ThreadExecutor, Task
from ..resolwe import ResolweAPI, to_orange_table, ResolweCredentialsException, ResolweServerException

error_red = 'QWidget { background-color:#FFCCCC;}'


#  Support cache with requests_cache module
cache_path = os.path.join(environ.cache_dir(), "resolwe")
try:
    os.makedirs(cache_path)
except OSError:
    pass
cache_file = os.path.join(cache_path, 'vaccinesurvey_cache')
#  cache successful requests for one hour
requests_cache.install_cache(cache_name=cache_file, backend='sqlite', expire_after=3600)


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

    def _on_exception(self):
        self._update_info(error_msg='Error while downloading data...\n'
                                    'Please check your connection.')

    def _update_info(self, error_msg=None):
        if not error_msg:
            if self._datatask is not None:
                if not self._datatask.future().done():
                    self.info.setText('Retrieving data...')
                    self._handle_inputs(False)
            if self.data:
                self._handle_inputs(True)
                self.info.setText('Data ready: {} samples loaded.'.format(len(self.data)))
        else:
            self.info.setText(error_msg)

    def _handle_inputs(self, enable):
        self.name_field.setEnabled(enable)
        self.pass_field.setEnabled(enable)
        self.servers.setEnabled(enable)

    def _handle_styles(self, login=False, server=False, user=False, passwd=False):
        if login:
            self.name_field.setFocus()
            self.name_field.setStyleSheet(error_red)
            self.pass_field.setStyleSheet(error_red)
        elif server:
            self.servers.setFocus()
            self.servers.setStyleSheet(error_red)
        elif user:
            self.name_field.setFocus()
            self.name_field.setStyleSheet(error_red)
        elif passwd:
            self.pass_field.setFocus()
            self.pass_field.setStyleSheet(error_red)

    def _reset_styles(self):
        self.pass_field.setStyleSheet('')
        self.name_field.setStyleSheet('')
        self.servers.setStyleSheet('')

    def on_server_changed(self):
        if self.servers.itemText(self.selected_server) != '':
            if self.username and self.password:
                self.connect()
            elif not self.username:
                self._handle_styles(user=True)
            elif not self.password:
                self._handle_styles(passwd=True)
        else:
            self._handle_styles(server=True)

    def auth_set(self):
        self.pass_field.setDisabled(not self.username)
        self.pass_field.setFocus()

    def auth_changed(self):
        self.auth_set()
        if self.servers.itemText(self.selected_server) == '':
            self._handle_styles(server=True)
        else:
            self._reset_styles()
            self.connect()

    def commit(self):
        self.data = self._datatask.result()
        self._datatask = None
        self._update_info()
        if self.data:
            self.send("Data", to_orange_table(self.data))

    def connect(self):
        self.res = None
        self.data = None

        if self.username and self.password:
            self._reset_styles()
            """Store widget settings (Login)"""
            self.combo_items = [self.servers.itemText(i) for i in range(self.servers.count())]
            self.selected_server = self.servers.currentIndex()

            try:
                self.res = ResolweAPI(self.username, self.password, self.servers.itemText(self.selected_server))
            except (ResolweCredentialsException, ResolweServerException, Exception) as e:
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
                self._datatask = DownloadTask(self.res)
                self._datatask.finished.connect(self.commit)
                self._datatask.exception.connect(self._on_exception)
                self._executor.submit(self._datatask)
                self._update_info()

    def onDeleteWidget(self):
        super().onDeleteWidget()
        self._executor.shutdown(wait=False)


class DownloadTask(Task):
    exception = pyqtSignal(Exception)

    def __init__(self, res):
        super().__init__()
        self.res = res

    def run(self):
        try:
            return list(self.res.get_samples())
        except requests.exceptions.ConnectionError as e:
            self.exception.emit(e)
