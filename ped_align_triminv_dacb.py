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
def make_plots(channel,configFile): #Heat map, here there will be only one channel per plot (the shape is expected to be pretty much the same for all channels anyway)
    #expandAllChannels.expandAllChannels(configFile,output)
    with open(configFile) as f:
        cfg = yaml.safe_load(f)
    #calib_i =0
    #cm_i    =0
    #chan_i  =0 
    
    dacb = []
    #df = pd.read_csv('/home/reinecke/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/pedestal_adjustment_MalindaTB3/data/test/pedestal_scan/run_20240522_190858/dataPd.csv', index_col=0)
    #df = pd.read_csv('/home/reinecke/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/pedestal_adjustment_MalindaTB3/data/test/pedestal_scan/run_20240523_140026/dataPd.csv', index_col=0)
    #df = pd.read_csv('/home/reinecke/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/pedestal_adjustment_MalindaTB3/data/test/pedestal_scan/run_20240524_112745/dataPd.csv', index_col=0)
    #df = pd.read_csv('/home/reinecke/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/pedestal_adjustment_MalindaTB3/data/test/pedestal_scan/run_20240524_161528/dataPd.csv', index_col=0)
    df = pd.read_csv('/home/reinecke/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/pedestal_adjustment_MalindaTB3/data/test/pedestal_scan/run_20240527_103749/dataPd.csv', index_col=0)
    print(df) 
    column_headers_old = list(df.columns.values)
    print("The Column Header old:", column_headers_old)    

    #data frame cut for deciding first pedestal target half wise
    #dacb_grad_0 = target_0
    #Putting cuts for gradient not equal to 0 in both directions simultaneously (of course by fixing the other)
    #First is for dacb keeping trim_inv fixed at 0, second is for trim_inv keeping dacb fixed at 0
    
    target_0_cut = df[df['channel']<36].loc[df[df['channel']<36].apply(lambda row: row['16'] > row['0'], axis=1), column_headers_old]

    data_grad_0 = pd.DataFrame()
    data_grad_0['triminv_grad'] = df[df['channel']<36].loc[0]['16']-df[df['channel']<36].loc[0]['0']

    plt.plot(df[df['channel']<36].channel[df[df['channel']<36].index ==0], data_grad_0.triminv_grad, marker='o',linestyle='none')
    plt.savefig("/home/reinecke/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/pedestal_adjustment_MalindaTB3/triminv_grad0_%s.png"%channel)

    # | (target_0.loc[16]['0']>target_0.loc[0]['0'])
    target_half_0 = target_0_cut.loc[0]['32'].median()
    print(df[df['channel']<36])
    print(target_0_cut)

    print("Target for half 0",target_half_0)
    print("Number of channels",len(df[df['channel']<36][df[df['channel']<36].index ==0]))

    target_1_cut = df[(df['channel']>=36) & (df['channel']<72)].loc[df[(df['channel']>=36) & (df['channel']<72)].apply(lambda row: row['16'] > row['0'], axis=1), column_headers_old]

    data_grad_1 = pd.DataFrame()
    data_grad_1['triminv_grad'] = df[(df['channel']>=36) & (df['channel']<72)].loc[0]['16']-df[(df['channel']>=36) & (df['channel']<72)].loc[0]['0']

    plt.plot(df[(df['channel']>=36) & (df['channel']<72)].channel[df[(df['channel']>=36) & (df['channel']<72)].index ==0], data_grad_1.triminv_grad, marker='o',linestyle='none')
    plt.savefig("/home/reinecke/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/pedestal_adjustment_MalindaTB3/triminv_grad1_%s.png"%channel)

    target_half_1 = target_1_cut.loc[0]['32'].median()
    print(df[(df['channel']>=36) & (df['channel']<72)])
    print(target_1_cut)
    print("Target for half 1",target_half_1)

    print("Number of channels",len(df[(df['channel']>=36) & (df['channel']<72)][df[(df['channel']>=36) & (df['channel']<72)].index ==0]))
    
    for i in range(len(ch_total)):
        ch_loop = 0
        
        for channel in ch_total[i]:
            grad  = (df[df.channel ==channel].loc[0]['16']-df[df.channel ==channel].loc[0]['0'])/(16-0)
            offset = df[df.channel ==channel].loc[0]['16'] - 16*grad
            grad_dacb = (df[df.channel ==channel].loc[16]['0']-df[df.channel ==channel].loc[0]['0'])/(16-0)
            print(round(grad,3),round(offset,3),round(grad_dacb,3))
            flag=0
  
            try:  
                if channel <36:
                    intval = int((target_half_0-offset)/grad)
                elif channel >=36 & channel < 72:
                    intval = int((target_half_1-offset)/grad)
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

            cfg["roc_s0"]["sc"][ch_key[i]][ch_loop]["trim_inv"] = intval
            if dacbval >=0:
                cfg["roc_s0"]["sc"][ch_key[i]][ch_loop]["dacb"] = dacbval
            elif dacbval < 0:
                cfg["roc_s0"]["sc"][ch_key[i]][ch_loop]["dacb"] = -dacbval
                cfg["roc_s0"]["sc"][ch_key[i]][ch_loop]["sign_dac"] = 1
            print(ch_key[i],ch_loop)
            ch_loop += 1
            print("trim_inv value is ", intval)
            print("dacb value is ", dacbval)

        #print("over")

    #data frame cut for deciding first pedestal target half wise
    configFile0 = configFile[:configFile.find(".yaml")]
    
    with open(configFile0+"_triminv_D8_4_new.yaml", "w") as o:
        yaml.dump(cfg, o)
    print("Saved new config file as:"+configFile0+"_triminv_D8_4_new.yaml")        
    
    data_0 = df[df['channel']==channel].copy()
    print(data_0)
    #dacb.append(data_0['dacb'])


    data_inter = data_0.drop("channel", axis='columns')
    column_headers = list(data_inter.columns.values)
    print("The Column Header :", column_headers)    
    print(data_inter)

    sb.heatmap(data_inter, annot=True)
    plt.savefig("/home/reinecke/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/pedestal_adjustment_MalindaTB3/triminv_dacb_%s.png"%channel)
    print("Dacb values",dacb)

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

    make_plots(1,options.configFile)
