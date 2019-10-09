from matplotlib.backends.backend_qt5agg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
from PyQt5.QtWidgets import QWidget, QVBoxLayout

class MplWidget(QWidget):
    def __init__(self, centralWidget):
        super(MplWidget, self).__init__()
        layout = QVBoxLayout()
        self.figure = Figure()
        self.mplPlot = self.figure.add_subplot(111)
        self.mplPlot.grid()
        self.canvas = FigureCanvas(self.figure)
        toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(self.canvas)
        layout.addWidget(toolbar)
        self.setLayout(layout)

    def setAxisLabels(self, x=None, y=None):
        if x:
            self.mplPlot.set_xlabel(x)
        if y:
            self.mplPlot.set_ylabel(y)

    def setAutoScale(self, on=True):
        self.mplPlot.set_autoscalex_on(on)
        self.mplPlot.set_autoscaley_on(on)

    def drawPlot(self):
        self.mplPlot.legend(loc=0, framealpha=0.5, fontsize='small')
        self.canvas.draw()

    def clearPlot(self):
        self.mplPlot.clear()
        self.mplPlot.grid()
        self.drawPlot()

    def graph(self, x, y, label, xLabel=None, yLabel=None):
        line, = self.mplPlot.plot(x, y, label=label)
        self.setAxisLabels(x=xLabel, y=yLabel)
        self.drawPlot()
        return line
