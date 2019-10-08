from pathlib import Path
import xlwings as xw
import pandas as pd
import numpy as np
import sys
import shelve
import time
import constants
import warnings
from factors import CorrectionFactors
from settings import Instruments

class ConfidenceCheck:
    corrected = constants.CORRECTED
    ycol = constants.YCOL
    xcol = constants.XCOL
    resultsSuffix = ' Results'

    def __init__(self, fRange='lf', filepath=Path('G:\Shared drives\Facebook EMI Lab\Test Data\Daily Confidence Checks.xlsx')):
        self.filepath = filepath
        self._goldenValues = pd.DataFrame()
        self.trace = pd.DataFrame()
        self.fRanges = {
            'lf': 'RE 30MHz - 1GHz',
            'mf': 'RE 1GHz - 18GHz',
            'hf': 'RE 18GHz - 40GHz',
            'ce': 'CE 150kHz - 30MHz',
        }
        self.fRange = fRange
        
    @property
    def filepath(self):
        return self._filepath

    @filepath.setter
    def filepath(self, fp):
        if Path(fp).exists():
            self._filepath = fp
            with shelve.open(str(constants.CONFIG_FP / 'initial')) as d:
                d['ccFile'] = Path(fp)
        else:
            with shelve.open(str(constants.CONFIG_FP / 'initial')) as d:
                self._filepath = d['ccFile']
            warnings.warn('Invalid file selection, switching to default')

        self.app = xw.App(visible=True)
        self.wb = xw.Book(str(self.filepath))

    @property
    def fRange(self):
        return self._fRange

    @fRange.setter
    def fRange(self, val):
        if val in self.fRanges:
            self._fRange = val
            self.ws = self.wb.sheets[self.fRanges[val]]
            self.measuredTable = f'Measured_{val}'
            self.deltaTable = f'Deltas_{val}'
            self.measCol = self.ws.range(f'{self.measuredTable}')[:,3]
            self.deltaCol = self.ws.range(f'{self.deltaTable}')[:,0]
            self.instruments = Instruments(val)
            self.factors = CorrectionFactors(fRange=val)
        else:
            warnings.warn('Invalid range selection')

    @property
    def goldenValues(self):
        frequencies = self.ws.range(f'{self.measuredTable}')[:,0]
        values = self.ws.range(f'{self.measuredTable}')[:,1]
        self._goldenValues = pd.DataFrame(data={
            self.xcol: frequencies.value,
            self.corrected: values.value,
        })
        return self._goldenValues

    def initAnalyzer(self):
        try:
            self.instruments.sa.establishConnection()
            instId = str(self.instruments.sa)
            self.instruments.setupSaSettings()
            self.instruments.sa.resource.close()
            return instId
        except:
            return 'Connection unsuccessful. Verify connection settings'

    def readCorrectedTrace(self, num_trace=1, delay=0):
        self.instruments.sa.resource.open()
        self.trace = self.instruments.sa.readTrace(num_trace, delay)

        # Merge correction factors
        self.trace = pd.merge_asof(self.trace, 
            self.factors.cf, 
            on=self.xcol, 
            direction='nearest', 
            tolerance=2)

        # Merge upper and lower correction factor bounds
        lastFreq = self.trace[self.xcol].iloc[-1]
        firstFreq = self.trace[self.xcol].iloc[0]

        cfFreqs = list(self.factors.cf[self.xcol].values)
        for freq in cfFreqs:
            if firstFreq > freq:
                first_cf = freq
            elif firstFreq < freq:
                break
        for freq in cfFreqs:
            if lastFreq < freq:
                last_cf = freq
                break

        # Interpolate factors
        columns = self.trace.columns.tolist()
        columns.remove(self.xcol)
        columns.remove(self.ycol)

        for col in columns:
            first = self.trace[col].first_valid_index()
            last = self.trace[col].last_valid_index()
            self.trace.loc[first:last, col] =self.trace.loc[first:last, col].interpolate(method='index')

        self.trace[self.corrected] = self.trace[self.ycol] + self.trace['Total Correction Factor']

        self.instruments.sa.resource.close()
        return self.trace

    def sweepAntenna(self, maximum):
        # Sweep antenna mast from 100 - maximum
        self.instruments.ctrl.setPolarity('V')
        self.instruments.ctrl.setSpeed(self.instruments.ctrl, 3)
        self.instruments.ctrl.setPosition(self.instruments.ctrl.tower, 100)
        self.syncTower()
        self.instruments.ctrl.setPosition(self.instruments.ctrl.tower, maximum)
        self.syncTower()
        self.instruments.ctrl.setPosition(self.instruments.ctrl.tower, 100)
        self.syncTower()

    def syncTower(self):
        # Wait for tower movement to complete
        while not self.instruments.ctrl.isOpComplete(self.instruments.ctrl.tower):
            time.sleep(0.5)

    def findPeaks(self):
        # Empty peaks dataframe
        self.peaks = pd.DataFrame(columns=[self.xcol, self.corrected])
        traceMax = self.readCorrectedTrace(1)

        # Lookup closest frequency/amplitude to frequency list
        for freq in self.goldenValues[self.xcol]:
            peak = traceMax[[self.xcol, self.corrected]].iloc[
                (traceMax[self.xcol]-freq).abs().argsort()[:1]]
            self.peaks = self.peaks.append(peak)

        return self.peaks

    def insertDataToExcel(self, user):
        # Insert empty column values to table
        # Store equations
        average = self.ws.range(f'{self.measuredTable}[Average]')
        averageFormula = average.formula
        deltaFormula = self.deltaCol.formula

        # Insert empty columns
        if sys.platform == 'win32' or 'win64':
            self.ws.api.ListObjects(f'{self.measuredTable}').ListColumns.add(4)
            self.ws.api.ListObjects(f'{self.deltaTable}').ListColumns.add(1)
        else:
            self.measCol.api.insert_into_range()
            self.deltaCol.api.insert_into_range()

        # Repopulate columns with stored equations
        average.value = averageFormula
        self.ws.range(f'{self.deltaTable}')[:,0].value = deltaFormula

        # Enter user and date 
        date = time.strftime('%x', time.localtime())
        self.ws.range('D9').value = f'{user} - {date}'

        # Reshape array to column vector and update the excel sheet
        self.measCol.value = self.peaks[self.corrected].values.reshape(-1,1)

    def clearResults(self):
        # Clear the measurements column
        self.measCol.clear_contents()

    def checkPass(self):
        # Check the delta column is not more than +/- 3dB
        passing = True
        for d in self.resultData['Delta'].values
            if d > 3 or d < -3:
                passing = False
                break
        return passing

    def getResultsFrame(self):
        results = self.peaks[self.corrected].reset_index(drop=True)
        results.drop(columns=self.xcol, inplace=True)
        self.resultData = self.goldenValues
        self.resultData = self.resultData.merge(
            results, 
            left_index=True, 
            right_index=True, 
            suffixes=('', self.resultsSuffix))
        self.resultData['Delta'] = (self.resultData[self.corrected] - 
            self.resultData[self.corrected + self.resultsSuffix])
        return self.resultData

    def save_and_exit(self):
        self.wb.save(self.filepath)
        self.wb.close()
        self.app.quit()
        sys.exit(0)

    def exit(self):
        self.wb.close()
        self.app.quit()
        sys.exit(0)

if __name__ == "__main__":
    data = ConfidenceCheck(fRange='hf')
    data.initAnalyzer()
    print(data.readTrace(1, 0.5))
    data.exit()