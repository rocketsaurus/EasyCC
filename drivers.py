#!/usr/bin/env python3
''' 
Instrument driver classes
Author: Jeremy
'''
import visa
import pandas as pd
import numpy as np
import time

class BaseInstrument:
    '''Common SCPI commands'''
    def __init__(self, connectionType='GPIB', connectionId=20, log=False, *args, **kwargs):
        '''Initialize resource object'''
        self.connectionType = connectionType.upper()
        self.connectionId = connectionId
        self.log = log

    def establishConnection(self):
        self.rm = visa.ResourceManager()
        self.setResourceString()
        self.resource = self.rm.open_resource(self.resourceString)
        self.resource.timeout = 35000

    def setResourceString(self):
        self.resourceString = f'{self.connectionType}::{self.connectionId}::INSTR'

    def __repr__(self):
        '''Returns instrument ID'''
        return self.resource.query('*IDN?')

    def __str__(self):
        '''Returns instrument ID'''
        try:
            return self.resource.query('*IDN?')
        except:
            self.setResourceString()
            return f'{self.__class__.__name__} {self.resourceString}'

    def reset(self):
        '''Resets instrument'''
        self.resource.write('*RST')

    def wait(self):
        '''Wait for instrument to complete operation'''
        return self.resource.write('*WAI')

    def isOpComplete(self):
        '''Returns 1 when command is completed, 0 otherwise'''
        return int(self.resource.query('*OPC?'))

    def close(self):
        try:
            self.resource.close()
        except:
            pass
        

    
class ESW(BaseInstrument):
    def __init__(self, *args, **kwargs):
        return super().__init__(*args, **kwargs)

    def preset(self):
        '''Preset selection button'''
        self.resource.write('SYST:PRES')
        self.displayOn()
        return self.isOpComplete()

    def displayOn(self):
        self.resource.write('SYST:DISP:UPD ON')

    def instrumentMode(self, mode):
        '''Modes: SAN -> Spectrum Analyzer
                  REC -> EMI Test Receiver
        '''
        self.resource.write(f'INST:SEL {mode}')
        return self.isOpComplete()

    def setSweepMode(self, n, mode):
        ''' Options: on -> Continuous sweep (Default)
                     off -> Single sweep
            Returns 1 on success
            Example usage: 
                esw = ESW()
                esw.sweep(2, 'off')  # Sets single sweep mode
        '''
        self.resource.write(f'INIT{n}:CONT {mode.upper()}')
        return self.isOpComplete()

    def setSweepCount(self, count):
        ''' Options: count -> number of sweeps to perform if not continuous
            Returns 1 on success
            Example usage: 
                esw = ESW()
                esw.setSweepCount(20)
        '''
        self.resource.write(f'SWE:COUN {count}')
        if self.getSweepCount() == count:
            if self.log:
                print(f'Sweep count: {count}')
            return True
        else:
            if self.log:
                print(f'Error: Sweep count not set to {count}')
            return False

    def getSweepCount(self):
        return int(self.resource.query('SWE:COUN?'))

    def setSweepPoints(self, points):
        self.resource.write(f'SWE:POIN {points}')

    def getSweepPoints(self):
        return self.resource.query('SWE:POIN?')

    def setRbw(self, rbw, units):
        ''' Options: rbw -> numerical value to set resolution bandwidth
                     units -> frequency units to use
            Returns 1 on success
            Example usage:
                esw = ESW()
                esw.setRbw(1, 'MHz')  # Sets RBW to 1MHz
        '''
        self.resource.write(f'BAND {rbw}{units.upper()}')
        return self.isOpComplete()

    def setVbw(self, vbw, units):
        ''' Options: vbw -> numerical value to set resolution bandwidth
                     units -> frequency units to use
            Returns 1 on success
            Example usage:
                esw = ESW()
                esw.setVbw(1, 'MHz')  # Sets VBW to 1MHz
        '''
        self.resource.write(f'BAND:VID {vbw}{units.upper()}')
        return self.isOpComplete()

    def setFrequencyCenter(self, frequency, units):
        ''' Options: frequency -> numerical value for frequency
                     units -> frequency units to use
            Returns 1 on success
            Example usage:
                esw = ESW()
                esw.setFrequencyCenter(1, 'MHz')
        '''
        self.resource.write(f'SENS:FREQ:CENT {frequency}{units.upper()}')
        return self.isOpComplete()

    def setFrequencyStart(self, frequency, units):
        ''' Options: frequency -> numerical value for frequency
                     units -> frequency units to use
            Returns 1 on success
            Example usage:
                esw = ESW()
                esw.setFrequencyStart(1, 'MHz')
        '''
        self.resource.write(f'SENS:FREQ:STAR {frequency}{units.upper()}')
        return self.isOpComplete()

    def setFrequencyStop(self, frequency, units):
        ''' Options: frequency -> numerical value for frequency
                     units -> frequency units to use
            Returns 1 on success
            Example usage:
                esw = ESW()
                esw.setFrequencyStop(1, 'MHz')
        '''
        self.resource.write(f'SENS:FREQ:STOP {frequency}{units.upper()}')
        return self.isOpComplete()

    def getFrequencyCenter(self):
        ''' Returns analyzer center frequency
            Example usage:
                esw = ESW()
                esw.getFrequencyCenter()
        '''
        return self.resource.query('SENS:FREQ:CENT?')

    def getFrequencyStart(self):
        return int(self.resource.query('SENS:FREQ:START?')) / 1000000

    def getFrequencyStop(self):
        return int(self.resource.query('SENS:FREQ:STOP?')) / 1000000

    def setTraceMode(self, trace, mode):
        ''' Options: trace -> int value 1-6
                     mode -> AVERage
                             BLANk
                             MAXHold
                             MINHold
                             TRD
                             VIEW
                             WRIT
            Example usage:
                esw = ESW()
                # Set Trace 1 to Max Hold
                esw.setTraceMode(1, 'MAXH')
        '''
        self.resource.write(f'DISP:TRAC{trace}:MODE {mode}'.upper())
        return self.isOpComplete()

    def getTraceMode(self, trace):
        ''' Returns specified trace (1-6) mode
        '''
        return self.resource.query(f'DISP:TRAC{trace}:MODE?')

    def setDetector(self, trace, mode):
        ''' Options: trace -> int value 1-6
                     mode -> AVERage
                             CAVerage
                             CRMS
                             NEGative
                             POSitive
                             QPEak
                             RMS
            Example usage:
                esw = ESW()
                # Set Trace 1 detector to average
                esw.setDetector(1, 'AVER')
        '''
        self.resource.write(f'DET{trace} {mode}'.upper())
        return self.isOpComplete()

    def getDetector(self, trace):
        ''' Returns specified trace (1-6) detector
        '''
        return self.resource.query(f'DET{trace}?')

    def startScan(self):
        self.resource.write('INIT2;*OPC?')
        return self.isOpComplete()

    def readTrace(self, n, delay=None):
        ''' Returns pandas dataframe of Frequency (MHz), Amplitude (dBuV)
        '''
        pd.options.display.float_format = '{:.2f}'.format
        sweepPoints = self.getSweepPoints()
        self.resource.write('FORM REAL, 32')
        data = self.resource.query_binary_values(f'TRAC:DATA? TRACE{n}', delay=delay, data_points=sweepPoints)
        frequency = np.linspace(self.getFrequencyStart(), self.getFrequencyStop(), len(data))
        df = pd.DataFrame(data={'Frequency (MHz)': frequency, 'Amplitude (dBuV/m)': data})
        df['Amplitude (dBuV/m)'] = df['Amplitude (dBuV/m)'].astype(float)
        return df

    def autoScale(self, trace):
        self.resource.write('DISP:TRAC{}:Y:AUTO ONCE')
        return self.isOpComplete()

    def transducerOn(self, transducer):
        self.resource.write('SENS1:CORR:TRAN:SEL "{}"'.format(transducer))
        self.resource.write('CORR:TRAN ON')


class EMCenter(BaseInstrument):
    def __init__(self, *args, **kwargs):
        self.tower = 'A'
        self.turntable = 'B'
        return super().__init__(*args, **kwargs)

    def setPosition(self, device, position):
        ''' Tower values 100 to 400
            Turntable values 0 to 360
            Example:
            controller = EMCenter(connectionId=7)
            controller.setPosition(controller.tower, 150)
        '''
        self.resource.write('1{}SK {}\n'.format(device, position))

    def setAcceleration(self, device, seconds):
        ''' Seconds values 0.1 to 30.0
            Example
            controller.setAcceleration(controller.tower, 2)
        '''
        self.resource.write('1{}ACC {}\n'.format(device, seconds))

    def setSpeed(self, device, speed):
        ''' Speed integer 1 to 8 '''
        self.resource.write('1{}S{}\n'.format(device, speed))

    def getSpeed(self, device):
        return self.resource.query('1{}S?\n'.format(device))
    
    def getAcceleration(self, device):
        return self.resource.query('1{}ACC?\n'.format(device))

    def getCurrentPosition(self, device):
        return self.resource.query('1{}CP?\n'.format(device))

    def getDirection(self, device):
        return self.resource.query('1{}DIR?\n'.format(device))

    def getError(self, device):
        error = int(self.resource.query('1{}ERR?\n'.format(device)))
        if error == 1:
            print('Parameters Lost : Set at startup if the EMControl '
                'detects that previous settings have been lost.')
        if error == 2:
            print('Motor Not Moving : Indicates a device stuck condition. '
                'The controller automatically generates a STOP condition to '
                'protect the motor.')
        if error == 3:
            print('Motor Not Stopping : Indicates that the device failed to '
                'stop moving when commanded.')
        if error == 4:
            print('Moving Wrong Direction : Indicates that the device '
                'moved in the opposite direction of than commanded.')
        if error == 5:
            print('Hard Limit Hit : Indicates that the device is unable to '
                'move because it is at a hardware limit.')
        if error == 6:
            print('Polarization Limit Violation : Indicates that the tower '
                'was told to change polarization while it was outside the '
                'position limits specified for the new polarization.')
        if error == 7:
            print('Communication Lost : Indicates that the controller is '
                'unable to communicate with the device over the '
                'fiber optic link.')
        if error == 8:
            print(' Flotation Violation : Indicates that the air flotation '
                'turntable was told to turn flotation off while it was moving')
        if error == 9:
            print('Encoder Failure : Indicates that the EMControl has '
                'detected device encoder behavior consistent with a fault in the '
                'encoder, its wiring, or connections.')
        return error

    def getAntennaPolarity(self):
        polarity = int(self.resource.query('1AP?\n'))
        if polarity:
            return 'H'
        else:
            return 'V'
  
    def setPolarity(self, polarity):
        ''' Polarity = V or H '''
        self.resource.write('1AP{}\n'.format(polarity))

    def clearStatus(self, device):
        self.resource.write('1{}*CLS\n'.format(device))

    def isOpComplete(self, device):
        ''' Returns 1 if in motion'''
        return int(self.resource.query('1{}*OPC?\n'.format(device)))

    def wait(self, device):
        self.resource.write('1{}*WAI\n'.format(device))

def faraday_scan():
    esw = ESW(connectionType='GPIB', connectionId=20, log=True)
    esw.preset()
    esw.setTraceMode(1, 'MAXH')
    esw.setDetector(1, 'QPE')
    esw.setSweepMode(2, 'OFF')
    esw.setSweepCount(1)
    esw.startScan()
    return esw.readTrace()

if __name__ == '__main__':
    esw = ESW(connectionType='TCPIP', connectionId='10.0.0.10', log=True)
    esw.establishConnection()
    trace = esw.readTrace(1)
    print(trace)

