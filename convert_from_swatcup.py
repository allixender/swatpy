import os
from pathlib import Path
import uuid
import shutil
import sys
import getopt
import traceback

import numpy as np
import pandas as pd

import chardet
import pyswat

from pyswat import FileEdit

# bsnManipulator
# import pyswat.FileEdit.gwManipulator
# import pyswat.FileEdit.mgtManipulator
# import pyswat.FileEdit.subManipulator
# import pyswat.FileEdit.hruManipulator
# import pyswat.FileEdit.solManipulator
# import pyswat.FileEdit.rteManipulator

allowed_endings = ["bsn", "gw", "mgt", "sub", "hru", "sol", "rte"]


def guess_text_encoding(infile):
    f = open(infile, "rb")
    detector = chardet.UniversalDetector()
    detector.reset()
    for line in f:
        detector.feed(line)
    f.close()
    detector.close()
    print(detector.result)
    enc = detector.result["encoding"]
    redirects = ["", "ascii"]
    if enc is None:
        enc = "latin-1"
        print(f"model text encoding unclear, assuming {enc}")
        return enc
    elif enc in redirects:
        enc = "latin-1"
        print(f"model text encoding unlikely, assuming {enc}")
        return enc
    else:
        print(f"model text encoding set to {enc}")
        return enc


def parse(infile, outfile):
    # dtype = [("f0", "|U30"), ("f1", "<f8"), ("f2", "<f8")]
    # par_file_load = np.genfromtxt(par_file_name, dtype=dtype, encoding="utf-8")
    enc = guess_text_encoding(infile)

    with open(infile, "r", encoding=enc) as f:
        line_counter=0
        work_pars = []

        for line in f.readlines():
            line_counter += 1
            trim = line.strip()
            if trim.startswith("#") or trim.strip().startswith("//") or len(trim) == 0:
                continue
            else:
                for tp in allowed_endings:

                    if trim.find("." + tp) > -1 or trim.find("." + tp.upper()) > -1:
                        print(f"woring with {tp} -> {trim}")

                        trim_a = trim.replace("." + tp, "__" + tp)
                        trim_u = trim_a.replace("." + tp.upper(), "__" + tp)

                        if trim_u.startswith("V__"):
                            trim_u = trim_u.replace("V__", "v__", 1)
                        if trim_u.startswith("A__"):
                            trim_u = trim_u.replace("A__", "v__", 1)
                        if trim_u.startswith("R__"):
                            trim_u = trim_u.replace("R__", "v__", 1)

                        if trim_u.find("()") > -1:
                            trim_u = trim_u.replace("()", "")

                        paramlist = (
                            list(FileEdit.bsnManipulator.parInfo.keys())
                            + list(FileEdit.gwManipulator.parInfo.keys())
                            + list(FileEdit.mgtManipulator.parInfo.keys())
                            + list(FileEdit.subManipulator.parInfo.keys())
                            + list(FileEdit.hruManipulator.parInfo.keys())
                            + list(FileEdit.solManipulator.parInfo.keys())
                            + list(FileEdit.rteManipulator.parInfo.keys())
                        )

                        try:
                            field_list = trim_u.split(' ')[0].strip().split("__")
                            how = field_list[0]
                            param_field = field_list[1]
                            manip_ext = field_list[2]
                            if len(field_list) > 3:
                                hydrp = field_list[3]
                            if len(field_list) > 4:
                                soltext = field_list[4]
                            if len(field_list) > 5:
                                landuse = field_list[5]
                            if len(field_list) > 6:
                                subbsn = field_list[6]
                            if len(field_list) > 7:
                                slope = field_list[7]

                            if not how in ['v', 'a', 'r']:
                                print(f"error, line {line_counter} not correct modifier {how} not in ['v', 'a', 'r']")
                                continue
                            if not param_field in paramlist:
                                print(f"error, line {line_counter} param_field {param_field} not known")
                                continue
                            if not manip_ext in allowed_endings:
                                print(f"error, line {line_counter} file type {manip_ext} not in {allowed_endings}")
                                continue

                            already_used_params = [t[0] for t in work_pars]



                            if not param_field in already_used_params:
                                work_pars.append((param_field, trim_u))
                            else:
                                print(f"error, line {line_counter} param field {param_field} already used before")
                                continue
                        except Exception as e:
                            print('error parsing')
                            print(trim_u)
                            print(repr(e))
                    else:
                        continue
                # print(trim)
                # print(trim_u)
        for t in work_pars:
            print(t)
        with open(outfile, 'w', encoding=enc) as outf:
            for t in work_pars:
                outf.write(t[1] + "\n")




def main(argv):
    infile = ""
    outfile = ""
    try:
        opts, args = getopt.getopt(argv, "hi:o:", ["infile=", "outfile="])
    except getopt.GetoptError:
        print("test.py -i <infile> -o <outfile>")
        sys.exit(2)
    for opt, arg in opts:
        if opt == "-h":
            print("test.py -i <infile> -o <outfile>")
            sys.exit()
        elif opt in ("-i", "--infile"):
            infile = arg

        elif opt in ("-o", "--outfile"):
            outfile = arg

    print("Infile is " + infile)
    print("Outfile is " + outfile)

    parse(infile, outfile)


if __name__ == "__main__":
    main(sys.argv[1:])
