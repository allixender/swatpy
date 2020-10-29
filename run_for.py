import os
from pathlib import Path
import uuid
import stat
import shutil
import sys
import getopt
import traceback

import numpy as np
import pandas as pd

import spotpy
from swatpy import SimManage, ReadOut, FileEdit

import logging
import datetime

log_level = logging.INFO
# create logger
logger = logging.getLogger(__name__)
logger.setLevel(log_level)

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

console = logging.StreamHandler(sys.stdout)
console.setFormatter(formatter)
logger.addHandler(console)

swat_bin = os.path.join(os.environ["HOME"], "bin/swat_rel670_static")


def update_SLSOIL(mpath):

    model3 = SimManage.SwatModel.initFromTxtInOut(
        mpath, copy=False, target_dir=None, swat_version="2012", force=True
    )
    logger.info(model3.working_dir)

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

    logger.info("after reload()")
    manip2 = model3.reloadFileManipulators()
    hruMan = manip2["hru"][-1]
    logger.info(
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
    logger.info(model3.working_dir)

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

    logger.info("after reload()")
    manip2 = model3.reloadFileManipulators()
    hruMan = manip2["hru"][-1]
    logger.info(
        f"{hruMan.filename} LAT_TTIME_val_new {hruMan.parValue['LAT_TTIME'][0]} -> LAT_TTIME_val_old {LAT_TTIME_val}"
    )

    model3.swat_exec = swat_bin
    model3.enrichModelMeta()
    model3.is_runnable()

    model3.run()


class swat_callib_setup(object):
    def __init__(
        self, swat_model, observed_data, param_defs, parallel="seq", temp_dir=None
    ):

        self.model = swat_model
        self.observed_data = observed_data

        self.params = []
        for i in range(len(param_defs)):
            self.params.append(
                spotpy.parameter.Uniform(
                    name=param_defs[i][0],
                    low=param_defs[i][1],
                    high=param_defs[i][2],
                    optguess=np.mean([param_defs[i][1], param_defs[i][2]]),
                )
            )

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
                temp_id = f"mpi{self.mpi_rank}_" + str(temp_id)
            except NameError:
                pass

        test_path = f"swat_{temp_id}"

        if self.temp_dir is None:
            test_path = Path(os.path.join(os.getcwd(), test_path))
        else:
            test_path = Path(os.path.join(self.temp_dir, test_path))

        if os.path.exists(test_path):
            logger.info("Deleting temp folder " + str(test_path))
            shutil.rmtree(test_path, onerror=self.onerror)

        logger.info("Copying model to folder " + str(test_path))
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
            logger.info("Deleting temp folder " + str(model.working_dir))
            shutil.rmtree(model.working_dir, onerror=self.onerror)
        except Exception as e:
            logger.info(e)
            traceback.print_exc(file=sys.stdout)
            logger.info("Error deleting tmp model run")
            pass

    def manipulate_model_params(self, model, parameters):

        logger.info(f"this iteration's parameters:")
        logger.info(parameters)
        # logger.info(self.params[0].name)

        # logger.info(parameters['v__SFTMP__bsn'])

        how_apply = {"v": "s", "r": "*", "a": "+"}

        for idx, param_string in enumerate(self.params):
            # logger.info(param_string.name)
            # logger.info(idx)
            # logger.info(len(param_string.name))
            # logger.info(parameters[idx])

            # slice the stringname open
            # how  param  manipu   1        2         3          4         5   (times __)
            # orig: x__<parname>.<ext>__<hydrp>__<soltext>__<landuse>__<subbsn>__<slope>
            # [0] split ('.')  split ('__') [0]  how v_s r_* a_+  [1] param field name
            # ---
            # [1] split('__') [0] manipulator/file type [1] hydgrp ... etc
            # only __ double underscore
            # how  param  manipu   3        4          5          6         7   (times __)
            # x__<parname>__<ext>__<hydrp>__<soltext>__<landuse>__<subbsn>__<slope>

            field_list = param_string.name.split("__")
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

            logger.info(
                f"field {param_field} in file/manip {manip_ext} will be changed via '{changeHow}' and value {parameters[idx]} "
            )
            if len(field_list) > 3:
                logger.info(f"ignored constraints ({field_list[2:]})")

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
            logger.info(
                f"{the_model.swat_exec} is NOT runnable: {the_model.is_runnable()}"
            )

        self.manipulate_model_params(the_model, parameters)

        # TODO: edit the correct parameters in SWAT files

        ret_val = the_model.run(capture_logs=False, silent=False)
        logger.info(f"returns {ret_val} - vs {the_model.last_run_succesful}")
        # logger.info(model4.last_run_logs)

        reach = 1
        # simulated data
        reader1 = ReadOut.rchOutputManipulator(
            ["FLOW_OUT"],
            [reach],
            "skip",
            True,
            0,
            the_model.working_dir,
            iprint="month",
            stats_dir=self.temp_dir,
        )
        sim_flow_1 = reader1.outValues["FLOW_OUT"][reach]

        # cleanup
        self.remove_temp_model_dir(the_model)
        return sim_flow_1

    # if we want to minimize our function, we can select a negative objective function
    def objectivefunction(self, simulation, evaluation):
        logger.info("simulation")
        logger.info(len(simulation))
        logger.info("evaluation")
        logger.info(len(evaluation))

        objectivefunction = spotpy.objectivefunctions.nashsutcliffe(
            evaluation, simulation
        )
        return objectivefunction


def model_callib(model, mpath, param_file, sampler, repetitions, parallel):

    target_dir = f"/tmp/callib_{model}_{sampler}_{uuid.uuid4()}"
    # target_dir = os.path.join(os.getcwd(), f"callib_{model}_{sampler}_{uuid.uuid4()}")

    model4 = SimManage.SwatModel.initFromTxtInOut(
        txtInOut=mpath,
        copy=True,
        target_dir=os.path.join(target_dir, "TxtInOut"),
        force=False,
    )
    temp_dir = target_dir

    obs_filename = os.path.join("observed", "pori_flow_monthly_2003-2010.txt")
    f = open(obs_filename, "r")
    lines = f.readlines()
    f.close()
    measured = []
    for i in lines:
        measured.append(i.split(";")[2].strip())

    obs = np.array([float(i) for i in measured])

    obs_masked = np.ma.masked_where(obs == -9999.0, obs)

    par_file_name = param_file
    logger.info(f"loading parameter file {par_file_name}")

    dtype = [("f0", "|U30"), ("f1", "<f8"), ("f2", "<f8")]
    par_file_load = np.genfromtxt(par_file_name, dtype=dtype, encoding="utf-8")

    model4.swat_exec = swat_bin
    spot_setup = swat_callib_setup(
        model4, obs_masked, par_file_load, parallel=parallel, temp_dir=temp_dir
    )

    dbformat = "csv"

    kwargs = {
        "spot_setup": spot_setup,
        "parallel": parallel,
        "dbname": f"{model}_{sampler}_{repetitions}_pid{os.getpid()}",
        "dbformat": dbformat,
    }
    spot_sampler = None

    if sampler == "LHS":
        spot_sampler = spotpy.algorithms.lhs(**kwargs)

    if sampler == "MC":
        spot_sampler = spotpy.algorithms.mc(**kwargs)

    if sampler == "ROPE":
        spot_sampler = spotpy.algorithms.rope(**kwargs)

    if sampler == "MCMC":
        spot_sampler = spotpy.algorithms.mcmc(**kwargs)

    if sampler == "SA":
        spot_sampler = spotpy.algorithms.sa(**kwargs)

    if sampler == "MLE":
        spot_sampler = spotpy.algorithms.mle(**kwargs)

    if sampler == "DEMCZ":
        spot_sampler = spotpy.algorithms.demcz(**kwargs)

    if sampler == "SCEUA":
        spot_sampler = spotpy.algorithms.sceua(**kwargs)

    if sampler == "ABC":
        spot_sampler = spotpy.algorithms.abc(**kwargs)

    if sampler == "FSCABC":
        spot_sampler = spotpy.algorithms.fscabc(**kwargs)

    if sampler == "DREAM":
        spot_sampler = spotpy.algorithms.dream(**kwargs)

    if sampler == "FAST":
        spot_sampler = spotpy.algorithms.fast(**kwargs)

    spot_sampler.sample(repetitions)

    try:
        shutil.rmtree(target_dir)
    except Exception as e:
        logger.info(
            f"error removing old calibration workdir: {str(target_dir)} | {repr(e)}"
        )

    # this might break in mpi parallel mode
    if parallel == "seq":
        callib_results = spot_sampler.getdata()

        if not sampler == "FAST":
            logger.info(spotpy.analyser.get_best_parameterset(callib_results))


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
    "pori3": {"path": "Pori3_sim2.Sufi2.SwatCup/Backup"},
}

models = ["pori3", "hwsd", "isric10km", "isric5km", "isric1km", "isric250m"]

all_algorithms = [
    "MC",
    "LHS",
    "MLE",
    "MCMC",
    "SCEUA",
    "SA",
    "DEMCZ",
    "ROPE",
    "ABC",
    "FSCABC",
    "DEMCZ",
    "DREAM",
    "FAST",
]
not_parallel_samplers = ["MLE", "MCMC", "SA", "DREAM", "ABC", "FSCABC"]
parallel_samplers = ["LHS", "MC", "ROPE", "DEMCZ", "SCEUA", "FAST"]


def main(argv):
    my_pid = os.getpid()
    model = ""
    sampler = ""
    repetitions = 0
    parallel = "seq"
    try:
        opts, args = getopt.getopt(
            argv, "hm:s:r:p:", ["model=", "sample=", "reps=", "parallel="]
        )
        logger.info(f"opts {opts} args ({args})")
    except getopt.GetoptError:
        logger.info("test.py -m <model> -s <sampler> -r <reps> -p <parallel>")
        sys.exit(2)
    for opt, arg in opts:
        if opt == "-h":
            logger.info("test.py -m <model> -s <sampler> -r <reps> -p <parallel>")
            sys.exit()
        elif opt in ("-m", "--model"):
            model = arg
            if not model in models:
                logger.info(f"{model} not in models, abort ({models})")
                sys.exit()
        elif opt in ("-s", "--sampler"):
            sampler = arg
            if not sampler in all_algorithms:
                logger.info(f"{sampler} not in models, abort ({all_algorithms})")
                sys.exit()
        elif opt in ("-r", "--reps"):
            repetitions = int(arg)
            if repetitions <= 0:
                logger.info(f"invalid number of repetitions ({repetitions}), abort")
                sys.exit()
        elif opt in ("-p", "--parallel"):
            if arg in ["seq", "mpi"]:
                parallel = arg
                if parallel == "mpi":
                    try:
                        import mpi4py
                    except ImportError:
                        logger.info(
                            f"mpi4py can't imported but is needed for ({parallel}), abort"
                        )
                        sys.exit()
                    if not sampler in parallel_samplers:
                        logger.info(
                            f"{sampler} not parallelizable, abort ({parallel_samplers})"
                        )
                        sys.exit()
            else:
                logger.info(f"{arg} not seq or mpi, abort")
                sys.exit()

    fh = logging.FileHandler(f"{model}_{sampler}_{repetitions}_{my_pid}_output.log")
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    logger.info("Model is " + model)
    logger.info("Sampler is " + sampler)
    logger.info("Repetitions is " + str(repetitions))
    logger.info("Parallel is " + parallel)

    mpath = os.path.join(os.getcwd(), os.path.join(model, config[model]["path"]))
    logger.info(f"model init path is: {mpath}")

    param_file = os.path.join(
        os.getcwd(), os.path.join("params", model + "_par_inf_spotpy.txt")
    )
    # update_SLSOIL(os.path.join(model, config[model]["path"]))
    # update_LAT_TTIME(os.path.join(model, config[model]["path"]))

    model_callib(
        model=model,
        mpath=mpath,
        param_file=param_file,
        sampler=sampler,
        repetitions=repetitions,
        parallel=parallel,
    )


if __name__ == "__main__":
    main(sys.argv[1:])
