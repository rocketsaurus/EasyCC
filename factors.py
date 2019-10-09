from PyQt5 import QtWidgets, QtCore
from ccFactorsUi import Ui_Factors
from dfModel import DataFrameModel
from pathlib import Path
import pandas as pd
import shelve

class CorrectionFactors:
    xcol = 'Frequency (MHz)'

    def __init__(self, configPath=Path(__file__).parent.absolute() / 'config', fRange='lf'):
        self.configPath = configPath
        self.fRange = fRange
        
    @property
    def fRange(self):
        return self._fRange

    @fRange.setter
    def fRange(self, val):
        self._fRange = Path(f'{val}Factors')
        self.loadDict()

    def getFactorsDict(self):
        # Read factors from saved shelve file
        factorsDict = {}

        with shelve.open(str(self.configPath / self.fRange)) as factors:
            for factor, fp in factors.items():
                factorsDict[factor] = fp

        return factorsDict

    def loadDict(self):
        self.cf = pd.DataFrame(columns=[self.xcol])
        for factor, fp in self.getFactorsDict().items():
            if fp.exists() and fp != Path():
                cfLocal = pd.read_csv(
                    fp,
                    names=[self.xcol, fp.stem],
                    header=None,
                    dtype=float,
                    )
                
                firstValue = cfLocal[fp.stem].iloc[0]
                # Ensure Preamp factors are negative
                if factor == 'Preamp' and firstValue > 0:
                    cfLocal[fp.stem] *= -1
                # Ensure all other factors are positive
                elif factor != ('Preamp' and 'Antenna') and firstValue < 0:
                    cfLocal[fp.stem] *= -1

                self.cf = self.cf.merge(cfLocal, on=self.xcol, how='outer')

        self.cf.sort_values(self.xcol, inplace=True)
        self.cf = self.interpolate_cf(self.cf)
        self.cf.dropna(inplace=True)
        self.cf['Total Correction Factor'] = self.cf.sum(axis=1)
        self.cf.reset_index(inplace=True)

    def interpolate_cf(self, df):
        df.set_index(self.xcol, inplace=True)
        for col in df.columns.tolist():
            first = df[col].first_valid_index()
            last = df[col].last_valid_index()
            df.loc[first:last, col] = df.loc[first:last, col].interpolate(method='index')
        return df

    def saveShelve(self, factors):
        with shelve.open(str(self.configPath / self.fRange)) as saved:
            for factor, fp in factors.items():
                saved[factor] = fp


class FactorsView(QtWidgets.QDialog, Ui_Factors):
    def __init__(self, fRange='lf'):
        super(FactorsView, self).__init__()
        self.setupUi(self)
        self.fRange = fRange
        self.loadFactors()
        
    def loadFactors(self):
        self.factors = CorrectionFactors(fRange=self.fRange)
        try:
            factorsDict = self.factors.getFactorsDict()
            self.antennaEdit.setText(str(factorsDict['Antenna']))
            self.preampEdit.setText(str(factorsDict['Preamp']))
            self.cableEdit.setText(str(factorsDict['Cable']))
            self.attenuatorEdit.setText(str(factorsDict['Attenuator']))
            self.lisnEdit.setText(str(factorsDict['LISN']))
        except KeyError:
            pass

    def saveFactors(self):
        self.factors.saveShelve(self.getFilepaths())

    def openFileDialog(self):
        options = QtWidgets.QFileDialog.Options()
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(
                        None,
                        "QFileDialog.getOpenFileName()",
                        "",
                        "CSV Files (*.csv);;All Files (*)",
                        options=options)
        return fileName

    @QtCore.pyqtSlot()
    def browseAntennaSlot(self):
        fileName = self.openFileDialog()
        if fileName:
            self.antennaEdit.setText(fileName)

    @QtCore.pyqtSlot()
    def browsePreampSlot(self):
        fileName = self.openFileDialog()
        if fileName:
            self.preampEdit.setText(fileName)
            
    @QtCore.pyqtSlot()
    def browseCableSlot(self):
        fileName = self.openFileDialog()
        if fileName:
            self.cableEdit.setText(fileName)

    @QtCore.pyqtSlot()
    def browseAttenuatorSlot(self):
        fileName = self.openFileDialog()
        if fileName:
            self.attenuatorEdit.setText(fileName)

    @QtCore.pyqtSlot()
    def browseLisnSlot(self):
        fileName = self.openFileDialog()
        if fileName:
            self.lisnEdit.setText(fileName)

    @QtCore.pyqtSlot()
    def updateFactorsSlot(self):
        filepaths = self.getFilepaths()
        self.factors.loadDict()
        model = DataFrameModel(self.factors.cf)
        self.factorTable.setModel(model)

    def getFilepaths(self):
        filepaths = {}
        filepaths['Antenna'] = Path(self.antennaEdit.text())
        filepaths['Preamp'] = Path(self.preampEdit.text())
        filepaths['Cable'] = Path(self.cableEdit.text())
        filepaths['Attenuator'] = Path(self.attenuatorEdit.text())
        filepaths['LISN'] = Path(self.lisnEdit.text())
        return filepaths


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    ccFactors = FactorsView()
    ccFactors.show()    
    sys.exit(app.exec_())