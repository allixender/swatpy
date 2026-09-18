"""Generate the synthetic SWAT2012 test fixtures in tests/data.

The files mimic the fixed-width layout of SWAT2012 rev 637 / ArcSWAT 2012 input and
output files (verified against a real project run), but all values are synthetic:

    TxtInOut/        mini model, 2 subbasins, 3 HRUs (000010002 is urban)
    output_monthly/  output.rch/.sub/.hru, IPRINT=0, 2 printed years, all variables
    output_daily/    output.rch/.hru, IPRINT=1, 1 year, reduced variable selection

Values are chosen so that tests can identify rows and columns, see expected_input_value and
out_value. Run `python tests/data/make_fixtures.py` to regenerate.
"""

import os
import sys
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))

from swatpy import FileEdit  # noqa: E402

HEADER_DATE = "9/18/2026 12:00:00 AM ArcSWAT 2012.10_0.14"

# model setup
IYR = 2001
NBYR = 3
NYSKIP = 1
PRINTED_YEARS = [2002, 2003]

SUBBASINS = {1: 10.0, 2: 5.0}  # SUB_KM
HRUS = {
    # file id: (subbasin, hru number, landuse, soil, HRU_FR)
    "000010001": (1, 1, "AGRL", "SOILA", 0.6),
    "000010002": (1, 2, "URBN", "SOILA", 0.4),
    "000020001": (2, 3, "FRST", "SOILB", 1.0),
}

SOILS = {
    "SOILA": {"SOL_ZMX": 1520.0, "ANION_EXCL": 0.5, "SOL_CRK": 0.5,
              "SOL_Z": [300.0, 1000.0, 1520.0], "SOL_BD": [1.4, 1.5, 1.6],
              "SOL_AWC": [0.15, 0.12, 0.1], "SOL_K": [20.0, 10.0, 5.0],
              "SOL_CBN": [1.5, 0.5, 0.2], "CLAY": [20.0, 25.0, 30.0],
              "SILT": [40.0, 35.0, 30.0], "SAND": [40.0, 40.0, 40.0],
              "ROCK": [0.0, 5.0, 10.0], "SOL_ALB": [0.1, 0.1, 0.1],
              "USLE_K": [0.3, 0.3, 0.3], "SOL_EC": [0.0, 0.0, 0.0],
              "SOL_PH": [6.5, 6.8, 7.0], "SOL_CACO3": [0.0, 0.0, 0.0]},
    "SOILB": {"SOL_ZMX": 800.0, "ANION_EXCL": 0.5, "SOL_CRK": 0.5,
              "SOL_Z": [250.0, 800.0], "SOL_BD": [1.3, 1.45],
              "SOL_AWC": [0.2, 0.18], "SOL_K": [45.5, 12.25],
              "SOL_CBN": [2.5, 0.8], "CLAY": [10.0, 15.0],
              "SILT": [30.0, 30.0], "SAND": [60.0, 55.0],
              "ROCK": [2.0, 4.0], "SOL_ALB": [0.2, 0.2],
              "USLE_K": [0.2, 0.2], "SOL_EC": [0.0, 0.0],
              "SOL_PH": [5.5, 5.6], "SOL_CACO3": [0.0, 0.0]},
}

SOL_LABELS = [
    (8, "SOL_Z", " Depth                [mm]:"),
    (9, "SOL_BD", " Bulk Density Moist [g/cc]:"),
    (10, "SOL_AWC", " Ave. AW Incl. Rock Frag  :"),
    (11, "SOL_K", " Ksat. (est.)      [mm/hr]:"),
    (12, "SOL_CBN", " Organic Carbon [weight %]:"),
    (13, "CLAY", " Clay           [weight %]:"),
    (14, "SILT", " Silt           [weight %]:"),
    (15, "SAND", " Sand           [weight %]:"),
    (16, "ROCK", " Rock Fragments   [vol. %]:"),
    (17, "SOL_ALB", " Soil Albedo (Moist)      :"),
    (18, "USLE_K", " Erosion K                :"),
    (19, "SOL_EC", " Salinity (EC, Form 5)    :"),
    (20, "SOL_PH", " Soil pH                  :"),
    (21, "SOL_CACO3", " Soil CACO3               :"),
]


def fixture_value(ext, name, row, dig):
    # distinct per row, so a row mix-up is detectable; integers for 0-digit fields
    if dig == 0:
        return float(row % 10)
    return round(row + 0.25, dig)


FILECIO_VALUES = {"NBYR": NBYR, "IYR": IYR, "IPRINT": 0, "NYSKIP": NYSKIP}


def expected_input_value(ext, name, file_id=None):
    """Value written for parameter `name` into the fixture file of type `ext`."""
    if ext == "cio":
        return float(FILECIO_VALUES[name])
    if ext == "sub" and name == "SUB_KM":
        return SUBBASINS[int(file_id[:5])]
    if ext == "hru" and name == "HRU_FR":
        return HRUS[file_id][4]
    cls = MANIPULATORS[ext]
    row, col1, col2, dig = cls.parInfo[name]
    return fixture_value(ext, name, row, dig)


MANIPULATORS = {
    "bsn": FileEdit.bsnManipulator,
    "gw": FileEdit.gwManipulator,
    "mgt": FileEdit.mgtManipulator,
    "sub": FileEdit.subManipulator,
    "hru": FileEdit.hruManipulator,
    "rte": FileEdit.rteManipulator,
    "cio": FileEdit.fileCioManipulator,
}

# lines that are not parameter rows (title / separator lines as in ArcSWAT files)
FILLER = {
    "mgt": {3: "Initial Plant Growth Parameters", 9: "General Management Parameters",
            15: "Urban Management Parameters", 18: "Irrigation Management Parameters",
            24: "Tile Drain Management Parameters", 28: "Management Operations:"},
    "hru": {18: "Special HRU: Pothole", 25: "", 26: "", 27: ""},
    "rte": {24: "    0.000    0.000    0.000    0.000    0.000    0.000    0.000    0.000    0.000    0.000    0.000    0.000    0.000"},
}


def param_line(value, dig, width, name):
    return ("%" + str(width) + "." + str(dig) + "f") % value + "    | " + name + " : synthetic test value"


def write_lines(path, lines):
    with open(path, "w", encoding="latin-1", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def parinfo_file(ext, header, n_rows, file_id=None):
    cls = MANIPULATORS[ext]
    by_row = {row: (name, col1, col2, dig) for name, (row, col1, col2, dig) in cls.parInfo.items()}
    lines = [header]
    for row in range(2, n_rows + 1):
        if row in by_row:
            name, col1, col2, dig = by_row[row]
            value = expected_input_value(ext, name, file_id)
            lines.append(param_line(value, dig, col2 - col1 + 1, name))
        else:
            lines.append(FILLER.get(ext, {}).get(row, "Section %d" % row))
    return lines


def hru_header(ext, file_id):
    sub, hru, luse, soil, fr = HRUS[file_id]
    return (" .%s file Watershed HRU:%d Subbasin:%d HRU:%d Luse:%s Soil: %s Slope: 0-9999 %s"
            % (ext, hru, sub, hru, luse, soil, HEADER_DATE))


def file_cio():
    lines = ["Master Watershed File: file.cio", "Project Description:",
             "General Input/Output section (file.cio):", "9/18/2026 12:00:00 AM ARCGIS-SWAT interface AV",
             "", "General Information/Watershed Configuration:", "fig.fig"]
    by_row = {row: name for name, (row, c1, c2, d) in FileEdit.fileCioManipulator.parInfo.items()}
    for row in range(8, 86):
        if row in by_row:
            name = by_row[row]
            lines.append("%16d    | %s : synthetic test value" % (FILECIO_VALUES[name], name))
        elif row == 58:
            lines.append("Output Information:")
        else:
            lines.append("               0    | FILLER%d : synthetic test value" % row)
    return lines


def sol_file(file_id):
    sub, hru, luse, soil, fr = HRUS[file_id]
    s = SOILS[soil]
    lines = [" .Sol file Watershed HRU:%d Subbasin:%d HRU:%d Luse:%s Soil: %s Slope: 0-9999 %s"
             % (hru, sub, hru, luse, soil, HEADER_DATE),
             " Soil Name: %s" % soil,
             " Soil Hydrologic Group: B",
             " Maximum rooting depth(m) : %.2f" % s["SOL_ZMX"],
             " Porosity fraction from which anions are excluded: %.3f" % s["ANION_EXCL"],
             " Crack volume potential of soil: %.3f" % s["SOL_CRK"],
             " Texture 1                : L-L"]
    for row, name, label in SOL_LABELS:
        lines.append(label + "".join("%12.2f" % v for v in s[name]))
    lines.append("")
    return lines


def make_txtinout(target):
    os.makedirs(target, exist_ok=True)
    write_lines(os.path.join(target, "file.cio"), file_cio())
    write_lines(os.path.join(target, "basins.bsn"),
                parinfo_file("bsn", "Basin data           .bsn file %s" % HEADER_DATE, 131))
    for sub in SUBBASINS:
        sub_id = "%05d0000" % sub
        write_lines(os.path.join(target, sub_id + ".sub"),
                    parinfo_file("sub", " .sub file Subbasin: %d %s" % (sub, HEADER_DATE), 40, sub_id))
        write_lines(os.path.join(target, sub_id + ".rte"),
                    parinfo_file("rte", " .rte file Subbasin: %d %s" % (sub, HEADER_DATE), 25, sub_id))
    for file_id in HRUS:
        write_lines(os.path.join(target, file_id + ".hru"),
                    parinfo_file("hru", hru_header("hru", file_id), 45, file_id))
        write_lines(os.path.join(target, file_id + ".gw"),
                    parinfo_file("gw", hru_header("gw", file_id), 17, file_id))
        mgt = parinfo_file("mgt", hru_header("mgt", file_id), 29, file_id)
        mgt += ["  4 15           1    1          1600.00000   0.00     0.00000 0.00   0.00  0.00",
                "  9 30           5                  0.00000", "                17"]
        write_lines(os.path.join(target, file_id + ".mgt"), mgt)
        write_lines(os.path.join(target, file_id + ".sol"), sol_file(file_id))


# ---------------------------------------------------------------------------------------
# outputs

def fortran_e(value, width, digits):
    """Fortran Ew.d formatting, e.g. fortran_e(8.782, 12, 4) -> ' 0.8782E+01'."""
    if value == 0:
        mantissa, exponent = 0.0, 0
    else:
        exponent = 0
        mantissa = abs(value)
        while mantissa >= 1.0:
            mantissa /= 10.0
            exponent += 1
        while mantissa < 0.1:
            mantissa *= 10.0
            exponent -= 1
        mantissa = round(mantissa, digits)
        if mantissa >= 1.0:
            mantissa /= 10.0
            exponent += 1
    text = ("%." + str(digits) + "f") % mantissa + ("E%+03d" % exponent)
    if value < 0:
        text = "-" + text
    if len(text) > width:
        text = text.replace("0.", ".", 1)
    return text.rjust(width)


RCH_LABELS = ["FLOW_INcms", "FLOW_OUTcms", "EVAPcms", "TLOSScms", "SED_INtons", "SED_OUTtons",
              "SEDCONCmg/kg", "ORGN_INkg", "ORGN_OUTkg", "ORGP_INkg", "ORGP_OUTkg", "NO3_INkg",
              "NO3_OUTkg", "NH4_INkg", "NH4_OUTkg", "NO2_INkg", "NO2_OUTkg", "MINP_INkg",
              "MINP_OUTkg", "CHLA_INkg", "CHLA_OUTkg", "CBOD_INkg", "CBOD_OUTkg", "DISOX_INkg",
              "DISOX_OUTkg", "SOLPST_INmg", "SOLPST_OUTmg", "SORPST_INmg", "SORPST_OUTmg",
              "REACTPSTmg", "VOLPSTmg", "SETTLPSTmg", "RESUSP_PSTmg", "DIFFUSEPSTmg",
              "REACBEDPSTmg", "BURYPSTmg", "BED_PSTmg", "BACTP_OUTct", "BACTLP_OUTct",
              "CMETAL#1kg", "CMETAL#2kg", "CMETAL#3kg", "TOT Nkg", "TOT Pkg", "NO3ConcMg/l",
              "WTMPdegc"]
RCH_NAMES = ["FLOW_IN", "FLOW_OUT", "EVAP", "TLOSS", "SED_IN", "SED_OUT", "SEDCONC", "ORGN_IN",
             "ORGN_OUT", "ORGP_IN", "ORGP_OUT", "NO3_IN", "NO3_OUT", "NH4_IN", "NH4_OUT",
             "NO2_IN", "NO2_OUT", "MINP_IN", "MINP_OUT", "CHLA_IN", "CHLA_OUT", "CBOD_IN",
             "CBOD_OUT", "DISOX_IN", "DISOX_OUT", "SOLPST_IN", "SOLPST_OUT", "SORPST_IN",
             "SORPST_OUT", "REACTPST", "VOLPST", "SETTLPST", "RESUSP_PST", "DIFFUSEPST",
             "REACBEDPST", "BURYPST", "BED_PST", "BACTP_OUT", "BACTLP_OUT", "CMETAL#1",
             "CMETAL#2", "CMETAL#3", "TOT_N", "TOT_P", "NO3CONC", "WTMP"]

SUB_LABELS = ["PRECIPmm", "SNOMELTmm", "PETmm", "ETmm", "SWmm", "PERCmm", "SURQmm", "GW_Qmm",
              "WYLDmm", "SYLDt/ha", "ORGNkg/ha", "ORGPkg/ha", "NSURQkg/ha", "SOLPkg/ha",
              "SEDPkg/ha", "LAT Q(mm)", "LATNO3kg/h", "GWNO3kg/ha", "CHOLAmic/L", "CBODU mg/L",
              " DOXQ mg/L", "TNO3kg/ha"]
SUB_NAMES = ["PRECIP", "SNOMELT", "PET", "ET", "SW", "PERC", "SURQ", "GW_Q", "WYLD", "SYLD",
             "ORGN", "ORGP", "NSURQ", "SOLP", "SEDP", "LAT_Q", "LATNO3", "GWNO3", "CHOLA",
             "CBODU", "DOXQ", "TNO3"]

HRU_LABELS = ["PRECIPmm", "SNOFALLmm", "SNOMELTmm", "IRRmm", "PETmm", "ETmm", "SW_INITmm",
              "SW_ENDmm", "PERCmm", "GW_RCHGmm", "DA_RCHGmm", "REVAPmm", "SA_IRRmm", "DA_IRRmm",
              "SA_STmm", "DA_STmm", "SURQ_GENmm", "SURQ_CNTmm", "TLOSSmm", "LATQGENmm", "GW_Qmm",
              "WYLDmm", "DAILYCN", "TMP_AVdgC", "TMP_MXdgC", "TMP_MNdgC", "SOL_TMPdgC",
              "SOLARMJ/m2", "SYLDt/ha", "USLEt/ha", "N_APPkg/ha", "P_APPkg/ha", "NAUTOkg/ha",
              "PAUTOkg/ha", "NGRZkg/ha", "PGRZkg/ha", "NCFRTkg/ha", "PCFRTkg/ha", "NRAINkg/ha",
              "NFIXkg/ha", "F-MNkg/ha", "A-MNkg/ha", "A-SNkg/ha", "F-MPkg/ha", "AO-LPkg/ha",
              "L-APkg/ha", "A-SPkg/ha", "DNITkg/ha", "NUPkg/ha", "PUPkg/ha", "ORGNkg/ha",
              "ORGPkg/ha", "SEDPkg/ha", "NSURQkg/ha", "NLATQkg/ha", "NO3Lkg/ha", "NO3GWkg/ha",
              "SOLPkg/ha", "P_GWkg/ha", "W_STRS", "TMP_STRS", "N_STRS", "P_STRS", "BIOMt/ha",
              "LAI", "YLDt/ha", "BACTPct", "BACTLPct", "WTAB CLIm", "WTAB SOLm", "SNOmm",
              "CMUPkg/ha", "CMTOTkg/ha", "QTILEmm", "TNO3kg/ha", "LNO3kg/ha", "GW_Q_Dmm",
              "LATQCNTmm"]
HRU_NAMES = ["PRECIP", "SNOFALL", "SNOMELT", "IRR", "PET", "ET", "SW_INIT", "SW_END", "PERC",
             "GW_RCHG", "DA_RCHG", "REVAP", "SA_IRR", "DA_IRR", "SA_ST", "DA_ST", "SURQ_GEN",
             "SURQ_CNT", "TLOSS", "LATQGEN", "GW_Q", "WYLD", "DAILYCN", "TMP_AV", "TMP_MX",
             "TMP_MN", "SOL_TMP", "SOLAR", "SYLD", "USLE", "N_APP", "P_APP", "NAUTO", "PAUTO",
             "NGRZ", "PGRZ", "NCFRT", "PCFRT", "NRAIN", "NFIX", "F-MN", "A-MN", "A-SN", "F-MP",
             "AO-LP", "L-AP", "A-SP", "DNIT", "NUP", "PUP", "ORGN", "ORGP", "SEDP", "NSURQ",
             "NLATQ", "NO3L", "NO3GW", "SOLP", "P_GW", "W_STRS", "TMP_STRS", "N_STRS", "P_STRS",
             "BIOM", "LAI", "YLD", "BACTP", "BACTLP", "WTAB_CLI", "WTAB_SOL", "SNO", "CMUP",
             "CMTOT", "QTILE", "TNO3", "LNO3", "GW_Q_D", "LATQCNT"]
# e11.5 fields in output.sub / output.hru, one character wider than their header label
WIDE = {"CHOLA", "BACTP", "BACTLP"}

YEAR_ROW = 99.0     # value of every variable in the yearly summary rows
AVERAGE_ROW = 88.0  # value of every variable in the closing average-annual rows

REACH_AREAS = {1: 10.0, 2: 15.0}
HRU_AREAS = {1: 6.0, 2: 4.0, 3: 5.0}


def out_value(j, area, year, step):
    """Value of variable j (index in *_NAMES) for area/year/step (month or julian day).

    j == 0 encodes time, j == 1 encodes area and step, the others identify the column.
    """
    if j == 0:
        return (year - 2000) + step / 1000.0
    if j == 1:
        return area + step / 1000.0
    return j + area / 10.0


def out_text(value, width, wide):
    if wide:
        # e.g. " .19200E+02", the leading zero is dropped to fit
        return fortran_e(value, width, 5).rjust(width + 1)
    return ("%" + str(width) + ".3f") % value


def out_header_lines():
    return ["1", "    SWAT Sep 18 2026    VER 2012/Rev 637 (synthetic test fixture)", "",
            "    General Input/Output section (file.cio):",
            "    9/18/2026 12:00:00 AM ARCGIS-SWAT interface AV", "", "", ""]


def output_rows(kind, names, periods):
    # periods: list of (year, mon_text, step or None) where step None = summary row
    rows = []
    areas = REACH_AREAS if kind in ("rch", "sub") else HRU_AREAS
    for year, mon, step in periods:
        for area, size in areas.items():
            values = []
            for j, name in enumerate(names):
                if step == "year":
                    value = YEAR_ROW
                elif step == "avg":
                    value = AVERAGE_ROW
                else:
                    value = out_value(j, area, year, step)
                if kind == "rch":
                    values.append(fortran_e(value, 12, 4))
                else:
                    values.append(out_text(value, 10, name in WIDE))
            if kind == "rch":
                prefix = "REACH%5d%9d%6s" % (area, 0, mon) + fortran_e(size, 12, 4)
            elif kind == "sub":
                prefix = "BIGSUB%4d%9d%5s" % (area, 0, mon) + fortran_e(size, 10, 5)
            else:
                sub = 1 if area < 3 else 2
                luse = HRUS[list(HRUS)[area - 1]][2]
                prefix = "%-4s%5d %s%5d%5d%5s" % (luse, area, list(HRUS)[area - 1], sub, 0, mon)
                prefix += fortran_e(size, 10, 5)
            rows.append(prefix + "".join(values))
    return rows


def header_line(kind, labels, names):
    if kind == "rch":
        return "       RCH      GIS   MON     AREAkm2" + "".join("%12s" % lab for lab in labels)
    if kind == "sub":
        return "       SUB      GIS  MON   AREAkm2" + "".join("%10s" % lab for lab in labels)
    return "LULC  HRU       GIS  SUB  MGT  MON   AREAkm2" + "".join("%10s" % lab for lab in labels)


def monthly_periods():
    periods = []
    for year in PRINTED_YEARS:
        for month in range(1, 13):
            periods.append((year, "%d" % month, month))
        periods.append((year, "%d" % year, "year"))
    periods.append((PRINTED_YEARS[-1], "%.1f" % len(PRINTED_YEARS), "avg"))
    return periods


def daily_periods(year):
    periods = []
    day = date(year, 1, 1)
    while day.year == year:
        periods.append((year, "%d" % day.timetuple().tm_yday, day.timetuple().tm_yday))
        day += timedelta(days=1)
    return periods


DAILY_RCH = ["FLOW_IN", "FLOW_OUT", "SED_OUT"]
DAILY_HRU = ["PRECIP", "ET", "SURQ_GEN"]


def make_outputs(target_monthly, target_daily):
    os.makedirs(target_monthly, exist_ok=True)
    os.makedirs(target_daily, exist_ok=True)
    for kind, labels, names in [("rch", RCH_LABELS, RCH_NAMES), ("sub", SUB_LABELS, SUB_NAMES),
                                ("hru", HRU_LABELS, HRU_NAMES)]:
        lines = out_header_lines() + [header_line(kind, labels, names)]
        lines += output_rows(kind, names, monthly_periods())
        write_lines(os.path.join(target_monthly, "output." + kind), lines)

    for kind, labels, names, subset in [("rch", RCH_LABELS, RCH_NAMES, DAILY_RCH),
                                        ("hru", HRU_LABELS, HRU_NAMES, DAILY_HRU)]:
        idx = [names.index(n) for n in subset]
        sub_labels = [labels[i] for i in idx]
        lines = out_header_lines() + [header_line(kind, sub_labels, subset)]
        # keep the variable index of the full list, so out_value stays comparable
        rows = output_rows(kind, names, daily_periods(PRINTED_YEARS[0]))
        width = 12 if kind == "rch" else 10
        start = 37 if kind == "rch" else 44
        for row in rows:
            values = "".join(row[start + i * width:start + (i + 1) * width] for i in idx)
            lines.append(row[:start] + values)
        write_lines(os.path.join(target_daily, "output." + kind), lines)


if __name__ == "__main__":
    make_txtinout(os.path.join(HERE, "TxtInOut"))
    make_outputs(os.path.join(HERE, "output_monthly"), os.path.join(HERE, "output_daily"))
    print("fixtures written to", HERE)
