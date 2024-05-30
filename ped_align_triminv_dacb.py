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
    
    nchip = ped_analyzer.data['chip'].unique()
    for chip in nchip:
        print("ROC number",chip)
        channel_chip = ped_analyzer.data[ped_analyzer.data['chip']==chip].copy()

        channel_chip = channel_chip.sort_values(by=["dacb","trim_inv"], ignore_index=True)
        #print(channel_chip[(channel_chip['dacb']==0) & (channel_chip['trim_inv']==0)])
        #print(channel_chip)
        dacb_val = channel_chip['dacb'].unique()
        trim_val = channel_chip['trim_inv'].unique()
        print("dacb values", dacb_val)   
        print(type(dacb_val)) 

        column_headers_old = list(channel_chip.columns.values)
        print("The Column Header old:", column_headers_old)    
        grad_trim_high = 2.5
        grad_trim_low = 0.5

        grad_dacb_high = 8
        grad_dacb_low = 0.5

        nhalf = channel_chip['half'].unique()
        print("Number of halves",nhalf)
        for half in nhalf:
            channel_half = channel_chip[(channel_chip['half']==half) & (channel_chip['channeltype']==0)]
            channel_target = channel_half[(channel_half['trim_inv']==32) & (channel_half['dacb']==0)].set_index('channel')

            #Noise check
            for channel in channel_target.index:
                channel_target.loc[channel,'noise_0'] = int(len(channel_half[(channel_half['channel']==channel) & (channel_half['adc_stdd'] <=0.1)]))
                #print(channel_half[(channel_half['channel']==channel)]['adc_stdd'])
                #''' '''
            print(channel_target['noise_0'])
            trim_0_cut = channel_half[(channel_half['trim_inv']==trim_val[0]) & (channel_half['dacb']==dacb_val[0])]
            dacb_0_cut = channel_half[(channel_half['trim_inv']==trim_val[0]) & (channel_half['dacb']==dacb_val[0])]
            
            #Comparing the gradients instead of doing a fit and calculating chi_squared
            for i in range(1,4):
                dacb_cut = channel_half[(channel_half['trim_inv']==trim_val[0]) & (channel_half['dacb']==dacb_val[i])].set_index('channel')
                trim_cut = channel_half[(channel_half['trim_inv']==trim_val[i]) & (channel_half['dacb']==dacb_val[0])].set_index('channel')
                channel_target['trim_grad_'+str(i)] = (trim_cut['adc_median']-trim_0_cut['adc_median'])/(trim_val[i]-trim_val[0])
                channel_target['dacb_grad_'+str(i)] = (dacb_cut['adc_median']-dacb_0_cut['adc_median'])/(dacb_val[i]-dacb_val[0])

            #In this case, this is the y intercept of triminv
                if i==1:
                    channel_target['offset'] = trim_cut['adc_median'] - trim_val[i]*channel_target['trim_grad_'+str(i)] #Warning 3
                    
            #Cuts for filtering out bad channels        
            channel_cut = channel_target[(channel_target['trim_grad_1'] > grad_trim_low*4/4) & (channel_target['trim_grad_1'] < grad_trim_high*4/4) & (channel_target['dacb_grad_1'] > grad_dacb_low*4/4) & (channel_target['dacb_grad_1'] < grad_dacb_high*4/4)]
            channel_cut = channel_cut[channel_cut['noise_0'] == 0]
            #2nd cut for comparing 3 different gradients
            channel_cut = channel_cut[(abs(channel_cut['dacb_grad_3'] - channel_cut['dacb_grad_2'])<0.5) & (abs(channel_cut['dacb_grad_3'] - channel_cut['dacb_grad_1'])<0.5) & (abs(channel_cut['dacb_grad_2'] - channel_cut['dacb_grad_1'])<0.5)]
            channel_cut = channel_cut[(abs(channel_cut['trim_grad_3'] - channel_cut['trim_grad_2'])<0.5) & (abs(channel_cut['trim_grad_3'] - channel_cut['trim_grad_1'])<0.5) & (abs(channel_cut['trim_grad_2'] - channel_cut['trim_grad_1'])<0.5)]

            print(channel_cut)
            target = channel_target[channel_target['trim_grad_1']>0]['adc_median'].median()
            print(target)

            channel_mod = channel_cut.copy()
            #for channel in channel_cut.index:
            channel_mod['trim'] = (target-channel_cut['offset'])/channel_cut['trim_grad_1'] #Warning 4
            #Default values for dacb and sign_dac before calculating triminv limits
            channel_mod['dacb_fit'] = 0
            channel_mod['signdac'] = 0
            
            channel_mod_2 = channel_mod.copy()
            
            #Rounding off to the nearest integer for triminv
            channel_mod_2.loc[channel_mod_2['trim'] % 1 < 0.5,'trim'] = channel_mod['trim'].apply(lambda x: math.floor(x)) #Warning 5
            #channel_cut.loc[channel_cut['trim'] % 1 < 0.5,'trim'] = channel_cut.loc[channel_cut['trim'] % 1 < 0.5,'trim'].apply(lambda x: math.floor(x))
            channel_mod_2.loc[channel_mod_2['trim'] % 1 >= 0.5,'trim'] = channel_mod['trim'].apply(lambda x: math.ceil(x)) #Warning 6
            
            channel_mod_3 = channel_mod_2.copy()

            channel_mod_3.loc[channel_mod_3['trim'] > 64, 'dacb_fit'] = (channel_mod_2['trim'] - 63)*channel_mod_2['trim_grad_1']/channel_mod_2['dacb_grad_1'] #Warning 7
            channel_mod_3.loc[channel_mod_3['trim'] < 0, 'dacb_fit'] = (channel_mod_2['trim'] - 0)*channel_mod_2['trim_grad_1']/channel_mod_2['dacb_grad_1'] #Warning 8

            channel_mod_3.loc[channel_mod_3['trim'] > 64, 'trim'] = 63
            channel_mod_3.loc[channel_mod_3['trim'] < 0, 'trim'] = 0
            
            channel_mod_4 = channel_mod_3.copy()

            channel_mod_4.loc[channel_mod_4['dacb_fit'] < 0, 'signdac'] = 1 #Warning 9
            channel_mod_4.loc[channel_mod_4['dacb_fit'] < 0, 'dacb_fit'] = -channel_mod_3['dacb_fit']

            channel_mod_5 = channel_mod_4.copy()

            #Rounding off to the nearest integer for dacb
            channel_mod_5.loc[channel_mod_5['dacb_fit'] % 1 < 0.5,'dacb_fit'] = channel_mod_4['dacb_fit'].apply(lambda x: math.floor(x)) #Warning 11
            channel_mod_5.loc[channel_mod_5['dacb_fit'] % 1 >= 0.5,'dacb_fit'] = channel_mod_4['dacb_fit'].apply(lambda x: math.ceil(x)) #Warning 12

            channel_mod_5.loc[abs(channel_mod_5['dacb_fit']) > 63 , 'dacb_fit'] = 0
            print(channel_mod_5)
            #print(channel_mod_5['noise_0'])

            for channel in channel_mod_5.index:
                cfg["roc_s0"]["sc"]["ch"][channel]["trim_inv"] = int(channel_mod_5.loc[channel,'trim'])
                cfg["roc_s0"]["sc"]["ch"][channel]["dacb"] = int(channel_mod_5.loc[channel,'dacb_fit'])
                cfg["roc_s0"]["sc"]["ch"][channel]["sign_dac"] = int(channel_mod_5.loc[channel,'signdac'])
            
    #data frame cut for deciding first pedestal target half wise
    configFile0 = configFile[:configFile.find(".yaml")]
    
    #'''
    with open(configFile0+"_triminv_D8_11_new.yaml", "w") as o:
        yaml.dump(cfg, o)
    print("Saved new config file as:"+configFile0+"_triminv_D8_11_new.yaml")   
    #'''

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

    odir = '/home/reinecke/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/pedestal_adjustment_MalindaTB3/data/test/pedestal_scan/run_20240528_135349'
    #odir = '/home/reinecke/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/pedestal_adjustment_MalindaTB3/data/test/pedestal_scan/run_20240528_135323_alice' 
    #This is the D8_11 board which has at least one negative dacb (channel 4 half 0) so this is for exception checks
    ped_analyzer = analyzer.pedestal_scan_analyzer(odir=odir)
    files = glob.glob(odir + "/pedestal_scan*.root")
    print(files)

    for f in files:
        ped_analyzer.add(f)

    ped_analyzer.mergeData()
    print(ped_analyzer.data)
    
    make_plots(1,options.configFile)
