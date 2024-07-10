import zmq, datetime,  os, subprocess, sys, yaml, glob
from time import sleep

import pandas
from level0.analyzer import *
import myinotifier,util
#import analysis.level0.tot_scan_analysis as analyzer
#import analysis.level0.tot_scan_analysis_TB_23_08 as analyzer
import zmq_controler as zmqctrl
from nested_dict import nested_dict
import miscellaneous_functions as misc_func
import injection_scan_int_preamp_0502 as inj_preamp

def tot_scurvescan(i2csocket,daqsocket,clisocket,basedir,device_name,device_type,tot_vals,configFile,suffix=''):
    testName = "global_tot_scurvescan"
    odir = misc_func.mkdir(os.path.realpath(basedir),device_type,testName = testName,suffix=suffix)
    with open(configFile) as f:
        config = yaml.safe_load(f)

    for totvref in tot_vals:
        nestedConf = nested_dict()    
        totvref_odir = odir+"Tot_vref_%s/"%(totvref)
        print("Directories",totvref_odir)
        
        for rocId in config.keys():
            if rocId.find('roc_s')==0:
                nestedConf[rocId]['sc']['ReferenceVoltage'][0]['Tot_vref'] = totvref
                nestedConf[rocId]['sc']['ReferenceVoltage'][1]['Tot_vref'] = totvref
                    
        i2csocket.configure(yamlNode=nestedConf.to_dict())
        print("Injection scan for Tot_vref",totvref)
        sipm_injection_scan(i2csocket,daqsocket,clisocket,totvref_odir,options.dut,options.device_type,suffix=options.suffix,keepRawData=0,analysis=1)

def sipm_injection_scan(i2csocket,daqsocket,clisocket,totvref_odir,device_name,device_type,suffix='',keepRawData=1,analysis=1):
    
    injectedChannels = range(0, 1)
       
    injection_scan_mode=1
    '''
    preamp_sampling_scan_phase_dir = '/home/hgcal/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/data/TB3/TB3_D8_11/PreampSampling_scan_Calib_200_TB3_D8_11_14/'
    with open(preamp_sampling_scan_phase_dir+'/best_phase.yaml','r+') as fin:
        BX_phase_info = yaml.safe_load(fin)   
    '''
    len_batch = 1
    #len_batch = 6
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

            #High range max phase for 1 injected channel
            'BXoffset' : 21, # was 22
            'phase' : 15,
            'gain' : 1,
            
            #Low range max phase for 6 injected channels
            #'BXoffset' : 21, # was 22
            #'phase' : 12,
            
            #'gain' : 0,
            #'calib' : [i for i in range(100,2000,20)],
            
            'calib' : [i for i in range(0,2000,20)], #Useful for global tot (tot vref) of 300
            
            
            #'calib' : [i for i in range(1500,2500,20)], #for debugging
            #'calib' : [i for i in range(100,140,20)],
            #'injectedChannels' : [injChannel, injChannel + 36]
            'injectedChannels' : inj_batch
            }
            print("Batch number", batch_num)
            print("Injected channels", inj_batch)
            inj_preamp.sipm_injection_scan(i2csocket,daqsocket,clisocket,totvref_odir,options.dut,device_type, injectionConfig,scurve_scan = 1,suffix="gain0_ch%i"%batch_num,active_menu = 'calibAndL1AplusTPG',keepRawData=1,analysis=1)
            
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
        options_dut = options.dut + "/vreftot_scurvescan/test_%s"%(timestamp_fulltest)
    else:
        options_dut = options.dut + "/vreftot_scurvescan/test_%s_%s"%(timestamp_fulltest, options.suffix)
    '''    
    #print(" ############## options_dut = ",options_dut ," #################")
    ############
    tot_vals = [0,50,100,150,200,250,300,350,400,450,500,550,600,650,700,750,800,850,900,950] #Same as what I had used last time (for conveyor injection)
    #tot_vals = [300]
    #tot_vals = [32]
    #tot_vals = [0,8,16]
    tot_scurvescan(i2csocket,daqsocket,clisocket,options.odir,options.dut,options.device_type,tot_vals,options.configFile,suffix='')
