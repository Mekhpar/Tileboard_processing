import datetime,  os, subprocess, sys, yaml, glob

import analysis.level0.pedestal_run_analysis as analyzer
import miscellaneous_functions as misc_func
from nested_dict import nested_dict 
from time import sleep

def pedestal_run_analysis(basedir,device_name,device_type,device_size,directory_index,suffix=""): #device_size is for the main type of boards i.e. TB3_D8 and not TB3_D8_11 or number of board
    	
    testName = "pedestal"
    odir = "%s/%s/%s/%s_%s_%s/"%( os.path.realpath(basedir), device_name,device_type,testName,device_type,directory_index)
    '''
    try:
        ped_analyzer = analyzer.pedestal_run_analyzer(odir=odir)
        print("Output directory for analysis and making plots is",odir)
        files = glob.glob(odir+"/*.root")
    	
        for f in files:
    	    ped_analyzer.add(f)
    
        ped_analyzer.mergeData()
        
        pedestal_event_analyzer = analyzer.ped_event_analyzer(fin=odir+"pedestal_run0.root") #This is reading from the unpacker/hgcroc tree instead of the summary tree
        corruption_percentage_half = pedestal_event_analyzer.check_corruption(pass_limit = 0.1, fail_limit = 0.2, fout = odir + "analysis_summary_new.yaml")
        #pedestal_event_analyzer.check_corruption(pass_limit = 0.1, fail_limit = 0.2)

        
        
        
        ped_analyzer.makePlots()
        ped_analyzer.addSummary()
        ped_analyzer.writeSummary()
        
    except Exception as e:
         with open(odir+"crash_report.log","w") as fout:
            fout.write("pedestal_run analysis went wrong and crash\n")
            fout.write("Error {0}\n".format(str(e)))
    '''
    ped_analyzer = analyzer.pedestal_run_analyzer(odir=odir)
    print("Output directory for analysis and making plots is",odir)
    files = glob.glob(odir+"/*.root")
	
    for f in files:
	    ped_analyzer.add(f)

    ped_analyzer.mergeData()
    
    pedestal_event_analyzer = analyzer.ped_event_analyzer(fin=odir+"pedestal_run0.root") #This is reading from the unpacker/hgcroc tree instead of the summary tree
    corruption_percentage_half = pedestal_event_analyzer.check_corruption(pass_limit = 0.1, fail_limit = 0.2, fout = odir + "analysis_summary_new.yaml")
    print(corruption_percentage_half)
    
    for chip in range(len(corruption_percentage_half)):
    
        if corruption_percentage_half[chip] ==0:
            print("Check physical connections!")
            
        elif corruption_percentage_half[chip] ==1:
            print("Take pedestal data once more")
            
        elif corruption_percentage_half[chip] ==2: #Here we proceed to actually do the check of the individual channels
            ped_analyzer.channel_ped_check(device_size)
            
    '''
    ped_analyzer.makePlots()
    ped_analyzer.addSummary()
    ped_analyzer.writeSummary()
    '''    
    
    return odir


if __name__ == "__main__":
    #options = misc_func.options_analyze()
    parser = misc_func.options_analyze()#This will be constant for every test irrespective of the type of test
    parser.add_option("-z","--device_size", action="store", dest="device_size",default='0', help="Main type of tileboard")
    (options, args) = parser.parse_args()
    
    print(options)

    pedestal_run_analysis(options.odir,options.dut,options.device_type,options.device_size,options.directory_index,suffix=options.suffix)
