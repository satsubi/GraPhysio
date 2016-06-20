import sys,csv,os

import pandas as pd
import numpy as np

from PyQt4 import QtGui,QtCore
from PyQt4.QtCore import Qt

import plotwidget

from newplot_ui    import Ui_NewPlot
from mainwindow_ui import Ui_MainWindow

class MainUi(QtGui.QMainWindow, Ui_MainWindow):
    hasdata  = QtCore.pyqtSignal(object)
    haserror = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super(MainUi, self).__init__(parent=parent)
        self.setupUi(self)

        self.tabWidget.tabCloseRequested.connect(self.closeTab)

        self.menuFile.addAction('&New Plot', self.requestNewPlot, Qt.CTRL + Qt.Key_N)
        self.menuFile.addSeparator()
        self.menuFile.addAction('&Quit', self.fileQuit, Qt.CTRL + Qt.Key_Q)

        self.menuExport.addAction('&Series to CSV', self.exportCsv)
        self.menuExport.addAction('&Time info to CSV', self.exportPeriod)

        self.hasdata.connect(self.createNewPlotWithData)
        self.haserror.connect(self.displayError)

    def requestNewPlot(self):
        dlgNewplot = DlgNewPlot(parent = self)
        if not dlgNewplot.exec_(): return
        plotdescr = dlgNewplot.result
        self.statusBar.showMessage("Loading... {}...".format(plotdescr.name))

        reader = Reader(self, plotdescr)
        QtCore.QThreadPool.globalInstance().start(reader)

    def createNewPlotWithData(self, plotdescr):
        plotframe = plotwidget.PlotFrame(self)
        plotframe.addPlot(plotdescr)
        tabindex = self.tabWidget.addTab(plotframe, plotdescr.name)
        self.tabWidget.setCurrentIndex(tabindex)
        self.statusBar.showMessage("Loading... done")

    def exportCsv(self):
        i = self.tabWidget.currentIndex()
        if i < 0: return
        plotwidget = self.tabWidget.widget(i)
        plotwidget.exporter.tocsv()

    def exportPeriod(self):
        i = self.tabWidget.currentIndex()
        if i < 0: return
        plotwidget = self.tabWidget.widget(i)
        plotwidget.exporter.toperiodcsv()

    def fileQuit(self):
        self.close()

    def closeTab(self, i):
        w = self.tabWidget.widget(i)
        self.tabWidget.removeTab(i)
        w.close()
        w.deleteLater()
        del w

    def displayError(self, errmsg):
        msgbox = QtGui.QMessageBox()
        msgbox.setWindowTitle("Error creating plot")
        msgbox.setText(str(errmsg))
        msgbox.setStandardButtons(QtGui.QMessageBox.Ok)
        msgbox.setIcon(QtGui.QMessageBox.Critical)
        msgbox.exec_()


class Reader(QtCore.QRunnable):
    def __init__(self, parent, plotdescr):
        super(Reader, self).__init__()
        self._parent = parent
        self._plotdescr = plotdescr

    def run(self):
        try:
            data = self.getdata()
        except ValueError as e:
            self._parent.haserror.emit(str(e))
        else:
            self._plotdescr.data = data
            self._parent.hasdata.emit(self._plotdescr)

    def getdata(self):
        if self._plotdescr.loadall:
            # usecols = None loads all columns
            usecols = None
        else:
            usecols = self._plotdescr.fields
        data = pd.read_csv(self._plotdescr.filename,
                           sep     = self._plotdescr.seperator,
                           usecols = usecols,
                           decimal = self._plotdescr.decimal,
                           index_col = False,
                           encoding = 'latin1',
                           engine  = 'c')
        if self._plotdescr.xisdate:
            # Convert datetime to int64 so pyqtgraph can handle it.
            if self._plotdescr.isunixtime:
                data['nsdatetime'] = pd.to_datetime(data[self._plotdescr.datefield],
                                                    unit = 'ms').astype(np.int64)
            else:
                data['nsdatetime'] = pd.to_datetime(data[self._plotdescr.datefield],
                                                    format = self._plotdescr.datetime_format).astype(np.int64)
            data = data.set_index('nsdatetime')
        return data


class DlgNewPlot(QtGui.QDialog, Ui_NewPlot):
    def __init__(self, parent=None):
        super(DlgNewPlot, self).__init__(parent=parent)
        self.setupUi(self)

        self.plotdescr = plotwidget.PlotDescription()
        self.dircache = ""

        # Attach models to ListViews
        self.lstX = QtGui.QStandardItemModel()
        self.lstY = QtGui.QStandardItemModel()
        self.lstAll = QtGui.QStandardItemModel()

        self.lstVX.setModel(self.lstX)
        self.lstVY.setModel(self.lstY)
        self.lstVAll.setModel(self.lstAll)

        # Setup Field Table
        self.lstVAll.verticalHeader().hide()
        self.lstVAll.horizontalHeader().setResizeMode(QtGui.QHeaderView.ResizeToContents)

        # Connect callbacks
        self.btnBrowse.clicked.connect(self.selectFile)
        self.btnLoad.clicked.connect(self.loadCsvFields)
        self.btnOk.clicked.connect(self.loadPlot)
        self.btnCancel.clicked.connect(self.reject)
        self.btnToX.clicked.connect(self.moveToX)
        self.btnToY.clicked.connect(self.moveToY)
        self.btnRemoveX.clicked.connect(self.delFromX)
        self.btnRemoveY.clicked.connect(self.delFromY)
        self.chkUnixTime.stateChanged.connect(self.boolUnixtime)

    @property
    def result(self):
        return self.plotdescr

    # Methods / Callbacks
    def boolUnixtime(self, state):
        self.txtDateTime.setEnabled(not self.chkUnixTime.isChecked())

    def selectFile(self):
        filepath = QtGui.QFileDialog.getOpenFileName(parent = self,
                                                     caption = "Open CSV file",
                                                     directory = self.dircache)
        if not filepath: return
        self.dircache = os.path.dirname(filepath)
        self.txtFile.setText(filepath)
        # Guesstimate CSV field and decimal seperators
        delims = self.estimateDelimiters(filepath)
        self.txtSep.setEditText(delims[0])
        self.txtDecimal.setEditText(delims[1])
        self.txtDateTime.setEditText("%Y-%m-%d %H:%M:%S{}%f".format(delims[1]))

    def estimateDelimiters(self, filepath):
        with open(filepath, 'r') as csvfile:
            line1 = next(csvfile)
            line2 = next(csvfile)
            semipos = line1.find(';')
            if semipos == -1:
                seperator = ','
            else:
                seperator = ';'
            periodpos = line2.find('.')
            if periodpos == -1:
                decimal   = ','
            else:
                decimal   = '.'
        return (seperator, decimal)

    def loadCsvFields(self):
        sep = self.txtSep.currentText()
        filename = self.txtFile.text()
        fields = []
        # Use the csv module to retrieve csv fields
        for lst in [self.lstAll, self.lstX, self.lstY]: lst.clear()
        self.lstAll.setHorizontalHeaderLabels(["Field", "1st Line"])
        with open(filename, 'r') as csvfile:
            csvreader = csv.DictReader(csvfile, delimiter=sep)
            row = next(csvreader)
            for key, value in row.items():
                if key is None: continue
                keyitem = QtGui.QStandardItem(key)
                valueitem = QtGui.QStandardItem(value)
                self.lstAll.appendRow([keyitem, valueitem])
        self.lstAll.sort(0)

    def moveToX(self):
        if self.lstX.rowCount() > 0: return # Only allow one element allowed for X.
        selection = self.lstVAll.selectedIndexes()
        rowindex = selection[0].row()
        row = self.lstAll.takeRow(rowindex)
        self.itemCheckable(row, True)
        self.lstX.appendRow(row)

    def moveToY(self):
        while True:
            selection = self.lstVAll.selectedIndexes()
            if len(selection) < 1: break
            rowindex = selection[0].row()
            self.lstY.appendRow(self.lstAll.takeRow(rowindex))

    def delFromX(self):
        while True:
            selection = self.lstVX.selectedIndexes()
            if len(selection) < 1: break
            rowindex = selection[0].row()
            row = self.lstX.takeRow(rowindex)
            self.itemCheckable(row, False)
            self.lstAll.appendRow(row)

    def delFromY(self):
        while True:
            rowindexes = self.lstVY.selectedIndexes()
            if len(rowindexes) < 1: break
            row = rowindexes[0].row()
            self.lstAll.appendRow(self.lstY.takeRow(row))

    def itemCheckable(self, row, checkable):
            field = row[0]
            if checkable:
                field.setFlags(field.flags() | QtCore.Qt.ItemIsUserCheckable)
                field.setData(Qt.Checked, Qt.CheckStateRole)
            else:
                field.setFlags(field.flags() ^ QtCore.Qt.ItemIsUserCheckable)
                field.setData(None, Qt.CheckStateRole)

    def loadPlot(self):
        yRows = [i.text() for i in self.lstY.findItems("", Qt.MatchContains)]
        xRows = [i.text() for i in self.lstX.findItems("", Qt.MatchContains)]
        xState = [i.checkState() for i in self.lstX.findItems("", Qt.MatchContains)]
        for s in xState:
            self.plotdescr.xisdate = s > Qt.Unchecked
            break
        if len(xRows) > 0:
            self.plotdescr.xfield = xRows[0]
        else:
            self.plotdescr.xfield = None
        self.plotdescr.yfields = yRows
        self.plotdescr.filename = self.txtFile.text()
        self.plotdescr.seperator = self.txtSep.currentText()
        self.plotdescr.decimal = self.txtDecimal.currentText()
        self.plotdescr.datetime_format = self.txtDateTime.currentText()
        self.plotdescr.isunixtime = self.chkUnixTime.isChecked()
        self.plotdescr.loadall = self.chkLoadAll.isChecked()
        self.accept()


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)

    winmain = MainUi()
    winmain.show()

    sys.exit(app.exec_())
