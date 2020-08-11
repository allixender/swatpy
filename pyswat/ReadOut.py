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
import numpy as np

"""
__init__        subclass loads corresponding file, afterwards output is read in;
                calls readAreaSizes;
                calls readValues;
                calls.write

readAreaSizes   sizes of selected subbasins or HRUs (also for reaches,
                but shouldn't be used) are returned as a dictionary

readValues      time series of selected output parameters and subbasins or HRUs
                are returned as a dictionary. Each key (parameter) refers to
                a subkey (subbasin or HRU), which on his part refers to a
                list of output values

write           writes output values and/or corresponding statistics in a file.
                File name describes source file and contained parameter.
                Furthermore subbasin/HRU and aggregation mode ("SUM") respectivly;
                uses "calculateStatistics"

calculateStatistics     to date: mean, median, variation,
                        autocorrelation coefficient (lag = 1)


subclasses just have to be called once after each SWAT run.

"""


class OutputFileManipulator(object):

    # calls everthing else (open inputfile command in subclass)
    # method=("sum", "indi" or "sum & indi" or "skip"; onlyStatistics=(True or False)
    def __init__(self, outList, areasList, method, onlyStatistics, daysSkip, working_dir, iprint='day', stats_dir=None, encoding='latin-1'):
        # set file and folder paths
        self.working_dir = working_dir
        self.stats_dir=stats_dir
        self.iprint=iprint
        self.file_enc = encoding
        # read from input file
        self.textOld = self.inputFile.readlines()
        self.inputFile.close()
        # calculate stats
        self.areaSizes = self.readAreaSizes(areasList)
        self.outValues = self.readValues(outList, areasList)

        if self.iprint == 'month' or self.iprint == 0:
            for outName in outList:
                for area in areasList:
                    new_list = []
                    for i in range(len(self.outValues[outName][area])-1):
                        if (i+1) % 12 == 0 and i+1 > 0:
                            pass
                        else:
                            new_list.append(self.outValues[outName][area][i])
                    self.outValues[outName][area] = new_list

        # write stats out
        if not method == 'skip':
            self.write(method, onlyStatistics, daysSkip)

    def readAreaSizes(self, areasList):
        areaSizes = {}
        for area in areasList:
            areaSizes[area] = None
        row = self.outInfo["firstRow"] - 1
        for textRow in self.textOld[row:]:
            col1, col2 = self.outInfo["area"]
            area = int(textRow[col1:col2])
            if area in areaSizes:
                col1, col2 = self.outInfo["areaSize"]
                if areaSizes[area] == None:
                    areaSizes[area] = float(textRow[col1:col2])
                else:
                    break
        return areaSizes

    def readValues(self, outList, areasList):
        outValues = {}
        for outName in outList:
            outValues[outName] = {}
            for area in areasList:
                outValues[outName][area] = []
        row = self.outInfo["firstRow"] - 1
        for textRow in self.textOld[row:]:
            col1, col2 = self.outInfo["area"]
            area = int(textRow[col1:col2])
            if area in self.areaSizes:
                for outName in outValues:
                    col1, col2 = self.outInfo[outName]
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
                    F = open(os.path.join(outdir,
                        "SWAT_readout_" + str(outName) + "_" + "%4.4i" % area + "_statistics" + self.outInfo["type"]), "a", encoding=self.file_enc)
                    F.writelines(outText)
                    F.close()
                    # write values
                    if onlyStatistics == False:
                        outText = []
                        for value in self.outValues[outName][area]:
                            outText.append("%.3E" % value + " ")
                        outText[len(outText) - 1] = outText[len(outText) - 1].replace(" ", "\n")
                        F = open(os.path.join(outdir,"SWAT_readout_" + str(
                            outName) + "_" + "%4.4i" % area + self.outInfo["type"]), "a", encoding=self.file_enc)
                        F.writelines(outText)
                        F.close()

        # write "summed" files
        if method == "sum & indi" or method == "sum":
            key = self.outValues.keys()[0]
            subkey = self.outValues[key].keys()[0]
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
                F = open(os.path.join(outdir, "SWAT_readout_" + str(
                    outName) + "_SUMstatistics" + self.outInfo["type"]), "a", encoding=self.file_enc)
                F.writelines(outText)
                F.close()
                # write values
                if onlyStatistics == False:
                    outText = []
                    for value in sumValues:
                        outText.append("%.3E" % value + " ")
                    outText[len(outText) - 1] = outText[len(outText) - 1].replace(" ", "\n")
                    F = open(os.path.join(outdir,"SWAT_readout_" + str(
                        outName) + "_SUM" + self.outInfo["type"]), "a", encoding=self.file_enc)
                    F.writelines(outText)
                    F.close()

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
    outInfo = {"type": ".rch",
               "firstRow": (10),
               "area": (7, 11),
               "RCH": (7, 11),
               "GIS": (12, 19),
               "MON" : (21, 25),
               "areaSize": (26, 37),
               "FLOW_IN": (38, 49),
               "FLOW_OUT": (50, 61),
               "EVAP": (62, 73),
               "TLOSS": (74, 85),
               "SED_IN": (86, 97),
               "SED_OUT": (98, 109),
               "SEDCONC": (110, 121),
               "ORGN_IN": (122, 133),
               "ORGN_OUT": (134, 145),
               "ORGP_IN": (146, 157),
               "ORGP_OUT": (158, 169),
               "NO3_IN": (170, 181),
               "NO3_OUT": (182, 193),
               "NH4_IN": (194, 205),
               "NH4_OUT": (206, 217),
               "NO2_IN": (218, 229),
               "NO2_OUT": (230, 241),
               "MINP_IN": (242, 253),
               "MINP_OUT": (254, 265),
               "CHLA_IN": (266, 277),
               "CHLA_OUT": (278, 289),
               "CBOD_IN": (290, 301),
               "CBOD_OUT": (302, 313),
               "DISOX_IN": (314, 325),
               "DISOX_OUT": (326, 337),
               "SOLPST_IN": (338, 349),
               "SOLPST_OUT": (350, 361),
               "SORPST_IN": (362, 373),
               "SORPST_OUT": (374, 385),
               "REACTPST": (386, 397),
               "VOLPST": (398, 409),
               "SETTLPST": (410, 421),
               "RESUSP_PST": (422, 433),
               "DIFFUSEPST": (434, 445),
               "REACBEDPST": (446, 457),
               "BURYPST": (458, 469),
               "BED_PST": (470, 481),
               "BACTP_OUT": (482, 493),
               "BACTLP_OUT": (494, 505),
               "CMETAL#1": (506, 517),
               "CMETAL#2": (518, 529),
               "CMETAL#3": (530, 541)}

    def __init__(self, outList, areasList, method, onlyStatistics, daysSkip, working_dir, iprint='day', stats_dir=None, encoding='latin-1'):
        self.inputFile = open(os.path.join(working_dir, "output.rch"), "r", encoding=encoding)
        OutputFileManipulator.__init__(self, outList, areasList, method, onlyStatistics, daysSkip, working_dir, iprint, stats_dir, encoding)


class subOutputManipulator(OutputFileManipulator):
    outInfo = {"type": ".sub",
               "firstRow": (10),
               "area": (7, 11),
               "SUB": (7, 12),
               "GIS": (13, 18),
               "MON": (19, 23),
               "areaSize": (24, 34),
               "PRECIP": (35, 44),
               "SNOMELT": (45, 54),
               "PET": (55, 64),
               "ET": (65, 74),
               "SW": (75, 84),
               "PERC": (85, 94),
               "SURQ": (95, 104),
               "GW_Q": (105, 114),
               "WYLD": (115, 124),
               "SYLD": (125, 134),
               "ORGN": (135, 144),
               "ORGP": (145, 154),
               "NSURQ": (155, 164),
               "SOLP": (165, 174),
               "SEDP": (175, 184),
               "LAT_Q": (185, 194),
               "LATNO3": (195, 204)}

    def __init__(self, outList, areasList, method, onlyStatistics, daysSkip, working_dir, iprint='day', stats_dir=None, encoding='latin-1'):
        self.inputFile = open(os.path.join(working_dir, "output.sub"), "r", encoding=encoding)
        OutputFileManipulator.__init__(self, outList, areasList, method, onlyStatistics, daysSkip, working_dir, iprint, stats_dir, encoding)


class hruOutputManipulator(OutputFileManipulator):
    outInfo = {"type": ".hru",
               "firstRow": (10),
               "area": (4, 8),
               "LULC": (0, 3),
               "HRU" : (4, 8),
               "GIS": (9, 19),
               "SUB": (20, 23),
               "MGT": (24, 28),
               "MON": (29, 33),
               "areaSize": (34, 42),
               "PRECIP": (44, 54),
               "SNOFALL": (55, 64),
               "SNOMELT": (65, 74),
               "IRR": (75, 84),
               "PET": (85, 94),
               "ET": (95, 104),
               "SW_INIT": (105, 114), # TODO: update actual fields
               "SW_END": (113, 122),
               "PERC": (123, 132),
               "GW_RCHG": (133, 142),
               "DA_RCHG": (143, 152),
               "REVAP": (153, 162),
               "SA_IRR": (163, 172),
               "DA_IRR": (173, 182),
               "SA_ST": (183, 192),
               "DA_ST": (193, 202),
               "SURQ_GEN": (203, 212),
               "SURQ_CNT": (213, 222),
               "TLOSS": (223, 232),
               "LATQ": (233, 242),
               "GW_Q": (243, 252),
               "WQLD": (253, 262),
               "DAILYCN": (263, 272),
               "TMP_AV": (273, 282),
               "TMP_MX": (283, 292),
               "TMP_MN": (293, 302),
               "SOL_TMP": (303, 312),
               "SOLAR": (313, 322),
               "SYLD": (323, 332),
               "USLE": (333, 342),
               "N_APP": (343, 352),
               "P_APP": (353, 362),
               "NAUTO": (363, 372),
               "PAUTO": (373, 382),
               "NGRZ": (383, 392),
               "PGRZ": (393, 402),
               "NCFRT": (403, 412),
               "PCFRT": (413, 422),
               "NRAIN": (423, 432),
               "NFIX": (433, 442),
               "F-MN": (443, 452),
               "A-MN": (453, 462),
               "A-SN": (463, 472),
               "F-MP": (473, 482),
               "AO-LP": (483, 492),
               "L-AP": (493, 502),
               "A-SP": (503, 512),
               "DNIT": (513, 522),
               "NUP": (523, 532),
               "PUP": (533, 542),
               "ORGN": (543, 552),
               "ORGP": (553, 562),
               "SEDP": (563, 572),
               "NSURQ": (573, 582),
               "NLATQ": (583, 592),
               "NO3L": (593, 602),
               "NO3GW": (603, 612),
               "SOLP": (613, 622),
               "P_GW": (623, 632),
               "W_STRS": (633, 642),
               "TMP-STRS": (643, 652),
               "N_STRS": (653, 662),
               "P_STRS": (663, 672),
               "BIOM": (673, 682),
               "LAI": (683, 692),
               "YLD": (693, 702),
               "BACTP": (703, 712),
               "BACTLP": (713, 722)}

    def __init__(self, outList, areasList, method, onlyStatistics, daysSkip, working_dir, stats_dir=None, encoding='latin-1'):
        self.inputFile = open(os.path.join(working_dir, "output.hru"), "r", encoding=encoding)
        OutputFileManipulator.__init__(self, outList, areasList, method, onlyStatistics, daysSkip, working_dir, stats_dir, encoding)


class efficiency(rchOutputManipulator):

    def __init__(self, output, area, observed, fileColumn, daysSkip, working_dir, iprint='day', nodata=-9999, encoding='latin-1'):
        self.area = area
        self.daysSkip = daysSkip
        self.output = output
        self.working_dir = working_dir
        self.iprint = iprint
        self.file_enc = encoding

        f = open(observed, "r", encoding=encoding)
        lines = f.readlines()
        f.close()
        measured = []
        for i in lines:
            measured.append(i.split(";")[fileColumn - 1])
        self.obs = np.array([float(i) for i in measured[daysSkip:]])

        self.obs_masked = np.ma.masked_where(self.obs == nodata, self.obs)
        self.obsMean = np.mean(self.obs_masked)

        f = open(os.path.join(self.working_dir, "output.rch"), "r", encoding=encoding)
        self.textOld = f.readlines()
        f.close()

        self.areaSizes = self.readAreaSizes([self.area])
        self.outValues = self.readValues([self.output], [self.area])

        if self.iprint == 'month' or self.iprint == 0:
            new_list = []
            for i in range(len(self.outValues[self.output][self.area])-1):
                if (i+1) % 12 == 0 and i+1 > 0:
                    pass
                else:
                    new_list.append(self.outValues[self.output][self.area][i])
            self.outValues = new_list
        else:
            self.outValues = self.outValues[self.output][self.area]
        

    def nash(self):
        # f = open(os.path.join(self.working_dir, "output.rch"), "r")
        # self.textOld = f.readlines()
        # f.close()
        
        # outValues = self.readValues([self.output], [self.area])
        # outValues = outValues[self.output][self.area]
        # outValues = self.outValues[self.output][self.area]
        sim = np.array([float(i) for i in self.outValues[self.daysSkip:]])
        
        return (1 - sum((self.obs_masked - sim) ** 2) / sum((self.obs_masked - self.obsMean) ** 2))

    def agr(self):
        # f = open(os.path.join(self.working_dir, "output.rch"), "r")
        # self.textOld = f.readlines()
        # f.close()
        # self.areaSizes = self.readAreaSizes([self.area])
        # outValues = self.readValues([self.output], [self.area])
        # outValues = outValues[self.output][self.area]
        sim = np.array([float(i) for i in self.outValues[self.daysSkip:]])

        return (1 - sum((self.obs_masked - sim) ** 2) / sum((abs(sim - self.obsMean) + abs(self.obs_masked - self.obsMean)) ** 2))


class fluxes(subOutputManipulator):

    def __init__(self, output, areasList, daysSkip, working_dir, iprint='day', stats_dir=None, encoding='latin-1'):
        self.working_dir = working_dir
        self.file_enc = encoding
        inputFile = open(os.path.join(self.working_dir, "output.sub"), "r", encoding=encoding)
        self.textOld = inputFile.readlines()
        inputFile.close()
        self.areaSizes = self.readAreaSizes(areasList)
        outValues = self.readValues([output], areasList)
        self.sumSim = np.zeros(len(outValues[output][areasList[0]][daysSkip:]), float)
        for area in self.areaSizes:
            sim = np.array([float(i) for i in outValues[output][area][daysSkip:]])
            sim *= (self.areaSizes[area] * 1000.0 / 24 / 60 / 60)
            self.sumSim += sim

    def result(self):
        return (np.mean(self.sumSim))

