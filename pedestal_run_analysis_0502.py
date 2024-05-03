import datetime,  os, subprocess, sys, yaml, glob

import analysis.level0.pedestal_run_analysis as analyzer
import miscellaneous_functions as misc_func
from nested_dict import nested_dict 
from time import sleep

def pedestal_run_analysis(basedir,device_name,device_type,directory_index,suffix=""):
    	
    testName = "pedestal_run"
    odir = "%s/%s/%s/%s_%s_%s/"%( os.path.realpath(basedir), device_name,device_type,testName,device_type,directory_index)
    try:
        ped_analyzer = analyzer.pedestal_run_analyzer(odir=odir)
        print("Output directory for analysis and making plots is",odir)
        files = glob.glob(odir+"/*.root")
    	
        for f in files:
    	    ped_analyzer.add(f)
    
        ped_analyzer.mergeData()
        ped_analyzer.makePlots()
        ped_analyzer.addSummary()
        ped_analyzer.writeSummary()
    except Exception as e:
         with open(odir+"crash_report.log","w") as fout:
            fout.write("pedestal_run analysis went wrong and crash\n")
            fout.write("Error {0}\n".format(str(e)))

    return odir


if __name__ == "__main__":
    options = misc_func.options_analyze()
    pedestal_run_analysis(options.odir,options.dut,options.device_type,options.directory_index,suffix=options.suffix)
