import os
from enum import Enum

class FootType(Enum):
    none     = 'None'
    pressure = 'Pressure'
    velocity = 'Velocity'

class CsvRequest():
    def __init__(self, filepath  = "",
                       seperator = ",",
                       decimal   = ".",
                       dtfield  = None,
                       yfields = [],
                       datetime_format = "%Y-%m-%d %H:%M:%S,%f",
                       droplines = 0,
                       generatex = False,
                       samplerate = None):
        self.filepath = filepath
        self.seperator = seperator
        self.decimal = decimal
        self.dtfield = dtfield
        self.yfields = yfields
        self.datetime_format = datetime_format
        self.droplines = droplines
        self.generatex = generatex
        self.samplerate = samplerate

    @property
    def fields(self):
        dtfields = [] if self.dtfield is None else [self.dtfield]
        return dtfields + self.yfields

    @property
    def name(self):
        name, _ = os.path.splitext(os.path.basename(self.filepath))
        return name

    @property
    def folder(self):
        folder = os.path.dirname(self.filepath)
        return folder

class PlotData():
    def __init__(self, data = None,
                       fields = [],
                       filepath = "",
                       name = None):
        self.data = data
        self.fields = fields
        self.filepath = filepath
        self._name = name

    @property
    def name(self):
        if self._name is not None:
            name = self._name
        else:
            name, _ = os.path.splitext(os.path.basename(self.filepath))
        return name

    @property
    def folder(self):
        folder = os.path.dirname(self.filepath)
        return folder
