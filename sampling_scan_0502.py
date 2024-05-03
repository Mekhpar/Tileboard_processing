import zmq, datetime,  os, subprocess, sys, yaml, glob
from time import sleep
from nested_dict import nested_dict

import myinotifier,util,math,time
import miscellaneous_functions as misc_func
import analysis.level0.sampling_scan_analysis as analyzer
import zmq_controler as zmqctrl

A_T = 3.9083e-3
B_T = -5.7750e-7
R0 = 1000

def scan(i2csocket, daqsocket, calibreq, startBX, stopBX, stepBX, startPhase, stopPhase, stepPhase, trimstart, trimstop, trimstep, injectedChannels, odir):
    testName='sampling_scan'

    index=0
#=============================================added for sampling scan ext======================
# added for ROCv3 configuration ------------------------
    my_calib=0
    gain=1
    
    # pre-configure the injection
    
    #======================measure temperature and bias voltage=====================
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    fout=open(odir+"TB2_info.txt", "x")
    fout.write("####  Before data capture ####" + '\n')
    fout.write("#  Tileboard2 Slow Control Data" + '\n')
    fout.write("#  Date, Time: " + timestamp + '\n')
    i2csocket.meas_temp_bias(fout,A_T = A_T,B_T = B_T,R0 = R0)
    #===============================================================================

    for trim_val in range(trimstart, trimstop, trimstep):
   
        print("Marke 1")
        i2csocket.trim_val_configure(trim_val,my_calib,gain,injectedChannels)
        
        for BX in range(startBX, stopBX, stepBX):
            daqsocket.daq_sampling_scan_settings(active_menu = 'calibAndL1A', num_events = 2500, calibType = 'CALPULEXT', lengthCalib = 4, lengthL1A = 1, bxCalib = calibreq, bxL1A = BX, prescale = 15, repeatOffset = 0)

            daqsocket.configure()

            for phase in range(startPhase,stopPhase+1,stepPhase):
                print("Phase ", phase)
                i2csocket.phase_set(phase)
                util.acquire_scan(daq=daqsocket)
                print("acquire scan")
                chip_params = { 'BX' : BX-startBX, 'Phase' : phase }
                util.saveMetaYaml(odir=odir,i2c=i2csocket,daq=daqsocket,
                                  runid=index,testName=testName,keepRawData=1,
                                  chip_params=chip_params)
                
                print("finish phase:", phase)
                
                 #======================measure temperature and bias voltage=====================    
                fout.write("####  BX, PHASE, TRIM_VAL ####" + '\n')
                fout.write("sample_scan: {} bx: {} phase: {} trim_val: {} \n".format(index,BX,phase,trim_val))
                fout.write("#  Tileboard2 Slow Control Data" + '\n')
                fout.write("#  Date, Time: " + timestamp + '\n')
                i2csocket.meas_temp_bias(fout,A_T = A_T,B_T = B_T,R0 = R0)
               
                #===============================================================================
                index=index+1
    return

def sampling_scan(i2csocket,daqsocket, clisocket, basedir,device_name, device_type, injectionConfig,suffix=""):
    testName='sampling_scan'
        
    calibreq = 0x10
    bxoffset = 24  #  was 24--------24 in mathias's script
    noofoffsets = 2  # was 3
    startBX=calibreq+bxoffset  #----------calibreq+bxoffset-1 in Mathias's script
    stopBX=calibreq+bxoffset+noofoffsets
    print("StartBX: ",startBX)
    print("StopBX: ",stopBX)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    voltages = injectionConfig['OV']#-----------added for sampling scan ext
    LEDvolt = injectionConfig['LEDvolt']#------------added for sampling scan ext
    odir = misc_func.mkdir(basedir,device_name,device_type,testName,suffix)    
        
    mylittlenotifier = myinotifier.mylittleInotifier(odir=odir)

    clisocket.yamlConfig['client']['outputDirectory'] = odir
    clisocket.yamlConfig['client']['run_type'] = testName
    clisocket.configure()
    
    daqsocket.daq_sampling_scan_settings(active_menu = 'calibAndL1A',num_events = 2500, calibType = 'CALPULEXT', lengthCalib = 1, lengthL1A = 1, bxCalib = calibreq, bxL1A = 20, prescale = 0, repeatOffset = 0) #Some settings like BXL1A = 20 are generalized here and will be overriden the scan loop later

    print("gain = %i" %injectionConfig['gain'])
    print("calib = %i" %injectionConfig['calib'])
    gain = injectionConfig['gain'] # 0 for low range ; 1 for high range
    calib = injectionConfig['calib'] # 

    injectedChannels=injectionConfig['injectedChannels']

    util.saveFullConfig(odir=odir,i2c=i2csocket,daq=daqsocket,cli=clisocket)

    i2csocket.configure_injection(injectedChannels, activate=0, gain=gain, phase=0, calib_dac=calib)

    clisocket.start()
    mylittlenotifier.start()
    scan(i2csocket=i2csocket, daqsocket=daqsocket, calibreq = calibreq, startBX=startBX, stopBX=stopBX, stepBX=1, startPhase=0, stopPhase=15, stepPhase=1, trimstart=0, trimstop=1, trimstep=1, injectedChannels=injectedChannels, odir=odir)
    print("scan finish")
    mylittlenotifier.stop()
    print("mylittlenotifier stop")
    clisocket.stop()
    print("clisocket stop")

    
    try:
        scan_analyzer = analyzer.sampling_scan_analyzer(odir=odir)
        files = glob.glob(odir+"/"+clisocket.yamlConfig['client']['run_type']+"*.root")
    
        for f in files:
	        scan_analyzer.add(f)
        scan_analyzer.mergeData()
        scan_analyzer.makePlots(injectedChannels)
        scan_analyzer.determine_bestPhase(injectedChannels)

        # return to no injection setting
        i2csocket.configure_injection(injectedChannels,activate=0,calib_dac=0,gain=0) # 14 is the best phase -> might need to extract it from analysis

        with open(odir+'/best_phase.yaml') as fin:
            cfg = yaml.safe_load(fin)
            i2csocket.configure(yamlNode=cfg)
            i2csocket.update_yamlConfig(yamlNode=cfg)
    except:
        with open(odir+"crash_report.log","w") as fout:
            fout.write("analysis went wrong and crash\n")
       
    return odir


if __name__ == "__main__":
    options = misc_func.options_run()#This will be constant for every test irrespective of the type of test
    (daqsocket,clisocket,i2csocket) = zmqctrl.pre_init(options)

    injectionConfig = {
        'gain' : 1, # 0 in original
        'calib' : 0, #900 in original
        'injectedChannels' : [9, 10, 12, 28, 29, 30, 36, 37, 38, 59],
        # 'injectedChannels' : [3, 10, 21, 31, 35, 38, 45, 49, 61, 64],
        'LEDvolt' : 6100,  # LED_BIAS (LED amplitude) in mV  #------------added for sampling scan ext
        'OV'    : 4   # SiPM overvoltage   #------------added for sampling scan ext
    }
    sampling_scan(i2csocket,daqsocket,clisocket,options.odir,options.dut,options.device_type,injectionConfig,suffix="")
