from level0.analyzer import *
from scipy.optimize import curve_fit
import glob
from matplotlib.ticker import AutoMinorLocator

class sampling_scan_analyzer(analyzer):
    
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
    
    def makePlots(self, injectedChannels):
        nchip = len( self.data.groupby('chip').nunique() )        
        cmap = cm.get_cmap('Dark2')

        inj_data = self.data[ (self.data['channeltype']==0) & (self.data['channel'].isin(injectedChannels)) ].copy()
        inj_data['time'] = inj_data.apply( lambda x: 25/16.0*(x.Phase+16*x.BX),axis=1 )
        for chip in self.data.groupby('chip')['chip'].mean():
            chanColor=0
            fig, ax = plt.subplots(1,1,figsize=(16,9))
            for injectedChannel in injectedChannels:
                sel_data = inj_data[ (inj_data['chip']==chip) & (inj_data['channel']==injectedChannel) ]
                sel_data = sel_data.sort_values(by=['time'],ignore_index=True)
                plt.plot( sel_data['time'], sel_data['adc_median'], color=cmap(chanColor), label=r'Channel %d'%(injectedChannel),marker='o')
                chanColor=chanColor+1

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
        indir = sys.argv[1]
        odir = sys.argv[2]
        sampling_analyzer = sampling_scan_analyzer(odir=odir)
        files = glob.glob(indir+"/sampling_scan*.root")
        print(files)
        
        for f in files:
            sampling_analyzer.add(f)

        injectedChannels=[11,30,46,66]
       
        sampling_analyzer.mergeData()
        sampling_analyzer.makePlots(injectedChannels)
        sampling_analyzer.addSummary(injectedChannels)
        sampling_analyzer.writeSummary()

    else:
        print("No argument given")
