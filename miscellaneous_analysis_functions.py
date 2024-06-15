from level0.analyzer import *
from scipy.optimize import curve_fit
import glob
import seaborn as sns
sns.set_style("ticks")
from matplotlib.ticker import MultipleLocator
import yaml, os
from typing import List

from nested_dict import nested_dict

import pandas as pd
import numpy as np
import copy

def get_num_string(string,search_string):
    string_start = string.find(search_string)
    val = ''
       
    flag = 0
    print("Find string",string_start)
    if string[string_start+len(search_string)].isdigit():
        flag = 1
        search_begin = string_start+len(search_string)
        if flag == 1:
            for i in range(search_begin,len(string)):
                cur_char = string[i]
                #print()
                if cur_char.isdigit():
                    val+=cur_char
                else:
                    break
    print("Value obtained from string",val)                
    return val                    


#This assumes the config file is named in a somewhat specific format - either convgain"value" or gainconv"value" (no spaces and no underscore and the search is not case specific)
def get_conveyor_gain(config_file):
    search_string = config_file.lower()
    gain_start = search_string.find("gain")
    conv_start = search_string.find("conv")
    conveyor_gain = ''
    flag = 0
    
    if search_string[gain_start+4].isdigit():
        flag = 1
        search_begin = gain_start+4
        
    elif search_string[conv_start+4].isdigit():
        flag = 1
        search_begin = conv_start+4
    
    else:
        print("Wrong format for file name!")
    
    if flag == 1:
        for i in range(search_begin,len(search_string)):
            cur_char = search_string[i]
            print()
            if cur_char.isdigit():
                conveyor_gain+=cur_char
            else:
                break
        #print(conveyor_gain)
        return(float(conveyor_gain))
    
def set_key_dict(nestedConf:dict, level_keys:List[str], bottom_level_keys:List[str], key_values:List[float]):
    if len(bottom_level_keys) != len(key_values):
        print("Insufficient number of channelwise parameters")

    elif len(bottom_level_keys) == len(key_values):
        #print()
        #print(level_keys)
        level = len(level_keys)
        #print("Level of the key",level)
        if level > 0:
            cur_key = level_keys.pop()
            #print("Current level key",cur_key)

            if cur_key not in nestedConf:
                nestedConf.setdefault(cur_key,dict())
            
            #print(nestedConf)
            nestedConf[cur_key] = set_key_dict(nestedConf[cur_key], level_keys, bottom_level_keys, key_values)
        
        elif level == 0:
            for i in range(len(bottom_level_keys)):
                if bottom_level_keys[i] not in nestedConf:
                    nestedConf.setdefault(bottom_level_keys[i],key_values[i])
                elif bottom_level_keys[i] in nestedConf:
                    nestedConf[bottom_level_keys[i]]=key_values[i]
    return nestedConf
    
def merge_nested(a:nested_dict,b:nested_dict):
    print("Original safe load array",b)
    for key in a.keys():
        if key in b.keys():
            print("common key exists")
            print(key)
            #print(a[key])
            #print(b[key])
            #print()
            merge_nested(a[key],b[key])
        else:
            ("No common key")
            print(str(key))
            print(a[key])
            
            b[key] = copy.deepcopy(a[key])
            #print(type(b))
            #print(b[key])
    return b           
      
 #Performs fit from the yaml file and determines the injection scan slope wrt the number of channels in each half     
 
def get_slope_ch_nos(process,subprocess,indir,odir,channel_nos,conv_gain,chip):

    with open(indir,'r') as file:
        slope_limits = yaml.safe_load(file)
        ch_nos_x = []
        slope_y = []
        
        for key in slope_limits.keys():
            print("Key name", key)
            if key.find(process+'ernal '+ subprocess + ' injection') == 0: #i.e. the key starts with this substring
            #Because there will be other tests as well
                print("Injection criteria written to file")
                
                for key_chip in slope_limits[key].keys():
                    print("Key name for chips keys",key_chip)
                    if key_chip.find("roc_s"+str(chip))==0:
                        
                        for key_slope in slope_limits[key][key_chip].keys():
                            string_start = key_slope.find('ADC_vs_calib_slope_')
                            if string_start>=0 & string_start <len(key_chip): #This means that the search string is somewhere inside the main string

                                ch_nos = int(get_num_string(key_slope,'ADC_vs_calib_slope_'))

                                ch_nos_x = np.append(ch_nos_x,ch_nos)
                                for key_gain in slope_limits[key][key_chip][key_slope].keys():
                                    conv_gain_file = float(get_num_string(key_gain,'conv_gain_'))
                                    #From the file, we only need one because that can be scaled accordingly for conveyor case (not dependent on conveyor gain for preamp case)
                                    
                                    if subprocess == 'preamp':
                                        scale_factor = 1
                                    elif subprocess == 'conv':
                                        scale_factor = conv_gain/conv_gain_file
                                    
                                    slope_val = float(slope_limits[key][key_chip][key_slope][key_gain])*scale_factor
                                    slope_y = np.append(slope_y,slope_val)
                                
                        print(ch_nos_x)
                        print(slope_y)

                        #popt, pcov = curve_fit(lambda x,a,b:a*x+b, ch_nos_x, slope_y, p0=[-0.1,2.1])
                        popt, pcov = curve_fit(lambda x, A, t, y0: A * np.exp(x * t) + y0, ch_nos_x, slope_y, p0=[2.5,-1,0.5])
                        fig, axes = plt.subplots(1,1,figsize=(16,9),sharey=False)
                        axes.set_ylabel(f'Slope from injection scan')
                        axes.set_xlabel(r'Number of channels injected in one half')
                        axes.xaxis.grid(True)
                        
                        axes.scatter( ch_nos_x, slope_y, marker='o')
                        #axes.plot(ch_nos_x,popt[0]*ch_nos_x+popt[1])
                        print("fit parameter values", popt[0],popt[1],popt[2])
                        
                        ch_nos_plot = []
                        for i in range(int(np.amin(ch_nos_x)),int(np.amax(ch_nos_x))+1):
                            ch_nos_plot = np.append(ch_nos_plot,i)
                        axes.plot(ch_nos_plot,popt[0] * np.exp(ch_nos_plot * popt[1]) + popt[2])
                        
                        plt.savefig(f'{odir}/Injection_scan_slope_exp_decay_fit.png', format='png', bbox_inches='tight')         
                        #print("Saved image for linear region")
                        plt.close()
                        
                        slope_ch = popt[0] * np.exp(channel_nos * popt[1]) + popt[2]
                        #print("Slope of injection scan according to number of injected channels", slope_ch)
                        
    return slope_ch
              
'''                 
def get_width_ch_nos(process,subprocess,indir,odir,channel_nos,conv_gain,chip,wd_type):
    width_ch = 0
    with open(indir,'r') as file:
        slope_limits = yaml.safe_load(file)
        ch_nos_x = []
        width_y = []
        
        for key in slope_limits.keys():
            print("Key name", key)
            if key.find(process+'ernal '+ subprocess + ' injection') == 0: #i.e. the key starts with this substring
            #Because there will be other tests as well
                print("Injection criteria written to file")
                
                for key_chip in slope_limits[key].keys():
                    print("Key name for chips keys",key_chip)
                    if key_chip.find("roc_s"+str(chip))==0:
                    
                        for key_ch in slope_limits[key][key_chip].keys():
                            string_start = key_ch.find('num_ch_')
                            if string_start>=0 & string_start <len(key_ch): #This means that the search string is somewhere inside the main string
                                ch_nos = int(get_num_string(key_ch,'num_ch_'))
                                ch_nos_x = np.append(ch_nos_x,ch_nos)
                                
                                for key_wd in slope_limits[key][key_chip][key_ch].keys():
                                    if key_wd.find(wd_type)==0:
                                        width_y = np.append(width_y,slope_limits[key][key_chip][key_ch][key_wd])
                        
                                
                        print(ch_nos_x)
                        print(width_y)
                        
                        fig, axes = plt.subplots(1,1,figsize=(16,9),sharey=False)
                        axes.set_ylabel(f'Slope from injection scan')
                        axes.set_xlabel(r'Number of channels injected in one half')
                        axes.xaxis.grid(True)
                        axes.scatter( ch_nos_x, width_y, marker='o')
                        
                        popt, pcov = curve_fit(lambda x, A, t: A * np.exp(x * t), ch_nos_x, width_y, p0=[2,1])
                        print("fit parameter values", popt[0],popt[1])
                        
                        ch_nos_plot = []
                        for i in range(int(np.amin(ch_nos_x)),int(np.amax(ch_nos_x))+1):
                            ch_nos_plot = np.append(ch_nos_plot,i)
                        axes.plot(ch_nos_plot,popt[0] * np.exp(ch_nos_plot * popt[1]))
                        
                        plt.savefig(f'{odir}/Sampling_scan_'+wd_type+'.png', format='png', bbox_inches='tight')         
                        #print("Saved image for linear region")
                        plt.close()
                        
                        #width_ch = popt[0] * np.exp(channel_nos * popt[1]) + popt[2]
                        #print("Slope of injection scan according to number of injected channels", width_ch)
                        
'''      


def get_width_ch_nos(process,subprocess,indir,odir,channel_nos,conv_gain,chip):
    width_ch = 0
    with open(indir,'r') as file:
        slope_limits = yaml.safe_load(file)
        ch_nos_x = []
        rise_wd_y = []
        fall_wd_y = []
        slope_y = []
        inv_prod_y = []
        ratio_rf_y = []
        
        for key in slope_limits.keys():
            print("Key name", key)
            if key.find(process+'ernal '+ subprocess + ' injection') == 0: #i.e. the key starts with this substring
            #Because there will be other tests as well
                print("Injection criteria written to file")
                
                for key_chip in slope_limits[key].keys():
                    print("Key name for chips keys",key_chip)
                    if key_chip.find("roc_s"+str(chip))==0:
                        
                        for key_ch in slope_limits[key][key_chip].keys():
                            string_start = key_ch.find('num_ch_')
                            if string_start>=0 & string_start <len(key_ch): #This means that the search string is somewhere inside the main string
                                ch_nos = int(get_num_string(key_ch,'num_ch_'))
                                ch_nos_x = np.append(ch_nos_x,ch_nos)
                                
                                for key_wd in slope_limits[key][key_chip][key_ch].keys():
                                    if key_wd.find("Rise")==0:
                                        rise_wd_y = np.append(rise_wd_y,slope_limits[key][key_chip][key_ch][key_wd])
                                            
                                    if key_wd.find("Fall")==0:
                                        fall_wd_y = np.append(fall_wd_y,slope_limits[key][key_chip][key_ch][key_wd])

                                    
                                    if key_wd.find("ADC_vs_calib_slope")==0:

                                        for key_gain in slope_limits[key][key_chip][key_ch][key_wd].keys():
                                            conv_gain_file = float(get_num_string(key_gain,'conv_gain_'))
                                            #From the file, we only need one because that can be scaled accordingly for conveyor case (not dependent on conveyor gain for preamp case)
                                            
                                            if subprocess == 'preamp':
                                                scale_factor = 1
                                            elif subprocess == 'conv':
                                                scale_factor = conv_gain/conv_gain_file
                                            
                                            slope_val = float(slope_limits[key][key_chip][key_ch][key_wd][key_gain])*scale_factor
                                            slope_y = np.append(slope_y,slope_val)
                        for i in range(len(slope_y)):          
                            inv_prod_y = np.append(inv_prod_y,slope_y[i]*(fall_wd_y[i]+rise_wd_y[i]))
                            ratio_rf_y = np.append(ratio_rf_y,rise_wd_y[i]/fall_wd_y[i])
                                
                        print(ch_nos_x)
                        print(rise_wd_y)
                        print(fall_wd_y)
                        print(slope_y)
                        print(inv_prod_y)
                        print(np.mean(inv_prod_y))
                        print(ratio_rf_y)
                        popt, pcov = curve_fit(lambda x, A, t: A * np.exp(x * t), ch_nos_x, fall_wd_y, p0=[2,1])
                        print("fit parameter values", popt[0],popt[1])
                        
                        #popt, pcov = curve_fit(lambda x,a,b:a*x+b, ch_nos_x, fall_wd_y, p0=[2,20])
                        #print("fit parameter values", popt[0],popt[1])
                        #width_ch = popt[0] * np.exp(channel_nos * popt[1]) + popt[2]
                        #print("Slope of injection scan according to number of injected channels", width_ch)

    return np.mean(inv_prod_y), ratio_rf_y
