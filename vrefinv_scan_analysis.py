from level0.analyzer import *
import glob
from matplotlib.ticker import MaxNLocator

class vrefinv_scan_analyzer(analyzer):

    def makePlots(self):
        cmap = cm.get_cmap('viridis')
        cmcmap = cm.get_cmap('Set1')
        nchip = len( self.data.groupby('chip').nunique() )        

        sel_data = self.data[['chip','channel','channeltype','adc_mean','adc_stdd','Inv_vref','half']].copy()
        for chip in range(nchip):
            ####################################
            ## let's plot pedestal vs inv vref: 
            ####################################
            data = sel_data[ sel_data['chip']==chip ]
       
            fig, axes = plt.subplots(1,2,figsize=(16,9),sharey=True)
            nhalf = data['half'].unique()
                        
            for half in nhalf:
                data_half = data[data['half']==half].copy()

                ax=axes[half]
                ax.xaxis.set_major_locator(MaxNLocator(6))
                ax.xaxis.grid(True)
                
                chan_data = data_half[ (data_half['channeltype']==0) ].copy()
                u, inv = np.unique(chan_data.channel.values, return_inverse=True)
                print("Argument for color")
                print(inv)
                for channel in chan_data['channel'].unique():
                    chan = chan_data[chan_data['channel'] == channel].copy()
                    #ax.scatter(chan['Inv_vref'], chan['adc_mean'], c=inv[channel], cmap=cmap)
                    ax.scatter(chan['Inv_vref'], chan['adc_mean'], cmap=cmap, label="Ch "+str(channel))
                ax.set_title('Half'+str(half))
                ax.set_xlabel(r'Inv vref ')
                ax.set_ylabel(r'Pedestal [ADC counts]')

                h,l=ax.get_legend_handles_labels()
                ax.legend(handles=h,labels=l,loc='upper right',ncol=2)


            plt.savefig("%s/pedestal_vs_vrefinv_chip%d.png"%(self.odir,chip),format='png',bbox_inches='tight') 
            plt.close()
            ####################################
            ## let's also plot noise vs inv vref: 
            ####################################

            fig, axes = plt.subplots(1,2,figsize=(16,9),sharey=True)
            ax=axes[0]
            data = sel_data[ sel_data['chip']==chip ]
            chan_data = data[ (data['channeltype']<=1) & (data['half']==0) ].copy()
            u, inv = np.unique(chan_data.channel.values, return_inverse=True)
            ax.scatter(chan_data['Inv_vref'], chan_data['adc_stdd'], c=inv, cmap=cmap)
            
            chan_data = data[ (data['channeltype']==100) & (data['half']==0) ].copy()
            u, inv = np.unique(chan_data.channel.values, return_inverse=True)
            ax.scatter(chan_data['Inv_vref'], chan_data['adc_stdd'], c=inv, cmap=cmcmap)

            ax.set_title('First half')
            ax.set_xlabel(r'Inv vref ')
            ax.set_ylabel(r'Pedestal [ADC counts]')

            ax=axes[1]
            chan_data = data[ (data['channeltype']<=1) & (data['half']==1) ].copy()
            u, inv = np.unique(chan_data.channel.values, return_inverse=True)
            ax.scatter(chan_data['Inv_vref'], chan_data['adc_stdd'], c=inv, cmap=cmap)
            
            chan_data = data[ (data['channeltype']==100) & (data['half']==1) ].copy()
            u, inv = np.unique(chan_data.channel.values, return_inverse=True)
            ax.scatter(chan_data['Inv_vref'], chan_data['adc_stdd'], c=inv, cmap=cmcmap)

            ax.set_title('Second half')
            ax.set_xlabel(r'Inv vref ')

            plt.savefig("%s/noise_vs_vrefinv_chip%d.png"%(self.odir,chip),format='png',bbox_inches='tight') 
            plt.close()

            # means = data[ data['channeltype']==0 ].groupby(['half','Inv_vref']).mean().reset_index()
            # fig, axes = plt.subplots(1,2,figsize=(16,9),sharey=True)
            # for half in range(2):
            #     ax=axes[half]
            #     half_data = means[ means['half']==half ]
            #     ax.scatter(half_data['Inv_vref'], half_data['adc_mean'], color='blue')
            
            #     xs, alpha, beta = self.fit( half_data, 'Inv_vref', 'adc_mean' )
            #     lin = lambda x : alpha*x + beta
            #     ax.plot(xs, lin(xs), color='red')
                
            #     ax.set_title('Half %d'%(half))
            #     ax.set_xlabel(r'Inv vref ')
            # axes[0].set_ylabel(r'Mean of channel pedestals [ADC counts]')
            # plt.savefig("%s/pedestal_vs_vrefinv_chip%d_all.png"%(self.odir,chip),format='png',bbox_inches='tight') 
            # plt.close()
            
    def fit(self, xy_df, x_name, y_name):
        df = xy_df.groupby(x_name)[y_name].mean().reset_index()  # preprocess df
        imax = df.index[df[y_name] < 0.95*df[y_name].max()].min()  # get index of rightmost maximum
        xs = df[(df[y_name] > 1.1*df[ df[y_name]>0 ][y_name].min()) & (df.index >= imax)][x_name]  # fit range
        if len(xs.to_list())>0:
            m, b = np.polyfit(xs.to_list(), df[ df[x_name].isin(xs.to_list()) ][y_name].to_list(), 1)
            return xs, m, b
        else:
            return xs,-1,-1

    def determine_bestVrefInv(self):
        nchip = len( self.data.groupby('chip').nunique() )
        data = self.data[['chip','channel','channeltype','adc_mean','adc_stdd','Inv_vref','half']].copy()
        sel = data.channel.isin([17,53])
        data = data[sel]
        yaml_dict={}
        
        rockeys = []
        with open("%s/initial_full_config.yaml"%(self.odir)) as fin:
            initconfig = yaml.safe_load(fin)
            for key in initconfig.keys():
                if key.find('roc')==0:
                    rockeys.append(key)
        rockeys.sort()
 
 
        for chip in range(nchip):
            if chip<len(rockeys):
                chip_key_name = rockeys[chip]
                yaml_dict[chip_key_name] = {
                    'sc' : {
                        'ReferenceVoltage' : { 
                        }
                    }
                }
                means = data[ (data['chip']==chip) & (data['channeltype']==0) & (data['Inv_vref']>200) ].groupby(['half','Inv_vref']).mean().reset_index()
                for half in range(2):
                    half_data = means[ means['half']==half ]
                    xs, alpha, beta = self.fit( half_data, 'Inv_vref', 'adc_mean' )
                    prof = half_data.groupby('Inv_vref')['adc_mean'].mean()
                    target = 300.0 #270.0 #50
                    # sel = abs(prof.values - target) < 10
                    # res = prof.index[sel][0]
                    if alpha!=-1 and beta!=-1:
                        yaml_dict[chip_key_name]['sc']['ReferenceVoltage'][half] = { 'Inv_vref' : int( (target-beta)/alpha ) }
                    # yaml_dict[chip_key_name]['sc']['ReferenceVoltage'][half] = { 'Inv_vref' : int(res)}
            else :
                print("WARNING : optimised Inv_vref will not be saved for ROC %d"%(chip))
 
        with open(self.odir+'/vrefinv.yaml','w') as fout:
            yaml.dump(yaml_dict,fout)

if __name__ == "__main__":

    if len(sys.argv) == 2:
        #indir = sys.argv[1]
        odir = sys.argv[1]

        vrefinv_analyzer = vrefinv_scan_analyzer(odir=odir)
        files = glob.glob(odir+"/*.root")
        print(files)

        for f in files:
            vrefinv_analyzer.add(f)

        vrefinv_analyzer.mergeData()
        vrefinv_analyzer.determine_bestVrefInv()
        vrefinv_analyzer.makePlots()

    else:
        print("No argument given")
        
