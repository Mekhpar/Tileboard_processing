from level0.analyzer import *
from scipy.optimize import curve_fit
import glob
from matplotlib.ticker import AutoMinorLocator
from nested_dict import nested_dict
import pandas as pd
import numpy as np

#import analysis.level0.miscellaneous_analysis_functions as analysis
#import analysis.level0.pedestal_run_analysis

import miscellaneous_analysis_functions as analysis
import pedestal_run_analysis

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
    use_file = eval(test_name + '_analysis')
    
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
        val = analysis.get_num_string(search_string,parameter+'_')
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

    #At the moment, only for internal injection
    def pass_criteria_sampling_scan_internal(self,device_type,injectedChannels,file_num,odir,process,subprocess): #Here device_type is only size and not index (for eg TB3_D8 and not TB3_D8_11)
        directory = "/home/hgcal/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/analysis/level0/Pass_criteria/%s_limits.yaml"%(device_type)
        nestedConf = dict()
        #Next part copied from the functions below, probably looping over in case of 2 or more ROCs
        nchip = len( self.data.groupby('chip').nunique() )
        inj_data = self.data[ (self.data['channeltype']==0) & (self.data['channel'].isin(injectedChannels)) ].copy() #First condition only for the real 72 channels and second is obvious

        #Getting gain from config file name
        conv_gain = analysis.get_conveyor_gain(config_file)
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
                nestedConf = analysis.set_key_dict(nestedConf,['ADC_vs_calib_slope_'+str(inj_0)+'_channels','roc_s'+str(chip),process+'ernal '+ subprocess + ' injection'],['conv_gain_'+str(int(conv_gain))],[float(slope_avg)])
                #nestedConf[process+'ernal '+ subprocess + ' injection']['roc_s'+str(chip)]['ADC_vs_calib_slope_'+str(inj_0)+'_channels']['conv_gain_'+str(int(conv_gain))] = float(slope_avg)
                print("Initialized dict", nestedConf)
                    
                #else:
                #    print("Not a good injection run - pick another one!")        
                    
                
            handles, labels = axes.get_legend_handles_labels()
            axes.legend(handles, labels)
            plt.savefig(f'{odir}/adc_injection_scan_chip{chip}_linear_fit.png', format='png', bbox_inches='tight')         
            print("Saved image for linear region")
            plt.close()

        injection_slope = analysis.merge_nested(nestedConf,injection_slope)
        print("Merged dictionary",injection_slope)
        with open(directory,'w') as file:
            #yaml.dump(injection_slope,file,sort_keys=False)
            yaml.dump(injection_slope,file,sort_keys=True)

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
            
            if (cur_val < 0.9*ped) & (prev_val >= 0.9*ped) & (cur_slope < -20*calib/200.0): #the percentage of the pedestal is meant to take into account baseline variation at the end of the pulse
            #Very stringent limit for second condition because do not want to have false negatives (still could be possible though)
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
        
    def channel_sampling_scan_internal_check(self,device_type,injectedChannels,file_num,odir,process,subprocess,fout=''):
        directory = "/home/hgcal/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/analysis/level0/Pass_criteria/%s_limits.yaml"%(device_type)
        nestedConf = nested_dict()
        
        inj_data = self.data[ (self.data['channeltype']==0) & (self.data['channel'].isin(injectedChannels)) ].copy() #First condition only for the real 72 channels and second is obvious
        inj_data['time'] = inj_data.apply( lambda x: 25/16.0*(x.Phase+16*x.BX),axis=1 )
        inj_data['entries'] = inj_data.apply( lambda x: (int(x.Phase+16*x.BX)),axis=1 )
        #Getting gain from config file name
        conv_gain = analysis.get_conveyor_gain(config_file)
        print(conv_gain)
        cmap = cm.get_cmap('viridis') 
        calib = float(self.get_parameter_value(odir,'calib'))
        print(calib)
        
        #Optional plotting (both halves in one plot) with linear fit instead of calculating chi_squared
        ped_data = read_files('/home/hgcal/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/data/TB3/TB3_D8_11/pedestal_run_TB3_D8_11_7','pedestal_run')
        nchip = inj_data['chip'].unique()
        
        for chip in nchip:
            #Seems a little redundant to copypaste this all over again from making the yaml file
            print("ROC number",chip)
            inj_chip = inj_data[inj_data['chip']==chip].copy()
            nhalf = inj_chip['half'].unique()
            ch_bad_wave = 0
            for half in nhalf:
                inj_half = inj_chip[inj_chip['half']==half].copy()
                inj_sorted = inj_half.sort_values(by=["channel","time"], ignore_index=True)
                
                inj = int(len(inj_sorted.copy())/file_num)
                print("Number of injected channels in half",half," are ", inj)
                injected_channels = inj_sorted['channel'].unique()
                print(injected_channels)
                
                slope = analysis.get_slope_ch_nos(process,subprocess,directory,odir,inj,conv_gain,chip)
                print("Slope from injection scan for half", half," is",slope)
                print()
                
                for i in injected_channels:
                    print("Channel number",i)
                    inj_pulse = inj_sorted[(inj_sorted['channel']==i)].copy().set_index("entries")
                    #print(inj_pulse)
                    max_pulse = max(inj_pulse['adc_median'])
                    print("Maximum value of ADC counts in pulse", max_pulse)
                    inj_pulse = inj_pulse.astype({'adc_median':float})
                    #This will also help when there are two phases that could have the maximum value, just take the first one
                    BX_amp = inj_pulse.loc[inj_pulse['adc_median'] == max_pulse,'BX'].values[0]
                    phase_amp = inj_pulse.loc[inj_pulse['adc_median'] == max_pulse,'Phase'].values[0]
                    
                    print("BX and Phase at which max amplitude occurs", BX_amp, phase_amp)
                    print("Net Phase at which max amplitude occurs", phase_amp+16*BX_amp) #In case of choosing the file for sps (albeit that is external injection and not internal), this will give the actual index of the file
                    
                    inj_ped = inj_sorted[(inj_sorted['channel']==i) & (inj_sorted['entries']<4)].copy().set_index("entries")
                    #print(inj_ped)
                    pedestal_baseline = inj_ped.mean(axis=0)['adc_median']
                    print("Pedestal from pulse baseline", pedestal_baseline)
                    
                    #Pedestal value from one of the pedestal runs (has to have the same triminv, dacb, vrefinv etc settings from the config file)
                    #Channeltype will be 0 by default since only those can be injected into (gain settings can be changed)
                    pedestal_ped_run = read_val(chip,i,0,ped_data,'adc_median')
                    print("Average (mean/median) pedestal from previous pedestal runs", pedestal_ped_run)
                    
                    #if abs(pedestal_ped_run - pedestal_baseline)<10:
                    #    print("Pedestal values consistent")
                    
                    inj_pulse_glitch = self.sub_zero_signal_time(inj_pulse,calib,pedestal_baseline)
                    phase_glitch = inj_pulse_glitch[inj_pulse_glitch['glitch_ct']>2]
                    print(phase_glitch)
                    if len(phase_glitch) >=1:
                        print("Bad waveform")
                        ch_bad_wave+=1

                    pulse_amp = max_pulse - pedestal_baseline
                    print("Pulse amplitude", pulse_amp)
                    if abs(pulse_amp - slope*calib) <= 0.1*calib: #Important condition but not the deciding one
                    #if abs(pulse_amp - slope*calib) == 0:
                        pass
                    else:
                        print("Potentially bad pulse")
                            
                    print()        

            print("Number of channels with bad waveforms in both halves for chip", chip, " are",ch_bad_wave)

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
                print ("Max Phase lenght", len(max_adc_phase))
                #print ("sel_data['adc_median']", sel_data['adc_median'].max())

                ## rejection criteria based on phase at max adc to be implemented               
                ## if max_adc_phase.to_list()[0] < 20:
                ##    badchns_phase['ch'].append(injectedChannel)

                self._summary['sampling_scan']['chip%d' % chip][injectedChannel]['Phase_at_adc_max'] = max_adc_phase.to_list()[0] 

            self._summary['bad_channels_phase']['chip%d' % chip] = badchns_phase
            self._summary['bad_channels_phase']['chip%d' % chip]['total'] = len(badchns_phase['ch']) + len(badchns_phase['cm']) + len(badchns_phase['calib'])

            
    def fit(self,data):
        pass

    def determine_bestPhase(self,injectedChannels):

        rockeys = []
        with open("%s/initial_full_config.yaml"%(self.odir)) as fin:
            initconfig = yaml.safe_load(fin)
            for key in initconfig.keys():
                if key.find('roc')==0:
                    rockeys.append(key)
        rockeys.sort()

        inj_data = self.data[ (self.data['channeltype']==0) & (self.data['channel'].isin(injectedChannels)) ].copy()
        inj_data['time'] = inj_data.apply( lambda x: 25/16.0*(x.Phase+16*x.BX),axis=1 )

        nchip = len(inj_data.groupby('chip').nunique() )        
        yaml_dict = {}

        for chip in range(nchip):
            chanColor=0
            best_phase = []
            for injectedChannel in injectedChannels:
                
                sel_data = inj_data[ (inj_data['chip']==chip) & (inj_data['channel']==injectedChannel) ]
                sel_data = sel_data.sort_values(by=['time'],ignore_index=True)
                prof = sel_data.groupby("Phase")["adc_mean"].mean()
                #print(sel_data.iloc[sel_data[['adc_mean']].idxmax()]['Phase'].values[0])
                best_phase.append(sel_data.iloc[sel_data[['adc_mean']].idxmax()]['Phase'].values[0])
            ret = int(sum(best_phase)/len(best_phase)) #Looks like the average over the injected channels
            #print(ret)

            if chip<len(rockeys):
                chip_key_name = rockeys[chip]
                yaml_dict[chip_key_name] = {
                    'sc' : {
                        'Top' : { 
                            'all': {
                                'phase_strobe': 15-ret
                                }
                            }
                        }
                    }
            else :
                print("WARNING : best phase will not be saved for ROC %d"%(chip))
        with open(self.odir+'/best_phase.yaml','w') as fout:
            yaml.dump(yaml_dict,fout)


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
            
        sampling_analyzer.channel_sampling_scan_internal_check("TB3_D8",injectedChannels,len(files),odir,process='int',subprocess='preamp',fout = odir + "analysis_summary_new.yaml")
        
        
        #sampling_analyzer.makePlots(injectedChannels)
        #sampling_analyzer.addSummary(injectedChannels)
        #sampling_analyzer.writeSummary()

    else:
        print("No argument given")
