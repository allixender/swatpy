# SWAT_ReadOut.py


""" Christoph Hecht, 24.04.2008

    Instances of "OutputFileManipulator" subclasses readout selectable
    output values from either "output.rch", "output.sub" or "output.hru".
    These are stored seperately and/or aggregated (e. g. to get basin wide
    lateral flows). In the latter case (only useful for ".sub" and ".hru")
    values are multiplied with subbasin or HRU size respectivly before
    summation. The resulting values are therefore volumes instead of
    heights. The individual values and/or the corresponding statistics
    are written in seperate files.
    Attention: To account for SWATs warm up time, an arbitrary number of
    days can be ignored for statistical calculations ("daysSkip"). But the
    number of individual values in output files will remain unchanged.

"""

import os
import re
import numpy as np

"""
__init__        subclass loads corresponding file, afterwards output is read in;
                calls readAreaSizes;
                calls readValues;
                calls.write

readColumns     column positions of the output variables, derived from the
                header line, so that files with a reduced selection of printed
                variables (file.cio "output variables" section) are read correctly

readAreaSizes   sizes of selected subbasins or HRUs (also for reaches,
                but shouldn't be used) are returned as a dictionary

readValues      time series of selected output parameters and subbasins or HRUs
                are returned as a dictionary. Each key (parameter) refers to
                a subkey (subbasin or HRU), which on his part refers to a
                list of output values. Summary rows (yearly totals in monthly
                output, the closing average-annual row) are dropped, see keepRow

write           writes output values and/or corresponding statistics in a file.
                File name describes source file and contained parameter.
                Furthermore subbasin/HRU and aggregation mode ("SUM") respectivly;
                uses "calculateStatistics"

calculateStatistics     to date: mean, median, variation,
                        autocorrelation coefficient (lag = 1)


subclasses just have to be called once after each SWAT run.

"""

_LABEL_RE = re.compile(r"[A-Z0-9_#\-]+")


def keepRow(mon, iprint):
    # the MON column holds the month (monthly), julian day (daily) or year (yearly print);
    # monthly output additionally has one row per year with MON=<year> and every
    # output ends with an average-annual row where MON is the number of years ("3.0")
    mon = mon.strip()
    if "." in mon:
        return False
    try:
        mon = int(mon)
    except ValueError:
        return False
    if iprint == "month" or iprint == 0:
        return 1 <= mon <= 12
    if iprint == "day" or iprint == 1:
        return 1 <= mon <= 366
    return True


class OutputFileManipulator(object):

    # column layout of the output files (0-based python slices), verified with SWAT2012 rev 637:
    # "headerRow" and "firstRow" are 1-based line numbers, value columns start at "valueStart"
    # and are "valueWidth" wide each, their names are read from the header line
    outInfo = {}
    variables = ()

    # calls everthing else
    # method=("sum", "indi" or "sum & indi" or "skip"; onlyStatistics=(True or False)
    def __init__(self, outList, areasList, method, onlyStatistics, daysSkip, working_dir, iprint='day', stats_dir=None, encoding='latin-1'):
        # set file and folder paths
        self.working_dir = working_dir
        self.stats_dir = stats_dir
        self.iprint = iprint
        self.file_enc = encoding
        # read from input file
        self.readFile()
        # calculate stats
        self.areaSizes = self.readAreaSizes(areasList)
        self.outValues = self.readValues(outList, areasList)

        # write stats out
        if not method == 'skip':
            self.write(method, onlyStatistics, daysSkip)

    def readFile(self):
        with open(os.path.join(self.working_dir, "output" + self.outInfo["type"]), "r", encoding=self.file_enc) as f:
            self.textOld = f.readlines()
        self.columns = self.readColumns()

    def readColumns(self):
        header = self.textOld[self.outInfo["headerRow"] - 1].rstrip("\r\n")
        width = self.outInfo["valueWidth"]
        # some data fields are wider than their header label, the following
        # data columns are then shifted against the header
        widen = self.outInfo.get("widen", {})
        columns = {}
        offset = 0
        for col1 in range(self.outInfo["valueStart"], len(header), width):
            name = self.labelToName(header[col1:col1 + width])
            extra = widen.get(name, 0)
            if name and name not in columns:
                columns[name] = (col1 + offset, col1 + offset + width + extra)
            offset += extra
        return columns

    def labelToName(self, label):
        # header labels are the variable name plus unit, e.g. "FLOW_OUTcms", "LAT Q(mm)"
        label = label.strip().replace(" ", "_")
        if not label:
            return None
        known = [name for name in self.variables if label.upper().startswith(name)]
        if known:
            return max(known, key=len)
        match = _LABEL_RE.match(label)
        if match:
            return match.group(0).rstrip("_")
        return label

    def dataRows(self):
        col1, col2 = self.outInfo["area"]
        mon1, mon2 = self.outInfo["MON"]
        for textRow in self.textOld[self.outInfo["firstRow"] - 1:]:
            if not textRow.strip():
                continue
            if not keepRow(textRow[mon1:mon2], self.iprint):
                continue
            yield int(textRow[col1:col2]), textRow

    def readAreaSizes(self, areasList):
        areaSizes = {}
        for area in areasList:
            areaSizes[area] = None
        col1, col2 = self.outInfo["areaSize"]
        for area, textRow in self.dataRows():
            if area in areaSizes:
                if areaSizes[area] is None:
                    areaSizes[area] = float(textRow[col1:col2])
                else:
                    break
        return areaSizes

    def readValues(self, outList, areasList):
        for outName in outList:
            if outName not in self.columns:
                raise KeyError(f"{outName} not in output{self.outInfo['type']} (available: {list(self.columns)})")
        outValues = {}
        for outName in outList:
            outValues[outName] = {}
            for area in areasList:
                outValues[outName][area] = []
        for area, textRow in self.dataRows():
            if area in self.areaSizes:
                for outName in outValues:
                    col1, col2 = self.columns[outName]
                    outValues[outName][area].append(float(textRow[col1:col2]))
        return outValues

    def write(self, method, onlyStatistics, daysSkip):

        outdir = self.working_dir
        if not self.stats_dir is None:
            outdir = self.stats_dir

        # write "individual" files
        if method == "sum & indi" or method == "indi":
            for outName in self.outValues:
                for area in self.outValues[outName]:
                    # write statistics
                    numValues = np.array(self.outValues[outName][area])
                    outText = self.calculateStatistics(numValues, daysSkip)
                    with open(os.path.join(outdir,
                        "SWAT_readout_" + str(outName) + "_" + "%4.4i" % area + "_statistics" + self.outInfo["type"]), "a", encoding=self.file_enc) as F:
                        F.writelines(outText)
                    # write values
                    if onlyStatistics == False:
                        outText = []
                        for value in self.outValues[outName][area]:
                            outText.append("%.3E" % value + " ")
                        outText[len(outText) - 1] = outText[len(outText) - 1].replace(" ", "\n")
                        with open(os.path.join(outdir, "SWAT_readout_" + str(
                            outName) + "_" + "%4.4i" % area + self.outInfo["type"]), "a", encoding=self.file_enc) as F:
                            F.writelines(outText)

        # write "summed" files
        if method == "sum & indi" or method == "sum":
            key = next(iter(self.outValues))
            subkey = next(iter(self.outValues[key]))
            length = len(self.outValues[key][subkey])
            for outName in self.outValues:
                # do summation
                sumValues = np.zeros(length, float)
                for area in self.outValues[outName]:
                    numValues = np.array(self.outValues[outName][area])
                    numValues *= (self.areaSizes[area] * 1000.0 / 24 / 60 / 60)  # mm/d on km2 to cubic metres per second
                    sumValues += numValues
                # write statistics
                outText = self.calculateStatistics(sumValues, daysSkip)
                with open(os.path.join(outdir, "SWAT_readout_" + str(
                    outName) + "_SUMstatistics" + self.outInfo["type"]), "a", encoding=self.file_enc) as F:
                    F.writelines(outText)
                # write values
                if onlyStatistics == False:
                    outText = []
                    for value in sumValues:
                        outText.append("%.3E" % value + " ")
                    outText[len(outText) - 1] = outText[len(outText) - 1].replace(" ", "\n")
                    with open(os.path.join(outdir, "SWAT_readout_" + str(
                        outName) + "_SUM" + self.outInfo["type"]), "a", encoding=self.file_enc) as F:
                        F.writelines(outText)

    def calculateStatistics(self, numValues, daysSkip):
        nV = numValues[daysSkip:]
        outText = []
        outText.append("%.3E" % np.mean(nV) + " ")  # mean
        outText.append("%.3E" % np.median(nV) + " ")  # median
        outText.append("%.3E" % np.var(nV) + "\n")  # variation
        # outText.append("%.3E"%corrcoef(nV[:-1],nV[1:])[0,1] + " ") # autocorrelation, lag=1
        # if outText[len(outText)-1] == "-1.#IOE+000 ":
        #    outText[len(outText)-1] = "NA "
        # outText[len(outText)-1] = outText[len(outText)-1].replace(" ", "\n")
        return outText


class rchOutputManipulator(OutputFileManipulator):
    # REACH    1        0     1  0.8782E+01  0.9536E-01 ...
    outInfo = {"type": ".rch",
               "headerRow": 9,
               "firstRow": 10,
               "area": (5, 10),
               "GIS": (10, 19),
               "MON": (19, 25),
               "areaSize": (25, 37),
               "valueStart": 37,
               "valueWidth": 12}

    variables = ("FLOW_IN", "FLOW_OUT", "EVAP", "TLOSS", "SED_IN", "SED_OUT", "SEDCONC",
                 "ORGN_IN", "ORGN_OUT", "ORGP_IN", "ORGP_OUT", "NO3_IN", "NO3_OUT",
                 "NH4_IN", "NH4_OUT", "NO2_IN", "NO2_OUT", "MINP_IN", "MINP_OUT",
                 "CHLA_IN", "CHLA_OUT", "CBOD_IN", "CBOD_OUT", "DISOX_IN", "DISOX_OUT",
                 "SOLPST_IN", "SOLPST_OUT", "SORPST_IN", "SORPST_OUT", "REACTPST", "VOLPST",
                 "SETTLPST", "RESUSP_PST", "DIFFUSEPST", "REACBEDPST", "BURYPST", "BED_PST",
                 "BACTP_OUT", "BACTLP_OUT", "CMETAL#1", "CMETAL#2", "CMETAL#3",
                 "TOT_N", "TOT_P", "NO3CONC", "WTMP")

    def __init__(self, outList, areasList, method, onlyStatistics, daysSkip, working_dir, iprint='day', stats_dir=None, encoding='latin-1'):
        OutputFileManipulator.__init__(self, outList, areasList, method, onlyStatistics, daysSkip, working_dir, iprint, stats_dir, encoding)


class subOutputManipulator(OutputFileManipulator):
    # BIGSUB   1        0    1.87822E+01    53.500 ...  (MON i4 and AREA e10.5 touch)
    outInfo = {"type": ".sub",
               "headerRow": 9,
               "firstRow": 10,
               "area": (6, 10),
               "GIS": (10, 19),
               "MON": (19, 24),
               "areaSize": (24, 34),
               "valueStart": 34,
               "valueWidth": 10,
               "widen": {"CHOLA": 1}}

    variables = ("PRECIP", "SNOMELT", "PET", "ET", "SW", "PERC", "SURQ", "GW_Q", "WYLD",
                 "SYLD", "ORGN", "ORGP", "NSURQ", "SOLP", "SEDP", "LAT_Q", "LATNO3",
                 "GWNO3", "CHOLA", "CBODU", "DOXQ", "TNO3")

    def __init__(self, outList, areasList, method, onlyStatistics, daysSkip, working_dir, iprint='day', stats_dir=None, encoding='latin-1'):
        OutputFileManipulator.__init__(self, outList, areasList, method, onlyStatistics, daysSkip, working_dir, iprint, stats_dir, encoding)


class hruOutputManipulator(OutputFileManipulator):
    # PNUT    1 000010001    1    0    1.18540E+00    53.500 ...
    outInfo = {"type": ".hru",
               "headerRow": 9,
               "firstRow": 10,
               "LULC": (0, 4),
               "area": (4, 9),
               "GIS": (10, 19),
               "SUB": (19, 24),
               "MGT": (24, 29),
               "MON": (29, 34),
               "areaSize": (34, 44),
               "valueStart": 44,
               "valueWidth": 10,
               "widen": {"BACTP": 1, "BACTLP": 1}}

    variables = ("PRECIP", "SNOFALL", "SNOMELT", "IRR", "PET", "ET", "SW_INIT", "SW_END",
                 "PERC", "GW_RCHG", "DA_RCHG", "REVAP", "SA_IRR", "DA_IRR", "SA_ST", "DA_ST",
                 "SURQ_GEN", "SURQ_CNT", "TLOSS", "LATQ", "LATQGEN", "LATQCNT", "GW_Q", "WYLD", "DAILYCN",
                 "TMP_AV", "TMP_MX", "TMP_MN", "SOL_TMP", "SOLAR", "SYLD", "USLE",
                 "N_APP", "P_APP", "NAUTO", "PAUTO", "NGRZ", "PGRZ", "NCFRT", "PCFRT",
                 "NRAIN", "NFIX", "F-MN", "A-MN", "A-SN", "F-MP", "AO-LP", "L-AP", "A-SP",
                 "DNIT", "NUP", "PUP", "ORGN", "ORGP", "SEDP", "NSURQ", "NLATQ", "NO3L",
                 "NO3GW", "SOLP", "P_GW", "W_STRS", "TMP_STRS", "N_STRS", "P_STRS",
                 "BIOM", "LAI", "YLD", "BACTP", "BACTLP", "WTAB_CLI", "WTAB_SOL", "SNO",
                 "CMUP", "CMTOT", "QTILE", "TNO3", "LNO3", "GW_Q_D")

    def __init__(self, outList, areasList, method, onlyStatistics, daysSkip, working_dir, iprint='day', stats_dir=None, encoding='latin-1'):
        OutputFileManipulator.__init__(self, outList, areasList, method, onlyStatistics, daysSkip, working_dir, iprint, stats_dir, encoding)


class efficiency(rchOutputManipulator):

    def __init__(self, output, area, observed, fileColumn, daysSkip, working_dir, iprint='day', nodata=-9999, encoding='latin-1'):
        self.area = area
        self.daysSkip = daysSkip
        self.output = output
        self.working_dir = working_dir
        self.iprint = iprint
        self.file_enc = encoding

        with open(observed, "r", encoding=encoding) as f:
            lines = f.readlines()
        measured = []
        for i in lines:
            if i.strip():
                measured.append(i.split(";")[fileColumn - 1])
        self.obs = np.array([float(i) for i in measured[daysSkip:]])

        self.obs_masked = np.ma.masked_where(self.obs == nodata, self.obs)
        self.obsMean = np.mean(self.obs_masked)

        self.readFile()
        self.areaSizes = self.readAreaSizes([self.area])
        self.outValues = self.readValues([self.output], [self.area])[self.output][self.area]

    def nash(self):
        sim = np.array([float(i) for i in self.outValues[self.daysSkip:]])

        # np.ma.sum skips nodata (masked) observations, builtin sum would mask the result
        return float(1 - np.ma.sum((self.obs_masked - sim) ** 2) / np.ma.sum((self.obs_masked - self.obsMean) ** 2))

    def agr(self):
        sim = np.array([float(i) for i in self.outValues[self.daysSkip:]])

        return float(1 - np.ma.sum((self.obs_masked - sim) ** 2) / np.ma.sum((abs(sim - self.obsMean) + abs(self.obs_masked - self.obsMean)) ** 2))


class fluxes(subOutputManipulator):

    def __init__(self, output, areasList, daysSkip, working_dir, iprint='day', stats_dir=None, encoding='latin-1'):
        self.working_dir = working_dir
        self.iprint = iprint
        self.file_enc = encoding
        self.readFile()
        self.areaSizes = self.readAreaSizes(areasList)
        outValues = self.readValues([output], areasList)
        self.sumSim = np.zeros(len(outValues[output][areasList[0]][daysSkip:]), float)
        for area in self.areaSizes:
            sim = np.array([float(i) for i in outValues[output][area][daysSkip:]])
            sim *= (self.areaSizes[area] * 1000.0 / 24 / 60 / 60)
            self.sumSim += sim

    def result(self):
        return (np.mean(self.sumSim))
