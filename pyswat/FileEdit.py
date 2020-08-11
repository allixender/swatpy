# SWAT_Manipulate.py

""" Christoph Hecht, 16.04.2008

    Classes which inherit from "InputFileManipulator" are able
    to receive information and manipulate SWAT input files
    accordingly. Each instance is responible for one file.
    Each class is designed for one type of file (e.g. ".sol").


    Christoph Hecht, 15.07.2008

    Classes "solManipulationCorrection" and "solManipulationCheck"
    were added. Both inherit from "solManipulator". The first one
    assures that the sum of clay, silt and sand contents equals
    100 %. The second one checks for all horizons, if SWAT would
    calculate field capacities greater then whole porosities.
    Both were intended to allow for a consistent and distributed
    manipulation of soil parameters by factors.

    Christoph Hecht, 31.07.2008

    Method "changeSetPar" of class "solManipulator" is now able to
    manipulate soil depths in substitution mode ("s"). Therefore
    all horizons are assumed to have the same depths.

    Christoph Hecht, 19.08.2008

    sol..., hru..., mgt... and gwManipulator now have the attribute
    "landuse". If the landuse type of an HRU is "urban" ("URBN")
    one may choose not to manipulate the corresponding files.

    Christoph Hecht, 20.08.2008

    "hruManipulator" now contains "subbasin" and "hru_abs". Both
    attributes can be called directly. The first one is the number
    of the corresponding subbasin, the second one the total area
    of the corresponding HRU.
    "solManipulator" now contains "parValueMean". Here parameter
    values are averaged over the whole soil profile, taking into
    account the depth of each soil layer. For "SOL_Z" the depth
    of the deepest horizon is returned.

    Christoph Hecht, 21.08.2008

    "solManipulator" now contains the attribute lists
    "fieldCapacity", "saturationVolume" and "airCapacity"
    for each layer.

"""

import os
import numpy as np

"""
__init__            connects instance with a single file;
                    calls "initParValue"

initParValue        reads initial values from input files, these
                    won't be changed afterwards / are the
                    basis for repeated file manipulation;
                    should be overridden if one parameter exists
                    several times in the file (e.g. ".sol")
                    (below called: "multi paramter problem")

prepareChangePar    copies text of file to be changed and stored
                    as the manipulated file later on;
                    is automatically called after each file
                    manipulation by "finishChangePar"

setChangePar        a dummy which just calls "setChangePar";
                    is intended to be overridden in case of
                    the "multi parameter problem"

changePar           modifies a parameter according to a selected
                    value and a selected method;
                    substitutes the original values in the copy
                    of the text of the original file

finishChangePar     overwrites file with the modified string;
                    calls "prepareChangePar";
                    resets the original file if called twice


Use subclasses as follows:
    (1) f = FileManipulator(filename as string, parList as list)
    Begin Loop
    (2) f.setChangePar(namePar as string, changePar as float/integer,
        changeHow as string("+","*","s"))
    (3) f.finishChangePar()
    End Loop
    (4) f.finishChangePar()

for repeated manipulation: step (1) should not be processed several times,
otherwise step (4) won't work as supposed. 
Calling "f.finishChangePar() twice resets the original file

"""


class InputFileManipulator(object):

    # connect Object with a SWAT input file
    def __init__(self, filename, parList, working_dir, encoding='latin-1'):
        self.filename = filename
        self.file_enc=encoding
        self.working_dir = working_dir
        #        try:
        #		core_nr = str(int(os.environ['OMPI_COMM_WORLD_RANK'])) # +1 to prevent zero if necessary...
        #        except KeyError:
        #		core_nr = str(int(np.random.uniform(0,1000))) # if you run on windows
        ffile = open(os.path.join(self.working_dir, self.filename), "r", encoding=self.file_enc)
        self.textOld = ffile.readlines()
        ffile.close()
        self.initParValue(parList)
        self.prepareChangePar()

    # should be overridden if one parameter exists several times in each file, e.g. for different soil layers
    def initParValue(self, parList):
        # initial parameters --> parValue of subclass
        for namePar in parList:
            row, col1, col2, dig = self.parInfo[namePar]
            self.parValue[namePar] = [float(self.textOld[row - 1][col1:col2])]

    def prepareChangePar(self):
        self.textNew = self.textOld[:]  # copy instead of new name allocation

    # built to be overridden if one parameter exists several times in each file, e.g. for different soil layers
    def setChangePar(self, namePar, changePar, changeHow):
        self.changePar(namePar, changePar, changeHow)

    # built to be overridden if one parameter exists several times in each file, e.g. for different soil layers to change single Layers by self.Julich apr 09
    def setChangeParLay(self, namePar, changePar, changeHow):
        self.changePar(namePar, changePar, changeHow)

    # offset- and index-values are only relevant, if setChangePar is overridden

    def changePar(self, namePar, changePar, changeHow, offsetRow=0, offsetCol=0, index=0):
        # change initial parameter depending on chosen method
        changePar = float(changePar)
        if changeHow == "+":
            changedPar = self.parValue[namePar][index] + changePar
        elif changeHow == "*":
            changedPar = self.parValue[namePar][index] + self.parValue[namePar][index] * changePar
        elif changeHow == "s":
            changedPar = changePar
        # insert changed Parameter in textNew
        row, col1, col2, dig = self.parInfo[namePar]
        row += offsetRow
        col1 += offsetCol
        col2 += offsetCol
        format = "%" + str(col2 - col1 + 1) + "." + str(dig) + "f"
        self.textNew[row - 1] = (self.textNew[row - 1][:col1 - 1] +
                              (format % changedPar).rjust(col2 - col1 + 1) +
                              self.textNew[row - 1][col2:])

    # save textNew in file (file ready for SWAT)
    def finishChangePar(self):
        # try:
        #	core_nr = str(int(os.environ['OMPI_COMM_WORLD_RANK'])) # +1 to prevent zero if necessary...
        #  except KeyError:
        #	core_nr = str(int(np.random.uniform(0,10000))) # if you run on windows
        ffile = open(os.path.join(self.working_dir,  self.filename), "w", encoding=self.file_enc)
        ffile.writelines(self.textNew)
        ffile.close
        self.prepareChangePar()


"""

"""


class bsnManipulator(InputFileManipulator):
    # information about parameters:
    # (1)row in file, (2) first and (3) last relevant column in row
    # and (4) digits
    parInfo = {"SFTMP": (4, 1, 16, 4),
               "SMTMP": (5, 1, 16, 4),
               "SMFMX": (6, 1, 16, 4),
               "SMFMN": (7, 1, 16, 4),
               "TIMP": (8, 1, 16, 4),
               "SNOCOVMX": (9, 1, 16, 4),
               "SNO50COV": (10, 1, 16, 4),
               "IPET": (11, 1, 16, 0),
               "ESCO": (13, 1, 16, 4),
               "EPCO": (14, 1, 16, 4),
               "EVLAI": (15, 1, 16, 4),
               "FFCB": (16, 1, 16, 4),
               "IEVENT": (18, 1, 16, 0),
               "ICRK": (19, 1, 16, 0),
               "SURLAG": (20, 1, 16, 4),
               "ADJ_PKR": (21, 1, 16, 4),
               "PRF_BSN": (22, 1, 16, 4),
               "SPCON": (23, 1, 16, 6),
               "SPEXP": (24, 1, 16, 4),
               "RCN": (26, 1, 16, 4),
               "CMN": (27, 1, 16, 6),
               "N_UPDIS": (28, 1, 16, 4),
               "P_UPDIS": (29, 1, 16, 4),
               "NPERCO": (30, 1, 16, 4),
               "PPERCO": (31, 1, 16, 4),
               "PHOSKD": (32, 1, 16, 4),
               "PSP": (33, 1, 16, 4),
               "RSDCO": (34, 1, 16, 4),
               "PERCOP": (36, 1, 16, 4),
               "ISUBWQ": (38, 1, 16, 0),
               "WDPQ": (40, 1, 16, 4),
               "WGPQ": (41, 1, 16, 4),
               "WDLPQ": (42, 1, 16, 4),
               "WGLPQ": (43, 1, 16, 4),
               "WDPS": (44, 1, 16, 4),
               "WGPS": (45, 1, 16, 4),
               "WDLPS": (46, 1, 16, 4),
               "WGLPS": (47, 1, 16, 4),
               "BACTKDQ": (48, 1, 16, 4),
               "THBACT": (49, 1, 16, 4),
               "WOF_P": (50, 1, 16, 4),
               "WOF_LP": (51, 1, 16, 4),
               "WDPF": (52, 1, 16, 4),
               "WGPF": (53, 1, 16, 4),
               "WDLPF": (54, 1, 16, 4),
               "WGLPF": (55, 1, 16, 4),
               "ISED_DET": (56, 1, 16, 0),
               "IRTE": (58, 1, 16, 0),
               "MSK_CO1": (59, 1, 16, 4),
               "MSK_CO2": (60, 1, 16, 4),
               "MSK_X": (61, 1, 16, 4),
               "IDEG": (62, 1, 16, 0),
               "IWQ": (63, 1, 16, 0),
               "TRNSRCH": (65, 1, 16, 4),
               "EVRCH": (66, 1, 16, 4),
               "IRTPEST": (67, 1, 16, 0),
               "ICN": (68, 1, 16, 0),
               "CNCOEF": (69, 1, 16, 4),
               "CDN": (70, 1, 16, 4),
               "SDNCO": (71, 1, 16, 4),
               "BACT_SWF": (72, 1, 16, 4),
               "BACTMX": (73, 1, 16, 4),
               "BACTMINLP": (74, 1, 16, 4),
               "BACTMINP": (75, 1, 16, 4),
               "WDLPRCH": (76, 1, 16, 4),
               "WDPRCH": (77, 1, 16, 4),
               "WDLPRES": (78, 1, 16, 4),
               "WDPRES": (79, 1, 16, 4),
               "TB_ADJ": (80, 1, 16, 4),
               "DEPIMP_BSN": (81, 1, 16, 0),
               "DDRAIN_BSN": (82, 1, 16, 4),
               "TDRAIN_BSN": (83, 1, 16, 4),
               "GDRAIN_BSN": (84, 1, 16, 4),
               "CN_FROZ": (85, 1, 16, 6),
               "DORM_HR": (86, 1, 16, 4),
               "SMXCO": (87, 1, 16, 4),
               "FIXCO": (88, 1, 16, 4),
               "NFIXMX": (89, 1, 16, 4),
               "ANION_EXCL_BSN": (90, 1, 16, 4),
               "CH_ONCO_BSN": (91, 1, 16, 4),
               "CH_OPCO_BSN": (92, 1, 16, 4),
               "HLIFE_NGW_BSN": (93, 1, 16, 4),
               "RCN_SUB_BSN": (94, 1, 16, 4),
               "BC1_BSN": (95, 1, 16, 4),
               "BC2_BSN": (96, 1, 16, 4),
               "BC3_BSN": (97, 1, 16, 4),
               "BC4_BSN": (98, 1, 16, 4),
               "DECR_MIN": (99, 1, 16, 4),
               "ICFAC": (100, 1, 16, 4),
               "RSD_COVCO": (101, 1, 16, 4),
               "VCRIT": (102, 1, 16, 4),
               "CSWAT": (103, 1, 16, 0),
               "RES_STLR_CO": (104, 1, 16, 4),
               "BFLO_DIST": (105, 1, 16, 4),
               "IUH": (106, 1, 16, 0),
               "UHALPHA": (107, 1, 16, 4),
               "EROS_SPL": (111, 1, 16, 4),
               "RILL_MULT": (112, 1, 16, 4),
               "EROS_EXPO": (113, 1, 16, 4),
               "SUBD_CHSED": (114, 1, 16, 4),
               "C_FACTOR": (115, 1, 16, 4),
               "CH_D50": (116, 1, 16, 2),
               "SIG_G": (117, 1, 16, 4),
               "RE_BSN": (118, 1, 16, 3),
               "SDRAIN_BSN": (119, 1, 16, 3),
               "DRAIN_CO_BSN": (120, 1, 16, 3),
               "PC_BSN": (121, 1, 16, 4),
               "LATKSATF_BSN": (122, 1, 16, 3),
               "ITDRN": (123, 1, 16, 0),
               "IWTDN": (124, 1, 16, 0),
               "SOL_P_MODEL": (125, 1, 16, 0),
               "IABSTR": (126, 1, 16, 3),
               "IATMODEP": (127, 1, 16, 0),
               "R2ADJ_BSN": (128, 1, 16, 0),
               "SSTMAXD_BSN": (129, 1, 16, 0),
               "ISMAX": (130, 1, 16, 0),
               "IROUTUNIT": (131, 1, 16, 0)}

    # expands init-method of FileManipulator to generate parValue-dictionaries for individual instances
    def __init__(self, filename, parList, working_dir, encoding='latin-1'):
        self.parValue = {"SFTMP": None,
                      "SMTMP": None,
                      "SMFMX": None,
                      "SMFMN": None,
                      "TIMP": None,
                      "SNOCOVMX": None,
                      "SNO50COV": None,
                      "IPET": None,
                      "ESCO": None,
                      "EPCO": None,
                      "EVLAI": None,
                      "FFCB": None,
                      "IEVENT": None,
                      "ICRK": None,
                      "SURLAG": None,
                      "ADJ_PKR": None,
                      "PRF_BSN": None,
                      "SPCON": None,
                      "SPEXP": None,
                      "RCN": None,
                      "CMN": None,
                      "N_UPDIS": None,
                      "P_UPDIS": None,
                      "NPERCO": None,
                      "PPERCO": None,
                      "PHOSKD": None,
                      "PSP": None,
                      "RSDCO": None,
                      "PERCOP": None,
                      "ISUBWQ": None,
                      "WDPQ": None,
                      "WGPQ": None,
                      "WDLPQ": None,
                      "WGLPQ": None,
                      "WDPS": None,
                      "WGPS": None,
                      "WDLPS": None,
                      # "WDLPS": None,
                      "BACTKDQ": None,
                      "THBACT": None,
                      "WOF_P": None,
                      "WOF_LP": None,
                      "WDPF": None,
                      "WGPF": None,
                      "WDLPF": None,
                      "WGLPF": None,
                      "ISED_DET": None,
                      "IRTE": None,
                      "MSK_CO1": None,
                      "MSK_CO2": None,
                      "MSK_X": None,
                      "IDEG": None,
                      "IWQ": None,
                      "TRNSRCH": None,
                      "EVRCH": None,
                      "IRTPEST": None,
                      "ICN": None,
                      "CNCOEF": None,
                      "CDN": None,
                      "SDNCO": None,
                      "BACT_SWF": None,
                      "BACTMX": None,
                      "BACTMINLP": None,
                      "BACTMINP": None,
                      "WDLPRCH": None,
                      "WDPRCH": None,
                      "WDLPRES": None,
                      "WDPRES": None,
                      "TB_ADJ": None,
                      "DEPIMP_BSN": None,
                      "DDRAIN_BSN": None,
                      "TDRAIN_BSN": None,
                      "GDRAIN_BSN": None,
                      "CN_FROZ": None,
                      "DORM_HR": None,
                      "SMXCO": None,
                      "FIXCO": None,
                      "NFIXMX": None,
                      "ANION_EXCL_BSN": None,
                      "CH_ONCO_BSN": None,
                      "CH_OPCO_BSN": None,
                      "HLIFE_NGW_BSN": None,
                      "RCN_SUB_BSN": None,
                      "BC1_BSN": None,
                      "BC2_BSN": None,
                      "BC3_BSN": None,
                      "BC4_BSN": None,
                      "DECR_MIN": None,
                      "ICFAC": None,
                      "RSD_COVCO": None,
                      "VCRIT": None,
                      "CSWAT": None,
                      "RES_STLR_CO": None,
                      "BFLO_DIST": None,
                      "IUH": None,
                      "UHALPHA": None,
                      "EROS_SPL": None,
                      "RILL_MULT": None,
                      "EROS_EXPO": None,
                      "SUBD_CHSED": None,
                      "C_FACTOR": None,
                      "CH_D50": None,
                      "SIG_G": None,
                      "RE_BSN": None,
                      "SDRAIN_BSN": None,
                      "DRAIN_CO_BSN": None,
                      "PC_BSN": None,
                      "LATKSATF_BSN": None,
                      "ITDRN": None,
                      "IWTDN": None,
                      "SOL_P_MODEL": None,
                      "IABSTR": None,
                      "IATMODEP": None,
                      "R2ADJ_BSN": None,
                      "SSTMAXD_BSN": None,
                      "ISMAX": None,
                      "IROUTUNIT": None}
        InputFileManipulator.__init__(self, filename, parList, working_dir, encoding)


"""

"""


class gwManipulator(InputFileManipulator):
    # information about parameters:
    # (1)row in file, (2) first and (3) last relevant column in row
    # and (4) digits
    parInfo = {"SHALLST": (2, 1, 16, 5),
               "DEEPST": (3, 1, 16, 5),
               "GW_DELAY": (4, 1, 16, 5),
               "ALPHA_BF": (5, 1, 16, 5),
               "GWQMN": (6, 1, 16, 5),
               "GW_REVAP": (7, 1, 16, 5),
               "REVAPMN": (8, 1, 16, 5),
               "RCHRG_DP": (9, 1, 16, 5),
               "GWHT": (10, 1, 16, 5),
               "GW_SPYLD": (11, 1, 16, 5),
               "SHALLST_N": (12, 1, 16, 5),
               "GWSOLP": (13, 1, 16, 5),
               "HLIFE_NGW": (14, 1, 16, 5),
               "LAT_ORGN": (15, 1, 16, 5),
               "LAT_ORGP": (16, 1, 16, 5),
               "ALPHA_BF_D": (17, 1, 16, 5)}

    # expands init-method of FileManipulator to generate parValue-dictionaries for individual instances
    def __init__(self, filename, parList, working_dir, encoding='latin-1'):
        self.parValue = {"SFTMP": None,
                      "SHALLST": None,
                      "DEEPST": None,
                      "GW_DELAY": None,
                      "ALPHA_BF": None,
                      "GWQMN": None,
                      "GW_REVAP": None,
                      "REVAPMN": None,
                      "RCHRG_DP": None,
                      "GWHT": None,
                      "GW_SPYLD": None,
                      "SHALLST_N": None,
                      "GWSOLP": None,
                      "HLIFE_NGW": None,
                      "LAT_ORGN": None,
                      "LAT_ORGP": None,
                      "ALPHA_BF_D": None}
        InputFileManipulator.__init__(self, filename, parList, working_dir, encoding)
        self.landuse = self.textOld[0].split(" ")[7].split(":")[1]
        self.subbasin = self.textOld[0].split(" ")[5].split(":")[1]


"""

"""


class mgtManipulator(InputFileManipulator):
    # information about parameters:
    # (1)row in file, (2) first and (3) last relevant column in row
    # and (4) digits
    parInfo = {"NMGT": (2, 1, 16, 0),
               "IGRO": (4, 1, 16, 0),
               "PLANT_ID": (5, 1, 16, 0),
               "LAI_INIT": (6, 1, 16, 3),
               "BIO_INIT": (7, 1, 16, 3),
               "PHU_PLT": (8, 1, 16, 3),
               "BIOMIX": (10, 1, 16, 3),
               "CN2": (11, 1, 16, 3),
               "USLE_P": (12, 1, 16, 3),
               "BIO_MIN": (13, 1, 16, 3),
               "FILTERW": (14, 1, 16, 4),
               "IURBAN": (16, 1, 16, 0),
               "URBLU": (17, 1, 16, 0),
               "IRRSC": (19, 1, 16, 0),
               "IRRNO": (20, 1, 16, 0),
               "FLOWMIN": (21, 1, 16, 4),
               "DIVMAX": (22, 1, 16, 4),
               "FLOWFR": (23, 1, 16, 4),
               "DDRAIN": (25, 1, 16, 4),
               "TDRAIN": (26, 1, 16, 4),
               "GDRAIN": (27, 1, 16, 4),
               "NROT": (29, 1, 16, 0)}

    # expands init-method of FileManipulator to generate parValue-dictionaries for individual instances
    def __init__(self, filename, parList, working_dir, encoding='latin-1'):
        self.parValue = {"NMGT": None,
                      "IGRO": None,
                      "PLANT_ID": None,
                      "LAI_INIT": None,
                      "BIO_INIT": None,
                      "PHU_PLT": None,
                      "BIOMIX": None,
                      "CN2": None,
                      "USLE_P": None,
                      "BIO_MIN": None,
                      "FILTERW": None,
                      "IURBAN": None,
                      "URBLU": None,
                      "IRRSC": None,
                      "IRRNO": None,
                      "FLOWMIN": None,
                      "DIVMAX": None,
                      "FLOWFR": None,
                      "DDRAIN": None,
                      "TDRAIN": None,
                      "GDRAIN": None,
                      "NROT": None}
        InputFileManipulator.__init__(self, filename, parList, working_dir, encoding)
        self.landuse = self.textOld[0].split(" ")[7].split(":")[1]
        self.subbasin = self.textOld[0].split(" ")[5].split(":")[1]


"""

"""


class subManipulator(InputFileManipulator):
    # information about parameters:
    # (1)row in file, (2) first and (3) last relevant column in row
    # and (4) digits
    parInfo = {
        "SUB_KM": (2, 1, 16, 6),
        "CH_L1": (25, 1, 16, 6),
        "CH_S1": (26, 1, 16, 6),
        "CH_W1": (27, 1, 16, 6),
        "CH_K1": (28, 1, 16, 6),
        "CH_N1": (29, 1, 16, 6),
        "CO2":   (35, 1, 16, 6)
        }

    # expands init-method of FileManipulator to generate parValue-dictionaries for individual instances
    def __init__(self, filename, parList, working_dir, encoding='latin-1'):
        self.parValue = {
            "SUB_KM": None,
            "CH_L1": None,
            "CH_S1": None,
            "CH_W1": None,
            "CH_K1": None,
            "CH_N1": None,
            "CO2":   None
            }
        InputFileManipulator.__init__(self, filename, parList, working_dir, encoding)


"""

"""


class hruManipulator(InputFileManipulator):
    # information about parameters:
    # (1)row in file, (2) first and (3) last relevant column in row
    # and (4) digits
    parInfo = {"HRU_FR": (2, 1, 16, 7),
               "SLSUBBSN": (3, 1, 16, 4),
               "HRU_SLP": (4, 1, 16, 4),
               "OV_N": (5, 1, 16, 4),
               "LAT_TTIME": (6, 1, 16, 4),
               "LAT_SED": (7, 1, 16, 4),
               "SLSOIL": (8, 1, 16, 4),
               "CANMX": (9, 1, 16, 4),
               "ESCO": (10, 1, 16, 4),
               "EPCO": (11, 1, 16, 4),
               "RSDIN": (12, 1, 16, 4),
               "ERORGN": (13, 1, 16, 4),
               "ERORGP": (14, 1, 16, 4),
               "POT_FR": (15, 1, 16, 4),
               "FLD_FR": (16, 1, 16, 4),
               "RIP_FR": (17, 1, 16, 4),
               "POT_TILE": (19, 1, 16, 4),
               "POT_VOLX": (20, 1, 16, 4),
               "POT_VOL": (21, 1, 16, 4),
               "POT_NSED": (22, 1, 16, 4),
               "POT_NO3L": (23, 1, 16, 4),
               "DEP_IMP": (24, 1, 16, 0),
               "EVPOT": (28, 1, 16, 2),
               "DIS_STREAM": (29, 1, 16, 2),
               "CF": (30, 1, 16, 2),
               "CFH": (31, 1, 16, 2),
               "CFDEC": (32, 1, 16, 4),
               "SED_CON": (33, 1, 16, 2),
               "ORGN_CON": (34, 1, 16, 2),
               "ORGP_CON": (35, 1, 16, 2),
               "SOLN_CON": (36, 1, 16, 2),
               "SOLP_CON": (37, 1, 16, 2),
               "POT_SOLP": (38, 1, 16, 2),
               "POT_K": (39, 1, 16, 2),
               "N_REDUC": (40, 1, 16, 2),
               "N_LAG": (41, 1, 16, 2),
               "N_LN": (42, 1, 16, 2),
               "N_LNCO": (43, 1, 16, 2),
               "SURLAG": (44, 1, 16, 2),
               "R2ADJ": (45, 1, 16, 2)}

    # expands init-method of FileManipulator to generate parValue-dictionaries for individual instances
    def __init__(self, filename, parList, working_dir, encoding='latin-1'):
        self.parValue = {"HRU_FR": None,
                      "SLSUBBSN": None,
                      "HRU_SLP": None,
                      "OV_N": None,
                      "LAT_TTIME": None,
                      "LAT_SED": None,
                      "SLSOIL": None,
                      "CANMX": None,
                      "ESCO": None,
                      "EPCO": None,
                      "RSDIN": None,
                      "ERORGN": None,
                      "ERORGP": None,
                      "POT_FR": None,
                      "FLD_FR": None,
                      "RIP_FR": None,
                      "POT_TILE": None,
                      "POT_VOLX": None,
                      "POT_VOL": None,
                      "POT_NSED": None,
                      "POT_NO3L": None,
                      "DEP_IMP": None,
                      "EVPOT": None,
                      "DIS_STREAM": None,
                      "CF": None,
                      "CFH": None,
                      "CFDEC": None,
                      "SED_CON": None,
                      "ORGN_CON": None,
                      "ORGP_CON": None,
                      "SOLN_CON": None,
                      "SOLP_CON": None,
                      "POT_SOLP": None,
                      "POT_K": None,
                      "N_REDUC": None,
                      "N_LAG": None,
                      "N_LN": None,
                      "N_LNCO": None,
                      "SURLAG": None,
                      "R2ADJ": None}
        if "HRU_FR" not in parList:
            parList.append("HRU_FR")
        InputFileManipulator.__init__(self, filename, parList, working_dir, encoding)
        self.landuse = self.textOld[0].split(" ")[7].split(":")[1]
        self.subbasin = self.textOld[0].split(" ")[5].split(":")[1]
        zeros = "0"
        zeros *= 5 - len(self.subbasin)
        filename_subbasin = zeros + self.subbasin + "0000.sub"
        self.hru_abs = subManipulator(filename_subbasin, ["SUB_KM"], working_dir).parValue["SUB_KM"][0]
        self.hru_abs *= self.parValue["HRU_FR"][0]


"""

"""


class solManipulator(InputFileManipulator):
    # information about parameters:
    # (1)row in file, (2) first and (3) last relevant column in row
    # and (4) digits
    parInfo = {"SOL_ZMX": (4, 29, 36, 2),
               "ANION_EXCL": (5, 51, 56, 4),
               "SOL_CRK": (6, 33, 38, 4),
               "SOL_Z": (8, 28, 39, 2),
               "SOL_BD": (9, 28, 39, 4),
               "SOL_AWC": (10, 28, 39, 4),
               "SOL_K": (11, 28, 39, 4),
               "SOL_CBN": (12, 28, 39, 4),
               "CLAY": (13, 28, 39, 4),
               "SILT": (14, 28, 39, 4),
               "SAND": (15, 28, 39, 4),
               "ROCK": (16, 28, 39, 4),
               "SOL_ALB": (17, 28, 39, 4),
               "USLE_K": (18, 28, 39, 4),
               "SOL_EC": (19, 28, 39, 4),
               "SOL_PH": (20, 28, 39, 4),
               "SOL_CACO3": (21, 28, 39, 4)}

    # expands init-method of FileManipulator to generate parValue-dictionaries for individual instances
    def __init__(self, filename, parList, working_dir, encoding='latin-1'):
        self.parValue = {"SOL_ZMX": None,
                      "ANION_EXCL": None,
                      "SOL_CRK": None,
                      "SOL_Z": None,
                      "SOL_BD": None,
                      "SOL_AWC": None,
                      "SOL_K": None,
                      "SOL_CBN": None,
                      "CLAY": None,
                      "SILT": None,
                      "SAND": None,
                      "ROCK": None,
                      "SOL_ALB": None,
                      "USLE_K": None,
                      "SOL_EC": None,
                      "SOL_PH": None,
                      "SOL_CAL": None}

        self.parValueMean = {"SOL_BD": None,
                          "SOL_AWC": None,
                          "SOL_K": None,
                          "SOL_CBN": None,
                          "CLAY": None,
                          "SILT": None,
                          "SAND": None,
                          "ROCK": None,
                          "SOL_ALB": None,
                          "USLE_K": None,
                          "SOL_EC": None,
                          "SOL_PH": None,
                          "SOL_CAL": None}

        if "SOL_Z" not in parList:
            parList.append("SOL_Z")
        if "SOL_AWC" not in parList:
            parList.append("SOL_AWC")
        if "SOL_BD" not in parList:
            parList.append("SOL_BD")
        if "CLAY" not in parList:
            parList.append("CLAY")
        InputFileManipulator.__init__(self, filename, parList, working_dir, encoding)
        self.calculateParValueMean(parList)
        self.landuse = self.textOld[0].split(" ")[7].split(":")[1]

        n_horizons = len(self.parValue["SOL_Z"])
        self.fieldCapacity = []
        self.saturationVolume = []
        self.airCapacity = []
        for horizon in range(n_horizons):
            awc = self.parValue["SOL_AWC"][horizon]
            bd = self.parValue["SOL_BD"][horizon]
            clay = self.parValue["CLAY"][horizon]
            self.fieldCapacity.append(awc + 0.4 * clay / 100.0 * bd)
            self.saturationVolume.append(1 - bd / 2.65)
            self.airCapacity.append((1 - bd / 2.65) - (awc + 0.4 * clay / 100.0 * bd))

    # overrides method of FileManipulator: multiple soil layers have to be considered.
    def initParValue(self, parList):
        # initial parameters --> parValue of subclass
        for namePar in parList:
            row, col1, col2, dig = self.parInfo[namePar]
            llist = []
            llist.append(float(self.textOld[row - 1][col1:col2]))
            if row > 7:
                while len(self.textOld[row - 1]) > col2 + 3:
                    col1 += 12
                    col2 += 12
                    llist.append(float(self.textOld[row - 1][col1:col2]))
            self.parValue[namePar] = llist

    # overrides setChangePar: multiple soil layers have to be considered.
    def setChangePar(self, namePar, changePar, changeHow):
        n_par = len(self.parValue[namePar])
        for index in range(n_par):
            offsetCol = index * 12
            if namePar == "SOL_Z" and changeHow == "s":
                self.changePar(namePar, changePar * (index + 1) / n_par, changeHow, 0, offsetCol, index)
            else:
                self.changePar(namePar, changePar, changeHow, 0, offsetCol, index)

    def setChangeParLay(self, namePar, changePar, changeHow, layer):
        index = layer
        n_par = len(self.parValue[namePar])
        offsetCol = index * 12
        if namePar == "SOL_Z" and changeHow == "s":
            self.changePar(namePar, changePar * (index + 1) / n_par, changeHow, 0, offsetCol, index)
        else:
            self.changePar(namePar, changePar, changeHow, 0, offsetCol, index)

    # calculates averaged parameter values for the whole soil profile weighted by the depth of each horizon
    def calculateParValueMean(self, parList):
        n_horizons = len(self.parValue["SOL_Z"])
        for par in parList:
            if par == "SOL_Z":
                self.parValueMean[par] = self.parValue[par][n_horizons - 1]
            elif par in self.parValueMean:
                if n_horizons == 1:
                    self.parValueMean[par] = self.parValue[par][0]
                else:
                    valueMean = self.parValue[par][0] * self.parValue["SOL_Z"][0]
                    for n in range(1, n_horizons):
                        valueMean += self.parValue[par][n] * (self.parValue["SOL_Z"][n] - self.parValue["SOL_Z"][n - 1])
                    valueMean /= self.parValue["SOL_Z"][n_horizons - 1]
                    self.parValueMean[par] = valueMean


class solManipulationCorrection(solManipulator):

    def __init__(self, filename, working_dir, encoding='latin-1'):
        parList = ["CLAY", "SILT", "SAND"]
        solManipulator.__init__(self, filename, parList, working_dir, encoding)
        for index in range(len(self.parValue["CLAY"])):
            correctionFactor = (100.0 - self.parValue["CLAY"][index]) / (
                        self.parValue["SILT"][index] + self.parValue["SAND"][index])
            offsetCol = index * 12
            self.changePar("CLAY", 1.0, "*", 0, offsetCol, index)
            self.changePar("SILT", correctionFactor, "*", 0, offsetCol, index)
            self.changePar("SAND", correctionFactor, "*", 0, offsetCol, index)
        self.finishChangePar()


class solManipulationCheck(solManipulator):

    def __init__(self, filename, working_dir, encoding='latin-1'):
        parList = ["SOL_AWC", "SOL_BD", "CLAY"]
        solManipulator.__init__(self, filename, parList, working_dir, encoding)
        self.ok = True
        for i in range(len(self.parValue["CLAY"])):
            if (self.parValue["SOL_AWC"][i] + 0.4 * self.parValue["CLAY"][i] / 100.0 * self.parValue["SOL_BD"][i]) >= (
                    1 - self.parValue["SOL_BD"][i] / 2.65):
                self.ok = False
                print("solManipulationCheck found inconsistency in horizon: " + str(i + 1))


class rteManipulator(InputFileManipulator):
    # information about parameters:
    # (1)row in file, (2) first and (3) last relevant column in row
    # and (4) digits
    parInfo = {"CHW2": (2, 1, 14, 4),
               "CHD": (3, 1, 14, 4),
               "CH_S2": (4, 1, 14, 6),
               "CH_L2": (5, 1, 14, 4),
               "CH_N2": (6, 1, 14, 6),
               "CH_K2": (7, 1, 14, 4),
               "CH_COV1": (8, 1, 14, 4),
               "CH_COV2": (9, 1, 14, 4),
               "CH_WDR": (10, 1, 14, 4),
               "ALPHA_BNK": (11, 1, 14, 4),
               "ICANAL": (12, 1, 14, 3),
               "CH_ONCO": (13, 1, 14, 3),
               "CH_OPCO": (14, 1, 14, 3),
               "CH_SIDE": (15, 1, 14, 3),
               "CH_BNK_BD": (16, 1, 14, 3),
               "CH_BED_BD": (17, 1, 14, 3),
               "CH_BNK_KD": (18, 1, 14, 3),
               "CH_BED_KD": (19, 1, 14, 3),
               "CH_BNK_D50": (20, 1, 14, 3),
               "CH_BED_D50": (21, 1, 14, 3),
               "CH_BNK_TC": (22, 1, 14, 3),
               "CH_BED_TC": (23, 1, 14, 3),
               "CH_EQ": (25, 1, 14, 0)}

    # expands init-method of FileManipulator to generate parValue-dictionaries for individual instances
    def __init__(self, filename, parList, working_dir, encoding='latin-1'):
        self.parValue = {"CHWD2": None,
                      "CHD": None,
                      "CH_S2": None,
                      "CH_L2": None,
                      "CH_N2": None,
                      "CH_K2": None,
                      "CH_COV1": None,
                      "CH_COV2": None,
                      "CH_WDR": None,
                      "ALPHA_BNK": None,
                      "ICANAL": None,
                      "CH_ONCO": None,
                      "CH_OPCO": None,
                      "CH_SIDE": None,
                      "CH_BNK_BD": None,
                      "CH_BED_BD": None,
                      "CH_BNK_KD": None,
                      "CH_BED_KD": None,
                      "CH_BNK_D50": None,
                      "CH_BED_D50": None,
                      "CH_BNK_TC": None,
                      "CH_BED_TC": None,
                      "CH_EQ": None}
        InputFileManipulator.__init__(self, filename, parList, working_dir, encoding)
        self.subbasin = self.textOld[0].split(" ")[3].split(":")[0]


class fileCioManipulator(InputFileManipulator):
    # information about parameters:
    # (1)row in file, (2) first and (3) last relevant column in row
    # and (4) digits
    parInfo = {"NBYR": (8, 1, 17, 4),
               "IYR": (9, 1, 17, 4),
               "IPRINT": (59, 1, 17, 4),
               "NYSKIP": (60, 1, 17, 4)}

    # expands init-method of FileManipulator to generate parValue-dictionaries for individual instances
    def __init__(self, filename, parList, working_dir, encoding='latin-1'):
        self.parValue = {"NBYR": None,
                      "IYR": None,
                      "IPRINT": None,
                      "NYSKIP": None}
        InputFileManipulator.__init__(self, filename, parList, working_dir, encoding)
