import numpy as np
import pandas as pd
from pathlib import Path
import uuid
import shutil
import os
import sys
import subprocess
import json
import traceback
import chardet

from .FileEdit import fileCioManipulator, bsnManipulator, gwManipulator, solManipulator
from .FileEdit import hruManipulator, rteManipulator, mgtManipulator, subManipulator


class SwatModel(object):

    def __init__(self):
        self.swat_version = '2012'
        self.working_dir = 'swat2012_047fd78'
        self.metadata_obj = '.swatmodel.json'
        self.swat_exec = 'swat_64rel.exe'
        self.model_text_encoding = 'utf-8'
        self.last_run_succesful = False
        self.last_run_logs = ''
        self.fileManipulators = None

    
    def is_runnable(self):
        is_runnable = 0

        takes = []
        take_1 = shutil.which(self.swat_exec)
        if not take_1 is None:
            takes.append(take_1)

        take_2 = shutil.which(os.path.join(self.working_dir, self.swat_exec))
        if not take_2 is None:
            takes.append(take_2)

        if len(takes) < 1:
            print(f"{self.swat_exec} not in default paths")
        else:
            for elem in takes:
                swx = Path(elem)
                if swx.exists() and swx.is_file():
                    if os.access(elem, os.X_OK):
                        print(f"{elem} is executable")
                        self.swat_exec = str(elem)
                        is_runnable = 1
        
        return is_runnable
    

    def guess_model_text_encoding(model_dir):
        f = open(os.path.join(model_dir, 'file.cio'), 'rb')
        detector = chardet.UniversalDetector()
        detector.reset()
        for line in f:
            detector.feed(line)
        f.close()
        detector.close()
        print(detector.result)
        enc = detector.result['encoding']
        redirects = ['', 'ascii']
        if enc is None:
            enc = 'latin-1'
            print(f"model text encoding unclear, assuming {enc}")
            return enc
        elif enc in redirects:
            enc = 'latin-1'
            print(f"model text encoding unlikely, assuming {enc}")
            return enc
        else:
            print(f"model text encoding set to {enc}")
            return enc


    # FACTORY method, no self
    # pylint: disable=no-self-argument
    def initFromTxtInOut(txtInOut, copy=None, target_dir=None, swat_version='2012', force=False):
        """initialise the SwatModel working object from loading a SWAT 2012 TxtInOut directory
        
        Keyword arguments:
        argument -- description
        Return: return_description
        """

        config = {
            'swat_version' : '2012',
            'working_dir' : 'swat2012_047fd78',
            'metadata_obj' : '.swatmodel.json',
            'swat_exec' : 'swat_64rel.exe',
            'model_text_encoding' : 'utf-8'
        }

        if copy is None:
            raise ValueError("""Warning, you must explicitely state if you want to create a copy of the 
            TxtInOut (copy=True) dir or directly work in the exisiting folder (copy=False).
            Aborting!""")
        
        if copy == True:
            if not target_dir is None and target_dir != '':
                # check if target_dir exists and/or is empty
                test_path = Path(target_dir)
                
                if test_path.is_dir():
                    print(f"{test_path} exists ... ")
                    is_empty = not any(test_path.iterdir())
                    if is_empty or force:
                        print('... forcing init here and copy - not fully implemented')
                        try:
                            shutil.copytree(Path(txtInOut), test_path)
                            print('copying to working directory: ' + os.path.abspath(test_path))
                            config['working_dir'] = str(os.path.abspath(test_path))

                        except Exception as e:
                            print(e)
                            traceback.print_exc(file=sys.stdout)
                            raise ValueError("Couldn't force copy overwrite - error.")

                    else:
                        print("not empty and no force overwrite, aborting!")
                        raise ValueError("not empty and no force overwrite, aborting!")
                else:
                    try:
                        test_path = Path(os.path.join(os.getcwd(), target_dir))
                        # assuming relative to here
                        shutil.copytree(Path(txtInOut), test_path)
                        print('creating working directory: ' + os.path.abspath(test_path))
                        config['working_dir'] = str(os.path.abspath(test_path))

                    except Exception as e:
                        print(e)
                        traceback.print_exc(file=sys.stdout)
                        raise ValueError('Error copying.')

            else:
                temp_id = uuid.uuid1()
                try:
                    test_path = Path(os.path.join(os.getcwd(), f"swat_{temp_id}"))
                    shutil.copytree(Path(txtInOut), test_path)
                    print('creating working directory: ' + os.path.abspath(test_path))
                    config['working_dir'] = str(os.path.abspath(test_path))
                    
                except Exception as e:
                    print(e)
                    traceback.print_exc(file=sys.stdout)
                    raise ValueError('Error copying.')
                    
        else:
            if force == True:
                # init here
                # test if .swatmodel.json exists
                config['working_dir'] = str(Path(txtInOut).resolve().absolute())
                
            else:
                print("non-copy init without force confirm, aborting!")
                raise ValueError("non-copy init without force confirm, aborting!")
            
        # check if referenced TxtInOut directory exists
        # check if target_dir is set 
        # copy True then target_dir must be different from TxtInOut folder
        # create target_dir, shutil copy TxtInOut content over
        # check if SWAT executable in path
        # only if user is certain then swatmodel can be initialised in origin TxtInOut folder
        
        model = SwatModel()
        model.working_dir = config['working_dir']
        # metadata obj is for flexibility and should not be changed really
        model.metadata_obj = config['metadata_obj']
        # executable should be discovered or provided
        model.swat_exec = config['swat_exec']
        model.swat_version = config['swat_version']
        
        config['model_text_encoding'] = SwatModel.guess_model_text_encoding(model.working_dir)
        model.model_text_encoding = config['model_text_encoding']
        
        model.is_runnable()

        # TODO write self.metadata_obj = os.path.join(working_dir, '.swatmodel.json')
        with open(os.path.join(model.working_dir, '.swatmodel.json'), 'w') as fp:
            json.dump(config, fp)

        return model

    # FACTORY method, no self
    # pylint: disable=no-self-argument
    def loadModelFromDirectory(target_dir):
        """initialise the SwatModel working object from the metadata file from existing working directory
        
        Keyword arguments:
        argument -- description
        Return: return_description
        """
        
        config = {
            'swat_version' : '2012',
            'working_dir' : 'swat2012_047fd78',
            'metadata_obj' : '.swatmodel.json',
            'swat_exec' : 'swat_64rel.exe',
            'model_text_encoding' : 'utf-8'
        }

        if not target_dir is None and target_dir != '':
            # check if src dir exists and is not empty
            test_path = Path(target_dir)
            
            if test_path.is_dir():
                print(f"{test_path} exists ... ")

                try:
                    with open(os.path.join(Path(test_path), '.swatmodel.json'), 'r') as fp:
                        config_load = json.load(fp)
                        # config_load = json.loads(js)
                    
                    for key in config_load.keys():
                        config.update({ key: config_load[key]})

                    config['working_dir'] = os.path.abspath(test_path)
                    print(config)
                except Exception as e:
                        print(e)
                        traceback.print_exc(file=sys.stdout)
                        raise ValueError("error loading config, aborting!")

        model = SwatModel()
        model.working_dir = config['working_dir']
        # metadata obj is for flexibility and should not be changed really
        model.metadata_obj = config['metadata_obj']
        # executable should be discovered or provided
        model.swat_exec = config['swat_exec']
        model.swat_version = config['swat_version']
        
        config['model_text_encoding'] = SwatModel.guess_model_text_encoding(model.working_dir)
        model.model_text_encoding = config['model_text_encoding']
        
        model.is_runnable()

        # TODO write self.metadata_obj = os.path.join(working_dir, '.swatmodel.json')
        with open(os.path.join(model.working_dir, '.swatmodel.json'), 'w') as fp:
            json.dump(config, fp)
 
        return model
    

    def run(self, capture_logs=True, silent=False):

        # needs metadata swat exec and working_dir

        curdir = os.getcwd()

        # subprocess.call / Popen swat_exec, check if return val is 0 or not
        # yield logs?
        try:
            os.chdir(self.working_dir)
            
            logs = []
            o = subprocess.Popen([os.path.join(self.working_dir, self.swat_exec)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            
            while o.poll() is None:
                for b_line in o.stdout:
                    line = b_line.decode().strip()
                    # sys.stdout.write(line)
                    if not silent:
                        print(line)
                    if capture_logs:
                        logs.append(line.strip())
            
            if o.returncode == 0:
                self.last_run_succesful = True
            else:
                self.last_run_succesful = False

            if capture_logs:
                self.last_run_logs = '\n'.join(logs)
            else:
                self.last_run_logs = ''

        except Exception as e:
            self.last_run_succesful = False
            print(repr(e))
            traceback.print_exc(file=sys.stdout)
            self.last_run_logs(repr(e))
        finally:
            os.chdir(curdir)

        return o.returncode


    def read_output(self, out_types):
        # output.rch, output.sub ... 
        # maybe as tuple (rch, field_x), (rch, field_y)
        # return as numpy/pandas times series?

        return np.array([1, 3, 5])
    

    # serialize the mode lconfig from all input files and the model metadata into avro record
    # for binary transport (e.g. network, archive, database ...)
    def toAvro(self):
        # make the whole thing into mem and avro codec and return serialized binary object blob
        
        # including .swatmodel.json metadata
        pass


    # FACTORY method, no self
    # pylint: disable=no-self-argument
    def fromAvro(avro_model, target_dir):
        # deserialise avro_model into target path, and then init/load from metadata

        model = SwatModel.loadModelFromDirectory( target_dir)
        
        return model
    

    def getFileManipulators(self, force_update=False):
        
        if self.fileManipulators is None or force_update == True:

            files=os.listdir(self.working_dir)

            manipulators = {}

            fileCio = []
            fileCio.append(fileCioManipulator('file.cio', ["NBYR", "IYR", "IPRINT", "NYSKIP"], self.working_dir, self.model_text_encoding))
            manipulators["fileCio"] = fileCio

            ### here all parameters from the bsn-file are assigned in the dictionary for calibration
            bsnfiles = [i for i in files if i.endswith(".bsn")]
            bsn = []
            for i in bsnfiles:
                bsn.append(bsnManipulator(i, ["SURLAG","SFTMP","SMTMP","SMFMX", "SMFMN", "SNOCOVMX", "SNO50COV", "TIMP","ESCO","EPCO"], self.working_dir, self.model_text_encoding))
            manipulators["bsn"] = bsn

            ### here all parameters from the gw-file are assigned in the dictionary for calibration
            gwfiles = [i for i in files if i.endswith(".gw")]
            gw = []
            for i in gwfiles:
                gw.append(gwManipulator(i, ["GW_DELAY","ALPHA_BF","GW_REVAP","GWQMN","RCHRG_DP","REVAPMN"], self.working_dir, self.model_text_encoding))
            manipulators["gw"] = gw

            ### here all parameters from the sol-file are assigned in the dictionary for calibration
            solfiles = [i for i in files if i.endswith(".sol")]
            sol = []
            for i in solfiles:
                if solManipulator(i,[],self.working_dir).landuse != "URBN":
                    sol.append(solManipulator(i, ["SOL_K","SAND", "CLAY", "SOL_CBN", "SOL_BD", "SOL_AWC", "SOL_CRK"], self.working_dir, self.model_text_encoding))
            manipulators["sol"] = sol

            ## here all parameters from the hru-file are assigned in the dictionary for calibration
            hrufiles = [i for i in files if i.endswith(".hru") and i.startswith("0")]
            hru=[]
            for i in hrufiles:
                if i[0].isdigit():
                    hru.append(hruManipulator(i, ["HRU_FR","ESCO","EPCO","OV_N","CANMX","SLSUBBSN", "SLSOIL", "LAT_TTIME"], self.working_dir, self.model_text_encoding))
            manipulators["hru"] = hru

            ### here all parameters from the rte-file are assigned in the dictionary for calibration
            rtefiles = [i for i in files if i.endswith(".rte")]
            rte = []
            for i in rtefiles:
                rte.append(rteManipulator(i, ["CH_N2", "CH_K2", "CH_S2"], self.working_dir, self.model_text_encoding))
            manipulators["rte"] = rte

            ### here all parameters from the rte-file are assigned in the dictionary for calibration
            subfiles = [i for i in files if i.endswith(".sub") and i.startswith("0")]
            sub = []
            for i in subfiles:
                sub.append(subManipulator(i, ["SUB_KM", "CH_L1", "CH_S1", "CH_W1", "CH_K1", "CH_N1", "CO2"], self.working_dir, self.model_text_encoding))
            manipulators["sub"] = sub

            ### here all parameters from the mgt-file are assigned in the dictionary for calibration
            mgtfiles = [i for i in files if i.endswith(".mgt")]
            mgt = []
            for i in mgtfiles:
                mgt.append(mgtManipulator(i, ["CN2"], self.working_dir, self.model_text_encoding))
            manipulators["mgt"] = mgt

            self.fileManipulators = manipulators

        # always return
        return self.fileManipulators
    

    def reloadFileManipulators(self):
        return self.getFileManipulators(force_update=True)
    

    def enrichModelMeta(self, verbose=True, update_meta=True):

        manipulators = self.getFileManipulators()

        # print( manipulators['fileCio'][0].filename)
        # print( manipulators['fileCio'][0].parValue)

        # "NBYR", "IYR", "IPRINT", "NYSKIP"
        self.n_sub_basins = len(manipulators['sub'])
        self.n_hru = len(manipulators['hru'])

        self.n_years_simulated = int(manipulators['fileCio'][0].parValue['NBYR'][0])
        self.beginning_year_simulation = int(manipulators['fileCio'][0].parValue['IYR'][0])
        self.outprint_code = int(manipulators['fileCio'][0].parValue['IPRINT'][0]) # (0 month, 1 day, 2 year)
        self.n_years_skip = int(manipulators['fileCio'][0].parValue['NYSKIP'][0])
        
        from datetime import datetime as dt

        start_load_year = self.beginning_year_simulation + self.n_years_skip
        last_year = self.beginning_year_simulation + self.n_years_simulated

        start = dt(self.beginning_year_simulation,1,1)
        start_load = dt(start_load_year,1,1)
        end_sim = dt(last_year,12,31)

        self.n_days_skip = (start_load - start).days
        self.readout_years = last_year - start_load_year
        self.readout_days = (end_sim - start_load).days

        if verbose == True:
            print(f"subs/rch {self.n_sub_basins}, number of HRU {self.n_hru}")
            print(f"start year {self.beginning_year_simulation}, full sim length years {self.n_years_simulated}")
            print(F"skip sim init years {self.n_years_skip} - skip sim years in days {self.n_days_skip}")
            print(f"number of years sim/obs  {self.readout_years} - in days {self.readout_days}")
            print(f"sim is {self.outprint_code}# (0 month, 1 day, 2 year)")

        config = {
            'swat_version' : self.swat_version,
            'working_dir' : self.working_dir,
            'metadata_obj' : self.metadata_obj,
            'swat_exec' : self.swat_exec,
            'model_text_encoding' : self.model_text_encoding,

            'n_sub_basins' : self.n_sub_basins,
            'n_hru' : self.n_hru,

            'n_years_simulated' : self.n_years_simulated,
            'beginning_year_simulation' : self.beginning_year_simulation,
            'outprint_code' : self.outprint_code,
            'n_years_skip' : self.n_years_skip,

            'n_days_skip' : self.n_days_skip,
            'readout_years' : self.readout_years,
            'readout_days' : self.readout_days
        }

        
        if update_meta == True:
            try:
                with open(os.path.join(config['working_dir'], '.swatmodel.json'), 'w') as fp:
                    json.dump(config, fp)
            except Exception as e:
                print(e)
                traceback.print_exc(file=sys.stdout)
                print('Error updating .swatmodel.json model metadata file.')

        return config
