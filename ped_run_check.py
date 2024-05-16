from level0.analyzer import *
from scipy.optimize import curve_fit
import glob
import seaborn as sns
sns.set_style("ticks")
from matplotlib.ticker import MultipleLocator
import yaml, os
from nested_dict import nested_dict
import pandas as pd
import numpy as np

class ped_event_analyzer(rawroot_reader):
    #It is probably sufficient to check by half wise instead of channel wise
    def check_corruption(self):
        #print(self.df) #This looks like the data below (what we want with 10000 events for each channel)
        #data = self.df

        nchip = len( self.df.groupby('chip').nunique() )
        chip_goodness = []
        for chip in range(nchip):

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
                #corrpt.append((corrupted_events/total_events)*100.)
                corrupt_percentage = (corrupted_events/total_events)*100.
                
                corrpt.loc[half].half = half
                corrpt.loc[half].corrpt_percent = corrupt_percentage
                
            print(corrpt)
            pass_limit = 0.1
            fail_limit = 0.2
            #fail_limit = 100
            
            #Checking length of arrays after applying non corrupted/ corrupted cuts
            fail_half = corrpt[corrpt['corrpt_percent']>fail_limit].copy()
            pass_half = corrpt[corrpt['corrpt_percent']<=pass_limit].copy()
            grey_half = corrpt[corrpt['corrpt_percent']>pass_limit].copy()
            grey_half = grey_half[corrpt['corrpt_percent']<=fail_limit].copy()

            if len(fail_half) >=1:
                print("Chip failed to give good data")
                
            elif len(grey_half) >=1:
                print("Chip may or may not be great")
            
            elif len(pass_half) == nhalves:
                print("Chip is good")
                            
        #return chip_goodness
            
        '''
        nchannels = len( data.groupby('channel').nunique() )
        print("Half the Number of channels", nchannels)
        for channel_half in range(nchannels):
            data_channel = data[ data['channel']==channel_half].copy()
            #print("Channel number", channel_half)
            #print(data_channel)
            nhalves = len( data_channel.groupby('half').nunique() )
            for half in range(nhalves):
                data_channel_half = data_channel[ data_channel['half']==half].copy()
                print("Channel and half number", channel_half,half)
                #print(data_channel_half) #This is the set of events for each channel (separated)
                corrupted_events = len(data_channel_half[ data_channel_half['corruption']!=0])
                total_events = len(data_channel_half)
                print("Corrupted events and total number of events", corrupted_events,total_events)
        '''
class pedestal_run_analyzer(analyzer):
    #This is only a one time thing for a particular size of board
    def pass_criteria_pedestal(self,device_type): #Here device_type is only size and not index (for eg TB3_D8 and not TB3_D8_11)
        directory = "/home/reinecke/TBtesterv2_ROCv3_menu_Jia-Hao_copy/hexactrl-sw/hexactrl-script_Mar23TB/analysis/level0/Pass_criteria/%s_limits.yaml"%(device_type)
        nestedConf = nested_dict()
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
                
                ch_median = pd.DataFrame([ch_array[i]['adc_mean']])
                ch_stddev = pd.DataFrame([ch_array[i]['adc_stdd']])
                print(ch_median)
                print("Pedestal upper limit", ch_median.iloc[0,0] + 2*ch_stddev.iloc[0,0])
                print(type(ch_median.iloc[0,0] + 2*ch_stddev.iloc[0,0]))
                
                for ch in range(len(ch_array[i]['channel'])):
                    
                    #nestedConf['ch_array[i]'][ch]['pedestal_lower'] = ch_median.iloc[0,ch] - 2*ch_stddev.iloc[0,ch] #Do not use this!!
                    nestedConf[ch_key_array[i]][ch]['pedestal_lower'] = int(ch_median.iloc[0,ch] - 2*ch_stddev.iloc[0,ch])
                    nestedConf[ch_key_array[i]][ch]['pedestal_upper'] = int(ch_median.iloc[0,ch] + 2*ch_stddev.iloc[0,ch])+1
                    nestedConf[ch_key_array[i]][ch]['noise_lower'] = 0.2 #Should not be exactly 0 since that indicates a problem too
                    nestedConf[ch_key_array[i]][ch]['noise_upper'] = round(float(ch_stddev.iloc[0,ch]*1.5),2)
            
                with open(directory,'w') as file:
                    print(yaml.dump(nestedConf.to_dict(),file,sort_keys=False))
                    print("Written to yaml file")
                

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

if __name__ == "__main__":
    
    if len(sys.argv) == 3:
        indir = sys.argv[1]
        odir = sys.argv[2]

        ped_analyzer = pedestal_run_analyzer(odir=odir)
        files = glob.glob(indir+"/pedestal_run*.root")
        print(files)
        for f in files:
            ped_analyzer.add(f)

        ped_analyzer.mergeData()        
        ped_analyzer.pass_criteria_pedestal(device_type = "TB3_D8")    
        ped_analyzer.addSummary()
        ped_analyzer.writeSummary()
        
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
           
   
