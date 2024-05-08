import zmq, datetime,  os, subprocess, sys, yaml, glob
from time import sleep
from nested_dict import nested_dict

import myinotifier,util
import miscellaneous_functions as misc_func
import analysis.level0.sampling_scan_analysis as analyzer
import zmq_controler as zmqctrl

def scan(i2csocket, daqsocket, gain, calib, calibreq, startBX, stopBX, stepBX, startPhase, stopPhase, stepPhase, injectedChannels, odir):
    testName='sampling_scan'

    index=0
    # added for ROCv3 configuration ------------------------
    print("Calib and gain values taken by scan", calib, gain)

    # pre-configure the injection
    
    print("Marke 1")
    i2csocket.configure_injection(trim_val = 0, process = 'int', calib_preamp = calib, calib_conv = 0, gain = gain,injectedChannels = injectedChannels, IntCtest = 1, choice_cinj = 1, cmd_120p = 0, L_g2 = 1, H_g2 = 1, L_g1 = 0, H_g1 = 1, L_g0 = 1, H_g0 = 0)    
    # --------------------
       
    for BX in range(startBX, stopBX, stepBX):
        daqsocket.daq_sampling_scan_settings(active_menu = 'calibAndL1A', num_events = 500, calibType = 'CALPULINT', lengthCalib = 1, lengthL1A = 1, bxCalib = calibreq, bxL1A = BX, prescale = 1, repeatOffset = 0)
        daqsocket.configure()

        #CALPULINT instead of CALPULEXT because we have internal instead of external injection, the function was originally intended for external injection but all the parameters here are similar
        print(BX)

        for phase in range(startPhase,stopPhase+1,stepPhase):
            i2csocket.phase_set(phase)
            util.acquire_scan(daq=daqsocket)
            chip_params = { 'BX' : BX-startBX, 'Phase' : phase }
            util.saveMetaYaml(odir=odir,i2c=i2csocket,daq=daqsocket,
                              runid=index,testName=testName,keepRawData=1,
                              chip_params=chip_params)
            index=index+1
        for inj_chs in injectedChannels: #This particular setting seems to have been done only for this script (conveyor injection) - why do we want to have both ranges to be 0 at each BX except the first?
            i2csocket.lg_hg_deactivate(process = 'int', subprocess = 'preamp', injectedChannel = inj_chs, lg=0, hg=0)
    return

def PreampSampling_scan(i2csocket,daqsocket, clisocket, basedir,device_name, device_type, injectionConfig,suffix=""):
    testName='PreampSampling_scan'
    odir = misc_func.mkdir(basedir,device_name,device_type,testName,suffix)
            
    mylittlenotifier = myinotifier.mylittleInotifier(odir=odir)
    mylittlenotifier.start()

    clisocket.yamlConfig['client']['outputDirectory'] = odir
    clisocket.yamlConfig['client']['run_type'] = "sampling_scan"
    clisocket.configure()
    
    calibreq = 0x10
    bxoffset = 21   # was 23, 23 is better for phase_strobe clk,  Mathias 26.4.
    startBX=calibreq+bxoffset # -1
    stopBX=calibreq+bxoffset+5 # +4
    print("StartBX: ",startBX)
    print("StopBX: ",stopBX)
    
    daqsocket.daq_sampling_scan_settings(active_menu = 'calibAndL1A', num_events = 500, calibType = 'CALPULINT', lengthCalib = 1, lengthL1A = 1, bxCalib = calibreq, bxL1A = 20, prescale = 0, repeatOffset = 0)
    #Some settings like BXL1A = 20 are generalized here and will be overriden the scan loop later
    
    (gain, calib, injectedChannels) = misc_func.injection_config_assign_internal(injectionConfig) #Constructor of sorts for the internal injection case (both preamp and conveyor)
    
    print("gain = %i" %gain)
    print("calib = %i" %calib)

    util.saveFullConfig(odir=odir,i2c=i2csocket,daq=daqsocket,cli=clisocket)

    i2csocket.configure_injection(trim_val = 0, process = 'int', calib_preamp = calib, calib_conv = 0, gain=gain,injectedChannels=injectedChannels, IntCtest = 1, choice_cinj = 1, cmd_120p = 0, L_g2 = 0, H_g2 = 1, L_g1 = 0, H_g1 = 1, L_g0 = 1, H_g0 = 0)


    clisocket.start()
    scan(i2csocket=i2csocket, daqsocket=daqsocket, gain = gain, calib = calib, calibreq = calibreq, startBX=startBX, stopBX=stopBX, stepBX=1, startPhase=0, stopPhase=15, stepPhase=1, injectedChannels=injectedChannels, odir=odir)
    clisocket.stop()
    mylittlenotifier.stop()

    scan_analyzer = analyzer.sampling_scan_analyzer(odir=odir)
    # files = glob.glob(odir+"/"+clisocket.yamlConfig['global']['run_type']+"*.root")
    files = glob.glob(odir+"/"+clisocket.yamlConfig['client']['run_type']+"*.root")
     
    for f in files:
	    scan_analyzer.add(f)
    scan_analyzer.mergeData()
    scan_analyzer.makePlots(injectedChannels)
    scan_analyzer.determine_bestPhase(injectedChannels)

    # return to no injection setting
    #Lots of options here are equivalent to the default ones, might as well not write them down explicitly
    i2csocket.configure_injection(trim_val = 0, process = 'int', calib_preamp = 0, calib_conv = 0, gain=0,injectedChannels=injectedChannels, IntCtest = 0, choice_cinj = 0, cmd_120p = 0, L_g2 = 0, H_g2 = 0, L_g1 = 0, H_g1 = 0, L_g0 = 0, H_g0 = 0)


    with open(odir+'/best_phase.yaml') as fin:
        cfg = yaml.safe_load(fin)
        i2csocket.configure(yamlNode=cfg)
        i2csocket.update_yamlConfig(yamlNode=cfg)
    return odir


if __name__ == "__main__":
    parser = misc_func.options_run()#This will be constant for every test irrespective of the type of test
    
    #One extra option custommade just for this script - internal pulse height (calib)
    parser.add_option("-c","--calib", action="store", dest="calib",default='0', help="pulse height for internal injection")
 
    (options, args) = parser.parse_args()
    print(options)
    (daqsocket,clisocket,i2csocket) = zmqctrl.pre_init(options)

    injectionConfig = {
        'gain' : 1,   # gain=0: LowRange, gain=1: HighRange
        'calib' : int(options.calib),
        #'injectedChannels' : [0, 2, 4, 6, 8, 10, 12, 14, 16]  # scan 5
        'injectedChannels' : [6, 10, 45, 52]  # scan 8

    }
    PreampSampling_scan(i2csocket,daqsocket,clisocket,options.odir,options.dut,options.device_type,injectionConfig,suffix="")
