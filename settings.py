from PyQt5 import QtWidgets, QtCore
from ccSettingsUi import Ui_Settings 
import drivers
import shelve
import constants
from pathlib import Path

class Instruments:
    def __init__(self, fRange=''):
        self.fRange = fRange

    @property
    def fRange(self):
        return self._fRange

    @fRange.setter
    def fRange(self, val):
        self._fRange = val
        self.recallSettings()

    def recallSettings(self):
        if self.fRange != '':
            with shelve.open(str(constants.CONFIG_FP / f'{self.fRange}Instruments')) as settings:
                try:
                    self.sa = settings['sa']
                    self.ctrl = settings['ctrl']
                except KeyError:
                    self.sa = drivers.ESW()
                    self.ctrl = drivers.EMCenter()

    def saveInstruments(self):
        if self.fRange != '':
            with shelve.open(str(constants.CONFIG_FP / f'{self.fRange}Instruments')) as settings:
                settings['sa'] = self.sa
                settings['ctrl'] = self.ctrl

    def setupReLf(self):
        self.sa.preset()
        self.sa.instrumentMode('SAN')
        self.sa.setSweepPoints(30000)
        self.sa.setFrequencyStart(30, 'MHz')
        self.sa.setFrequencyStop(1, 'GHz')
        self.sa.setRbw(120, 'kHz')
        self.sa.setVbw(300, 'kHz')
        self.sa.setTraceMode(1, 'MAXH')
        self.sa.setTraceMode(2, 'WRIT')
        self.sa.autoScale(1)

    def setupReMf(self):
        self.sa.preset()
        self.sa.instrumentMode('SAN')
        self.sa.setSweepPoints(30000)
        self.sa.setFrequencyStart(1, 'GHz')
        self.sa.setFrequencyStop(18, 'GHz')
        self.sa.setRbw(1, 'MHz')
        self.sa.setVbw(3, 'MHz')
        self.sa.setTraceMode(1, 'MAXH')
        self.sa.setTraceMode(2, 'WRIT')
        self.sa.autoScale(1)

    def setupReHf(self):
        # 18GHz - 40GHz setup
        self.sa.preset()
        self.sa.instrumentMode('SAN')
        self.sa.setSweepPoints(30000)
        self.sa.setFrequencyStart(18, 'GHz')
        self.sa.setFrequencyStop(40, 'GHz')
        self.sa.setRbw(1, 'MHz')
        self.sa.setVbw(3, 'MHz')
        self.sa.setTraceMode(1, 'MAXH')
        self.sa.setTraceMode(2, 'WRIT')
        self.sa.autoScale(1)

    def setupSaSettings(self):
        scanType = {
            'lf': self.setupReLf,
            'mf': self.setupReMf,
            'hf': self.setupReHf,
        }
        func = scanType.get(self.fRange, 'Make a scan selection.')
        func()

class SettingsView(QtWidgets.QDialog, Ui_Settings):
    def __init__(self, ccFile='', fRange=''):
        super(SettingsView, self).__init__()
        self.setupUi(self)
        self.filepathEdit.setText(str(ccFile))
        self.fRange = fRange
        self.appFp = Path(__file__).parent.absolute()
        self.instruments = Instruments(fRange=self.fRange)
        self.recallUi()

    def recallUi(self):
        if self.instruments.sa.connectionType == 'GPIB':
            self.saGPIBRadio.setChecked(True)
            self.saGPIBSpin.setValue(int(self.instruments.sa.connectionId))
        else:
            self.saIPRadio.setChecked(True)
            self.saIPEdit.setText(self.instruments.sa.connectionId)

        if self.instruments.ctrl.connectionType == 'GPIB':
            self.ctrlGPIBRadio.setChecked(True)
            self.ctrlGPIBSpin.setValue(int(self.instruments.ctrl.connectionId))
        else:
            self.ctrlIPRadio.setChecked(True)
            self.ctrlIPEdit.setText(self.instruments.ctrl.connectionId)

    @QtCore.pyqtSlot()
    def browseSlot(self):
        options = QtWidgets.QFileDialog.Options()
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(
                        None,
                        "QFileDialog.getOpenFileName()",
                        "",
                        "Excel Files (*.xlsx);;Old Excel Files (*.xlx);;All Files (*)",
                        options=options)
        if fileName:
            self.filepathEdit.setText(fileName)

    @QtCore.pyqtSlot()
    def saIPSelectSlot(self):
        self.saIPRadio.setChecked(True)
        self.instruments.sa.connectionType = 'TCPIP'
        self.instruments.sa.connectionId = self.saIPEdit.text()

    @QtCore.pyqtSlot()
    def saGPIBSelectSlot(self):
        self.saGPIBRadio.setChecked(True)
        self.instruments.sa.connectionType = 'GPIB'
        self.instruments.sa.connectionId = self.saGPIBSpin.value()

    @QtCore.pyqtSlot()
    def ctrlIPSelectSlot(self):
        self.ctrlIPRadio.setChecked(True)
        self.instruments.ctrl.connectionType = 'TCPIP'
        self.instruments.ctrl.connectionId = self.ctrlIPEdit.text()

    @QtCore.pyqtSlot()
    def ctrlGPIBSelectSlot(self):
        self.ctrlGPIBRadio.setChecked(True)
        self.instruments.ctrl.connectionType = 'GPIB'
        self.instruments.ctrl.connectionId = self.ctrlGPIBSpin.value()

    def saveSettings(self):
        self.instruments.saveInstruments()

        if Path(self.filepathEdit.text()).exists():
            with shelve.open(str(self.appFp / 'config' / 'initial')) as f:
                f['ccFile'] = Path(self.filepathEdit.text())

    def findCheckedRadio(self, group):
        for radio in group.findChildren(QtWidgets.QRadioButton):
            if radio.isChecked():
                return radio

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Fp = Path(__file__).parent.absolute()
    with shelve.open(str(Fp / 'config' / 'initial')) as f:
        ccFile = f['ccFile']
    ccSettings = SettingsView(str(ccFile), 'mf')
    if ccSettings.exec_():
        ccSettings.saveSettings()
    sys.exit(app.exec_())