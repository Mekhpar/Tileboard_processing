import zmq, datetime,  os, subprocess, sys, yaml, glob
from time import sleep
from nested_dict import nested_dict

import myinotifier,util
import miscellaneous_functions as misc_func
import analysis.level0.sampling_scan_analysis as analyzer
import zmq_controler as zmqctrl

def scan(i2csocket, daqsocket, startBX, stopBX, stepBX, startPhase, stopPhase, stepPhase, injectedChannels, odir):
    testName='sampling_scan'

    index=0
    # added for ROCv3 configuration ------------------------
    my_calib = injectionConfig['calib']
    gain = injectionConfig['gain'] # 0 for low range ; 1 for high range
    print("Calib and gain values taken by scan", my_calib, gain)
    #nestedConf = nested_dict()
    # pre-configure the injection
    
    print("Marke 1")
    #update = lambda conf, chtype, channel, Range, val : conf[chtype][channel].update({Range:val})
    i2csocket.trim_val_configure(trim_val = 0,my_calib_preamp = my_calib, my_calib_conv = 0, gain = gain,injectedChannels = injectedChannels, IntCtest = 1, choice_cinj = 1, cmd_120p = 0, L_g2 = 1, H_g2 = 1, L_g1 = 0, H_g1 = 1, L_g0 = 1, H_g0 = 0)    
    '''
    for key in i2csocket.yamlConfig.keys():
        if key.find('roc_s')==0:
            nestedConf[key]['sc']['ReferenceVoltage']['all']['IntCtest'] = 1
            print("Marke 2")
            nestedConf[key]['sc']['ReferenceVoltage']['all']['Calib'] = my_calib
            print(" prog calib: ", my_calib)
            nestedConf[key]['sc']['ReferenceVoltage']['all']['choice_cinj'] = 1   # "1": inject to preamp input, "0": inject to conveyor input
            nestedConf[key]['sc']['ReferenceVoltage']['all']['cmd_120p'] = 0
            if gain==2:
                for inj_chs in injectedChannels:
                   print(" Gain=2, Channel: ", inj_chs)
                   [nestedConf[key]['sc']['ch'][inj_chs].update({'LowRange':1}) for key in i2csocket.yamlConfig.keys() if key.find('roc_s')==0 ] 
                   [nestedConf[key]['sc']['ch'][inj_chs].update({'HighRange':1}) for key in i2csocket.yamlConfig.keys() if key.find('roc_s')==0 ]             
                
            elif gain==1:
                for inj_chs in injectedChannels:
                   print(" Gain=1, Channel: ", inj_chs)
                   [nestedConf[key]['sc']['ch'][inj_chs].update({'LowRange':0}) for key in i2csocket.yamlConfig.keys() if key.find('roc_s')==0 ] 
                   [nestedConf[key]['sc']['ch'][inj_chs].update({'HighRange':1}) for key in i2csocket.yamlConfig.keys() if key.find('roc_s')==0 ] 
                
            elif gain==0:
                for inj_chs in injectedChannels:
                   print(" Gain=0, Channel: ", inj_chs)
                   [nestedConf[key]['sc']['ch'][inj_chs].update({'LowRange':1}) for key in i2csocket.yamlConfig.keys() if key.find('roc_s')==0 ] 
                   [nestedConf[key]['sc']['ch'][inj_chs].update({'HighRange':0}) for key in i2csocket.yamlConfig.keys() if key.find('roc_s')==0 ] 
                
            else:
                pass
    i2csocket.configure(yamlNode=nestedConf.to_dict())
    '''
    # --------------------
       
    for BXrun in range(startBX, stopBX, stepBX):
        
        # daqsocket.l1a_generator_settings(name='A',enable=1,BX=0x10,length=1,flavor='CALPULINT',prescale=0,followMode='DISABLE')
        # daqsocket.l1a_generator_settings(name='B',enable=1,BX=BXrun,length=1,flavor='L1A',prescale=0,followMode='A')
        daqsocket.yamlConfig['daq']['menus']['calibAndL1A']['calibType']="CALPULINT"
        daqsocket.yamlConfig['daq']['menus']['calibAndL1A']['lengthCalib']=1
        daqsocket.yamlConfig['daq']['menus']['calibAndL1A']['bxCalib']=0x10
        daqsocket.yamlConfig['daq']['menus']['calibAndL1A']['prescale']=1   
         
        #daqsocket.l1a_generator_settings(name='B',enable=1,BX=BX,length=1,flavor='L1A',prescale=0,followMode='A')  #--------added for sampling scan ext 
        daqsocket.yamlConfig['daq']['menus']['calibAndL1A']['lengthL1A']=1
        daqsocket.yamlConfig['daq']['menus']['calibAndL1A']['bxL1A']=BXrun
        # daqsocket.yamlConfig['daq']['menus']['calibAndL1A']['prescale']=0
        daqsocket.configure()
        
        print(BXrun)

        for phase in range(startPhase,stopPhase+1,stepPhase):
            nestedConf = nested_dict()
            for key in i2csocket.yamlConfig.keys():
                if key.find('roc_s')==0:
                    # nestedConf[key]['sc']['Top']['all']['phase_strobe']=15-phase
                    nestedConf[key]['sc']['Top']['all']['phase_ck']=phase
            i2csocket.configure(yamlNode=nestedConf.to_dict())
            i2csocket.resettdc()	# Reset MasterTDCs

            util.acquire_scan(daq=daqsocket)
            chip_params = { 'BX' : BXrun-startBX, 'Phase' : phase }
            util.saveMetaYaml(odir=odir,i2c=i2csocket,daq=daqsocket,
                              runid=index,testName=testName,keepRawData=1,
                              chip_params=chip_params)
            index=index+1
    return

def sampling_scan(i2csocket,daqsocket, clisocket, basedir,device_name, injectionConfig,suffix=""):

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if suffix:
        timestamp = timestamp + "_" + suffix
        
        
        
        
        
    odir = "%s/%s/TB3_D8_11/PreampSampling_scan_TB3_D8_11_5/"%( os.path.realpath(basedir), device_name) # a comlete path is needed
    
    
    
    
    
    
    # odir = "%s/%s/sampling_scan/run_%s/"%( os.path.realpath(basedir), device_name, timestamp ) # a comlete path is needed
    os.makedirs(odir)
    
    mylittlenotifier = myinotifier.mylittleInotifier(odir=odir)
    mylittlenotifier.start()

    startPhase=0
    stopPhase=15
    stepPhase=1

    clisocket.yamlConfig['client']['outputDirectory'] = odir
    clisocket.yamlConfig['client']['run_type'] = "sampling_scan"
    clisocket.configure()
    
    '''
    clisocket.yamlConfig['global']['outputDirectory'] = odir
    clisocket.yamlConfig['global']['run_type'] = "sampling_scan"
    clisocket.yamlConfig['global']['serverIP'] = daqsocket.ip
    clisocket.configure()
    '''
    
    calibreq = 0x10
    bxoffset = 22   # was 23, 23 is better for phase_strobe clk,  Mathias 26.4.
    startBX=calibreq+bxoffset-1 # -1
    stopBX=calibreq+bxoffset+4 # +4
    print("StartBX: ",startBX)
    print("StopBX: ",stopBX)
    stepBX=1
    
    daqsocket.yamlConfig['daq']['active_menu']='calibAndL1A'
    daqsocket.yamlConfig['daq']['menus']['calibAndL1A']['NEvents']= 500     # 500 before
    daqsocket.yamlConfig['daq']['menus']['calibAndL1A']['bxCalib']=calibreq
    daqsocket.yamlConfig['daq']['menus']['calibAndL1A']['lengthCalib']=1
    daqsocket.yamlConfig['daq']['menus']['calibAndL1A']['lengthL1A']=1
    daqsocket.yamlConfig['daq']['menus']['calibAndL1A']['prescale']=0
    daqsocket.yamlConfig['daq']['menus']['calibAndL1A']['repeatOffset']=0 # was 700
    
    # daqsocket.yamlConfig['daq']['NEvents']='500'
    # daqsocket.enable_fast_commands(0,0,0) ## disable all non-periodic gen L1A sources 
    # daqsocket.l1a_generator_settings(name='A',enable=1,BX=calibreq,length=1,flavor='L1A',prescale=0,followMode='DISABLE')
    # daqsocket.l1a_generator_settings(name='A',enable=1,BX=calibreq,length=1,flavor='CALPULINT',prescale=0,followMode='DISABLE')
    print("gain = %i" %injectionConfig['gain'])
    print("calib = %i" %injectionConfig['calib'])
    gain = injectionConfig['gain'] # 0 for low range ; 1 for high range
    calib = injectionConfig['calib'] # 
    injectedChannels=injectionConfig['injectedChannels']

    util.saveFullConfig(odir=odir,i2c=i2csocket,daq=daqsocket,cli=clisocket)

    i2csocket.configure_injection(injectedChannels, activate=1, gain=gain, phase=0, calib_dac=calib)

    clisocket.start()
    scan(i2csocket=i2csocket, daqsocket=daqsocket, 
	     startBX=startBX, stopBX=stopBX, stepBX=stepBX, 
	     startPhase=startPhase, stopPhase=stopPhase, stepPhase=stepPhase, 
	     injectedChannels=injectedChannels, odir=odir)
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
    i2csocket.configure_injection(injectedChannels,activate=0,calib_dac=0,gain=0) # 14 is the best phase -> might need to extract it from analysis

    with open(odir+'/best_phase.yaml') as fin:
        cfg = yaml.safe_load(fin)
        i2csocket.configure(yamlNode=cfg)
        i2csocket.update_yamlConfig(yamlNode=cfg)
    return odir


if __name__ == "__main__":
    options = misc_func.options_run()#This will be constant for every test irrespective of the type of test
    (daqsocket,clisocket,i2csocket) = zmqctrl.pre_init(options)

    #nestedConf = nested_dict()
    #for key in i2csocket.yamlConfig.keys():
    #    if key.find('roc_s')==0:
    #        nestedConf[key]['sc']['ReferenceVoltage']['all']['Toa_vref']=200
    #        nestedConf[key]['sc']['ReferenceVoltage']['all']['Tot_vref']=500
    #i2csocket.update_yamlConfig(yamlNode=nestedConf.to_dict())
    #i2csocket.configure(yamlNode=nestedConf.to_dict())

    injectionConfig = {
        'gain' : 1,   # gain=0: LowRange, gain=1: HighRange
        'calib' : 200,
        # 'injectedChannels' : [36, 38, 40, 42, 44, 46, 48, 50, 52]  # scan 1
        # 'injectedChannels' : [54, 56, 58, 60, 62, 64, 66, 68, 70]  # scan 2
        # 'injectedChannels' : [37, 39, 41, 43, 45, 47, 49, 51, 53]  # scan 3
        # 'injectedChannels' : [55, 57, 59, 61, 63, 65, 67, 69, 71]  # scan 4
        'injectedChannels' : [0, 2, 4, 6, 8, 10, 12, 14, 16]  # scan 5
        # 'injectedChannels' : [18, 20, 22, 24, 26, 28, 30, 32, 34]  # scan 6
        # 'injectedChannels' : [1, 3, 5, 7, 9, 11, 13, 15, 17]  # scan 7
        # 'injectedChannels' : [19, 21, 23, 25, 27, 29, 31, 33, 35]  # scan 8
        # 'injectedChannels' : [6, 10, 45, 52]  # scan 8
        
        # 'injectedChannels' : [6, 15, 24, 32, 39, 48, 57, 63]
        # 'injectedChannels' : [4*i for i in range(1,8)]
    }
    sampling_scan(i2csocket,daqsocket,clisocket,options.odir,options.dut,injectionConfig,suffix="")
