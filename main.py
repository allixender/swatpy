import os
from pathlib import Path
import uuid
import shutil
import sys
import traceback

import numpy as np
import pandas as pd

import spotpy
from swatpy import SimManage, ReadOut, FileEdit


class rosenspot_setup(object):
    def __init__(self):

        self.params = [
            spotpy.parameter.Uniform("x", -10, 10, 1.5, 3.0, -10, 10),
            spotpy.parameter.Uniform("y", -10, 10, 1.5, 3.0, -10, 10),
        ]

    def parameters(self):
        return spotpy.parameter.generate(self.params)

    # provide the available observed data
    def evaluation(self):
        observations = [0]
        return observations

    # Simulation function must not return values besides for which evaluation values/observed data are available
    def simulation(self, vector):
        x = np.array(vector)
        simulations = [
            sum(100.0 * (x[1:] - x[:-1] ** 2.0) ** 2.0 + (1 - x[:-1]) ** 2.0)
        ]
        return simulations

    # if we want to minimize our function, we can select a negative objective function
    def objectivefunction(self, simulation, evaluation):
        objectivefunction = -spotpy.objectivefunctions.rmse(evaluation, simulation)
        return objectivefunction


def demo3():

    results = []
    spot_setup = rosenspot_setup()
    rep = 1000
    timeout = 10  # Given in Seconds

    parallel = "seq"
    dbformat = "csv"

    sampler = spotpy.algorithms.lhs(
        spot_setup,
        parallel=parallel,
        dbname="DemoRosenLHS",
        dbformat=dbformat,
        sim_timeout=timeout,
    )

    sampler.sample(rep)

    results.append(sampler.getdata())

    print(type(results[0]))
    print(len(results))
    print(results[0].shape)

    algorithms = ["lhs"]
    spotpy.analyser.plot_parametertrace_algorithms(results, algorithms, spot_setup)

    sampler = spotpy.algorithms.fast(
        spot_setup, dbname="DemoRosenFAST", dbformat=dbformat
    )
    sampler.sample(rep)


def demo1():

    model3 = SimManage.SwatModel.loadModelFromDirectory("demo_callib2")
    print(model3.working_dir)

    print(f"is it runnable: {model3.is_runnable()}")

    # ret_val = model3.run(capture_logs=True, silent=False)
    # print(f"returns {ret_val} - vs {model3.last_run_succesful}")
    # print(model3.last_run_logs)

    temp_dir = "swat_21347e0a-d724-11ea-8ddc-54e1ad562245"
    model3.enrichModelMeta()

    subbasins = [1]

    print("reader1 rch 1")
    reader1 = ReadOut.rchOutputManipulator(
        ["FLOW_OUT"],
        subbasins,
        "indi",
        False,
        0,
        model3.working_dir,
        iprint="month",
        stats_dir=temp_dir,
    )
    print(reader1.outValues["FLOW_OUT"][subbasins[0]])

    outvalues = len(reader1.outValues["FLOW_OUT"][subbasins[0]])
    print(f"num sim points: {outvalues}")

    print("reader1 efficiency")
    # TODO: add logic for observed data?
    fileName = os.path.join(
        "data", os.path.join("observed", "pori_flow_monthly_2003-2010.txt")
    )
    efficiency = ReadOut.efficiency(
        output="FLOW_OUT",
        area=subbasins[0],
        observed=fileName,
        fileColumn=3,
        daysSkip=0,
        working_dir=model3.working_dir,
        iprint="month",
    )

    print(f"efficiency.obs.min() {efficiency.obs.min()}")

    # TODO: add nodata handling/masking to ReadOut and stats module
    import numpy.ma as ma

    obs_ma = ma.masked_where(efficiency.obs == -9999.0, efficiency.obs)
    print(f" obs ma masked mean {np.mean(obs_ma)}")

    print(f" obs_ma.min() {obs_ma.min()}")

    print(f" len(efficiency.obs) {len(efficiency.obs)}")
    print(f" len(obs_ma) {len(obs_ma)}")

    print(f" efficiency.nash() {efficiency.nash()}")

    print("reader2 sub 1")
    reader2 = ReadOut.subOutputManipulator(
        ["SURQ", "GW_Q", "LAT_Q", "PRECIP"],
        subbasins,
        "indi",
        False,
        0,
        model3.working_dir,
        stats_dir=temp_dir,
    )
    print(reader2.outValues)

    print("fluxes sub 1")
    fluxes = ReadOut.fluxes("SURQ", subbasins, 1, model3.working_dir)
    print(fluxes.result())


def demo2():

    model3 = SimManage.SwatModel.loadModelFromDirectory("demo_callib2")
    print(model3.working_dir)

    manipulators = model3.getFileManipulators()

    """
    Instruction to edit SLSOIL

	The variable "SLSOIL" within hru table of project.mdb will be having a value of "0" by default.
    This column needs to be replaced with the values in the variable "SLSUBBSN".
    """

    # hrufiles SLSUBBSN -> SLSOIL
    for hruMan in manipulators["hru"]:
        if hruMan.filename == "000060001.hru":
            print(
                f"{hruMan.filename} SLSUBBSN {hruMan.parValue['SLSUBBSN'][0]} -> SLSOIL {hruMan.parValue['SLSOIL'][0]}; LAT_TTIME {hruMan.parValue['LAT_TTIME'][0]}"
            )
    #     hruMan.setChangePar("SLSOIL",hruMan.parValue['SLSUBBSN'][0],"s")
    #     hruMan.finishChangePar()

    # print("after finishChangePar()")
    # print(f"{hruMan.filename} SLSUBBSN {hruMan.parValue['SLSUBBSN'][0]} -> SLSOIL {hruMan.parValue['SLSOIL'][0]}")

    # print("after reload()")
    # manip2 = model3.reloadFileManipulators()
    # hruMan = manip2['hru'][-1]
    # print(f"{hruMan.filename} SLSUBBSN {hruMan.parValue['SLSUBBSN'][0]} -> SLSOIL {hruMan.parValue['SLSOIL'][0]}")

    for subMan in manipulators["sub"]:
        if subMan.filename == "000060000.sub":
            print(subMan.parValue)

    model3.enrichModelMeta()

    """
    Instruction to edit LAT_TTIME

	The variable "LAT_TTIME" will also be having a default value of "0".
    This needs to be replaced with the values of "LAT_TTIME" estimated using the equation provided in SWAT theoretical documentation.
    - LAT_TTIME   (TTlag ): Lateral flow travel time (days)
    - SLSOIL   (Lhill): Hillslope length (m)
    - SOL_K   Ksat: Saturated hydraulic conductivity (mm/hr)
    - If drainage tiles are present in the HRU, lateral flow travel time or TTlag is calculated as :
        〖TT〗_(lag )= 〖tile〗_lag/24. Where tilelag is the drain tile lag time (hrs)
        〖TT〗_(lag  )=10.4  L_hill/K_(sat,mx)   (Page 163, SWAT 2009 theory)
        〖TT〗_(lag  )is the lateral flow travel time (days), L_hill is the hillslope length (m) (SLSOIL)
    K_(sat,mx) is the highest layer saturated hydraulic conductivity in the soil profile (mm/hr) (Obtain it from the SOL table from the database by finding the soil layer for each HRU that has the highest hydraulic conductivity)

    After replacing the values of SLSOIL and LAT_TTIME, rewrite the hru file before running SWAT.
    """

    # hrufiles set LAT_TTIME


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
                temp_id = f"mpi{self.mpi_rank}_" + str(temp_id)
            except NameError:
                pass

        test_path = f"swat_{temp_id}"

        if self.temp_dir is None:
            test_path = Path(os.path.join(os.getcwd(), test_path))
        else:
            test_path = Path(os.path.join(self.temp_dir, test_path))

        if os.path.exists(test_path):
            print("Deleting temp folder " + str(test_path))
            shutil.rmtree(test_path, onerror=self.onerror)

        print("Copying model to folder " + str(test_path))
        shutil.copytree(self.model.working_dir, test_path)

        try:
            return SimManage.SwatModel.loadModelFromDirectory(test_path)
        except ValueError:
            return SimManage.SwatModel.initFromTxtInOut(
                test_path, copy=False, force=True
            )

    def remove_temp_model_dir(self, model):
        try:
            print("Deleting temp folder " + str(model.working_dir))
            shutil.rmtree(model.working_dir, onerror=self.onerror)
        except Exception as e:
            print(e)
            traceback.print_exc(file=sys.stdout)
            print("Error deleting tmp model run")
            pass

    def manipulate_model_params(self, model, parameters):

        print(f"this iteration's parameters:")
        print(parameters)
        # print(self.params[0].name)
        # print(parameters['v__SFTMP__bsn'])

        how_apply = {"v": "s", "r": "*", "a": "+"}

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

            print(
                f"field {param_field} in file/manip {manip_ext} will be changed via '{changeHow}' and value {parameters[idx]} "
            )
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
        print(f"is it runnable: {the_model.is_runnable()}")

        self.manipulate_model_params(the_model, parameters)

        # TODO: edit the correct parameters in SWAT files

        ret_val = the_model.run(capture_logs=False, silent=False)
        print(f"returns {ret_val} - vs {the_model.last_run_succesful}")
        # print(model4.last_run_logs)

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
        print("simulation")
        print(len(simulation))
        print("evaluation")
        print(len(evaluation))

        objectivefunction = spotpy.objectivefunctions.nashsutcliffe(
            evaluation, simulation
        )
        return objectivefunction


def demo_callib():

    model4 = {}

    try:
        model4 = SimManage.SwatModel.initFromTxtInOut(
            txtInOut=os.path.join(os.getcwd(), os.path.join("data", "TxtInOut")),
            copy=True,
            target_dir="demo_callib2",
            force=False,
        )
    except ValueError:
        model4 = SimManage.SwatModel.loadModelFromDirectory("demo_callib2")

    model4.enrichModelMeta()
    print(f"is it runnable: {model4.is_runnable()}")

    # ret_val = model4.run(capture_logs=True, silent=True)
    # print(f"returns {ret_val} - vs {model4.last_run_succesful}")
    # print(model4.last_run_logs)

    temp_dir = "swat_b7c411b6-d727-11ea-b9a4-54e1ad562245"

    # simulated data
    # reader1 = ReadOut.rchOutputManipulator(["FLOW_OUT"], subbasins,"skip",False,0, model4.working_dir, iprint='month', stats_dir=temp_dir)
    # sim_flow_1 = reader1.outValues["FLOW_OUT"][subbasins[0]]

    # observed data
    obs_filename = os.path.join(
        "data", os.path.join("observed", "pori_flow_monthly_2003-2010.txt")
    )
    f = open(obs_filename, "r")
    lines = f.readlines()
    f.close()
    measured = []
    for i in lines:
        measured.append(i.split(";")[2].strip())

    obs = np.array([float(i) for i in measured])

    obs_masked = np.ma.masked_where(obs == -9999.0, obs)

    # print(efficiency.obs)
    # print(efficiency.obs_masked)

    # import functools

    # if functools.reduce(lambda i, j : i and j, map(lambda m, k: m == k, efficiency.outValues, efficiency.obs_masked), True) :
    #     print ("The lists are identical")
    # else :
    #     print ("The lists are not identical")

    # run spotpy callib sampling and sensitivity

    # delimiter=' ' n-consecutive whitespace is default
    # dtype U utf8 string

    par_file_name = os.path.join("data", os.path.join("params", "par_inf2.txt"))
    print(f"loading parameter file {par_file_name}")

    dtype = [("f0", "|U30"), ("f1", "<f8"), ("f2", "<f8")]
    par_file_load = np.genfromtxt(par_file_name, dtype=dtype, encoding="utf-8")

    parallel = "seq"
    spot_setup = swat_callib_setup(
        model4, obs_masked, par_file_load, parallel=parallel, temp_dir=temp_dir
    )

    repetitions = 5

    dbformat = "csv"

    lhs_calibrator_sampler = spotpy.algorithms.lhs(
        spot_setup, parallel=parallel, dbname="Demo4SwatLHS", dbformat=dbformat
    )

    lhs_calibrator_sampler.sample(repetitions)

    callib_results = lhs_calibrator_sampler.getdata()

    print(spotpy.analyser.get_best_parameterset(callib_results))

    spotpy.analyser.plot_parameterInteraction(callib_results)
    spotpy.analyser.plot_parametertrace_algorithms(
        result_lists=[callib_results], algorithmnames=["lhs"], spot_setup=spot_setup
    )

    # fast_sensitivity_sampler = spotpy.algorithms.fast(spot_setup,  dbname='Demo4SwatFAST',  dbformat=dbformat)
    # fast_sensitivity_sampler.sample(repetitions)

    # sens_results = fast_sensitivity_sampler.getdata()
    # spotpy.analyser.plot_parametertrace_algorithms(sens_results, ['fast'], spot_setup)


if __name__ == "__main__":

    # model1 = SimManage.SwatModel.initFromTxtInOut(txtInOut=os.path.join(os.getcwd(),
    #     os.path.join('data', 'TxtInOut')), copy=True)

    # model2 = SimManage.SwatModel.initFromTxtInOut(txtInOut=os.path.join(os.getcwd(),
    #     os.path.join('data', 'TxtInOut')), copy=True, target_dir="demo_worker2")

    # demo1()
    # demo2()
    # demo3()

    demo_callib()
