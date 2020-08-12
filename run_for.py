import os
from pathlib import Path
import uuid
import shutil
import sys
import getopt
import traceback

import numpy as np
import pandas as pd

import spotpy
from pyswat import SimManage, ReadOut, FileEdit

swat_bin = "/gpfs/hpc/home/kmoch/bin/swat_rel640_static"


def update_SLSOIL(mpath):

    model3 = SimManage.SwatModel.initFromTxtInOut(
        mpath, copy=False, target_dir=None, swat_version="2012", force=True
    )
    print(model3.working_dir)

    manipulators = model3.getFileManipulators()

    """
    Instruction to edit SLSOIL

	The variable "SLSOIL" within hru table of project.mdb will be having a value of "0" by default. 
    This column needs to be replaced with the values in the variable "SLSUBBSN".
    """

    # hrufiles SLSUBBSN -> SLSOIL
    for hruMan in manipulators["hru"]:
        hruMan.setChangePar("SLSOIL", hruMan.parValue["SLSUBBSN"][0], "s")
        hruMan.finishChangePar()

    print("after reload()")
    manip2 = model3.reloadFileManipulators()
    hruMan = manip2["hru"][-1]
    print(
        f"{hruMan.filename} SLSUBBSN {hruMan.parValue['SLSUBBSN'][0]} -> SLSOIL {hruMan.parValue['SLSOIL'][0]}"
    )

    model3.swat_exec = swat_bin
    model3.enrichModelMeta()
    model3.is_runnable()

    model3.run()


def update_LAT_TTIME(mpath):

    model3 = SimManage.SwatModel.initFromTxtInOut(
        mpath, copy=False, target_dir=None, swat_version="2012", force=True
    )
    print(model3.working_dir)

    manipulators = model3.getFileManipulators()
    """
    Instruction to edit LAT_TTIME

	The variable "LAT_TTIME" will also be having a default value of "0". 
    This needs to be replaced with the values of "LAT_TTIME" estimated using the equation provided in SWAT theoretical documentation. 
    - LAT_TTIME   (TTlag ): Lateral flow travel time (days)
    - SLSOIL   (Lhill): Hillslope length (m)
    - SOL_K   Ksat: Saturated hydraulic conductivity (mm/hr)
    - If drainage tiles are present in the HRU, lateral flow travel time or TTlag is calculated as :
        〖TT〗_(lag )= 〖tile〗_lag/24. Where tilelag is the drain tile lag time (hrs)
        〖TT〗_(lag  )=10.4  L_hill/K_(sat,max)   (Page 163, SWAT 2009 theory)
        〖TT〗_(lag  )is the lateral flow travel time (days), L_hill is the hillslope length (m) (SLSOIL)
    K_(sat,mx) is the highest layer saturated hydraulic conductivity in the soil profile (mm/hr) (Obtain it from the SOL table from the database by finding the soil layer for each HRU that has the highest hydraulic conductivity)

    After replacing the values of SLSOIL and LAT_TTIME, rewrite the hru file before running SWAT.
    """

    # hrufiles set LAT_TTIME
    for hruMan in manipulators["hru"]:
        hru_id = hruMan.filename.strip().split(".")[0]
        SLSOIL_val = hruMan.parValue["SLSOIL"][0]
        LAT_TTIME_val = hruMan.parValue["LAT_TTIME"][0]
 
        SOL_K_MAX = 1
        for solMan in manipulators["sol"]:
            sol_id = solMan.filename.strip().split(".")[0]
            if sol_id == hru_id:
                SOL_K = solMan.parValue["SOL_K"]
                SOL_K_MAX = np.array(SOL_K).max()
       
        LAT_TTIME_val_new = 10.4 * (SLSOIL_val / SOL_K_MAX)

        hruMan.setChangePar("LAT_TTIME", LAT_TTIME_val_new, "s")
        hruMan.finishChangePar()
   
    print("after reload()")
    manip2 = model3.reloadFileManipulators()
    hruMan = manip2["hru"][-1]
    print(
      f"{hruMan.filename} LAT_TTIME_val_new {hruMan.parValue['LAT_TTIME'][0]} -> LAT_TTIME_val_old {LAT_TTIME_val}"
    )

    model3.swat_exec = swat_bin
    model3.enrichModelMeta()
    model3.is_runnable()

    model3.run()


class swat_callib_setup(object):

    def __init__(self, swat_model, observed_data, param_defs, parallel="seq", temp_dir=None):

        self.model = swat_model
        self.observed_data = observed_data
        
        self.params = []
        for i in range(len(param_defs)):
            self.params.append(
                spotpy.parameter.Uniform(
                    name=param_defs[i][0],
                    low=param_defs[i][1],
                    high=param_defs[i][2],
                    optguess=np.mean( [param_defs[i][1], param_defs[i][2]] )))
    
        self.temp_dir = temp_dir
        self.parallel = parallel

        if self.parallel == "seq":
            pass

        if self.parallel == "mpi":

            from mpi4py import MPI

            comm = MPI.COMM_WORLD
            self.mpi_size = comm.Get_size()
            self.mpi_rank = comm.Get_rank()
    

    def onerror(self, func, path, exc_info):
        import stat
        if not os.access(path, os.W_OK):
            # Is the error an access error ?
            os.chmod(path, stat.S_IWUSR)
            func(path)
        else:
            raise


    def prep_temp_model_dir(self):
        temp_id = uuid.uuid1()

        if self.parallel == "mpi":
            try:
                temp_id = f'mpi{self.mpi_rank}_' + str(temp_id)
            except NameError:
                pass

        test_path = f"swat_{temp_id}"

        if self.temp_dir is None:
            test_path = Path(os.path.join(os.getcwd(), test_path))
        else:
            test_path = Path(os.path.join(self.temp_dir, test_path))

        if os.path.exists(test_path):
            print('Deleting temp folder ' + str(test_path))
            shutil.rmtree(test_path, onerror=self.onerror)

        print('Copying model to folder ' + str(test_path))
        shutil.copytree(self.model.working_dir, test_path)

        try:
            m = SimManage.SwatModel.loadModelFromDirectory(test_path)
            if m.is_runnable() == 0:
               m.swat_exec = self.model.swat_exec
            return m
        except ValueError:
            m = SimManage.SwatModel.initFromTxtInOut(test_path, copy=False, force=True)
            if m.is_runnable() == 0:
               m.swat_exec = self.model.swat_exec
            return m
    

    def remove_temp_model_dir(self, model):
        try:
            print('Deleting temp folder ' + str(model.working_dir))
            shutil.rmtree(model.working_dir, onerror=self.onerror)
        except Exception as e:
            print(e)
            traceback.print_exc(file=sys.stdout)
            print('Error deleting tmp model run')
            pass
    

    def manipulate_model_params(self, model, parameters):

        print(f"this iteration's parameters:")
        print(parameters)
        # print(self.params[0].name)
        # print(parameters['v__SFTMP__bsn'])
        
        how_apply = {
            'v':'s',
            'r':'*',
            'a':'+'
        }
        
        for idx, param_string in enumerate(self.params):
            # print(param_string.name)
            # print(idx)
            # print(len(param_string.name))
            # print(parameters[idx])
            
            # slice the stringname open
            # how  param  manipu   1        2         3          4         5   (times __)
            # orig: x__<parname>.<ext>__<hydrp>__<soltext>__<landuse>__<subbsn>__<slope>
            # [0] split ('.')  split ('__') [0]  how v_s r_* a_+  [1] param field name
            # ---
            # [1] split('__') [0] manipulator/file type [1] hydgrp ... etc
            # only __ double underscore
            # how  param  manipu   3        4          5          6         7   (times __)
            # x__<parname>__<ext>__<hydrp>__<soltext>__<landuse>__<subbsn>__<slope>

            field_list = param_string.name.split('__')
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
            
            changeHow = how_apply[how]
            
            print(f"field {param_field} in file/manip {manip_ext} will be changed via '{changeHow}' and value {parameters[idx]} ")
            if len(field_list) > 3:
                print(f"ignored constraints ({field_list[2:]})")

            manipulator_handle = model.getFileManipulators()[manip_ext]
            
            # here we could add addtional conditions for finer granularity
            for m in manipulator_handle:
                m.setChangePar(param_field, parameters[idx], changeHow)
                m.finishChangePar()


    def parameters(self):
        return spotpy.parameter.generate(self.params)
    
    
    # provide the available observed data
    def evaluation(self):
        # observations = [self.observed_data]
        return self.observed_data


    # Simulation function must not return values besides for which evaluation values/observed data are available
    def simulation(self, parameters):
        the_model = self.prep_temp_model_dir()
        the_model.enrichModelMeta(verbose=False)
        if the_model.is_runnable() == 0:
           print(f"{the_model.swat_exec} is NOT runnable: {the_model.is_runnable()}")

        self.manipulate_model_params(the_model, parameters)

        # TODO: edit the correct parameters in SWAT files

        ret_val = the_model.run(capture_logs=False, silent=False)
        print(f"returns {ret_val} - vs {the_model.last_run_succesful}")
        # print(model4.last_run_logs)

        reach = 1
        # simulated data
        reader1 = ReadOut.rchOutputManipulator(["FLOW_OUT"], [reach], "skip", True, 0, the_model.working_dir, iprint='month', stats_dir=self.temp_dir)
        sim_flow_1 = reader1.outValues["FLOW_OUT"][reach]

        # cleanup
        self.remove_temp_model_dir(the_model)
        return sim_flow_1


    # if we want to minimize our function, we can select a negative objective function
    def objectivefunction(self, simulation, evaluation):
        print("simulation")
        print(len(simulation))
        print("evaluation")
        print(len(evaluation))

        objectivefunction = spotpy.objectivefunctions.nashsutcliffe(evaluation,simulation)      
        return objectivefunction


def model_callib(model, mpath, param_file, sampler, repetitions):
    
    import uuid

    target_dir = f"/tmp/callib_{model}_{sampler}_{uuid.uuid4()}"

    model4 = SimManage.SwatModel.initFromTxtInOut(txtInOut=mpath,
      copy=True, target_dir=os.path.join(target_dir, 'TxtInOut'), force=False)
    temp_dir = target_dir

    obs_filename = os.path.join('observed','pori_flow_monthly_2003-2010.txt')
    f = open(obs_filename, "r")
    lines = f.readlines()
    f.close()
    measured = []
    for i in lines:
        measured.append(i.split(";")[2].strip())
        
    obs = np.array([float(i) for i in measured])

    obs_masked = np.ma.masked_where(obs == -9999.0, obs)

    par_file_name = param_file
    print(f'loading parameter file {par_file_name}')

    dtype=[('f0', '|U30'), ('f1', '<f8'), ('f2', '<f8')]
    par_file_load = np.genfromtxt(par_file_name, dtype=dtype, encoding='utf-8')

    parallel = "seq"
    model4.swat_exec = swat_bin
    spot_setup=swat_callib_setup(model4, obs_masked, par_file_load, parallel=parallel, temp_dir=temp_dir)

    dbformat = "csv"

    lhs_calibrator_sampler = None
    if sampler == "LHS":
        lhs_calibrator_sampler = spotpy.algorithms.lhs(spot_setup, parallel=parallel, dbname=f"{model}_{sampler}_{repetitions}", dbformat=dbformat)
    if sampler == "MC":
        lhs_calibrator_sampler = spotpy.algorithms.mc(spot_setup, parallel=parallel, dbname=f"{model}_{sampler}_{repetitions}", dbformat=dbformat)
    if sampler == "ROPE":
        lhs_calibrator_sampler = spotpy.algorithms.rope(spot_setup, parallel=parallel, dbname=f"{model}_{sampler}_{repetitions}", dbformat=dbformat)
    if sampler == "DEMCZ":
        lhs_calibrator_sampler = spotpy.algorithms.demcz(spot_setup, parallel=parallel, dbname=f"{model}_{sampler}_{repetitions}", dbformat=dbformat)

    lhs_calibrator_sampler.sample(repetitions)

    callib_results = lhs_calibrator_sampler.getdata()

    print(spotpy.analyser.get_best_parameterset(callib_results))
    
    # spotpy.analyser.plot_parameterInteraction(callib_results) 
    # spotpy.analyser.plot_parametertrace_algorithms(result_lists=[callib_results], algorithmnames=['lhs'], spot_setup=spot_setup)

    fast_sensitivity_sampler = spotpy.algorithms.fast(spot_setup,  dbname=f"{model}_{sampler}_{repetitions}_FAST",  dbformat=dbformat)
    fast_sensitivity_sampler.sample(repetitions)

    sens_results = fast_sensitivity_sampler.getdata()

    import shutil

    shutil.move(target_dir, os.path.join('/gpfs/hpc/home/kmoch/swat', 'callib_outs'))


"""
hwsd_par_inf.txt
isric10km_par_inf.txt
isric1km_par_inf.txt
isric250m_par_inf.txt
isric5km_par_inf.txt
pori3_par_inf.txt
"""

config = {
    "hwsd": {"path": "Balaji_HWSD1.Sufi2.SwatCup"},
    "isric10km": {"path": "Balaji_ISRIC_10km.Sufi2.SwatCup"},
    "isric1km": {"path": "Balaji_ISRIC_1km.Sufi2.SwatCup"},
    "isric250m": {"path": "Balaji_ISRIC_250m.Sufi2.SwatCup"},
    "isric5km": {"path": "Balaji_ISRIC_5km.Sufi2.SwatCup"},
    "pori3": {"path": "Pori3_sim2.Sufi2.SwatCup"},
}

models = ["pori3", "hwsd", "isric10km", "isric5km", "isric1km", "isric250m"]
samplers = ["LHS", "MC", "ROPE", "DEMCZ"]


def main(argv):
    model = ""
    sampler = ""
    try:
        opts, args = getopt.getopt(argv, "hm:s:", ["model=", "sample="])
    except getopt.GetoptError:
        print("test.py -m <model> -s <sampler>")
        sys.exit(2)
    for opt, arg in opts:
        if opt == "-h":
            print("test.py -m <model> -s <sampler>")
            sys.exit()
        elif opt in ("-m", "--model"):
            model = arg
            if not model in models:
                print(f"{model} not in models, abort ({models})")
        elif opt in ("-s", "--sampler"):
            sampler = arg
            if not sampler in samplers:
                print(f"{sampler} not in models, abort ({samplers})")
    print("Model is " + model)
    print("Sampler is " + sampler)

    mpath=os.path.join(os.getcwd(), os.path.join(model, config[model]["path"]))
    print(f"model init path is: {mpath}")

    param_file=os.path.join(os.getcwd(), os.path.join('params', model + "_par_inf.txt"))
    # update_SLSOIL(os.path.join(model, config[model]["path"]))
    # update_LAT_TTIME(os.path.join(model, config[model]["path"]))
    repetitions = 20

    model_callib(model=model, mpath=mpath, param_file=param_file, sampler=sampler, repetitions=repetitions)

if __name__ == "__main__":
    main(sys.argv[1:])
