#!/usr/bin/env python3
import time
import shelve
from pathlib import Path

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QThread, pyqtSignal
from matplotlib.animation import FuncAnimation
import numpy as np
import pandas as pd

from ccMainUi import Ui_ccMain
from ccModel import ConfidenceCheck
from dfModel import DataFrameModel
from factors import FactorsView
from settings import SettingsView
import constants

class AntennaSweepThread(QThread):
    signal = pyqtSignal('PyQt_PyObject')

    def __init__(self, cc):
        QThread.__init__(self)
        self.cc = cc
        self.re = ['lf', 'mf', 'hf']

    def run(self):
        if self.cc.fRange in self.re:
            self.cc.initController()
            if self.cc.fRange == 'lf':
                self.cc.sweepAntenna(400)
            else:
                self.cc.sweepAntenna(300)
        self.signal.emit('Done')

class EasyCC(QtWidgets.QMainWindow, Ui_ccMain):
    cc = ConfidenceCheck()        
    appFp = constants.APP_FP
    corrected = constants.CORRECTED
    ycol = constants.YCOL
    xcol = constants.XCOL

    def __init__(self):
        super(EasyCC, self).__init__()
        self.setupUi(self)
        self.setUser()
        self.run = 'RE 30MHz - 1GHz'
        self.fRange = 'lf'
        self.updateResultsTable(self.cc.goldenValues)
        self.toggleLogSlot(False)
        self.statusBar().showMessage('Select a frequency range to run')
        self.antennaThread = AntennaSweepThread(self.cc)
        self.antennaThread.signal.connect(self.sweepFinished)

    @property
    def fRange(self):
        return self._fRange

    @fRange.setter
    def fRange(self, val):
        if self.cc:
            self._fRange = val
            self.cc.fRange = val
        else:
            self.cc = ConfidenceCheck(fRange=val)
    
    def standby(self):
        self.runButton.setText('Run')
        self.setGroup(self.scanGroup, True)
        self.cancelButton.setEnabled(False)

    def inProgress(self):
        self.runButton.setText('Pause')
        self.setGroup(self.scanGroup, False)
        self.cancelButton.setEnabled(True)

    def paused(self):
        self.runButton.setText('Resume')
        self.setGroup(self.scanGroup, False)
        self.cancelButton.setEnabled(True)

    def setGroup(self, group, abled):
        self.nameEdit.setEnabled(abled)
        self.editFactorsButton.setEnabled(abled)
        for radio in group.findChildren(QtWidgets.QRadioButton):
            radio.setEnabled(abled)

    def setUser(self):
        home = Path.home()
        user = home.parts[2]
        self.nameEdit.setText(user)

    def debugOut(self, msg):
        self.logOutput.append(msg)

    def updateResultsTable(self, df):
        model = DataFrameModel(df)
        self.resultTable.setModel(model)
        self.resultTable.resizeColumnsToContents()

    def logFactors(self):
        for factor, fp in self.cc.factors.getFactorsDict().items():
            if fp.stem == '':
                self.debugOut(f'{factor}: None selected')
            else:
                self.debugOut(f'{factor}: {fp.stem}')

    @QtCore.pyqtSlot()
    def runSlot(self):
        if self.runButton.text() == 'Run':
            self.statusBar().showMessage('Starting Scan')
            self.inProgress()
            self.mplWidget.clearPlot()
            self.debugOut(f'{self.nameEdit.text()} executed {self.run} scan')
            self.statusBar().showMessage(self.cc.initAnalyzer())
            try:
                self.initAnimate()
                self.antennaThread.start()
            except Exception as e:
                self.debugOut(f'Could not read instruments.\n{e}')
                self.standby()
                self.showSettingsSlot()
        elif self.runButton.text() == 'Pause':
            self.paused()
            self.ani.event_source.stop()
        elif self.runButton.text() == 'Resume':
            self.inProgress()
            self.ani.event_source.start()

    @QtCore.pyqtSlot()
    def sweepFinished(self):
        self.standby()
        self.ani.event_source.stop()
        self.cc.findPeaks()
        self.updateResultsTable(self.cc.getResultsFrame())
        if self.cc.checkPass():
            self.cc.insertDataToExcel(self.nameEdit.text())
            self.cc.wb.save()
            self.statusBar().showMessage('Confidence Check Passed.  Data saved')
            self.debugOut('Confidence Check Passed.  Data saved')
        else:
            self.statusBar().showMessage('Confidence Check Failed')
            self.debugOut('Confidence Check Failed')

    @QtCore.pyqtSlot()
    def cancelSlot(self):
        self.standby()
        self.ani.event_source.stop()

    def initPlot(self):
        self.line[0].set_ydata([np.nan]*len(self.traceMax))
        self.line[1].set_ydata([np.nan]*len(self.traceMax))
        return self.line

    def initAnimate(self):
        self.traceMax = self.cc.readCorrectedTrace(1, 0.5)
        self.traceWrit = self.cc.readCorrectedTrace(2)
        self.line = [self.mplWidget.graph(
            x = self.traceMax[self.xcol].values, 
            y = self.traceMax[self.corrected].values, 
            label = f'{self.run} Max Hold', 
            xLabel = self.xcol, 
            yLabel = self.corrected)]
        self.line.append(self.mplWidget.graph(
            x = self.traceWrit[self.xcol].values, 
            y = self.traceWrit[self.corrected].values, 
            label = f'{self.run} Clear/Write', 
            xLabel = self.xcol, 
            yLabel = self.corrected))
        self.ani = FuncAnimation(self.mplWidget.figure, 
            self.animate, 
            init_func=self.initPlot, 
            interval=2, 
            blit=True)

    def animate(self, i):
        traceMax = self.cc.readCorrectedTrace(1)
        traceWrit = self.cc.readCorrectedTrace(2)
        self.line[0].set_ydata(traceMax[self.corrected])
        self.line[1].set_ydata(traceWrit[self.corrected])
        return self.line

    def radioSelect(self, radio, f):
        self.fRange = f
        self.run = radio.text()
        self.updateResultsTable(self.cc.goldenValues)
        self.logFactors()

    @QtCore.pyqtSlot()
    def lfSelectSlot(self):
        self.radioSelect(self.radioRElf, 'lf')

    @QtCore.pyqtSlot()
    def mfSelectSlot(self):
        self.radioSelect(self.radioREmf, 'mf')

    @QtCore.pyqtSlot()
    def hfSelectSlot(self):
        self.radioSelect(self.radioREhf, 'hf')

    @QtCore.pyqtSlot()
    def ceLineSelectSlot(self):
        self.radioSelect(self.radioCELine, 'L')

    @QtCore.pyqtSlot()
    def ceNeutralSelectSlot(self):
        self.radioSelect(self.radioCENeutral, 'N')

    @QtCore.pyqtSlot()
    def ceSignalSelectSlot(self):
        self.radioSelect(self.radioCESignal, 'S')

    @QtCore.pyqtSlot()
    def editFactorsSlot(self):
        ccFactors = FactorsView(self.fRange)
        if ccFactors.exec_():
            ccFactors.saveFactors()
            self.cc.fRange = self.fRange
            self.logFactors()
        else:
            self.debugOut('Factors not saved')

    @QtCore.pyqtSlot()
    def showSettingsSlot(self):
        ccSettings = SettingsView(ccFile=str(self.cc.filepath), fRange=self.fRange)
        if ccSettings.exec_():
            ccSettings.saveSettings()
        else:
            self.debugOut('Settings not saved')

    @QtCore.pyqtSlot(bool)
    def toggleScanSlot(self, toggled):
        if toggled:
            self.scanDock.show()
        elif not toggled:
            self.scanDock.hide()

    @QtCore.pyqtSlot(bool)
    def toggleResultsSlot(self, toggled):
        if toggled:
            self.resultsDock.show()
        elif not toggled:
            self.resultsDock.hide()

    @QtCore.pyqtSlot(bool)
    def toggleLogSlot(self, toggled):
        if toggled:
            self.logDock.show()
        elif not toggled:
            self.logDock.hide()

    @QtCore.pyqtSlot(bool)
    def scanDockChangedSlot(self, visible):
        self.actionViewScan.setChecked(visible)

    @QtCore.pyqtSlot(bool)
    def resultDockChangedSlot(self, visible):
        self.actionViewResults.setChecked(visible)

    @QtCore.pyqtSlot(bool)
    def logDockChangedSlot(self, visible):
        self.actionViewLogOutput.setChecked(visible)

    @QtCore.pyqtSlot()
    def close(self):
        self.cc.exit()
        super().close()


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    ccMain = EasyCC()
    ccMain.show()
    sys.exit(app.exec_())
