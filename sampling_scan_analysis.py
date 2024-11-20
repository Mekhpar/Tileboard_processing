from level0.analyzer import *
from scipy.optimize import curve_fit
import scipy
import glob
from matplotlib.ticker import AutoMinorLocator
import matplotlib
from nested_dict import nested_dict
import pandas as pd
import numpy as np

import analysis.level0.miscellaneous_analysis_functions as analysis_misc
import analysis.level0.pedestal_run_analysis
import awkward as ak

#import miscellaneous_analysis_functions as analysis_misc
#import pedestal_run_analysis

import yaml, os
import copy
from typing import List

def get_sign(num):
    sign = 0
    if num>0:
        sign = 1
    elif num<0:
        sign = -1
    else:
        pass
    return sign

#Right now this function is very specific but can/should be adapted to a more generic usage later  
#And this will only use the class that reads from the rnsummary/summary tree (not eventwise) 
def read_files(odir,test_name = 'pedestal_run'):
    #use_file = eval(test_name + '_analysis')
    use_file = eval('analysis.level0.'+test_name + '_analysis')
    test_analyzer = use_file.overall_analyzer(odir=odir)
    files = glob.glob(odir+"/"+test_name+"*.root")
    print(files)
    for f in files:
        test_analyzer.add(f)

    test_analyzer.mergeData()  
    data = test_analyzer.data.copy()
    return data
    
def read_val(chip,channel,channeltype,data,value = 'adc_median'):  
    val = data.loc[(data['chip']==chip) & (data['channeltype']==channeltype) & (data['channel']==channel), value].item()

    print("Read pedestal values successfully")
    return(val)

class event_analyzer(rawroot_reader):
    #It is probably sufficient to check by half wise instead of channel wise
    #3 flags for each chip (some boards have 2 ROCs) - 0 for fail, 1 for grey area and 2 for pass

    def check_corruption(self,pass_limit,fail_limit, fout = ''):
        #print(self.df) #This looks like the data below (what we want with 10000 events for each channel)
        #data = self.df
        nestedConf = nested_dict()
        nchip = len( self.df.groupby('chip').nunique() )
        chip_goodness = []
        for chip in range(nchip):
            nestedConf['corruption']['bad_half']['chip'+str(chip)]['half'] = []
            data = self.df[ self.df['chip']==chip ].copy()
            nhalves = len( data.groupby('half').nunique() )
            corrpt = pd.DataFrame(columns = ['half','corrpt_percent'],index=range(nhalves))
            chip_check_flag = 0
            for half in range(nhalves):
                data_half = data[ data['half']==half].copy()
                print("Half",half)
                corrupted_events = len(data_half[ data_half['corruption']!=0])
                total_events = len(data_half)
                print("Corrupted events and total number of events", corrupted_events,total_events)
                corrupt_percentage = (corrupted_events/total_events)*100.

                corrpt.loc[half].half = half
                corrpt.loc[half].corrpt_percent = corrupt_percentage

            print(corrpt)

            #Checking length of arrays after applying non corrupted/ corrupted cuts
            fail_half = corrpt[corrpt['corrpt_percent']>fail_limit].copy()
            pass_half = corrpt[corrpt['corrpt_percent']<=pass_limit].copy()

            grey_half = corrpt[corrpt['corrpt_percent']>pass_limit].copy()
            grey_half = grey_half[grey_half['corrpt_percent']<=fail_limit].copy()

            if len(fail_half) >=1:
                print("Chip failed to give good data")
                chip_goodness.append(0)
                for i in range(len(fail_half)):
                    nestedConf['corruption']['bad_half']['chip'+str(chip)]['half'] = int(fail_half['half'])

            elif len(grey_half) >=1:
                print("Chip may or may not be great")
                chip_goodness.append(1)

            elif len(pass_half) == nhalves:
                print("Chip is good")
                chip_goodness.append(2)

            with open(fout,'w') as file:
                print(yaml.dump(nestedConf.to_dict(),file,sort_keys=False))
                print("Written to yaml file")

        return chip_goodness

class overall_analyzer(analyzer):

    #This is for extracting the set parameter values from the directory/folder name (like calib pulse height for internal and LED bias or overvoltage for external case) since at present they are not stored in the root files
    def get_parameter_value(self,odir,parameter):
        search_string = odir.lower()
        val = analysis_misc.get_num_string(search_string,parameter+'_')
        #return (float(val))
        return val
        
    #Getting injected channels from the text file (TB2_info.txt) that also has temperature and bias information
    def get_injectedChannels(self,odir):
        line_number = 0
        line_ch = 0
        tb2_info = open(odir+"/TB2_info.txt", "r")
        lines_tb2 = tb2_info.readlines()
        #print(len(lines_tb2))
        for lines in lines_tb2:
            line_number+=1
            for words in lines.split():
                if words == "injectedChannels:":
                    line_ch = line_number
                    break
                        
        #print("Line containing injected channels", line_ch)
        injectedChannels = []

        for inj_ch in lines_tb2[line_ch].split():
            #print("Channels injected", int(inj_ch))
            injectedChannels.append(int(inj_ch))
     
        print("Full list of injected Channels (non zero gain)", injectedChannels)
        return injectedChannels

    def get_start_BX_phase(self,odir):
        line_number = 0
        line_ch = 0
        bx_start = 0
        phase_start = 0
        tb2_info = open(odir+"/TB2_info.txt", "r")
        lines_tb2 = tb2_info.readlines()
        print(len(lines_tb2))
        for lines in lines_tb2:
            line_number+=1
            for i in range(len(lines.split())): 
                if lines.split()[i] == "sample_scan:": #The latter word is the run number and 0 ensures that that is where the whole run is started from
                    if lines.split()[i+1]=="0":
                        line_ch = line_number
                        break
            #break           
        print("Line containing starting BX and phase settings", line_ch)
        line = lines_tb2[line_ch-1]
        print(line)
        for j in range(len(line.split())):
            #print(line[j])
            if line.split()[j] == "bx:":
                bx_start = int(line.split()[j+1])
            if line.split()[j] == "phase:":
                phase_start = int(line.split()[j+1])
        return bx_start,phase_start
        
    def get_start_trigger(self,odir):
        line_number = 0
        line_ch = 0
        bx_start = 0
        phase_start = 0
        tb2_info = open(odir+"/TB2_info.txt", "r")
        lines_tb2 = tb2_info.readlines()
        print(len(lines_tb2))
        for lines in lines_tb2:
            line_number+=1
            for i in range(len(lines.split())): 
                if lines.split()[i] == "trigger":
                    if lines.split()[i+1] == "pulse:":
                        line_ch = line_number
                        break
            #break           
        print("Line containing starting trigger pulse BX", line_ch)
        calib_bx = int(lines_tb2[line_ch].split()[0])
        return calib_bx

    def get_lh_range(self,odir):
        line_number = 0
        line_ch = 0
        bx_start = 0
        phase_start = 0
        tb2_info = open(odir+"/TB2_info.txt", "r")
        lines_tb2 = tb2_info.readlines()
        print(len(lines_tb2))
        for lines in lines_tb2:
            line_number+=1
            for i in range(len(lines.split())): 
                if lines.split()[i] == "gain:":
                    line_ch = line_number
                    break
            #break           
        print("Line containing gain value for low or high range case", line_ch)
        gain_lh = int(lines_tb2[line_ch].split()[0])
        return gain_lh

    #Getting number of injected channels for any particular half because that is required for deciding what pulse shape (mainly height and two widths) is required
    def chip_half(self,device_type,injectedChannels,odir):
        inj_data = self.data[ (self.data['channeltype']==0) & (self.data['channel'].isin(injectedChannels)) ].copy() #First condition only for the real 72 channels and second is obvious
        inj_data['time'] = inj_data.apply( lambda x: 25/16.0*(x.Phase+16*x.BX),axis=1 )
        inj_data['entries'] = inj_data.apply( lambda x: (int(x.Phase+16*x.BX)),axis=1 )
        
        nchip = inj_data['chip'].unique()
        self.chip_dict = dict()
        for chip in nchip:
            inj_chip = inj_data[inj_data['chip']==chip].copy()
            nhalf = inj_chip['half'].unique()
            self.chip_dict.setdefault(chip,dict())

            for half in nhalf:
                inj_half = inj_chip[inj_chip['half']==half].copy()
                inj_sorted = inj_half.sort_values(by=["channel","time"], ignore_index=True)
                self.chip_dict[chip][half] = inj_sorted
        
        
        
    def get_pulse(self,chip,half,channel):
        inj_half = self.chip_dict[chip][half]
        #.set_index("entries")
        inj_pulse = inj_half[(inj_half['channel']==channel)].copy()
        inj_pulse = inj_pulse.astype({'adc_median':float})
        print("Pulse df for channel",channel)
        print(inj_pulse)
        max_pulse = max(inj_pulse['adc_median'])

        inj_ped = inj_half[(inj_half['channel']==channel) & (inj_half['entries']<4)].copy()
        #print(inj_pulse)
        #print(inj_ped)
        pedestal_baseline = inj_ped.mean(axis=0)['adc_median']
        BX_max = inj_pulse.loc[inj_pulse['adc_median'] == max_pulse,'BX'].values[0]
        phase_max = inj_pulse.loc[inj_pulse['adc_median'] == max_pulse,'Phase'].values[0]
        #This will also help when there are two phases that could have the maximum value, just take the first one

        return inj_pulse, max_pulse, pedestal_baseline, BX_max, phase_max
        
        
    def get_width(self,chip,half,channel,height_percent,sign): #This will be used for both rising and falling widths
        
        print("Channel number",channel)
        (inj_pulse, max_pulse, pedestal_baseline, BX_amp, phase_amp) = self.get_pulse(chip,half,channel)
        net_phase = phase_amp+16*BX_amp
        pulse_amp = max_pulse - pedestal_baseline
        target_min_height = height_percent*pulse_amp+pedestal_baseline #This is the height (absolute height in ADC counts with pedestal included) upto which the rising and falling widths will be calculated

        print("Target minimum height",target_min_height)
        if sign == 1: #Positive slope i.e. rising edge
            start_val = 0 #Start of cut pulse array (i.e. the one above the target height)
        elif sign == -1:
            start_val = -1 #End of cut pulse array (i.e. the one above the target height)
                    
        phase_2 = inj_pulse.loc[inj_pulse['adc_median']>=target_min_height,'entries'].values[start_val] #This is the current lower phase for calculating the 'rising' width
        val_2 = inj_pulse.loc[inj_pulse.entries==phase_2,'adc_median'].values[0]

        phase_1 = inj_pulse.shift(sign, axis=0).loc[inj_pulse.entries==phase_2,'entries'].values[0]
        val_1 = inj_pulse.shift(sign, axis=0).loc[inj_pulse.entries==phase_2,'adc_median'].values[0] #positive shifts the rows forward, negative for backward

        print("Min/Max phase")
        print(phase_2)
        print("Other phase for calculating the slope")
        print(phase_1)
        
        #Finding net phase index using first order (linear) interpolation
        phase_slope = (val_2-val_1)/(phase_2-phase_1)
        print(phase_slope)
        phase_final = phase_2 - (val_2-target_min_height)/phase_slope
        
        return sign*(net_phase - phase_final)

    #At the moment, only for internal injection, and only for the amplitude comparison from the slopes of the injection scans (variation vs number of injected channels)
    def pass_criteria_sampling_scan_internal(self,device_type,injectedChannels,file_num,odir,process,subprocess): #Here device_type is only size and not index (for eg TB3_D8 and not TB3_D8_11)
        directory = "/home/hgcal/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/analysis/level0/Pass_criteria/%s_limits.yaml"%(device_type)
        nestedConf = dict()
        #Next part copied from the functions below, probably looping over in case of 2 or more ROCs
        nchip = len( self.data.groupby('chip').nunique() )
        inj_data = self.data[ (self.data['channeltype']==0) & (self.data['channel'].isin(injectedChannels)) ].copy() #First condition only for the real 72 channels and second is obvious

        #Getting gain from config file name
        conv_gain = analysis_misc.get_conveyor_gain(config_file)
        print(conv_gain)

        #cmap = cm.get_cmap('viridis') 
        cmap = matplotlib.colormaps['viridis']
        
        #Optional plotting (both halves in one plot) with linear fit instead of calculating chi_squared
        
        nchip = inj_data['chip'].unique()

        gain_lh = self.get_lh_range(odir)
        for chip in nchip:

            print("ROC number",chip)
            inj_chip = inj_data[inj_data['chip']==chip].copy()
            inj_sorted = inj_chip.sort_values(by=["channel","Calib"], ignore_index=True)
            #print(inj_sorted[inj_sorted['half']==0 ])
            
            nhalf = inj_sorted['half'].unique()

            #adc_max = 1023
            adc_max = 800

            fig, axes = plt.subplots(1,1,figsize=(16,9),sharey=False)
            axes.set_ylabel(f'ADC [ADC counts]')
            axes.set_xlabel(r'CalibDAC')
            axes.xaxis.grid(True)

            chanColor=0
            axes.set_title(f'chip{chip}')
            #12.0 because the initial limits of 1.4 and 2.5 (since the fit value is ~ 1.8) were decided for a convgain of 12
            slope_low = round(1.4*conv_gain/12.0,2)
            slope_high = round(2.5*conv_gain/12.0,2)
            print("Slope limits for writing to file", slope_low, slope_high)
            
            #if abs(inj_0-inj_1)<=1 & max(inj_0,inj_1)<4: #Then this is suitable for writing injection scan amplitudes for each calib value (or just slope might be sufficient) for that particular conveyor gain
            for half in nhalf:
                slope_avg = 0
                max_slope = 0 #also a non negative value considering that the slope values are positive
                min_slope = 100 #very high value considering the present slope values

                inj_half = inj_sorted[inj_sorted['half']==half]
                print("Injection dataframe for half",half)
                #print(inj_half)
                inj_chan_half = inj_half['channel'].unique()
                print("Injected channels",inj_chan_half)
                len_chan_half = len(inj_chan_half)

                slope_avg_arr = []
                for i in inj_chan_half:
                    inj_linear = inj_half[(inj_half['channel']==i) & (inj_half['adc_median']<adc_max)].copy()

                    #This next step is because there is a bug in writing multiple injected channels so that one channel and one calib row is replicated that many times
                    #So this is a quick filtering for that
                    inj_linear = inj_linear[inj_linear['injectedChannels']==i]


                    #print(inj_linear)
                    inj_linear.drop(inj_linear.tail(1).index,inplace=True) # drop last row
                    inj_linear.index = range(0,len(inj_linear))
                    print(inj_linear.loc[0,'adc_median']) #This is supposed to be close to the designated pedestal/y intercept of the fit

                    if len(inj_linear)>2: #Minimum number of points required for linear fit
                        slope_init = (inj_linear.loc[1,'adc_median'] - inj_linear.loc[0,'adc_median'])/(inj_linear.loc[1,'Calib'] - inj_linear.loc[0,'Calib'])
                        popt, pcov = curve_fit(lambda x,a,b:a*x+b, inj_linear['Calib'], inj_linear['adc_median'], p0=[slope_init,inj_linear.loc[0,'adc_median']])
                    else:
                        popt = [1,0]
                    print("Fitting parameters",popt)
                    slope_avg += popt[0]
                    max_slope = max(max_slope,popt[0])
                    min_slope = min(min_slope,popt[0])
                    
                    print("Max and min of slope for spread", max_slope, min_slope)
                    axes.scatter( inj_linear['Calib'], inj_linear['adc_median'],marker='o', label="Ch "+str(i))
                    axes.plot(inj_linear['Calib'],popt[0]*inj_linear['Calib']+popt[1])
                    chanColor=chanColor+1

                    if popt[0] > 0.01:
                        slope_avg_arr  = np.append(slope_avg_arr,popt[0])
                    
                #slope_avg = round(slope_avg/len_chan_half,3)
                slope_avg = np.mean(slope_avg_arr)

                #Histogram to check whether the average is a good measure
                fig, ax = plt.subplots(1,1,figsize=(16,9))

                plt.hist(slope_avg_arr)
                plt.savefig(f'{odir}/Slope_distribution_half_%s.png'%(half), format='png', bbox_inches='tight')
                h,l=ax.get_legend_handles_labels()
                ax.legend(handles=h,labels=l,loc='upper right',ncol=2)

                print(slope_avg)
                print(len(slope_avg_arr))
                slope_spread = round(max_slope - min_slope,3)
                print("Max and min of slope for spread", max_slope, min_slope)
                print("Slope spread", slope_spread)
                
                #if (slope_avg<=slope_high) & (slope_avg>=slope_low) & (slope_spread<=0.2):
                #'''  
                with open(directory,'r+') as file:
                #with open(directory,'w') as file:
                    injection_slope = yaml.safe_load(file)                    

                #This is only in case of high range, do not forget to add if condition for gain value (1)
                if gain_lh == 1:
                    injection_slope = analysis_misc.set_key_dict(injection_slope,['ADC_vs_calib_slope','num_ch_'+str(len_chan_half),'high_range','roc_s'+str(chip),process+'ernal '+ subprocess + ' injection'],['conv_gain_'+str(int(conv_gain))],[round(float(slope_avg),3)])
                elif gain_lh == 0:
                    injection_slope = analysis_misc.set_key_dict(injection_slope,['ADC_vs_calib_slope','low_range','roc_s'+str(chip),process+'ernal '+ subprocess + ' injection'],['conv_gain_'+str(int(conv_gain))],[round(float(slope_avg),3)])
                #'''      
                
            handles, labels = axes.get_legend_handles_labels()
            axes.legend(handles, labels)
            plt.savefig(f'{odir}/adc_injection_scan_chip{chip}_linear_fit.png', format='png', bbox_inches='tight')         
            print("Saved image for linear region")
            plt.close()

        print("Gain for low range or high range case",gain_lh)
        #'''
        with open(directory,'w') as file:
            yaml.dump(injection_slope,file,sort_keys=False)
            #yaml.dump(injection_slope,file,sort_keys=True)
        #'''

    #Only for writing the widths from the sampling scan for different injected channels (and fitting in a different script)
    #A lot of repetition between this and the channel_sampling_scan_internal_check function
    def pulse_width_pass(self,device_type,injectedChannels,file_num,odir,height_percent,process,subprocess):
        directory = "/home/hgcal/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/analysis/level0/Pass_criteria/%s_limits.yaml"%(device_type)
        nestedConf = dict()
        #Getting gain from config file name
        conv_gain = analysis_misc.get_conveyor_gain(config_file)
        print(conv_gain)
        calib = float(self.get_parameter_value(odir,'calib'))
        print(calib)
        
        gain_lh = self.get_lh_range(odir)
        #Optional plotting (both halves in one plot) with linear fit instead of calculating chi_squared
        ped_data = read_files('/home/hgcal/Desktop/kria/HGCROC3a/hexactrl-sw/hexactrl-script-anurag-cleanup/data/TB3_D8/pedestal_run_1','pedestal_run')
        self.chip_half("TB3_D8",injectedChannels,odir)
        for chip in self.chip_dict.keys():
            print("ROC number",chip)
            for half in self.chip_dict[chip].keys():
                print("half number",half)

                rise_avg_arr = []
                fall_avg_arr = []

                inj_half = self.chip_dict[chip][half]
                injectedChannels_half = inj_half['channel'].unique()  

                #Selected channels for debugging
                #if half == 0:
                #    injectedChannels_half = [4,9,13,14,15,23,28,30]
                inj = len(injectedChannels_half)
                print("Number of injected channels", inj)
                print(injectedChannels_half)
                #Average because these widths are supposed to be the same for the channels in each half
                
                #rise_avg = 0
                #fall_avg = 0
                for i in injectedChannels_half:
                    print("Channel number",i)

                    (inj_pulse,max_pulse,pedestal_baseline, BX_amp, phase_amp) = self.get_pulse(chip,half,i)
                    print("Pedestal from pulse baseline", pedestal_baseline)
                    
                    print("BX and Phase at which max amplitude occurs", BX_amp, phase_amp)
                    print("Net Phase at which max amplitude occurs", phase_amp+16*BX_amp) #In case of choosing the file for sps (albeit that is external injection and not internal), this will give the actual index of the file

                    #Pedestal value from one of the pedestal runs (has to have the same triminv, dacb, vrefinv etc settings from the config file)
                    #Channeltype will be 0 by default since only those can be injected into (gain settings can be changed)
                    pedestal_ped_run = read_val(chip,i,0,ped_data,'adc_median')
                    print("Average (mean/median) pedestal from previous pedestal runs", pedestal_ped_run)

                    pulse_amp = max_pulse - pedestal_baseline
                    print("Pulse amplitude", pulse_amp)
                    
                    if gain_lh == 1:
                        rise_wd = self.get_width(chip,half,i,height_percent,1)
                        fall_wd = self.get_width(chip,half,i,height_percent,-1)
                    elif gain_lh == 0:
                        rise_wd = self.get_width(chip,half,i,0.3,1)
                        fall_wd = self.get_width(chip,half,i,0.3,-1)

                    print("Rising width", rise_wd)
                    print("Falling width", fall_wd)
                    
                    #rise_avg += rise_wd
                    #fall_avg += fall_wd
                    
                    rise_avg_arr  = np.append(rise_avg_arr,rise_wd)
                    fall_avg_arr  = np.append(fall_avg_arr,fall_wd)

                    print()

                rise_avg = np.mean(rise_avg_arr)
                fall_avg = np.mean(fall_avg_arr)
                print("Average rising and falling widths for channels in half", half, " are",rise_avg," and", fall_avg)

                fig, ax = plt.subplots(1,1,figsize=(16,9))
                plt.hist(rise_avg_arr)

                plt.savefig(f'{odir}/Rise_wd_distribution_half_%s.png'%(half), format='png', bbox_inches='tight')
                h,l=ax.get_legend_handles_labels()
                ax.legend(handles=h,labels=l,loc='upper right',ncol=2)

                fig, ax = plt.subplots(1,1,figsize=(16,9))
                plt.hist(fall_avg_arr)

                plt.savefig(f'{odir}/Fall_wd_distribution_half_%s.png'%(half), format='png', bbox_inches='tight')
                h,l=ax.get_legend_handles_labels()
                ax.legend(handles=h,labels=l,loc='upper right',ncol=2)


                fig, ax = plt.subplots(1,1,figsize=(16,9))
                ax.xaxis.grid(True)
                ax.scatter(injectedChannels_half,rise_avg_arr)

                plt.savefig(f'{odir}/Rise_wd_chan_half_%s.png'%(half), format='png', bbox_inches='tight')
                h,l=ax.get_legend_handles_labels()
                ax.legend(handles=h,labels=l,loc='upper right',ncol=2)

                fig, ax = plt.subplots(1,1,figsize=(16,9))
                ax.xaxis.grid(True)
                ax.scatter(injectedChannels_half,fall_avg_arr)

                plt.savefig(f'{odir}/Fall_wd_chan_half_%s.png'%(half), format='png', bbox_inches='tight')
                h,l=ax.get_legend_handles_labels()
                ax.legend(handles=h,labels=l,loc='upper right',ncol=2)

                with open(directory,'r+') as file:
                
                    pulse_shape = yaml.safe_load(file)                    
                    print(pulse_shape.keys())
                    print(type(pulse_shape))

                if gain_lh == 1:
                    pulse_shape = analysis_misc.set_key_dict(pulse_shape,['num_ch_'+str(inj),'high_range','roc_s'+str(chip),process+'ernal '+ subprocess + ' injection'],['Rise_width'],[round(float(rise_avg),2)])
                    pulse_shape = analysis_misc.set_key_dict(pulse_shape,['num_ch_'+str(inj),'high_range','roc_s'+str(chip),process+'ernal '+ subprocess + ' injection'],['Fall_width'],[round(float(fall_avg),2)])
                elif gain_lh == 0:
                    pulse_shape = analysis_misc.set_key_dict(pulse_shape,['low_range','roc_s'+str(chip),process+'ernal '+ subprocess + ' injection'],['Rise_width'],[round(float(rise_avg),2)])
                    pulse_shape = analysis_misc.set_key_dict(pulse_shape,['low_range','roc_s'+str(chip),process+'ernal '+ subprocess + ' injection'],['Fall_width'],[round(float(fall_avg),2)])

                with open(directory,'w') as file:
                    yaml.dump(pulse_shape,file,sort_keys=False)
                
                                    
    def sub_zero_signal_time(self,sig_chan,calib,ped):
        sig_chan['glitch_ct'] = 0
        for phase in range(3,len(sig_chan)):
            #print("Value of pulse at phase",phase)
            #print(sig_chan['adc_median'].values[phase])
            
            #Also have to add some proper condition for sudden change/flipping direction of slope
            cur_val = sig_chan['adc_median'].values[phase]
            prev_val = sig_chan['adc_median'].values[phase-1]
            prev_val_2 = sig_chan['adc_median'].values[phase-2]

            cur_slope = (cur_val - prev_val)/(25/16.0)
            prev_slope = (prev_val - prev_val_2)/(25/16.0)
            #print("Values of current and previous slopes", cur_slope, prev_slope)
            #print("Sign of current and previous slopes",get_sign(cur_slope),get_sign(prev_slope))
            
            if (cur_val < 0.9*ped) & (prev_val >= 0.9*ped) & (cur_slope < -20*calib/200.0): 
            #the percentage of the pedestal is meant to take into account baseline variation at the end of the pulse
            
            #Very stringent limit for second condition because do not want to have false negatives (still could be possible though) - the -20 and 200 come from looking at the slopes for the falling edge of the pulse for a pulse height (calib) of 200, and the calib is the actual pulse height for the run
                sig_chan['glitch_ct'].values[phase] = 1

            #print("Number of glitches starting",sig_chan['glitch_ct'].values[phase])
        
        for phase in range(3,len(sig_chan)):
            
            if sig_chan['glitch_ct'].values[phase]==1:
                print("Phase with glitch",phase)
                phase_iter = phase+1
                while (sig_chan['adc_median'].values[phase_iter] < 0.9*ped):
                    sig_chan['glitch_ct'].values[phase]+=1
                    #print("Number of glitches",sig_chan['glitch_ct'].values[phase])
                    phase_iter+=1
                    if phase_iter >= len(sig_chan):
                        break

                print("Number of continuous glitches in total",sig_chan['glitch_ct'].values[phase])  
        return sig_chan  

    def npeaks_low(self,df,chan,pulse_amp,pedestal_baseline,num_peaks:dict,bad_chan):
        df = df.dropna()
        print("Dataframe without weird values")
        print(df)
        print("Max amplitude",pulse_amp)
        #peaks, _ = scipy.signal.find_peaks(df['adc_median'], threshold=0) #absolute value kept for debugging
        #threshold = pedestal_baseline+ 0.2*pulse_amp
        #peaks, _ = scipy.signal.find_peaks(df['adc_median'], height=pedestal_baseline+ 0.1*pulse_amp, prominence = 0.08*pulse_amp) #absolute value kept for debugging
        peaks, _ = scipy.signal.find_peaks(df['adc_median'], prominence = 0.08*pulse_amp) #absolute value kept for debugging
        print("Peaks found for channel",chan)
        print(peaks)

        zero_num = 0
        for peak in peaks:
            zero_num += 1
            current_BX = df['BX'].values[peak]
            peak_time = (peak+current_BX+1)*25/16.0
            num_peaks = analysis_misc.set_key_dict(num_peaks,['ch_'+str(chan)],['num_'+str(zero_num)],[float(peak_time)])
            

        '''
        for peak in peaks:
            print("Peak",peak)
            print(df['adc_median'].values[peak])
            
            print(current_BX)
            print()
        '''
        '''
        for adc_vals in df['adc_median'].values:
            print("actual indices excluding 15th phase",adc_vals)
        '''
        if zero_num >= 3: #Here 3 is used because the prominence feature in the find_peaks gets rid of the smaller peaks
            print("Potentially bad waveform")
            bad_chan.append(int(chan))
            
        return num_peaks

    #===========================================Mostly not going to be using this - using the automated peak finder from scipy========================

    def zero_crossing_pts(self,df,chan,num_peaks:dict,bad_chan):
        df = df.dropna()
        print("Dataframe without weird values")
        print(df['slope'])
        print(df['slope_conv'])

        zero_cross_arr = []
        close_val = 0.01

        zero_num = 0
        for i in range(df.index.min()+3,df.index.max()+1):
            if df.loc[i,'slope_conv'] < -close_val: #i.e. Sufficiently negative and not very close to 0
                if df.loc[i-1,'slope_conv'] > close_val:
                    slope = (df.loc[i,'slope_conv'] - df.loc[i-1,'slope_conv'])/(df.loc[i,'time'] - df.loc[i-1,'time'])
                    zero_cross = df.loc[i,'time'] - (df.loc[i,'slope_conv']/slope)

                    print("Zero crossing point",zero_cross)
                    print("Slope value",slope)

                    zero_num+=1
                    num_peaks = analysis_misc.set_key_dict(num_peaks,['ch_'+str(chan)],['num_'+str(zero_num)],[float(zero_cross)])

                elif (abs(df.loc[i-1,'slope_conv']) < close_val) & (df.loc[i-2,'slope_conv'] > close_val):
                    slope = (df.loc[i,'slope_conv'] - df.loc[i-2,'slope_conv'])/(df.loc[i,'time'] - df.loc[i-2,'time'])
                    zero_cross = df.loc[i,'time'] - (df.loc[i,'slope_conv']/slope)

                    print("Zero crossing point",zero_cross)
                    print("Slope value",slope)

                    zero_num+=1
                    num_peaks = analysis_misc.set_key_dict(num_peaks,['ch_'+str(chan)],['num_'+str(zero_num)],[float(zero_cross)])

                elif (abs(df.loc[i-1,'slope_conv']) < close_val) & (abs(df.loc[i-2,'slope_conv']) < close_val) & (df.loc[i-3,'slope_conv'] > close_val):
                    slope = (df.loc[i,'slope_conv'] - df.loc[i-3,'slope_conv'])/(df.loc[i,'time'] - df.loc[i-3,'time'])
                    zero_cross = df.loc[i,'time'] - (df.loc[i,'slope_conv']/slope)

                    slope_inst = min((df.loc[i,'slope_conv'] - df.loc[i-1,'slope_conv'])/(df.loc[i,'time'] - df.loc[i-1,'time']),(df.loc[i-2,'slope_conv'] - df.loc[i-3,'slope_conv'])/(df.loc[i-2,'time'] - df.loc[i-3,'time']))
                    print("Zero crossing point",zero_cross)
                    print("Slope value",slope_inst)

                    zero_num+=1
                    num_peaks = analysis_misc.set_key_dict(num_peaks,['ch_'+str(chan)],['num_'+str(zero_num)],[float(zero_cross)])
        if zero_num >= 4:
            print("Potentially bad waveform")
            bad_chan.append(int(chan))
        return num_peaks

    #=================================================================================================================================================


    def channel_sampling_scan_internal_check(self,device_type,injectedChannels,file_num,odir,process,subprocess,height_percent,config_file,fout=''):
        directory = "/home/hgcal/Desktop/kria/HGCROC3a/hexactrl-sw/hexactrl-script-anurag-cleanup/analysis/level0/Pass_criteria/%s_limits.yaml"%(device_type)
        nestedConf = nested_dict()
        
        #Getting gain from config file name
        conv_gain = analysis_misc.get_conveyor_gain(config_file)
        print(conv_gain)
        #cmap = cm.get_cmap('viridis') 
        calib = float(self.get_parameter_value(odir,'calib'))
        print(calib)

        #no_phase_chan = [] #This is the list of channels, which are not necessarily bad but do not satisfy at least one of the criteria right away and it is best if these are excluded from the list of channels used to calculate the max adc phase       
      
        no_phase_chan = dict() #This should have a list of channels for each chip

        #A lot of the methods, for example whether fitting is done or the value (for amplitude and widths) is directly picked from the yaml file depend on whether the gain is for low or high range, so this parameter is very crucial
        gain_lh = self.get_lh_range(odir)

        num_peaks = dict()
        pulse_amp_chan = dict()

        amp_limit = 0
        #Optional plotting (both halves in one plot) with linear fit instead of calculating chi_squared
        ped_data = read_files('/home/hgcal/Desktop/kria/HGCROC3a/hexactrl-sw/hexactrl-script-anurag-cleanup/data/TB3_D8/pedestal_run_1','pedestal_run')
        self.chip_half("TB3_D8",injectedChannels,odir)
        for chip in self.chip_dict.keys():
            print("ROC number",chip)
            ch_bad_wave = 0
            mult_peak_chan = []
            bad_amp_chan = []
            zero_amp_chan = []

            amp_arr = []
            no_phase_chan_arr = []
            for half in self.chip_dict[chip].keys():
                print("half number",half)

                inj_half = self.chip_dict[chip][half]

                injectedChannels_half = inj_half['channel'].unique()  
                #Removed and only few channels added for debugging
                '''
                if half == 1:
                    injectedChannels_half = [70,68,50]
                elif half == 0:
                    injectedChannels_half = [18,23,25]
                '''
                '''
                if half == 0:
                    injectedChannels_half = [14] #Just for debugging
                if half == 1:
                    injectedChannels_half = [45] #Just for debugging
                '''

                inj = len(injectedChannels_half)
                print("Number of injected channels", inj)
                print(injectedChannels_half)

                
                #Average because these widths are supposed to be the same for the channels in each half
        
                if gain_lh == 1:
                    amp_limit = 0.1

                elif gain_lh == 0:
                    amp_limit = 0.02
                
                slope = analysis_misc.get_slope_ch_nos(process,subprocess,directory,odir,inj,conv_gain,chip,gain_lh)
                
                print("Slope from injection scan for half", half," is",slope)
                print()
                
                #rise_wd = analysis_misc.get_width_ch_nos(process,subprocess,directory,odir,inj,conv_gain,chip,"Rise")
                #print("Rising width from sampling scan for half", half,"is",rise_wd)

                #'''
                #==========================================Only to be done for high range setting===================================

                if gain_lh == 1:
                    print("File for obtaining pulse width criteria",directory)
                    inv_prod_mean, ratio_rf_y = analysis_misc.get_width_ch_nos(process,subprocess,directory,odir,inj,conv_gain,chip)
                    
                    full_wd = inv_prod_mean/slope
                    rise_wd_y = []
                    fall_wd_y = []
                    for i in range(len(ratio_rf_y)):
                        fall_wd = full_wd/(1+ratio_rf_y[i])
                        rise_wd = full_wd*ratio_rf_y[i]/(1+ratio_rf_y[i])

                        fall_wd_y = np.append(fall_wd_y,fall_wd)
                        rise_wd_y = np.append(rise_wd_y,rise_wd)
                    #analysis_misc.get_width_ch_nos(process,subprocess,directory,odir,inj,conv_gain,chip,"Rise")
                    #analysis_misc.get_width_ch_nos(process,subprocess,directory,odir,inj,conv_gain,chip,"Fall")
                    print(rise_wd_y,fall_wd_y)
                    print()

                #===================================================================================================================
                #'''

                for injectedChannel in injectedChannels_half:
                    print("Channel number",injectedChannel)
                    (inj_pulse,max_pulse,pedestal_baseline, BX_amp, phase_amp) = self.get_pulse(chip,half,injectedChannel)

                    print("Maximum value of ADC counts in pulse", max_pulse)
                    #This will also help when there are two phases that could have the maximum value, just take the first one
                    
                    print("BX and Phase at which max amplitude occurs", BX_amp, phase_amp)
                    print("Net Phase at which max amplitude occurs", phase_amp+16*BX_amp) #In case of choosing the file for sps (albeit that is external injection and not internal), this will give the actual index of the file
                    
                    print("Pedestal from pulse baseline", pedestal_baseline)
                    
                    #Pedestal value from one of the pedestal runs (has to have the same triminv, dacb, vrefinv etc settings from the config file)
                    #Channeltype will be 0 by default since only those can be injected into (gain settings can be changed)
                    pedestal_ped_run = read_val(chip,injectedChannel,0,ped_data,'adc_median')
                    print("Average (mean/median) pedestal from previous pedestal runs", pedestal_ped_run)
                    
                    #if abs(pedestal_ped_run - pedestal_baseline)<10:
                    #    print("Pedestal values consistent")
                    amp_flag = 0
                    rise_flag = 0
                    fall_flag = 0
                    sat_flag = 0
                    glch_flag = 0
                    
                    inj_pulse_glitch = self.sub_zero_signal_time(inj_pulse,calib,pedestal_baseline)
                    phase_glitch = inj_pulse_glitch[inj_pulse_glitch['glitch_ct']>2]
                    print(phase_glitch)
                    if len(phase_glitch) >=1:
                        print("Bad waveform")
                        glch_flag = 1
                        ch_bad_wave+=1

                    pulse_amp = max_pulse - pedestal_baseline
                    print("Pulse amplitude", pulse_amp)
                    pulse_amp_chan = analysis_misc.set_key_dict(pulse_amp_chan,['chip_'+str(chip)],['ch_'+str(injectedChannel)],[float(pulse_amp)])

                    if (abs(max_pulse - 1023) < 0.5) & (len(inj_pulse.loc[inj_pulse['adc_median'] == max_pulse,'Phase'])>2):
                        print("Saturated pulse - do not attempt to calculate pulse width and pick best phase for injection scan!!")
                        sat_flag = 1
                    else:
                        amp_arr = np.append(amp_arr,pulse_amp)

                        if abs(pulse_amp - slope*calib) <= amp_limit*calib: #Important condition but not the deciding one
                        #if abs(pulse_amp - slope*calib) == 0:
                            pass
                        else:
                            if pulse_amp < 5: #Hard limit, could have a bit of a problem when a very low amplitude for low range is chosen (<50 in calib units)
                                print("Near zero signal")
                                zero_amp_chan.append(int(injectedChannel))
                            else:
                                print("Potentially bad amplitude")
                                amp_flag = 1
                                bad_amp_chan.append(int(injectedChannel))

                        print("Pulse dataframe")
                        print(inj_pulse)

                        #Peak finder using negative running derivative to find good maxima since low range pulses seem to have multiple decaying peaks
                        #==========================================Only to be done for low range setting====================================

                        if gain_lh == 0:
                            for i in range(inj_pulse.index.min()+1,inj_pulse.index.max()+1):
                                inj_pulse.loc[i,'slope'] = (inj_pulse.loc[i,'adc_median'] - inj_pulse.loc[i-1,'adc_median'])/(inj_pulse.loc[i,'time'] - inj_pulse.loc[i-1,'time'])

                            for i in range(inj_pulse.index.min()+1,inj_pulse.index.max()+1):
                                #print("Number of next entries available for running average")
                                ent = min(6,inj_pulse.index.max()+1-i)
                                #print(ent)
                                inj_pulse.loc[i,'slope_conv'] = 0
                                for j in range(0,ent):
                                    inj_pulse.loc[i,'slope_conv'] += inj_pulse.loc[i+j,'slope']
                                    #print("Entry number",j)

                                inj_pulse.loc[i,'slope_conv'] = inj_pulse.loc[i,'slope_conv']/(ent)

                            #num_peaks = self.zero_crossing_pts(inj_pulse,injectedChannel,num_peaks,mult_peak_chan)
                            num_peaks = self.npeaks_low(inj_pulse,injectedChannel,pulse_amp,pedestal_baseline,num_peaks,mult_peak_chan)
                            #print("Current dict zero crossing")
                            #print(num_peaks)

                        #===================================================================================================================


                        #''' 
                        #==========================================Only to be done for high range setting===================================

                        elif gain_lh == 1:
                            rise_wd = self.get_width(chip,half,injectedChannel,height_percent,1)
                            fall_wd = self.get_width(chip,half,injectedChannel,height_percent,-1)
                            print("Pulse widths",rise_wd,fall_wd)
                            
                            #Percentage limits are usually better than absolute count wise leeways
                            #if (rise_wd>=np.min(rise_wd_y)-0.5) & (rise_wd<=np.max(rise_wd_y)+0.5):
                            if (rise_wd >= 0.85*np.min(rise_wd_y)) & (rise_wd <= 1.15*np.max(rise_wd_y)):
                                pass
                            else:
                                print("Potentially bad rise width")        
                                rise_flag = 1
                            
                            #if (fall_wd>=np.min(fall_wd_y)-1) & (fall_wd<=np.max(fall_wd_y)+1):
                            if (fall_wd >= 0.9*np.min(fall_wd_y)) & (fall_wd <= 1.1*np.max(fall_wd_y)):
                                pass
                            else:
                                print("Potentially bad fall width")   
                                fall_flag = 1 

                        #===================================================================================================================
                        #'''
                    print("List of flags:","sat:",sat_flag,"amp:",amp_flag,"rise_wd:",rise_flag, "fall_wd:",fall_flag,"glitch:",glch_flag)
                    if ((sat_flag == 1) | (amp_flag == 1) | (rise_flag == 1) | (fall_flag == 1) | (glch_flag == 1)):
                        no_phase_chan_arr.append(i)
                    
                    print()        

            print("Number of channels with bad waveforms in both halves for chip", chip, " are",ch_bad_wave)
            print(amp_arr)
            fig, ax = plt.subplots(1,1,figsize=(16,9))

            plt.hist(amp_arr,bins = 30)
            plt.savefig(f'{odir}/Pulse_amplitude_distribution.png', format='png', bbox_inches='tight')
            h,l=ax.get_legend_handles_labels()
            ax.legend(handles=h,labels=l,loc='upper right',ncol=2)

            print("Channels with bad waveforms (multiple peaks)")
            print(mult_peak_chan)
            print("Channels with bad amplitude")
            print(bad_amp_chan)
            print("Channels with ~zero amplitude")
            print(zero_amp_chan)

            
            nestedConf = analysis_misc.set_key_dict(nestedConf,['ch','chip' + str(chip),'bad_channels'],['Multiple peaks in pulse'],[mult_peak_chan])
            nestedConf = analysis_misc.set_key_dict(nestedConf,['ch','chip' + str(chip),'bad_channels'],['Flat pulse'],[zero_amp_chan])
            nestedConf = analysis_misc.set_key_dict(nestedConf,['ch','chip' + str(chip),'bad_channels'],['Bad amplitude of pulse'],[bad_amp_chan])

            #nestedConf['bad_channels']['chip' + str(chip)]['ch'] = mult_peak_chan
            with open(odir + "num_peaks.yaml",'w') as file:
                print(yaml.dump(num_peaks,file,sort_keys=False))

        with open(odir + "pulse_amp.yaml",'w') as file:
            print(yaml.dump(pulse_amp_chan,file,sort_keys=False))

        with open(odir + "sampling_scan_summary.yaml",'w') as ana_file:
            print(yaml.dump(nestedConf.to_dict(),ana_file,sort_keys=False))

        no_phase_chan = analysis_misc.set_key_dict(no_phase_chan,[],['chip' + str(chip)],[no_phase_chan_arr])
        return no_phase_chan
            

    def makePlots(self, injectedChannels):
        nchip = len( self.data.groupby('chip').nunique() )        
        #cmap = cm.get_cmap('Dark2')
        cmap = matplotlib.colormaps['Dark2']

        inj_data = self.data[ (self.data['channeltype']==0) & (self.data['channel'].isin(injectedChannels)) ].copy()
        inj_data['time'] = inj_data.apply( lambda x: 25/16.0*(x.Phase+16*x.BX),axis=1 )
        
        #Selected channels only for debugging 
        #injectedChannels = [18,23,25,70,68,50]

        #injectedChannels = [4,9,13,14,15,23,28,30]
        #injectedChannels = [14]
        #print to csv file for grouping with the data from other files
        data_pd_csv = pd.DataFrame()
        N = 50

        for chip in self.data.groupby('chip')['chip'].mean():
            chanColor=0
            
            for injectedChannel in injectedChannels:

                #fig, axes = plt.subplots(1,3,figsize=(16,9))
                fig, axes = plt.subplots(1,1,figsize=(16,9))
                sel_data = inj_data[ (inj_data['chip']==chip) & (inj_data['channel']==injectedChannel) ]
                sel_data = sel_data.sort_values(by=['time'],ignore_index=True)

                sel_data = sel_data.astype({'adc_median':float})
                print("Original dataframe")
                print(sel_data['adc_median'])
                #ax = axes[0]
                ax = axes
                for i in range(1,len(sel_data['adc_median'])):
                    sel_data.loc[i,'slope'] = (sel_data.loc[i,'adc_median'] - sel_data.loc[i-1,'adc_median'])/(sel_data.loc[i,'time'] - sel_data.loc[i-1,'time'])

                for i in range(1,len(sel_data['adc_median'])):
                    #print("Number of next entries available for running average")
                    ent = min(6,len(sel_data['adc_median'])-i)
                    #print(ent)
                    sel_data.loc[i,'slope_conv'] = 0
                    for j in range(0,ent):
                        sel_data.loc[i,'slope_conv'] += sel_data.loc[i+j,'slope']
                        #print("Entry number",j)

                    sel_data.loc[i,'slope_conv'] = sel_data.loc[i,'slope_conv']/(ent)

                #sel_data['slope_conv'] = np.convolve(sel_data['slope'], np.ones(N)/N, mode='valid')
                print()
                print("Derivative of pulse")
                print(sel_data['slope'])
                #plt.xticks(range(int(inj_data.time.min()),int(inj_data.time.max()),25))
                ax.plot( sel_data['time'], sel_data['adc_median'], color=cmap(chanColor), label=r'Channel %d'%(injectedChannel),marker='o')
                #chanColor=chanColor+1
                                
                data_pd_csv['time'] = sel_data['time']
                data_pd_csv['chip_'+str(chip)+'_ch_'+str(injectedChannel)+'_adc_median'] = sel_data['adc_median']

                plt.title('Sampling scan, ch%d'%(injectedChannel))
                plt.xlabel(r'Time [ns]')
                plt.ylabel(r'Signal [ADC counts]')

                h,l=ax.get_legend_handles_labels()
                ax.legend(handles=h,labels=l,loc='upper right',ncol=2)

                ax.xaxis.grid(True)
                ax.yaxis.grid(True)
                ax.set_xticks(range(int(inj_data.time.min()),int(inj_data.time.max()),25))
                #ax.set_yticks(range(int(sel_data.adc_median.min()),int(sel_data.adc_median.max()),5))
                ax.set_yticks(range(int(sel_data.adc_median.min()),int(sel_data.adc_median.max()),1))
                ax.set_yticklabels(range(int(sel_data.adc_median.min()),int(sel_data.adc_median.max()),1),fontsize=4)
                #plt.xticks(range(int(inj_data.time.min()),int(inj_data.time.max()),25))
                ax.xaxis.set_minor_locator(AutoMinorLocator(16))

                '''
                ax = axes[1]
                ax.plot( sel_data['time'], sel_data['slope'], color=cmap(chanColor), label=r'Channel %d'%(injectedChannel),marker='o')
                
                h,l=ax.get_legend_handles_labels()
                ax.legend(handles=h,labels=l,loc='upper right',ncol=2)

                ax.xaxis.grid(True)
                ax.yaxis.grid(True)
                ax.set_xticks(range(int(inj_data.time.min()),int(inj_data.time.max()),25))

                #ax.yaxis.set_ticks(range(int(sel_data.slope.min()),int(sel_data.slope.max()),0.5))
                #plt.xticks(range(int(inj_data.time.min()),int(inj_data.time.max()),25))
                
                ax.xaxis.set_minor_locator(AutoMinorLocator(16))


                ax = axes[2]
                ax.plot( sel_data['time'], sel_data['slope_conv'], color=cmap(chanColor), label=r'Channel %d'%(injectedChannel),marker='o')
                chanColor=chanColor+1
                
                h,l=ax.get_legend_handles_labels()
                ax.legend(handles=h,labels=l,loc='upper right',ncol=2)

                ax.xaxis.grid(True)
                ax.yaxis.grid(True)
                ax.set_xticks(range(int(inj_data.time.min()),int(inj_data.time.max()),25))
                #ax.yaxis.set_ticks(range(int(sel_data.slope_conv.min()),int(sel_data.slope_conv.max()),0.5))

                #plt.xticks(range(int(inj_data.time.min()),int(inj_data.time.max()),25))
                ax.xaxis.set_minor_locator(AutoMinorLocator(16))
                '''

                plt.savefig("%s/Sampling_scans/adc_sampling_scan_ch_%d.png"%(self.odir,injectedChannel),format='png',bbox_inches='tight') 
                plt.close()

            '''
            plt.title('Sampling scan, chip%d'%(chip))
            plt.xlabel(r'Time [ns]')
            plt.ylabel(r'Signal [ADC counts]')

            h,l=ax.get_legend_handles_labels()
            ax.legend(handles=h,labels=l,loc='upper right',ncol=2)

            ax.xaxis.grid(True)
            plt.xticks(range(int(inj_data.time.min()),int(inj_data.time.max()),25))
            ax.xaxis.set_minor_locator(AutoMinorLocator(16))
            plt.savefig("%s/adc_sampling_scan_chip%d.png"%(self.odir,chip),format='png',bbox_inches='tight') 
            plt.close()
            '''

            chanColor=0
            fig, ax = plt.subplots(1,1,figsize=(16,9))
            for injectedChannel in injectedChannels:
                sel_data = inj_data[ (inj_data['chip']==chip) & (inj_data['channel']==injectedChannel) ]
                sel_data = sel_data.sort_values(by=['time'],ignore_index=True)
                plt.plot( sel_data['time'], sel_data['toa_median'], color=cmap(chanColor), label=r'Channel %d'%(injectedChannel),marker='o')
                chanColor=chanColor+1

            plt.title('Sampling scan, chip%d'%(chip))
            plt.xlabel(r'Time [ns]')
            plt.ylabel(r'ToA')

            h,l=ax.get_legend_handles_labels()
            ax.legend(handles=h,labels=l,loc='upper right',ncol=2)

            ax.xaxis.grid(True)
            plt.xticks(range(int(inj_data.time.min()),int(inj_data.time.max()),25))
            ax.xaxis.set_minor_locator(AutoMinorLocator(16))
            plt.savefig("%s/toa_sampling_scan_chip%d.png"%(self.odir,chip),format='png',bbox_inches='tight') 
            plt.close()

            chanColor=0
            fig, ax = plt.subplots(1,1,figsize=(16,9))
            for injectedChannel in injectedChannels:
                sel_data = inj_data[ (inj_data['chip']==chip) & (inj_data['channel']==injectedChannel) ]
                sel_data = sel_data.sort_values(by=['time'],ignore_index=True)
                plt.plot( sel_data['time'], sel_data['tot_median'], color=cmap(chanColor), label=r'Channel %d'%(injectedChannel),marker='o')
                chanColor=chanColor+1

            plt.title('Sampling scan, chip%d'%(chip))
            plt.xlabel(r'Time [ns]')
            plt.ylabel(r'ToT')

            h,l=ax.get_legend_handles_labels()
            ax.legend(handles=h,labels=l,loc='upper right',ncol=2)
            
            ax.xaxis.grid(True)
            plt.xticks(range(int(inj_data.time.min()),int(inj_data.time.max()),25))
            ax.xaxis.set_minor_locator(AutoMinorLocator(16))
            plt.savefig("%s/tot_sampling_scan_chip%d.png"%(self.odir,chip),format='png',bbox_inches='tight') 
            plt.close()
        
        print("Final dataframe",data_pd_csv)
        data_pd_csv.to_csv(os.path.join(self.odir,"sampling_scan_adc.csv"))


    def addSummary(self,injectedChannels):
            
        # add summary information
        ## rejection criteria based on phase at max adc to be implemented
        self._summary['bad_channels_phase'] = {
            'rejection criteria': 'Phase at Max ADC < to be decided'
        }

        nchip = len( self.data.groupby('chip').nunique() )        
        inj_data = self.data[ (self.data['channeltype']==0) & (self.data['channel'].isin(injectedChannels)) ].copy()
        inj_data['time'] = inj_data.apply( lambda x: 25/16.0*(x.Phase+16*x.BX),axis=1 )

        for chip in range(nchip):
            print ("chip%d "%chip)
            ## rejection criteria based on phase at max adc to be implemented
            badchns_phase = { 'ch'    : [] , 
                            'cm'    : [] ,
                            'calib' : [] } 

            for injectedChannel in injectedChannels:
                print ("channel", injectedChannel)
                sel_data = inj_data[ (inj_data['chip']==chip) & (inj_data['channel']==injectedChannel) ]
                sel_data = sel_data.sort_values(by=['time'],ignore_index=True)
                max_adc = sel_data['adc_median'].max()
                print ("max_adc", max_adc )
                data_max_adc = sel_data[sel_data['adc_median'] == sel_data['adc_median'].max()]
                #phase =  sel_data['Phase']
                #print ("Phase", phase)
                max_adc_phase =  data_max_adc['Phase']
                print ("Max Phase", max_adc_phase.to_list()[0])
                print ("Max Phase length", len(max_adc_phase))
                #print ("sel_data['adc_median']", sel_data['adc_median'].max())

                ## rejection criteria based on phase at max adc to be implemented               
                ## if max_adc_phase.to_list()[0] < 20:
                ##    badchns_phase['ch'].append(injectedChannel)

                self._summary['sampling_scan']['chip%d' % chip][injectedChannel]['Phase_at_adc_max'] = max_adc_phase.to_list()[0] 

            self._summary['bad_channels_phase']['chip%d' % chip] = badchns_phase
            self._summary['bad_channels_phase']['chip%d' % chip]['total'] = len(badchns_phase['ch']) + len(badchns_phase['cm']) + len(badchns_phase['calib'])

            
    def fit(self,data):
        pass

    def calc_bestPhase(self, injectedChannels, gain_lh, odir, no_phase_chan):
        self.chip_half("TB3_D8",injectedChannels,odir)

        print("Chip half from calc best phase",self.chip_dict)
        bx_begin, phase_begin = self.get_start_BX_phase(odir)
        print("Starting BX and phase", bx_begin, phase_begin)

        calib_bx = self.get_start_trigger(odir)
        print("Calibreq value",calib_bx)
        
        #BX_phase_info=dict()
        BX_phase_info=pd.DataFrame()
        if gain_lh == 1:
            list = ['chip','half','chan_num','phase','bx_begin','phase_begin','calib_bx']

        elif gain_lh == 0:
            list = ['chip','phase','bx_begin','phase_begin','calib_bx']

        print(len(list))
        BX_phase_info=pd.DataFrame(np.empty((0, len(list))))
        BX_phase_info.columns = list

        index_high = 0
        index_low = 0

        for chip in self.chip_dict.keys():
            index_low +=1
            print("ROC number",chip)
            useless_channels = no_phase_chan['chip'+str(chip)]
            #useless_channels = [7,40,51] #Some channels only for debugging
            print("Useless channels",useless_channels) #This is a dict with keys for each chip

            best_phase_net = []
            #BX_phase_info = dict()

            #=======================This loop is common to both low and high range, for low range everything is just combined later outside the loop========================
            for half in self.chip_dict[chip].keys():
                index_high +=1
                print("half number",half)
                best_phase_half = [] #For this (low range) it does not change with the number of injected channels, so we might as well take the average over two halves

                injectedChannels_half = self.chip_dict[chip][half]['channel'].unique()  
                chan_num = len(injectedChannels_half)
                print("Number of injected channels", chan_num)
                print(injectedChannels_half)

                used_inj_chan = np.setdiff1d(injectedChannels_half,useless_channels)            
                print("Injected channels used for max phase calculation in each half", used_inj_chan)  

            #Average because these widths are supposed to be the same for the channels in each half
                if len(used_inj_chan)>=1:
                    for i in used_inj_chan:
                        (inj_pulse,max_pulse,pedestal_baseline, BX_amp, phase_amp) = self.get_pulse(chip,half,i)
                        best_phase_half.append(phase_amp+16*BX_amp) #Do NOT take the average of BX and phase separately, it could cause problems if the phases are slightly different and in different BXs

                best_phase_net.append(best_phase_half)

            #=================================================================================================================================================================

                if gain_lh == 1:

                    phase = int(sum(best_phase_half)/len(best_phase_half))
                    '''
                    BX_phase_info = analysis_misc.set_key_dict(BX_phase_info,[],
                    ['chip','half','chan_num','phase','bx_begin','phase_begin','calib_bx'],
                    [chip,half,inj,phase,bx_begin,phase_begin,calib_bx])
                    '''

                    for column in BX_phase_info.columns:
                        BX_phase_info.loc[index_high,column] = eval(column)

            #==========================================================Exiting the half loop==================================================================================
            if gain_lh == 0:

                best_phase_net = np.concatenate([best_phase_net[i] for i in range(len(best_phase_net))]) 
                print("Number of channels from both halves",len(best_phase_net))
                phase = int(sum(best_phase_net)/len(best_phase_net))
                '''
                BX_phase_info = analysis_misc.set_key_dict(BX_phase_info,[],
                ['chip','phase','bx_begin','phase_begin','calib_bx'],
                [chip,phase,bx_begin,phase_begin,calib_bx])
                '''

                for column in BX_phase_info.columns:
                    BX_phase_info.loc[index_high,column] = eval(column)

        return BX_phase_info

        #=====================================================================================================================================================================

    #==============This uses the above calc_bestPhase for different runs, it is only used to get around the problem of phase shifting dramatically across runs=======
    def get_med_phase(self,odir_phase,nestedConf):
        odir_plot = '/home/hgcal/Desktop/kria/HGCROC3b/hexactrl-sw/hgcal_qc_hexactrl-script-cleanup/data/D8_8/'
        odir_list = ['/home/hgcal/Desktop/kria/HGCROC3b/hexactrl-sw/hgcal_qc_hexactrl-script-cleanup/data/D8_8/PreampSampling_scan_Calib_2000_1/','/home/hgcal/Desktop/kria/HGCROC3b/hexactrl-sw/hexactrl-script-anurag-cleanup/data/D8_8/PreampSampling_scan_Calib_2000_1/',
        '/home/hgcal/Desktop/kria/HGCROC3a/hexactrl-sw/hgcal_qc_hexactrl-script-cleanup/data/TB3_D8/PreampSampling_scan_Calib_400_1/']
        #nestedConf = dict()
        
        #The third one is an actual high range sampling scan and used to have an extra point for fitting
        gain_list = []
        runs = 0
        same_gain_flag = 1
        for odir in odir_list:
            runs +=1
            gain_lh = self.get_lh_range(odir) #Check whether gain is same for each of these set of files
            gain_lh = 0 #Only for debugging
            print(gain_lh)
            if runs > 1:
                print("Previous gain",gain_list[-1])
                if gain_lh != gain_list[-1]:
                    print("Runs do not have the same gain!")
                    same_gain_flag = 0
                    break

            gain_list.append(gain_lh)

        print(gain_list)
        print(same_gain_flag)

        BX_phase_net = []
        if same_gain_flag == 1:
            channel_df = pd.DataFrame()
            for odir in odir_list:
                sampling_analyzer = overall_analyzer(odir=odir)
                files = glob.glob(odir+"/sampling_scan*.root")
                print("Current directory",odir)
                #print(files)
                print("Number of sampling scan files", len(files)) 
                for f in files:
                    sampling_analyzer.add(f)

                injectedChannels = sampling_analyzer.get_injectedChannels(odir) 
                sampling_analyzer.mergeData()

                no_phase_chan = sampling_analyzer.channel_sampling_scan_internal_check("TB3_D8",injectedChannels,len(files), odir, process='int',subprocess='preamp',height_percent=0.1,config_file = config_file,fout = odir + "analysis_summary_new.yaml")    
                BX_phase_info = sampling_analyzer.calc_bestPhase(injectedChannels,gain_lh,odir,no_phase_chan)

                print("Dictionary for best phase from calc_bestPhase")
                print(BX_phase_info)
                BX_phase_net.append(BX_phase_info)        

            BX_phase_net = pd.concat([BX_phase_net[i] for i in range(len(BX_phase_net))],ignore_index=True) 

            #====================================Will output only best phase for each chip (low range)=========================================================

            if gain_list[0] == 0: #Since all gains from all runs are the same there is no need to check all the elements
                BX_med = BX_phase_net.groupby(['chip'])[['phase']].median()
                chip_val = BX_med.index #Only one level of index
                for chip in chip_val:
                    nestedConf = analysis_misc.set_key_dict(nestedConf,['low_range'],['chip_'+str(int(chip))],[int(BX_med[chip_val==chip].values[0])])

            #==================================================================================================================================================


            #====================Will output fitting parameters from best phase vs number of channels for each chip (high range)===============================

            elif gain_list[0] == 1: #Since all gains from all runs are the same there is no need to check all the elements

                #new_chip = {'chip':1.0,'chan_num':6.0,'phase':14.0} #Dummy row added for debugging, in reality there is only one chip on the D8 board
                #BX_phase_net = pd.concat([BX_phase_net, pd.DataFrame([new_chip])], ignore_index=True)

                #Do not use append - has been deprecated
                #BX_phase_net = BX_phase_net.append(new_chip, ignore_index=True)

                BX_med = BX_phase_net.groupby(['chip', 'chan_num'])[['phase']].median()

                print("List of indices after adding dummy row")
                print(BX_med.index)

                chip_val = BX_med.index.get_level_values('chip')

                #===========================================Cutting for each chip and fitting and plotting the points and fit===================================
                
                for chip in chip_val.unique(): #Only the 0th entry of a MultiIndex since that corresponds to the chip

                    fig, axes = plt.subplots(1,1,figsize=(16,9),sharey=False)
                    axes.set_ylabel(f'Best phase from sampling scan')
                    axes.set_xlabel(r'Number of channels injected in one half')
                    axes.xaxis.grid(True)

                    BX_fit_chip = BX_med[chip_val == chip]
                    print("Cut chip array for fitting")
                    print(BX_fit_chip)
                    chan_num_val = BX_fit_chip.index.get_level_values('chan_num') #No need for 'unique' because they are already done when median is calculated

                    axes.scatter( chan_num_val, BX_fit_chip['phase'], marker='o')
                    popt, pcov = curve_fit(lambda x, A, t: A * np.exp(x * t), chan_num_val, BX_fit_chip['phase'], p0=[2,1])

                    #popt, pcov = curve_fit(lambda x, A, t: A *x + t, chan_num_val, BX_fit_chip['phase'], p0=[0,10]) #Linear fit for debugging

                    print("fit parameter values", popt[0],popt[1])
                    print(type(popt))
                    nestedConf = analysis_misc.set_key_dict(nestedConf,['high_range'],['chip_'+str(int(chip))],[popt.tolist()])

                    axes.plot(chan_num_val,popt[0] * np.exp(chan_num_val * popt[1]))
                    plt.savefig(f'{odir_plot}/Chip_%s_best_phase_fit.png'%(chip), format='png', bbox_inches='tight')      

                #===============================================================================================================================================   

            #==================================================================================================================================================

            print(BX_med)
            print(type(BX_med))
            #print("Final data frame from all the runs")
            #print(BX_phase_net)

        return nestedConf        

    #================================================================Mostly not to be used=======================================================================================

    def make_fit_dict(self,odir):
        odir_main = '/home/hgcal/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/data/TB3_D8_11/'
        odir_list = [odir_main+'PreampSampling_scan_Calib_200_3',odir_main+'PreampSampling_scan_Calib_200_7',odir_main+'PreampSampling_scan_Calib_200_10']

        BX_fit = dict()
        for odir_current in odir_list:
            sampling_analyzer = overall_analyzer(odir=odir_current)
            files = glob.glob(odir_current+"/sampling_scan*.root")
            print("Current directory",odir_current)
            #print(files)
            print("Number of sampling scan files", len(files)) 
            for f in files:
                sampling_analyzer.add(f)

            injectedChannels = sampling_analyzer.get_injectedChannels(odir_current) 
            sampling_analyzer.mergeData()
            #sampling_analyzer.pulse_width_pass("TB3_D8",injectedChannels,len(files),odir,height_percent=0.1,process='int',subprocess='preamp')
            #sampling_analyzer.chip_half("TB3_D8",injectedChannels,odir)
            no_phase_chan = sampling_analyzer.channel_sampling_scan_internal_check("TB3_D8",injectedChannels,len(files),odir_current,process='int',subprocess='preamp',height_percent=0.1,config_file = config_file,fout = odir_current + "analysis_summary_new.yaml")
            print("List of channels excluded from phase calculation", no_phase_chan)
            #sampling_analyzer.determine_bestPhase(injectedChannels,odir, no_phase_chan)
            #(BX_current,bx_begin,phase_begin,calib_bx) = sampling_analyzer.calc_bestPhase(injectedChannels,odir_current,no_phase_chan)
            sampling_analyzer.calc_bestPhase(injectedChannels,odir_current,no_phase_chan)
            shift_cur = 0
            print("Current list of phases for fitting",BX_current) #,bx_begin,phase_begin,calib_bx
            for key_cur in BX_current.keys():
                #This is just shifting back the overall pulse in a run if we find that it is shifted wrt the previous run(s)
                #It is ok to use this for fitting, but for the final selection of the phase, we would not know which phase is 'right' anyway with such shifts
                #Also this assumes that only one key is common so that shift_cur has only one value (i.e. it is consistent across halves) and therefore not averaged
                if (key_cur in BX_fit):
                    if (BX_fit[key_cur]!=BX_current[key_cur]):
                        shift_cur = BX_current[key_cur] - BX_fit[key_cur]

            print("Phase shifting of pulse",shift_cur)
            for key_cur in BX_current.keys():        
                if key_cur not in BX_fit:
                    BX_fit.setdefault(key_cur,int(BX_current[key_cur]-shift_cur))
                elif key_cur in BX_fit:
                    pass #Shift already calculated so no need to update

                '''
                if key_cur not in BX_fit:
                    BX_fit.setdefault(key_cur,BX_current[key_cur])
                elif key_cur in BX_fit:
                    BX_fit[key_cur]=BX_current[key_cur]
                '''
            #BX_fit = analysis_misc.merge_nested(BX_current,BX_fit)

            print("Current directory",odir_current)
            print("Net list of phases for fitting",BX_fit)

            with open(odir + "BX_fit.yaml",'w') as file:
                print(yaml.dump(BX_fit,file,sort_keys=False))


    #This does not calculate the best phase (which is already calculated in the calc_bestPhase function above) but it writes either the best phase in case of low range to the yaml file, or just the fit parameters in case of high range to that yaml file
    def determine_bestPhase(self,injectedChannels,odir,no_phase_chan):
        #,bx_begin,phase_begin,calib_bx
        try:
            with open(odir + "BX_fit.yaml",'r') as file:
                BX_fits = yaml.safe_load(file)
                            
        except FileNotFoundError:
            self.make_fit_dict(odir)
            with open(odir + "BX_fit.yaml",'r') as file:
                BX_fits = yaml.safe_load(file)

        print("Dictionary loaded from file")
        print(BX_fits)

        #(BX_1,bx_begin,phase_begin,calib_bx) = self.calc_bestPhase(injectedChannels,odir,no_phase_chan)
        print("Phases for fitting for high range",BX_fits)
        print(BX_fits.keys())
        print(BX_fits.values())
        '''
        BX_fit_sort = sorted(BX_fits.items())
        print("Sorted dictionary",BX_fit_sort.keys())
        print("Sorted dictionary",BX_fit_sort.values())
        '''

        fig, axes = plt.subplots(1,1,figsize=(16,9),sharey=False)
        axes.set_ylabel(f'Best phase from sampling scan')
        axes.set_xlabel(r'Number of channels injected in one half')
        axes.xaxis.grid(True)
        axes.scatter( BX_fits.keys(), BX_fits.values(), marker='o')
        
        keys = np.fromiter(BX_fits.keys(), dtype=float)
        vals = np.fromiter(BX_fits.values(), dtype=float)   
        keys = np.sort(keys)     
        vals = np.sort(vals)      #Very ad hoc method at the moment, only works because the curve is strictly increasing
        popt, pcov = curve_fit(lambda x, A, t: A * np.exp(x * t), keys, vals, p0=[2,1])
        print("fit parameter values", popt[0],popt[1])
        
        axes.plot(keys,popt[0] * np.exp(keys * popt[1]))
        
        plt.savefig(f'{odir}/Best_phase_fit.png', format='png', bbox_inches='tight')         
        #print("Saved image for linear region")
        plt.close()
        
        #print(bx_begin,phase_begin,calib_bx)

        '''
        BX_half = int(ret/16)
        phase_half = int(ret - BX_half*16)
        #print("Best max BX and phase for half",half,"BX:",BX_half+bx_begin,"phase:",phase_half+phase_begin)
        print("Best max BX and phase for half",half,"BX:",BX_half,"phase:",phase_half)
        
        BX_phase_info=dict()
        try:
            with open(self.odir+'/best_phase.yaml','r+') as fin:
                BX_phase_info = yaml.safe_load(fin)    
                                        
        except FileNotFoundError:                        
            pass
        half_key = str(half)
        BX_phase_info = analysis_misc.set_key_dict(BX_phase_info,[half_key,'Top','sc','roc_s'+str(chip)],['BX'],[BX_half+bx_begin-calib_bx])
        BX_phase_info = analysis_misc.set_key_dict(BX_phase_info,[half_key,'Top','sc','roc_s'+str(chip)],['phase'],[phase_half+phase_begin])

        print(BX_phase_info)    
        with open(self.odir+'/best_phase.yaml','w') as fout:
            yaml.dump(BX_phase_info,fout,sort_keys=False)
        '''

    #==============================================================================================================================================================

if __name__ == "__main__":
    
    if len(sys.argv) == 3:
        odir = sys.argv[1]
        config_file = sys.argv[2]
        '''
        injection_scan_analyzer = overall_analyzer(odir=odir)
        files = glob.glob(odir+"/injection_scan*.root")
        print(files)
        print("Number of sampling scan files", len(files)) 
        for f in files:
            injection_scan_analyzer.add(f)
        
        injectedChannels = injection_scan_analyzer.get_injectedChannels(odir) 
        injection_scan_analyzer.mergeData()
        injection_scan_analyzer.pass_criteria_sampling_scan_internal("TB3_D8",injectedChannels,len(files),odir,process='int',subprocess='preamp')
        '''


        #'''
        sampling_analyzer = overall_analyzer(odir=odir)
        files = glob.glob(odir+"/sampling_scan*.root")
        
        print(files)
        print("Number of sampling scan files", len(files)) 
        for f in files:
            sampling_analyzer.add(f)

        injectedChannels = sampling_analyzer.get_injectedChannels(odir) 
        sampling_analyzer.mergeData()
        #sampling_analyzer.pulse_width_pass("TB3_D8",injectedChannels,len(files),odir,height_percent=0.1,process='int',subprocess='preamp')
        #sampling_analyzer.chip_half("TB3_D8",injectedChannels,odir)
        #no_phase_chan = sampling_analyzer.channel_sampling_scan_internal_check("TB3_D8",injectedChannels,len(files),odir,process='int',subprocess='preamp',height_percent=0.1,config_file = config_file,fout = odir + "analysis_summary_new.yaml")
        #print("List of channels excluded from phase calculation", no_phase_chan)
        #sampling_analyzer.determine_bestPhase(injectedChannels,odir, no_phase_chan)
        #(BX_1,bx_begin,phase_begin,calib_bx) = sampling_analyzer.calc_bestPhase(injectedChannels,odir,no_phase_chan)

        odir_phase = '/home/hgcal/Desktop/kria/HGCROC3b/hexactrl-sw/hgcal_qc_hexactrl-script-cleanup/data/D8_8/'
        #'''
        try:
            with open(odir_phase + "best_phase_low_high.yaml",'r') as best_phase_file:
                phase_yaml = yaml.safe_load(best_phase_file)
                print("File already exists")
                            
        except FileNotFoundError:
            with open(odir_phase + "best_phase_low_high.yaml",'w') as best_phase_file:
                phase_yaml = dict()
                print("First time creation of file")

        phase_yaml = sampling_analyzer.get_med_phase(odir_phase,phase_yaml) 
        print("Final low range or high range dict",phase_yaml)
        with open(odir_phase + "best_phase_low_high.yaml",'w') as best_phase_file:
            print(yaml.dump(phase_yaml,best_phase_file,sort_keys=False))

        print("Best phase/fit parameters written to yaml file",odir_phase + "best_phase_low_high.yaml")


        '''
        sampling_analyzer = overall_analyzer(odir=odir)
        files = glob.glob(odir+"/sampling_scan*.root")
        
        print(files)
        print("Number of sampling scan files", len(files)) 
        for f in files:
            sampling_analyzer.add(f)
        injectedChannels = sampling_analyzer.get_injectedChannels(odir) 
        sampling_analyzer.mergeData()

        sampling_analyzer.determine_bestPhase(odir)
        '''
        #sampling_analyzer.makePlots(injectedChannels)
        #sampling_analyzer.addSummary(injectedChannels)
        #sampling_analyzer.writeSummary()

    else:
        print("No argument given")
