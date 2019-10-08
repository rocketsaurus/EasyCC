import unittest, os, sys, shelve
from glob import glob
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5 import QtTest

import settings, constants

app = QApplication(sys.argv)

class TestSettings(unittest.TestCase):
    fRange = 'test'
    ip = '10.0.0.10'
    gpib = 7

    def createInstrumentsFile(self):
        ccSettings = settings.SettingsView(ccFile=self.ccFile, fRange=self.fRange)
        ccSettings.saIPEdit.setText('10.0.0.10')
        ccSettings.ctrlGPIBSpin.setValue(7)
        ccSettings.instruments.saveInstruments()

    def tearDown(self):
        files = glob(str(constants.CONFIG_FP / f'{self.fRange}Instruments.*'))
        for f in files:
            os.remove(f)

    def setUp(self):
        with shelve.open(str(constants.CONFIG_FP / 'initial')) as f:
            self.ccFile = f['ccFile']

    def test_filepath(self):
        ccSettings = settings.SettingsView(ccFile=self.ccFile)
        self.assertEqual(ccSettings.filepathEdit.text(), str(self.ccFile))

    def test_instrument_settings(self):
        ccSettings = settings.SettingsView(ccFile=self.ccFile, fRange=self.fRange)
        ccSettings.saIPEdit.setText(self.ip)
        ccSettings.ctrlGPIBSpin.setValue(self.gpib)
        self.assertEqual(str(ccSettings.instruments.sa), f'ESW TCPIP::{self.ip}::INSTR')
        self.assertEqual(str(ccSettings.instruments.ctrl), f'EMCenter GPIB::{self.gpib}::INSTR')

    def test_instrument_recall_settings(self):
        self.createInstrumentsFile()
        ccSettings = settings.SettingsView(ccFile=self.ccFile, fRange=self.fRange)
        self.assertEqual(ccSettings.instruments.sa.connectionType, 'TCPIP')
        self.assertEqual(ccSettings.instruments.sa.connectionId, self.ip)
        self.assertEqual(ccSettings.instruments.ctrl.connectionType, 'GPIB')
        self.assertEqual(ccSettings.instruments.ctrl.connectionId, self.gpib)

    def test_ui_recall_settings(self):
        self.createInstrumentsFile()
        ccSettings = settings.SettingsView(ccFile=self.ccFile, fRange=self.fRange)
        self.assertTrue(ccSettings.saIPRadio.isChecked())
        self.assertFalse(ccSettings.saGPIBRadio.isChecked())
        self.assertFalse(ccSettings.ctrlIPRadio.isChecked())
        self.assertTrue(ccSettings.ctrlGPIBRadio.isChecked())
        self.assertEqual(ccSettings.saIPEdit.text(), self.ip)
        self.assertEqual(ccSettings.ctrlGPIBSpin.value(), self.gpib)
