import zmq, datetime,  os, subprocess, sys, yaml, glob, math
from time import sleep

import myinotifier,util
import analysis.level0.pedestal_scan_analysis as analyzer
import zmq_controler as zmqctrl
from nested_dict import nested_dict
import expandAllChannels
import uproot
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sb

calib_ch = [72,73]
cm_ch    = [74,75,76,77]
ch = []
for i in range(0,72):
    ch.append(i)
print(ch)
#ch_total = [ch,cm_ch,calib_ch]
#ch_key = ["ch","cm","calib"]
ch_total = [ch]
ch_key = ["ch"]
ch_type = [0]
def make_plots(channel,configFile): #Heat map, here there will be only one channel per plot (the shape is expected to be pretty much the same for all channels anyway)
    #expandAllChannels.expandAllChannels(configFile,output)
    with open(configFile) as f:
        cfg = yaml.safe_load(f)
    
    ped_analyzer.data = ped_analyzer.data.sort_values(by=["dacb","trim_inv"], ignore_index=True)
    #print(ped_analyzer.data[(ped_analyzer.data['dacb']==0) & (ped_analyzer.data['trim_inv']==0)])
    print(ped_analyzer.data)
    dacb_val = ped_analyzer.data['dacb'].unique()
    trim_val = ped_analyzer.data['trim_inv'].unique()
    print("dacb values", dacb_val)   
    print(type(dacb_val)) 

    column_headers_old = list(ped_analyzer.data.columns.values)
    print("The Column Header old:", column_headers_old)    

    nhalf = ped_analyzer.data['half'].unique()
    print("Number of halves",nhalf)
    for half in range(len(nhalf)):
        channel_half = ped_analyzer.data[(ped_analyzer.data['half']==half) & (ped_analyzer.data['channeltype']==0)]
        trim_1_cut = channel_half[(channel_half['trim_inv']==trim_val[1]) & (channel_half['dacb']==dacb_val[0])].set_index('channel')
        trim_0_cut = channel_half[(channel_half['trim_inv']==trim_val[0]) & (channel_half['dacb']==dacb_val[0])]
        channel_target = channel_half[(channel_half['trim_inv']==32) & (channel_half['dacb']==0)].set_index('channel')
        print(channel_target)
        channel_target['triminv_grad'] = trim_1_cut['adc_median']-trim_0_cut['adc_median']
        channel_cut = channel_target[channel_target['triminv_grad']>0]
        print(channel_cut)
        target = channel_target[channel_target['triminv_grad']>0]['adc_median'].median()
        print(target)

        #This gives all the channels in one of the halves (excluding cm and calib)
        for channel in channel_cut.index: #This eliminates any whose second triminv entry is less than/equal to the first entry (adhoc gradient > 0 only)

            print("Channel number",channel)
            print("Channel type", channel_cut[channel_cut.index==channel]['channeltype'].item())

            #Values for triminv and dacb gradient
            ped_high = channel_half[(channel_half['channel'] ==channel) & (channel_half['trim_inv'] == 16) & (channel_half['dacb'] == 0)]['adc_median'].item()
            ped_low = channel_half[(channel_half['channel'] ==channel) & (channel_half['trim_inv'] == 0) & (channel_half['dacb'] == 0)]['adc_median'].item()
            ped_dacb_high = channel_half[(channel_half['channel'] ==channel) & (channel_half['trim_inv'] == 0) & (channel_half['dacb'] == 16)]['adc_median'].item()
            
            print("Pedestal Values for gradient", ped_high,ped_low)
            grad  = (ped_high - ped_low)/(16-0)
            #print("Value of gradient", grad)
            offset = ped_high - 16*grad
            #print(offset)
            grad_dacb = (ped_dacb_high-ped_low)/(16-0)
            
            print(round(grad,3),round(offset,3),round(grad_dacb,3))
            print(target)
            flag=0
      
            try:  
                intval = int((target-offset)/grad)
                dacbval = 0 #by default unless the intval overflows
            except (OverflowError, ValueError):
                intval = 0
                flag=1

            if intval >= 64:
                dacbval = int((intval - 63)*grad/grad_dacb)
                intval = 63
                print("triminv upper limit")
            elif intval < 0:
                dacbval = int((intval - 0)*grad/grad_dacb)
                intval = 0
                print("triminv lower limit")

            '''
            cfg["roc_s0"]["sc"][ch_key[i]][ch_loop]["trim_inv"] = intval
            cfg["roc_s0"]["sc"][ch_key[i]][ch_loop]["dacb"] = abs(dacbval)
            if dacbval >=0:
                cfg["roc_s0"]["sc"][ch_key[i]][ch_loop]["sign_dac"] = 0
            elif dacbval < 0:
                cfg["roc_s0"]["sc"][ch_key[i]][ch_loop]["sign_dac"] = 1
            print(ch_key[i],ch_loop)
            ch_loop += 1
            '''
            print("trim_inv value is ", intval)
            print("dacb value is ", dacbval)
        
        #print("over")
            print()

    #data frame cut for deciding first pedestal target half wise
    configFile0 = configFile[:configFile.find(".yaml")]
    
    with open(configFile0+"_triminv_D8_12_new.yaml", "w") as o:
        yaml.dump(cfg, o)
    print("Saved new config file as:"+configFile0+"_triminv_D8_12_new.yaml")        
    '''
    data_0 = ped_analyzer.data[ped_analyzer.data['channel']==channel].copy()
    print(data_0)
    #dacb.append(data_0['dacb'])


    data_inter = data_0.drop("channel", axis='columns')
    column_headers = list(data_inter.columns.values)
    print("The Column Header :", column_headers)    
    print(data_inter)

    sb.heatmap(data_inter, annot=True)
    plt.savefig("/home/reinecke/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/pedestal_adjustment_MalindaTB3/triminv_dacb_%s.png"%channel)
    #print("Dacb values",dacb)
    '''
if __name__ == "__main__":
    from optparse import OptionParser
    parser = OptionParser()
    
    parser.add_option("-d", "--dut", dest="dut",
                      help="device under test")
    
    parser.add_option("-i", "--hexaIP",
                      action="store", dest="hexaIP",
                      help="IP address of the zynq on the hexactrl board")
    
    parser.add_option("-f", "--configFile",default="./configs/init.yaml",
                      action="store", dest="configFile",
                      help="initial configuration yaml file")
    
    parser.add_option("-o", "--odir",
                      action="store", dest="odir",default='./data',
                      help="output base directory")
    
    parser.add_option("--daqPort",
                      action="store", dest="daqPort",default='6000',
                      help="port of the zynq waiting for daq config and commands (configure/start/stop/is_done)")
    
    parser.add_option("--i2cPort",
                      action="store", dest="i2cPort",default='5555',
                      help="port of the zynq waiting for I2C config and commands (initialize/configure/read_pwr,read/measadc)")
    
    parser.add_option("--pullerPort",
                      action="store", dest="pullerPort",default='6001',
                      help="port of the client PC (loccalhost for the moment) waiting for daq config and commands (configure/start/stop)")
    
    parser.add_option("-I", "--initialize",default=False,
                      action="store_true", dest="initialize",
                      help="set to re-initialize the ROCs and daq-server instead of only configuring")
    parser.add_option("-p", "--outputConfig",
                      action="store", dest="output",
                      help="output base directory")
    
    (options, args) = parser.parse_args()
    print(options)

    odir = '/home/reinecke/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/pedestal_adjustment_MalindaTB3/data/test/pedestal_scan/run_20240527_160313'
    ped_analyzer = analyzer.pedestal_scan_analyzer(odir=odir)
    files = glob.glob(odir + "/pedestal_scan*.root")
    print(files)

    for f in files:
        ped_analyzer.add(f)

    ped_analyzer.mergeData()
    print(ped_analyzer.data)
    
    
    #print(ped_analyzer.data[ped_analyzer.data['dacb']==0])
    #print(ped_analyzer.data[(ped_analyzer.data['dacb']==48) & (ped_analyzer.data['trim_inv']==48)])
    make_plots(1,options.configFile)
