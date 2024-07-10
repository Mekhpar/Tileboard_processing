import zmq, datetime,  os, subprocess, sys, yaml, glob
from time import sleep

import pandas
from level0.analyzer import *
import myinotifier,util
#import analysis.level0.toa_scan_analysis as analyzer
import analysis.level0.toa_scan_analysis_TB_23_08 as analyzer
import zmq_controler as zmqctrl
from nested_dict import nested_dict
import miscellaneous_functions as misc_func
import injection_scan_int_preamp_0502 as inj_preamp

def toa_scurvescan(i2csocket,daqsocket,clisocket,basedir,device_name,device_type,toa_vals,configFile,suffix=''):
    testName = "vreftoa_scurvescan"
    odir = misc_func.mkdir(os.path.realpath(basedir),device_type,testName = testName,suffix=suffix)
    with open(configFile) as f:
        config = yaml.safe_load(f)

    for trimtoa in toa_vals:
        nestedConf = nested_dict()    
        trimtoa_odir = odir+"trim_toa_%s/"%(trimtoa)
        print("Directories",trimtoa_odir)
        
        for rocId in config.keys():
            if rocId.find('roc_s')==0:
                for channel in range(0,72):
                    nestedConf[rocId]['sc']['ch'][channel]['trim_toa'] = trimtoa
                    
        i2csocket.configure(yamlNode=nestedConf.to_dict())
        print("Injection scan for trim_toa",trimtoa)
        sipm_injection_scan(i2csocket,daqsocket,clisocket,trimtoa_odir,options.dut,options.device_type,suffix=options.suffix,keepRawData=0,analysis=1)

def sipm_injection_scan(i2csocket,daqsocket,clisocket,trimtoa_odir,device_name,device_type,suffix='',keepRawData=1,analysis=1):
    
    injectedChannels = range(0, 36)
       
    injection_scan_mode=1
    '''
    preamp_sampling_scan_phase_dir = '/home/hgcal/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/data/TB3/TB3_D8_11/PreampSampling_scan_Calib_200_TB3_D8_11_14/'
    with open(preamp_sampling_scan_phase_dir+'/best_phase.yaml','r+') as fin:
        BX_phase_info = yaml.safe_load(fin)   
    '''
    len_batch = 36
    if injection_scan_mode == 1:
        print(" ############## Start injection scan #################")
        for batch_num in range(int(len(injectedChannels)/len_batch)):
            inj_batch = []
            for channel in range(len_batch):
                cur_chan = batch_num*len_batch+channel
                inj_batch.append(cur_chan)
                inj_batch.append(cur_chan+ 36)
            injectionConfig = {
            #High range max phase for 6 injected channels
            #'BXoffset' : 22, # was 22
            #'phase' : 1,
            #'gain' : 1,
            
            #High range max phase for 6 injected channels
            'BXoffset' : 21, # was 22
            'phase' : 12,
            
            'gain' : 0,
            'calib' : [i for i in range(100,2000,20)],
            #'calib' : [i for i in range(100,140,20)],
            #'injectedChannels' : [injChannel, injChannel + 36]
            'injectedChannels' : inj_batch
            }
            print("Batch number", batch_num)
            print("Injected channels", inj_batch)
            inj_preamp.sipm_injection_scan(i2csocket,daqsocket,clisocket,trimtoa_odir,options.dut,device_type, injectionConfig,scurve_scan = 1,suffix="gain0_ch%i"%batch_num,active_menu = 'calibAndL1AplusTPG',keepRawData=1,analysis=1)
            
     # do not run the inotifier if the unpacker is not yet ready to read vectors inside metaData yaml file using key "chip_params"
    


if __name__ == "__main__":
    parser = misc_func.options_run()#This will be constant for every test irrespective of the type of test
    
    (options, args) = parser.parse_args()
    print(options)
    (daqsocket,clisocket,i2csocket) = zmqctrl.pre_init(options)

    ############    
    # SUFFIX CONFIG:
    timestamp_fulltest = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    '''
    if options.suffix == None:
        options_dut = options.dut + "/vreftoa_scurvescan/test_%s"%(timestamp_fulltest)
    else:
        options_dut = options.dut + "/vreftoa_scurvescan/test_%s_%s"%(timestamp_fulltest, options.suffix)
    '''    
    #print(" ############## options_dut = ",options_dut ," #################")
    ############
    toa_vals = [0,4,8,12,16,20,24,28] #Same as what I had used last time (for conveyor injection)
    toa_scurvescan(i2csocket,daqsocket,clisocket,options.odir,options.dut,options.device_type,toa_vals,options.configFile,suffix='')
