import os, csv

import numpy as np
import pandas as pd

from pyqtgraph.Qt import QtGui

from graphysio import utils
from graphysio.dialogs import DlgPeriodExport

class TsExporter():
    periodfields = ['patient', 'begin', 'end', 'periodid', 'comment']

    def __init__(self, parent):
        self.parent = parent
        self.viewbox = parent.vb
        self.plotdata = parent.plotdata
        self.dircache = parent.plotdata.folder
        self.patientcache = parent.plotdata.name

    def seriestocsv(self):
        filename = "{}-subset.csv".format(self.patientcache)
        defaultpath = os.path.join(self.dircache, filename)
        filepath = QtGui.QFileDialog.getSaveFileName(caption = "Export to",
                                                     filter  = "CSV files (*.csv *.dat)",
                                                     directory = defaultpath)
        # PyQt5 API change
        if type(filepath) is not str:
            filepath = filepath[0]

        if not filepath:
            return
        self.dircache = os.path.dirname(filepath)
        xmin, xmax = self.parent.vbrange
        data = self.plotdata.data.ix[xmin:xmax]
        series = [curve.series for curve in self.parent.curves.values()]
        data = pd.concat(series, axis=1).sort_index()
        data['datetime'] = pd.to_datetime(data.index, unit = 'ns')
        data.to_csv(filepath, date_format="%Y-%m-%d %H:%M:%S.%f")

    def periodstocsv(self):
        xmin, xmax = self.parent.vbrange
        dlg = DlgPeriodExport(begin   = xmin,
                              end     = xmax,
                              patient = self.patientcache,
                              directory = self.dircache)
        if not dlg.exec_():
            return
        self.patientcache = dlg.patient
        self.dircache = os.path.dirname(dlg.filepath)

        if os.path.exists(dlg.filepath):
            fileappend = True
        else:
            fileappend = False

        with open(dlg.filepath, 'a', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.periodfields, quoting=csv.QUOTE_MINIMAL)
            if not fileappend: writer.writeheader()
            writer.writerow({'patient'  : dlg.patient,
                             'begin'    : xmin,
                             'end'      : xmax,
                             'periodid' : dlg.periodname,
                             'comment'  : dlg.comment})

    def cyclepointstocsv(self):
        filename = "{}-feet.csv".format(self.patientcache)
        defaultpath = os.path.join(self.dircache, filename)
        filepath = QtGui.QFileDialog.getSaveFileName(caption = "Export to",
                                                     filter  = "CSV files (*.csv *.dat)",
                                                     directory = defaultpath)
        # PyQt5 API change
        if type(filepath) is not str:
            filepath = filepath[0]

        if not filepath: return
        self.dircache = os.path.dirname(filepath)
        feetitems = self.parent.feetitems.values()
        feetidx = [pd.Series(item.feet.index) for item in feetitems]
        feetnames = [item.feet.name for item in feetitems]
        df = pd.concat(feetidx, axis=1, keys=feetnames)
        df.to_csv(filepath, date_format="%Y-%m-%d %H:%M:%S.%f")

class PuExporter():
    def __init__(self, parent):
        self.parent = parent
        self.basename = parent.plotdata.name
        self.outdir = None

    def exportloops(self):
        outdirtmp = QtGui.QFileDialog.getExistingDirectory(caption = "Export to",
                                                             directory = self.parent.plotdata.folder)
        if outdirtmp:
            self.outdir = outdirtmp
        self.writetable()
        self.writeloops()

    def writetable(self):
        if self.outdir is None:
            return
        data = []
        for loop in self.parent.loops:
            alpha, beta, gamma = loop.angles
            tmpdict = {'alpha' : alpha, 'beta' : beta, 'gamma' : gamma}
            data.append(tmpdict)
        df = pd.DataFrame(data)
        filename = "{}-loopdata.csv".format(self.basename)
        outfile = os.path.join(self.outdir, filename)
        df.to_csv(outfile)

    def writeloops(self):
        if self.outdir is None:
            return
        for n, loop in enumerate(self.parent.loops):
            df = pd.DataFrame({'u' : loop.u, 'p' : loop.p})
            filename = "{}-{}.csv".format(self.basename, n)
            outfile = os.path.join(self.outdir, filename)
            df.to_csv(outfile)
