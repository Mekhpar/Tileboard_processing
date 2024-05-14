'''
These are two generalized functions for all the sampling scans, external or internal preamp or internal conveyor
'''

import zmq, datetime,  os, subprocess, sys, yaml, glob
from time import sleep
from nested_dict import nested_dict

import myinotifier,util
import miscellaneous_functions as misc_func
import analysis.level0.sampling_scan_analysis as analyzer
import zmq_controler as zmqctrl

A_T = 3.9083e-3
B_T = -5.7750e-7
R0 = 1000

def scan(i2csocket, daqsocket, index, out_txt_dir, scan_injection, process, subprocess, trim_val, gain, calib, active_menu, num_events, calibreq, startBX, stopBX, stepBX, startPhase, stopPhase, stepPhase, injectedChannels, odir):
    testName='sampling_scan'
    #testName = subprocess.capitalize() + 'Sampling_scan' #This is the test name that will be saved in the yaml file so it is better to characterize it this way
    # pre-configure the injection
    
    print("Marke 1")
    #Put scan injection data here
    (calib_preamp, calib_conv, IntCtest, choice_cinj, cmd_120p, L_g2, L_g1, L_g0, H_g2, H_g1, H_g0) = misc_func.configure_injection_assign(scan_injection)
    i2csocket.configure_injection(trim_val = trim_val, process = process, calib_preamp = calib_preamp, calib_conv = calib_conv, gain = gain,injectedChannels = injectedChannels, IntCtest = IntCtest, choice_cinj = choice_cinj, cmd_120p = cmd_120p, L_g2 = L_g2, H_g2 = H_g2, L_g1 = L_g1, H_g1 = H_g1, L_g0 = L_g0, H_g0 = H_g0)    
    # --------------------
       
    for BX in range(startBX, stopBX, stepBX):
        daqsocket.daq_sampling_scan_settings(active_menu = active_menu, num_events = num_events, calibType = 'CALPUL' + process.upper(), lengthCalib = 1, lengthL1A = 1, bxCalib = calibreq, bxL1A = BX, prescale = 1, repeatOffset = 0)
        daqsocket.configure()

        #CALPULINT instead of CALPULEXT because we have internal instead of external injection, the function was originally intended for external injection but all the parameters here are similar
        print(BX)

        for phase in range(startPhase,stopPhase+1,stepPhase):
            print("RUN ID:", index)
            i2csocket.phase_set(phase)
            util.acquire_scan(daq=daqsocket)
            chip_params = { 'BX' : BX-startBX, 'Phase' : phase }
            util.saveMetaYaml(odir=odir,i2c=i2csocket,daq=daqsocket,
                              runid=index,testName=testName,keepRawData=1,
                              chip_params=chip_params)
            print("finish phase:", phase)
          
            #======================measure temperature and bias voltage=====================    
            if process == 'ext':
              out_txt_dir.write("####  BX, PHASE, TRIM_VAL ####" + '\n')
              out_txt_dir.write("sample_scan: {} bx: {} phase: {} trim_val: {} \n".format(index,BX,phase,trim_val))
            elif process == 'int': #At the moment, there is no need for trim_inv to be put here
              out_txt_dir.write("####  BX, PHASE ####" + '\n')
              out_txt_dir.write("sample_scan: {} bx: {} phase: {} \n".format(index,BX,phase))
          
            out_txt_dir.write("#  Tileboard2 Slow Control Data" + '\n')
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")            
            out_txt_dir.write("#  Date, Time: " + timestamp + '\n')
            i2csocket.meas_temp_bias(out_txt_dir,A_T = A_T,B_T = B_T,R0 = R0)
            #===============================================================================
          
            index=index+1
        for inj_chs in injectedChannels: #This particular setting seems to have been done only for this script (conveyor injection) - why do we want to have both ranges to be 0 at each BX except the first?
            i2csocket.lg_hg_deactivate(process = process, subprocess = subprocess, injectedChannel = inj_chs, lg=0, hg=0)
    return

#These calibL1A etc daq parameters are included in the function arguments because they may not necessarily be the same for external and internal injection
def Sampling_scan(i2csocket,daqsocket, clisocket, extra_text, basedir,device_name, device_type, injectionConfig, process = 'int', subprocess = 'preamp', suffix="", active_menu = 'calibAndL1A', num_events = 500, calibreq = 0x10, bxoffset = 21, noofoffsets = 5, stepBX = 1, startPhase=0, stopPhase=15, stepPhase=1):

    (gain, calib, injectedChannels) = misc_func.injection_config_assign(injectionConfig) #Constructor of sorts for all the injection case (both preamp and conveyor, as well as external)

    print("gain = %i" %gain)
    print("calib = %i" %calib)

    #testName='PreampSampling_scan'
    testName = subprocess.capitalize() + 'Sampling_scan_' + extra_text #To keep the test name somewhat consistent with before
    odir = misc_func.mkdir(basedir,device_name,device_type,testName,suffix)
    

    util.saveFullConfig(odir=odir,i2c=i2csocket,daq=daqsocket,cli=clisocket)

    if process == 'ext':
        pre_injection = {'calib_preamp' : calib, 'calib_conv' : 0, 'IntCtest' : 0, 'choice_cinj' : 1, 'cmd_120p' : 0, 'L_g2' : 0, 'H_g2' : 0, 'L_g1' : 0, 'H_g1' : 0, 'L_g0' : 0, 'H_g0' : 0}
        scan_injection = {'calib_preamp' : calib, 'calib_conv' : 0, 'IntCtest' : 0, 'choice_cinj' : 1, 'cmd_120p' : 0, 'L_g2' : 0, 'H_g2' : 0, 'L_g1' : 0, 'H_g1' : 0, 'L_g0' : 0, 'H_g0' : 0}
        post_injection = {'calib_preamp' : calib, 'calib_conv' : 0, 'IntCtest' : 0, 'choice_cinj' : 1, 'cmd_120p' : 0, 'L_g2' : 0, 'H_g2' : 0, 'L_g1' : 0, 'H_g1' : 0, 'L_g0' : 0, 'H_g0' : 0}
      
    elif process == 'int':
        if subprocess == 'preamp':
            pre_injection = {'calib_preamp' : calib, 'calib_conv' : 0, 'IntCtest' : 1, 'choice_cinj' : 1, 'cmd_120p' : 0, 'L_g2' : 0, 'H_g2' : 1, 'L_g1' : 0, 'H_g1' : 1, 'L_g0' : 1, 'H_g0' : 0}
            scan_injection = {'calib_preamp' : calib, 'calib_conv' : 0, 'IntCtest' : 1, 'choice_cinj' : 1, 'cmd_120p' : 0, 'L_g2' : 1, 'H_g2' : 1, 'L_g1' : 0, 'H_g1' : 1, 'L_g0' : 1, 'H_g0' : 0}
            post_injection = {'calib_preamp' : 0, 'calib_conv' : 0, 'IntCtest' : 0, 'choice_cinj' : 0, 'cmd_120p' : 0, 'L_g2' : 0, 'H_g2' : 0, 'L_g1' : 0, 'H_g1' : 0, 'L_g0' : 0, 'H_g0' : 0}
      
        elif subprocess == 'conv':
            pre_injection = {'calib_preamp' : 0, 'calib_conv' : calib, 'IntCtest' : 1, 'choice_cinj' : 1, 'cmd_120p' : 0, 'L_g2' : 0, 'H_g2' : 1, 'L_g1' : 0, 'H_g1' : 1, 'L_g0' : 1, 'H_g0' : 0}
            scan_injection = {'calib_preamp' : 0, 'calib_conv' : calib, 'IntCtest' : 0, 'choice_cinj' : 0, 'cmd_120p' : 1, 'L_g2' : 1, 'H_g2' : 1, 'L_g1' : 0, 'H_g1' : 1, 'L_g0' : 1, 'H_g0' : 0}
            post_injection = {'calib_preamp' : 0, 'calib_conv' : calib, 'IntCtest' : 1, 'choice_cinj' : 0, 'cmd_120p' : 0, 'L_g2' : 0, 'H_g2' : 1, 'L_g1' : 0, 'H_g1' : 1, 'L_g0' : 1, 'H_g0' : 0}
  
    mylittlenotifier = myinotifier.mylittleInotifier(odir=odir)
    mylittlenotifier.start()

    clisocket.yamlConfig['client']['outputDirectory'] = odir
    clisocket.yamlConfig['client']['run_type'] = "sampling_scan"
    clisocket.configure()
    
    #calibreq = 0x10
    #bxoffset = 21   # was 23, 23 is better for phase_strobe clk,  Mathias 26.4.
    startBX=calibreq+bxoffset # -1
    stopBX=calibreq+bxoffset+noofoffsets # +4
    print("StartBX: ",startBX)
    print("StopBX: ",stopBX)
    
    daqsocket.daq_sampling_scan_settings(active_menu = active_menu, num_events = num_events, calibType = 'CALPUL' + process.upper(), lengthCalib = 1, lengthL1A = 1, bxCalib = calibreq, bxL1A = 20, prescale = 0, repeatOffset = 0)
    #Some settings like BXL1A = 20 are generalized here and will be overriden the scan loop later
    

    #pre_injection
    (calib_preamp, calib_conv, IntCtest, choice_cinj, cmd_120p, L_g2, L_g1, L_g0, H_g2, H_g1, H_g0) = misc_func.configure_injection_assign(pre_injection)
    i2csocket.configure_injection(trim_val = 0, process = process, calib_preamp = calib_preamp, calib_conv = calib_conv, gain = gain,injectedChannels = injectedChannels, IntCtest = IntCtest, choice_cinj = choice_cinj, cmd_120p = cmd_120p, L_g2 = L_g2, H_g2 = H_g2, L_g1 = L_g1, H_g1 = H_g1, L_g0 = L_g0, H_g0 = H_g0)    
  
    #i2csocket.configure_injection(trim_val = 0, process = process, calib_preamp = calib, calib_conv = 0, gain=gain,injectedChannels=injectedChannels, IntCtest = 1, choice_cinj = 1, cmd_120p = 0, L_g2 = 0, H_g2 = 1, L_g1 = 0, H_g1 = 1, L_g0 = 1, H_g0 = 0)

    clisocket.start()
    # added for ROCv3 configuration ------------------------
    print("Calib and gain values taken by scan", calib, gain)

    #Doesn't hurt to measure these parameters even if there is no LED bias (i.e. in the internal case)
    #======================measure temperature and bias voltage=====================
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    fout=open(odir+"TB2_info.txt", "x")
    fout.write("injectedChannels:" + '\n')
    for inj_ch in injectedChannels:
        fout.write(str(inj_ch) + " ")
    
    fout.write('\n')
    fout.write("####  Before data capture ####" + '\n')
    fout.write("#  Tileboard2 Slow Control Data" + '\n')
    fout.write("#  Date, Time: " + timestamp + '\n')
    i2csocket.meas_temp_bias(fout,A_T = A_T,B_T = B_T,R0 = R0)
    #===============================================================================
    trimstart = 0
    trimstop = 1
    trimstep = 1
    index=0

    #Adding the trim_inv for loop here
    if process == 'int':
      scan(i2csocket=i2csocket, daqsocket=daqsocket, index = index, out_txt_dir = fout, scan_injection = scan_injection, process = process, subprocess = subprocess, trim_val = 0, gain = gain, calib = calib, active_menu = active_menu, num_events = num_events, calibreq = calibreq, startBX=startBX, stopBX=stopBX, stepBX=stepBX, startPhase=startPhase, stopPhase=stopPhase, stepPhase=stepPhase, injectedChannels=injectedChannels, odir=odir)
    elif process == 'ext':
      for trim_val in range(trimstart, trimstop, trimstep):
        scan(i2csocket=i2csocket, daqsocket=daqsocket, index = index, out_txt_dir = fout, scan_injection = scan_injection, process = process, subprocess = subprocess, trim_val = trim_val, gain = gain, calib = calib, active_menu = active_menu, num_events = num_events, calibreq = calibreq, startBX=startBX, stopBX=stopBX, stepBX=stepBX, startPhase=startPhase, stopPhase=stopPhase, stepPhase=stepPhase, injectedChannels=injectedChannels, odir=odir)

    clisocket.stop()
    mylittlenotifier.stop()
   
    # return to no injection setting
    #Lots of options here are equivalent to the default ones, might as well not write them down explicitly
    #post_injection
    (calib_preamp, calib_conv, IntCtest, choice_cinj, cmd_120p, L_g2, L_g1, L_g0, H_g2, H_g1, H_g0) = misc_func.configure_injection_assign(post_injection)
    i2csocket.configure_injection(trim_val = 0, process = process, calib_preamp = calib_preamp, calib_conv = calib_conv, gain = gain,injectedChannels = injectedChannels, IntCtest = IntCtest, choice_cinj = choice_cinj, cmd_120p = cmd_120p, L_g2 = L_g2, H_g2 = H_g2, L_g1 = L_g1, H_g1 = H_g1, L_g0 = L_g0, H_g0 = H_g0)    

    #i2csocket.configure_injection(trim_val = 0, process = process, calib_preamp = 0, calib_conv = 0, gain=0,injectedChannels=injectedChannels, IntCtest = 0, choice_cinj = 0, cmd_120p = 0, L_g2 = 0, H_g2 = 0, L_g1 = 0, H_g1 = 0, L_g0 = 0, H_g0 = 0)
    return odir
        
#Remove injectedChannels as an external argument because they will be read from the TB_info.txt file        
def Sampling_scan_analysis(i2csocket,process,subprocess,basedir,device_name,device_type,directory_index, calib, LEDvolt, OV, suffix=""): #This is already agnostic of the process, even the analysis file used is the same
#calib, LEDvolt, OV are required to be entered by the user because they define the folder name
#There is no need to give the full injectionConfig here, only the list of channels for plotting
    if process == 'ext':
        extra_text = 'LED_BV_'+ LEDvolt + '_OV_' + OV
    elif process == 'int':
        extra_text = 'Calib_'+ calib
        
    testName = subprocess.capitalize() + 'Sampling_scan_' + extra_text
    odir = "%s/%s/%s/%s_%s_%s/"%( os.path.realpath(basedir), device_name,device_type,testName,device_type,directory_index)
    print("Directory to be analyzed", odir)
    
    scan_analyzer = analyzer.sampling_scan_analyzer(odir=odir)

    files = glob.glob(odir+"/"+"sampling_scan"+"*.root")
    
    injectedChannels = scan_analyzer.get_injectedChannels(odir)
    for f in files:
	    scan_analyzer.add(f)
    scan_analyzer.mergeData()
    scan_analyzer.makePlots(injectedChannels)
    scan_analyzer.determine_bestPhase(injectedChannels)

    with open(odir+'/best_phase.yaml') as fin:
        cfg = yaml.safe_load(fin)
        i2csocket.configure(yamlNode=cfg)
        i2csocket.update_yamlConfig(yamlNode=cfg)

    return    
