from level0.analyzer import *
from scipy.optimize import curve_fit
import glob
from matplotlib.ticker import AutoMinorLocator
from nested_dict import nested_dict
import pandas as pd
import numpy as np

import analysis.level0.miscellaneous_analysis_functions as analysis_misc
import analysis.level0.pedestal_run_analysis

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
        
        (inj_pulse, max_pulse, pedestal_baseline, BX_amp, phase_amp) = self.get_pulse(chip,half,channel)
        net_phase = phase_amp+16*BX_amp
        pulse_amp = max_pulse - pedestal_baseline
        target_min_height = height_percent*pulse_amp+pedestal_baseline #This is the height (absolute height in ADC counts with pedestal included) upto which the rising and falling widths will be calculated

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

        cmap = cm.get_cmap('viridis') 
        
        #Optional plotting (both halves in one plot) with linear fit instead of calculating chi_squared
        
        nchip = inj_data['chip'].unique()
        for chip in nchip:

            print("ROC number",chip)
            inj_chip = inj_data[inj_data['chip']==chip].copy()
            inj_sorted = inj_chip.sort_values(by=["channel","Calib"], ignore_index=True)
            print(inj_sorted[inj_sorted['half']==0 ])
            
            inj_0 = int(len(inj_sorted[inj_sorted['half']==0 ].copy())/file_num)
            inj_1 = int(len(inj_sorted[inj_sorted['half']==1 ].copy())/file_num)
            print("Number of injected channels in half 0 and 1", inj_0, inj_1)
            injected_channels = inj_sorted['channel'].unique()
            print(injected_channels)
            #adc_max = 1023
            adc_max = 800
            slope_avg = 0
            max_slope = 0 #also a non negative value considering that the slope values are positive
            min_slope = 100 #very high value considering the present slope values

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
            for i in injected_channels:
                inj_linear = inj_sorted[(inj_sorted['channel']==i) & (inj_sorted['adc_median']<adc_max)].copy()
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
                
            slope_avg = round(slope_avg/len(injected_channels),3)
            print(slope_avg)
            slope_spread = round(max_slope - min_slope,3)
            print("Max and min of slope for spread", max_slope, min_slope)
            print("Slope spread", slope_spread)
            
            #if (slope_avg<=slope_high) & (slope_avg>=slope_low) & (slope_spread<=0.2):
                
            with open(directory,'r+') as file:
            #with open(directory,'w') as file:
                injection_slope = yaml.safe_load(file)                    
                print(injection_slope.keys())
                print(type(injection_slope))
                
            try:    
                injection_slope[process+'ernal '+ subprocess + ' injection']['roc_s'+str(chip)]['ADC_vs_calib_slope_'+str(inj_0)+'_channels']['conv_gain_'+str(int(conv_gain))] = float(slope_avg)
                print("Writing to existing keys")
                print(injection_slope)

            except KeyError:
                print("Writing keys for the first time")
                nestedConf = analysis_misc.set_key_dict(nestedConf,['ADC_vs_calib_slope_'+str(inj_0)+'_channels','roc_s'+str(chip),process+'ernal '+ subprocess + ' injection'],['conv_gain_'+str(int(conv_gain))],[float(slope_avg)])
                #nestedConf[process+'ernal '+ subprocess + ' injection']['roc_s'+str(chip)]['ADC_vs_calib_slope_'+str(inj_0)+'_channels']['conv_gain_'+str(int(conv_gain))] = float(slope_avg)
                print("Initialized dict", nestedConf)
                    
                #else:
                #    print("Not a good injection run - pick another one!")        
                    
                
            handles, labels = axes.get_legend_handles_labels()
            axes.legend(handles, labels)
            plt.savefig(f'{odir}/adc_injection_scan_chip{chip}_linear_fit.png', format='png', bbox_inches='tight')         
            print("Saved image for linear region")
            plt.close()

        injection_slope = analysis_misc.merge_nested(nestedConf,injection_slope)
        print("Merged dictionary",injection_slope)
        with open(directory,'w') as file:
            #yaml.dump(injection_slope,file,sort_keys=False)
            yaml.dump(injection_slope,file,sort_keys=True)


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
        
        #Optional plotting (both halves in one plot) with linear fit instead of calculating chi_squared
        ped_data = read_files('/home/hgcal/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/data/TB3_D8_10/pedestal_run_2','pedestal_run')
        self.chip_half("TB3_D8",injectedChannels,odir)
        for chip in self.chip_dict.keys():
            print("ROC number",chip)
            for half in self.chip_dict[chip].keys():
                print("half number",half)

                inj_half = self.chip_dict[chip][half]
                injectedChannels_half = inj_half['channel'].unique()  
                inj = len(injectedChannels_half)
                print("Number of injected channels", inj)
                print(injectedChannels_half)
                #Average because these widths are supposed to be the same for the channels in each half
                
                rise_avg = 0
                fall_avg = 0
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
                    
                    rise_wd = self.get_width(chip,half,i,height_percent,1)
                    fall_wd = self.get_width(chip,half,i,height_percent,-1)
                    
                    print("Rising width", rise_wd)
                    print("Falling width", fall_wd)
                    
                    rise_avg += rise_wd
                    fall_avg += fall_wd
                    
                print("Average rising and falling widths for channels in half", half, " are",rise_avg/inj," and", fall_avg/inj)
                
                with open(directory,'r+') as file:
                
                    pulse_shape = yaml.safe_load(file)                    
                    print(pulse_shape.keys())
                    print(type(pulse_shape))

                pulse_shape = analysis_misc.set_key_dict(pulse_shape,['num_ch_'+str(inj),'roc_s'+str(chip),process+'ernal '+ subprocess + ' injection'],['Rise_width'],[round(float(rise_avg/inj),2)])
                pulse_shape = analysis_misc.set_key_dict(pulse_shape,['num_ch_'+str(inj),'roc_s'+str(chip),process+'ernal '+ subprocess + ' injection'],['Fall_width'],[round(float(fall_avg/inj),2)])

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
        
        
    def channel_sampling_scan_internal_check(self,device_type,injectedChannels,file_num,odir,process,subprocess,height_percent,config_file,fout=''):
        directory = "/home/hgcal/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/analysis/level0/Pass_criteria/%s_limits.yaml"%(device_type)
        nestedConf = nested_dict()
        
        #Getting gain from config file name
        conv_gain = analysis_misc.get_conveyor_gain(config_file)
        print(conv_gain)
        cmap = cm.get_cmap('viridis') 
        calib = float(self.get_parameter_value(odir,'calib'))
        print(calib)

        no_phase_chan = [] #This is the list of channels, which are not necessarily bad but do not satisfy at least one of the criteria right away and it is best if these are excluded from the list of channels used to calculate the max adc phase       
        
        #Optional plotting (both halves in one plot) with linear fit instead of calculating chi_squared
        ped_data = read_files('/home/hgcal/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/data/TB3_D8_10/pedestal_run_2','pedestal_run')
        self.chip_half("TB3_D8",injectedChannels,odir)
        for chip in self.chip_dict.keys():
            print("ROC number",chip)
            ch_bad_wave = 0

            for half in self.chip_dict[chip].keys():
                print("half number",half)

                inj_half = self.chip_dict[chip][half]
                injectedChannels_half = inj_half['channel'].unique()  
                inj = len(injectedChannels_half)
                print("Number of injected channels", inj)
                print(injectedChannels_half)
                #Average because these widths are supposed to be the same for the channels in each half
        
                slope = analysis_misc.get_slope_ch_nos(process,subprocess,directory,odir,inj,conv_gain,chip)
                print("Slope from injection scan for half", half," is",slope)
                print()
                
                #rise_wd = analysis_misc.get_width_ch_nos(process,subprocess,directory,odir,inj,conv_gain,chip,"Rise")
                #print("Rising width from sampling scan for half", half,"is",rise_wd)
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
                         
                for i in injectedChannels_half:
                    print("Channel number",i)
                    (inj_pulse,max_pulse,pedestal_baseline, BX_amp, phase_amp) = self.get_pulse(chip,half,i)

                    print("Maximum value of ADC counts in pulse", max_pulse)
                    #This will also help when there are two phases that could have the maximum value, just take the first one
                    
                    print("BX and Phase at which max amplitude occurs", BX_amp, phase_amp)
                    print("Net Phase at which max amplitude occurs", phase_amp+16*BX_amp) #In case of choosing the file for sps (albeit that is external injection and not internal), this will give the actual index of the file
                    
                    print("Pedestal from pulse baseline", pedestal_baseline)
                    
                    #Pedestal value from one of the pedestal runs (has to have the same triminv, dacb, vrefinv etc settings from the config file)
                    #Channeltype will be 0 by default since only those can be injected into (gain settings can be changed)
                    pedestal_ped_run = read_val(chip,i,0,ped_data,'adc_median')
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
                    
                    
                    if (abs(max_pulse - 1023) < 0.5) & (len(inj_pulse.loc[inj_pulse['adc_median'] == max_pulse,'Phase'])>2):
                        print("Saturated pulse - do not attempt to calculate pulse width and pick best phase for injection scan!!")
                        sat_flag = 1
                    else:
                        if abs(pulse_amp - slope*calib) <= 0.1*calib: #Important condition but not the deciding one
                        #if abs(pulse_amp - slope*calib) == 0:
                            pass
                        else:
                            print("Potentially bad amplitude")
                            amp_flag = 1
                                
                        rise_wd = self.get_width(chip,half,i,height_percent,1)
                        fall_wd = self.get_width(chip,half,i,height_percent,-1)
                        print("Pulse widths",rise_wd,fall_wd)
                        
                        if (rise_wd>=np.min(rise_wd_y)-0.5) & (rise_wd<=np.max(rise_wd_y)+0.5):
                            pass
                        else:
                            print("Potentially bad rise width")        
                            rise_flag = 1
                        
                        if (fall_wd>=np.min(fall_wd_y)-1) & (fall_wd<=np.max(fall_wd_y)+1):
                            pass
                        else:
                            print("Potentially bad fall width")   
                            fall_flag = 1 
                    
                    print("List of flags:","sat:",sat_flag,"amp:",amp_flag,"rise_wd:",rise_flag, "fall_wd:",fall_flag,"glitch:",glch_flag)
                    if ((sat_flag == 1) | (amp_flag == 1) | (rise_flag == 1) | (fall_flag == 1) | (glch_flag == 1)):
                        no_phase_chan.append(i)
                    
                    print()        

            print("Number of channels with bad waveforms in both halves for chip", chip, " are",ch_bad_wave)
            return no_phase_chan

    def makePlots(self, injectedChannels):
        nchip = len( self.data.groupby('chip').nunique() )        
        cmap = cm.get_cmap('Dark2')

        inj_data = self.data[ (self.data['channeltype']==0) & (self.data['channel'].isin(injectedChannels)) ].copy()
        inj_data['time'] = inj_data.apply( lambda x: 25/16.0*(x.Phase+16*x.BX),axis=1 )
        
        #print to csv file for grouping with the data from other files
        data_pd_csv = pd.DataFrame()
        for chip in self.data.groupby('chip')['chip'].mean():
            chanColor=0
            fig, ax = plt.subplots(1,1,figsize=(16,9))
            for injectedChannel in injectedChannels:
                sel_data = inj_data[ (inj_data['chip']==chip) & (inj_data['channel']==injectedChannel) ]
                sel_data = sel_data.sort_values(by=['time'],ignore_index=True)
                
                print("Original dataframe",sel_data['adc_median'])
                plt.plot( sel_data['time'], sel_data['adc_median'], color=cmap(chanColor), label=r'Channel %d'%(injectedChannel),marker='o')
                chanColor=chanColor+1
                
                data_pd_csv['time'] = sel_data['time']
                data_pd_csv['chip_'+str(chip)+'_ch_'+str(injectedChannel)+'_adc_median'] = sel_data['adc_median']

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

    def determine_bestPhase(self,injectedChannels,odir,no_phase_chan):
        self.chip_half("TB3_D8",injectedChannels,odir)
        bx_begin, phase_begin = self.get_start_BX_phase(odir)
        print("Starting BX and phase", bx_begin, phase_begin)
        
        calib_bx = self.get_start_trigger(odir)
        print("Calibreq value",calib_bx)
        BX_phase_info=dict()
        for chip in self.chip_dict.keys():
            print("ROC number",chip)
            for half in self.chip_dict[chip].keys():
                print("half number",half)
                
                inj_half = self.chip_dict[chip][half]
                injectedChannels_half = inj_half['channel'].unique()  
                inj = len(injectedChannels_half)
                print("Number of injected channels", inj)
                print(injectedChannels_half)
                ret = 0
                used_inj_chan = []
                
                for i in injectedChannels_half:
                    if i in no_phase_chan:
                        pass
                    else:
                        used_inj_chan.append(i)
                
                print("Injected channels used for max phase calculation", used_inj_chan)         
                #Average because these widths are supposed to be the same for the channels in each half
                best_phase_half = []
                if len(used_inj_chan)>=1:
                    for i in used_inj_chan:

                        (inj_pulse,max_pulse,pedestal_baseline, BX_amp, phase_amp) = self.get_pulse(chip,half,i)
                        best_phase_half.append(phase_amp+16*BX_amp) #Do NOT take the average of BX and phase separately, it could cause problems if the phases are slightly different and in different BXs

                    ret = int(sum(best_phase_half)/len(best_phase_half))
                    print("BX and phase combo", ret)
                    BX_half = int(ret/16)
                    phase_half = int(ret - BX_half*16)
                    print("Best max BX and phase for half",half,"BX:",BX_half+bx_begin,"phase:",phase_half+phase_begin)

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
        no_phase_chan = sampling_analyzer.channel_sampling_scan_internal_check("TB3_D8",injectedChannels,len(files),odir,process='int',subprocess='preamp',height_percent=0.1,config_file = config_file,fout = odir + "analysis_summary_new.yaml")
        print("List of channels excluded from phase calculation", no_phase_chan)
        sampling_analyzer.determine_bestPhase(injectedChannels,odir, no_phase_chan)
        
        #sampling_analyzer.makePlots(injectedChannels)
        #sampling_analyzer.addSummary(injectedChannels)
        #sampling_analyzer.writeSummary()

    else:
        print("No argument given")
