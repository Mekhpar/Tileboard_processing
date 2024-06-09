from level0.analyzer import *
from scipy.optimize import curve_fit
import glob
import seaborn as sns
sns.set_style("ticks")
from matplotlib.ticker import MultipleLocator
import yaml, os
from typing import List

import analysis.level0.miscellaneous_analysis_functions as analysis
from nested_dict import nested_dict
import pandas as pd
import numpy as np
import copy

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

            with open(fout,'w') as file: #This is the first time the fresh file (analysis_summary_new.yaml etc) is to be opened
                print(yaml.dump(nestedConf.to_dict(),file,sort_keys=False))
                print("Written to yaml file")                   
                
        return chip_goodness

class overall_analyzer(analyzer):
    #This is only a one time thing for a particular size of board
    def pass_criteria_pedestal(self,device_type): #Here device_type is only size and not index (for eg TB3_D8 and not TB3_D8_11)
        directory = "/home/hgcal/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/analysis/level0/Pass_criteria/%s_limits.yaml"%(device_type)
        #nestedConf = nested_dict()
        nestedConf = dict()
        #Next part copied from the functions below, probably looping over in case of 2 or more ROCs
        nchip = len( self.data.groupby('chip').nunique() )
        for chip in range(nchip):
            data = self.data[ self.data['chip']==chip ].copy()
            print("Number of channels",len(data['channel']))
            
            
            ch = data[ data['channeltype']==0 ].copy()
            calib = data[ data['channeltype']==1 ].copy()
            cm = data[ data['channeltype']==100 ].copy()
            ch_array=[ch,calib,cm]#This seems like it is the whole series/dataframe
            ch_key_array = ['ch','calib','cm']


            for i in range(len(ch_array)):
                #ch_median = pd.DataFrame([ch_array[i]['adc_median']])
                
                ch_median = pd.DataFrame([ch_array[i]['adc_median']])
                ch_stddev = pd.DataFrame([ch_array[i]['adc_stdd']])
                print(ch_median)
                print("Pedestal upper limit", ch_median.iloc[0,0] + 2*ch_stddev.iloc[0,0])
                print(type(ch_median.iloc[0,0] + 2*ch_stddev.iloc[0,0]))
                
                for ch in range(len(ch_array[i]['channel'])):
                    
                    #nestedConf['ch_array[i]'][ch]['pedestal_lower'] = ch_median.iloc[0,ch] - 2*ch_stddev.iloc[0,ch] #Do not use this!!
                    '''
                    nestedConf['pedestal_run']['roc_s'+str(chip)][ch_key_array[i]][ch]['pedestal_lower'] = int(ch_median.iloc[0,ch] - 2*ch_stddev.iloc[0,ch])
                    nestedConf['pedestal_run']['roc_s'+str(chip)][ch_key_array[i]][ch]['pedestal_upper'] = int(ch_median.iloc[0,ch] + 2*ch_stddev.iloc[0,ch])+1
                    nestedConf['pedestal_run']['roc_s'+str(chip)][ch_key_array[i]][ch]['noise_lower'] = 0.2 #Should not be exactly 0 since that indicates a problem too
                    nestedConf['pedestal_run']['roc_s'+str(chip)][ch_key_array[i]][ch]['noise_upper'] = round(float(ch_stddev.iloc[0,ch]*1.5),2)
                    '''

                    with open(directory,'r+') as file:
                        pedestal_values = yaml.safe_load(file)                    
                        print(pedestal_values.keys())
                        print("Old dictionary type",type(pedestal_values))
                        #pedestal_values = nested_dict(pedestal_values)
                        print("New dictionary type",type(pedestal_values))

                    try:    
                        pedestal_values['pedestal_run']['roc_s'+str(chip)][ch_key_array[i]][ch]['pedestal_lower'] = int(ch_median.iloc[0,ch] - 10)
                        pedestal_values['pedestal_run']['roc_s'+str(chip)][ch_key_array[i]][ch]['pedestal_upper'] = int(ch_median.iloc[0,ch] + 10)+1
                        pedestal_values['pedestal_run']['roc_s'+str(chip)][ch_key_array[i]][ch]['noise_lower'] = 0.2 #Should not be exactly 0 since that indicates a problem too
                        pedestal_values['pedestal_run']['roc_s'+str(chip)][ch_key_array[i]][ch]['noise_upper'] = max(3,round(float(ch_stddev.iloc[0,ch]*1.5),2))

                        print("Existing keys",pedestal_values)
                        print('\n')

                    except KeyError:
                        print("Writing limits for the first time")
                        nestedConf = analysis.set_key_dict(nestedConf,[ch,ch_key_array[i],'roc_s'+str(chip),'pedestal_run'],['pedestal_lower','pedestal_upper','noise_lower','noise_upper'],[int(ch_median.iloc[0,ch] - 10),int(ch_median.iloc[0,ch] + 10)+1,0.2,max(3,round(float(ch_stddev.iloc[0,ch]*1.5),2))])
                        print("Initialized dict", nestedConf)

                    print("Written pedestal limits to yaml file for channel", ch_key_array[i], ch)

        pedestal_values = analysis.merge_nested(nestedConf,pedestal_values)
        print("Merged dictionary",pedestal_values)
        with open(directory,'w') as file:
            #yaml.dump(pedestal_values,file,sort_keys=False)
            yaml.dump(pedestal_values,file,sort_keys=True)
                    #New limits since old ones produced very many false bad channels
                    
                #with open(directory,'w') as file:

    def channel_ped_check(self,device_type,fout=''):
        directory = "/home/hgcal/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/analysis/level0/Pass_criteria/%s_limits.yaml"%(device_type)
        nestedConf = nested_dict() 
        nchip = len( self.data.groupby('chip').nunique() )
        with open(directory,'r') as file:
            ped_limits = yaml.safe_load(file)
            print("Ped limits file contents")
            #print(ped_limits)
                
            for key in ped_limits.keys():
                print("Key name", key)
                if key == 'pedestal_run': #Because there will be other tests as well
                    for chip in range(nchip):
                        #Seems a little redundant to copypaste this all over again from making the yaml file
                        data = self.data[ self.data['chip']==chip ].copy()
                        ch = data[ data['channeltype']==0 ].copy()
                        calib = data[ data['channeltype']==1 ].copy()
                        cm = data[ data['channeltype']==100 ].copy()
                        ch_array=[ch,calib,cm]#This seems like it is the whole series/dataframe
                        ch_key_array = ['ch','calib','cm']
                        
                        
                        for key_roc in ped_limits[key].keys():
                            if key_roc =='roc_s' + str(chip):
                                for i in range(len(ch_array)):
                                    bad_channels = []
                                    ch_median = pd.DataFrame([ch_array[i]['adc_median']])
                                    ch_stddev = pd.DataFrame([ch_array[i]['adc_stdd']])                    
                                    for ch in range(len(ch_array[i]['channel'])):
                                        ped_low = ped_limits[key][key_roc][ch_key_array[i]][ch]['pedestal_lower']
                                        ped_high = ped_limits[key][key_roc][ch_key_array[i]][ch]['pedestal_upper']
                                        noise_low = ped_limits[key][key_roc][ch_key_array[i]][ch]['noise_lower']
                                        noise_high = ped_limits[key][key_roc][ch_key_array[i]][ch]['noise_upper']
                                        
                                        #Actual comparison
                                        if ch_stddev.iloc[0,ch] >= noise_low and ch_stddev.iloc[0,ch] <= noise_high:
                                            if ch_median.iloc[0,ch] >= ped_low and ch_median.iloc[0,ch] <= ped_high:
                                                pass
                                            else:
                                                print("Channel with bad pedestal value",ch_key_array[i],ch)
                                                print("Actual mean pedestal value", ch_median.iloc[0,ch])
                                                print("Pedestal limits for this channel", ped_low, ped_high)
                                        else:
                                            print("Channel with bad noise and/or pedestal value",ch_key_array[i],ch)                
                                            print("Actual noise value", ch_stddev.iloc[0,ch])
                                            print("Noise limits for this channel", noise_low, noise_high)
                                            bad_channels.append(ch)
                                    nestedConf['bad_channels']['chip' + str(chip)][ch_key_array[i]] = bad_channels
        print(nestedConf)                                    
        with open(fout,'r+') as file:
            bad_channels = yaml.safe_load(file)
            print(yaml.dump(nestedConf.to_dict(),file,sort_keys=False))

    def makePlots(self):

        nchip = len( self.data.groupby('chip').nunique() )
        
        fig= plt.figure(figsize=(18,9))
        for chip in range(nchip):

            data = self.data[ self.data['chip']==chip ].copy() #[ self.data['channeltype']==0 ]
            # data['x'] = data.apply( lambda x: x.channel if x.channeltype==0 and x.channel<36 
            #                         # else x.channel+72 if x.channeltype==1 
            #                         # else x.channel+74
            #                         else 0
            #                         , axis=1 )
            #sel = data.adc_median < 1000
            #sel &= data.adc_median > 0
            #data = data[sel]
            data['x'] = data.apply( lambda x: x.channel if x.channeltype==0 and x.channel<36 # first half, channels 
                                    else x.channel+36 if x.channeltype==1 and x.channel==0 # first half, calib 
                                    else x.channel+37 if x.channeltype==100 and x.channel<2 # first half, cm 
                                    else x.channel+3 if x.channeltype==0 and x.channel>=36 # second half, channels 
                                    else x.channel+74 if x.channeltype==1 and x.channel==1 # second half, calib
                                    else x.channel+74 if x.channeltype==100 and x.channel>=2  # second half, cm
                                    else -10,
                                    axis=1
                                    )

            calib = data[ data['channeltype']==1 ].copy()
            cm = data[ data['channeltype']==100 ].copy()

            ax=fig.add_subplot(1,1,1)
            plt.scatter(data['x'], data['adc_median'], color='black', label=r'normal channels')
            plt.scatter(calib['x'], calib['adc_median'], color='blue', label=r'calibration channels')
            plt.scatter(cm['x'], cm['adc_median'], color='red', label=r'common mode channels')
            plt.xlabel(r'Channel ')
            plt.ylabel(r'Pedestal')
            high = data['adc_median'].max()
            low  = data['adc_median'].min()
            plt.ylim([low-0.5*(high-low), high+0.5*(high-low)])
            h,l=ax.get_legend_handles_labels() # get labels and handles from ax1
            ax.legend(handles=h,labels=l,loc='upper right')
            plt.title("chip %d"%(chip))
            plt.grid()
            plt.savefig("%s/pedestal_vs_channel_chip%d.png"%(self.odir,chip),format='png',bbox_inches='tight') 
            # plt.savefig("%s/pedestal_vs_channel_chip%d.pdf"%(self.odir,chip),format='pdf',bbox_inches='tight') 
            plt.cla()
            plt.clf()

            ax=fig.add_subplot(1,1,1)
            plt.scatter(data['x'], data['adc_stdd'], color='black', label=r'normal channels')
            plt.scatter(calib['x'], calib['adc_stdd'], color='blue', label=r'calibration channels')
            plt.scatter(cm['x'], cm['adc_stdd'], color='red', label=r'common mode channels')
            plt.xlabel(r'Channel ')
            plt.ylabel(r'Noise')
            high = data['adc_iqr'].max()
            low  = data['adc_iqr'].min()
            plt.ylim([low-0.5*(high-low), high+0.5*(high-low)])
            h,l=ax.get_legend_handles_labels() # get labels and handles from ax1
            ax.legend(handles=h,labels=l,loc='upper right')
            plt.title("chip %d"%(chip))            
            plt.grid()
            plt.savefig("%s/noise_vs_channel_chip%d.png"%(self.odir,chip),format='png',bbox_inches='tight') 
            #plt.savefig("%s/noise_vs_channel_chip%d.pdf"%(self.odir,chip),format='pdf',bbox_inches='tight') 
            plt.cla()
            plt.clf()

            fig, ax = plt.subplots(figsize=(16,9))
            histdata = data[ (data['channeltype']!=100) & (data['adc_stdd']!=0)  ]
            ax.hist( histdata['adc_stdd'],bins=25 )
            ax.set_title('Chip %d'%(chip))
            ax.set_xlabel('Total noise [ADC counts]')
            plt.text( 0.7, 0.8, r'$\mu = %4.3f$ [ADC counts]'%histdata['adc_stdd'].mean(),transform = ax.transAxes)
            plt.text( 0.7, 0.7, r'$\sigma = %4.3f$ [ADC counts]'%histdata['adc_stdd'].std(),transform = ax.transAxes)
            plt.savefig("%s/total_noise_chip%d.png"%(self.odir,chip),format='png',bbox_inches='tight')
            plt.cla()
            plt.clf()

        plt.close()



    def addSummary(self):
        # add summary information
        nchip = len( self.data.groupby('chip').nunique() )
        self._summary['stats'] = {
            'mean and std of pedestal and noise distributions': ''
        }
        self._summary['bad_channels'] = {
            'rejection criteria': 'noise = 0'
        }

        for chip in range(nchip):
            cmdata = self.data[ (self.data['channeltype']==100) & (self.data['chip']==chip) ].copy()
            bad_cm = cmdata[ (cmdata['adc_stdd']==0) ].copy()

            data = self.data[ (self.data['channeltype']!=100) & (self.data['chip']==chip) ].copy()
            bad_channels = data[ (data['channeltype']==0) & (data['adc_stdd']==0) ].copy()
            bad_calib = data[ (data['channeltype']==1) & (data['adc_stdd']==0) ].copy()
            data = data[ (data['adc_stdd']!=0) ].copy()
            ##df = fitParams.query('chip==%d' % chip)
            mean_noise = data['adc_stdd'].mean()
            std_noise = data['adc_stdd'].std()
            mean_ped = data['adc_mean'].mean()
            std_ped = data['adc_mean'].std()
            #print ("mean noise ", mean_noise)
            #print ("std noise ", std_noise)
            #print ("chip%d "%chip)
            #print(self._summary['pedestal_run'])
            self._summary['stats']['chip%d' % chip] = {
                'MeanNoise': float(mean_noise),
                'StdNoise': float(std_noise),
                'MeanPedestal': float(mean_ped),
                'StdPedestal': float(std_ped),
            }
            self._summary['bad_channels']['chip%d' % chip] = {
                'ch': bad_channels['channel'].to_list(),
                'calib': bad_calib['channel'].to_list(),
                'cm': bad_cm['channel'].to_list()
            }

            self._summary['bad_channels']['chip%d' % chip]['total'] = ( len(bad_channels['channel'].to_list()) +
                                                                        len(bad_calib['channel'].to_list()) +
                                                                        len(bad_cm['channel'].to_list()) )

            
class pedestal_run_raw_analyzer(analyzer):

    def makePlots(self):
        channel_type_names = ('normal channel', 'calibration', 'common mode')
        color_palette = sns.color_palette(['tab:green', 'tab:purple', 'tab:orange'])
        chntype = np.array([channel_type_names[0]] * len(self.data))
        chntype[self.data.channel == 36] = channel_type_names[1]
        chntype[self.data.channel > 36] = channel_type_names[2]
        self.data['channel_type'] = chntype
        print(self.data)

        df = self.data[['chip', 'half', 'channel', 'adc', 'channel_type']]

        df_agg = df.groupby(['chip', 'half', 'channel']).agg(
            noise=('adc', lambda a: a.std()),
            # noise=('adc', lambda a: np.percentile(a, 75) - np.percentile(a, 25)),
            channel_type=('channel_type', lambda a: a.iloc[0])
        )
        print(df_agg)
        ymax_noise = np.nanmax(df_agg.noise) * 1.05

        grouped = df.groupby(['chip', 'half'])
        ymax_adc = np.nanpercentile(self.data['adc'], 98) * 1.2

        for chip in self.data['chip'].unique():
            fig, axes = plt.subplots(2, 2, figsize=(18, 12), sharex=True, gridspec_kw={'height_ratios': [3, 1], 'hspace': 0.03})
            fig.suptitle('Pedestal run')

            for half in 0, 1:
                ax = axes[0][half]
                ax.set_title('Half %s' % half)
                sns.boxplot(x='channel', y='adc', hue='channel_type', data=grouped.get_group((chip, half)), 
                            ax=ax, fliersize=1, width=2, saturation=1, linewidth=1, hue_order=channel_type_names, palette=color_palette)
                # ax.set_ylim(0, ymax_adc)
                ax.xaxis.grid(True)
                ax.set_xlabel('')
                ax.set_ylabel('Pedestal [ADC counts]')

                ax = axes[1][half]
                sns.scatterplot(x='channel', y='noise', hue='channel_type',
                                data=df_agg.loc[chip, half], ax=ax, legend=False, hue_order=channel_type_names, palette=color_palette)
                ax.set_xlim(-1, 39)
                ax.xaxis.set_major_locator(MultipleLocator(5))
                ax.xaxis.set_minor_locator(MultipleLocator(1))
                # ax.set_ylim(0, ymax_noise)
                ax.xaxis.grid(True)
                ax.set_ylabel('Noise [ADC counts]')

            plt.savefig("%s/pedestal_and_noise_vs_channel_chip%d.png"%(self.odir,chip),format='png',bbox_inches='tight') 
            # plt.savefig("%s/pedestal_and_noise_vs_channel_chip%d.pdf"%(self.odir,chip),format='pdf',bbox_inches='tight') 

def pass_refined_criteria_pedestal(device_type): #Here device_type is only size and not index (for eg TB3_D8 and not TB3_D8_11)
    directory_out = "/home/hgcal/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/analysis/level0/Pass_criteria/%s_limits.yaml"%(device_type)
    print("File to be written to",directory_out)
    data = {}
    run_ped_list = ["run_20240523_185030","run_20240523_125208","run_20240523_125538","run_20240522_174021"]
    #run_ped_list = ["run_20240522_174021"]
    run_index = 0
    for directory in run_ped_list:
        ped_analyzer = overall_analyzer(odir=indir+ directory)
        files = glob.glob(indir+directory+"/pedestal_run*.root")
        print(files)
        for f in files:
            ped_analyzer.add(f)
        data[run_index] = pd.DataFrame()
        ped_analyzer.mergeData()   
        data[run_index] = ped_analyzer.data.copy()

        if run_index == 0:  
            nchip = len( data[run_index].groupby('chip').nunique() )
        elif run_index>1:
            if nchip != len( data[run_index].groupby('chip').nunique() ):
                print("Number of chips inconsistent across runs!")
            elif nchip == len( data[run_index].groupby('chip').nunique() ):   
                pass
        run_index+=1
    nestedConf = nested_dict() 

    df_net = {}

    for chip in range(nchip): #sort of assuming that the number of chips for all the runs are the same (which is reasonable because it is the same type of board)
        df_net[chip] = pd.DataFrame()
        run_id_chip = 0
        for directory in run_ped_list:
            data_chip = data[run_id_chip][ data[run_id_chip]['chip']==chip ].copy()

            if run_id_chip ==0:
                df_net[chip]['channel'] = data[run_id_chip]['channel']
                df_net[chip]['channeltype'] = data[run_id_chip]['channeltype']
            df_net[chip]['adc_mean_'+str(run_id_chip)] = data[run_id_chip]['adc_mean']
            df_net[chip]['adc_median_'+str(run_id_chip)] = data[run_id_chip]['adc_median']
            df_net[chip]['adc_stdd_'+str(run_id_chip)] = data[run_id_chip]['adc_stdd']
            run_id_chip+=1

        print(df_net[chip])
        df_net_half_0 = df_net[chip][(df_net[chip]['channel']<36) & (df_net[chip]['channeltype']==0)].copy()
        df_net_half_1 = df_net[chip][(df_net[chip]['channel']>=36) & (df_net[chip]['channeltype']==0)].copy()

        #for channel in range(len(df_net[chip])):
        #    if df_net[chip]['channeltype'] !=0:
        df_net[chip]['min_channel_ped'] = df_net[chip][['adc_median_0','adc_median_1','adc_median_2','adc_median_3']].min(axis=1)
        df_net[chip]['max_channel_ped'] = df_net[chip][['adc_median_0','adc_median_1','adc_median_2','adc_median_3']].max(axis=1)
        df_net[chip]['max_channel_noise'] = df_net[chip][['adc_stdd_0','adc_stdd_1','adc_stdd_2','adc_stdd_3']].max(axis=1)
        
        dict_spread = {}
        for run_id in range(len(run_ped_list)):

            dict_spread['min_half_0_'+str(run_id).format(run_id)] = df_net_half_0[df_net_half_0['adc_stdd_'+str(run_id)]>0]['adc_median_'+str(run_id)].min()
            dict_spread['max_half_0_'+str(run_id).format(run_id)] = df_net_half_0[df_net_half_0['adc_stdd_'+str(run_id)]>0]['adc_median_'+str(run_id)].max()
            dict_spread['min_half_1_'+str(run_id).format(run_id)] = df_net_half_1[df_net_half_1['adc_stdd_'+str(run_id)]>0]['adc_median_'+str(run_id)].min()
            dict_spread['max_half_1_'+str(run_id).format(run_id)] = df_net_half_1[df_net_half_1['adc_stdd_'+str(run_id)]>0]['adc_median_'+str(run_id)].max()

        print(dict_spread)
        print(df_net[chip])

        min_half_0_net = min(dict_spread['min_half_0_0'],dict_spread['min_half_0_1'],dict_spread['min_half_0_2'],dict_spread['min_half_0_3'])
        max_half_0_net = max(dict_spread['max_half_0_0'],dict_spread['max_half_0_1'],dict_spread['max_half_0_2'],dict_spread['max_half_0_3'])
        min_half_1_net = min(dict_spread['min_half_1_0'],dict_spread['min_half_1_1'],dict_spread['min_half_1_2'],dict_spread['min_half_1_3'])
        max_half_1_net = max(dict_spread['max_half_1_0'],dict_spread['max_half_1_1'],dict_spread['max_half_1_2'],dict_spread['max_half_1_3'])

        print(min_half_0_net,max_half_0_net,min_half_1_net,max_half_1_net)
        ch = pd.DataFrame()
        calib = pd.DataFrame()
        cm = pd.DataFrame()

        ch_array=[ch,calib,cm] #This seems like it is the whole series/dataframe
        ch_key_array = ['ch','calib','cm']
        channeltype_array = [0,1,100]
        
        for i in range(len(ch_array)):
            ch_array[i] = df_net[chip][ df_net[chip]['channeltype']==channeltype_array[i] ].copy()
            ch_array[i].set_index(ch_array[i]['channel'], inplace=True)
            print("Cut arrays")
            print(ch_array[i])
            #ch_median = pd.DataFrame([ch_array[i]['adc_median']])
            #ch_stddev = pd.DataFrame([ch_array[i]['adc_stdd']])
            #print(ch_array[i]['min_channel_ped'])
            for ch_loop in range(len(ch_array[i])):
                if ch_key_array[i] == 'ch':
                    if ch_loop <36:
                        nestedConf['pedestal_run']['roc_s'+str(chip)][ch_key_array[i]][ch_loop]['pedestal_lower'] = float(min_half_0_net)-10
                        nestedConf['pedestal_run']['roc_s'+str(chip)][ch_key_array[i]][ch_loop]['pedestal_upper'] = float(max_half_0_net)+10
                        
                    elif ch_loop >=36:
                        nestedConf['pedestal_run']['roc_s'+str(chip)][ch_key_array[i]][ch_loop]['pedestal_lower'] = float(min_half_1_net)-10
                        nestedConf['pedestal_run']['roc_s'+str(chip)][ch_key_array[i]][ch_loop]['pedestal_upper'] = float(max_half_1_net)+10
                        
                    nestedConf['pedestal_run']['roc_s'+str(chip)][ch_key_array[i]][ch_loop]['noise_lower'] = 0.2 #Should not be exactly 0 since that indicates a problem too        
                else:
                    nestedConf['pedestal_run']['roc_s'+str(chip)][ch_key_array[i]][ch_loop]['pedestal_lower'] = min(float(ch_array[i]['min_channel_ped'][ch_loop]),0)
                    nestedConf['pedestal_run']['roc_s'+str(chip)][ch_key_array[i]][ch_loop]['pedestal_upper'] = max(20,float(ch_array[i]['max_channel_ped'][ch_loop]))
                
                    nestedConf['pedestal_run']['roc_s'+str(chip)][ch_key_array[i]][ch_loop]['noise_lower'] = 0.0
                nestedConf['pedestal_run']['roc_s'+str(chip)][ch_key_array[i]][ch_loop]['noise_upper'] = max(3,float(ch_array[i]['max_channel_noise'][ch_loop]))

    print(nestedConf)
    #with open(directory_out,'w') as file:
    with open(directory_out,'r+') as file:
        print(yaml.dump(nestedConf.to_dict(),file,sort_keys=False))
        print("Written to yaml file")


if __name__ == "__main__":
    
    if len(sys.argv) == 3:
        indir = sys.argv[1]
        odir = sys.argv[2]
        
        ped_analyzer = overall_analyzer(odir=odir)
        files = glob.glob(indir+"/pedestal_run*.root")
        print(files)
        for f in files:
            ped_analyzer.add(f)

        ped_analyzer.mergeData()        
        ped_analyzer.pass_criteria_pedestal(device_type = "TB3_D8")    
        ped_analyzer.addSummary()
        ped_analyzer.writeSummary()
        
        #pass_refined_criteria_pedestal(device_type = "TB3_E8")    

        #ped_analyzer = pedestal_run_raw_analyzer(odir=odir, treename = 'unpacker_data/hgcroc')
        #why is this even needed here anyway?
        '''
        files = glob.glob(indir+"/pedestal_run*.root")
        print(files)
        for f in files:
            ped_analyzer.add(f)

        ped_analyzer.mergeData()
        ped_analyzer.makePlots()
        ped_analyzer.addSummary()
        ped_analyzer.writeSummary()
        '''

    else:
        print("No argument given")
           
   
