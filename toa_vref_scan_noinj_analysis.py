from level0.analyzer import *
import argparse
import yaml
import glob

    
class toa_vref_scan_noinj_analyzer(analyzer):

    def makePlots(self):
        nchip = len( self.data.groupby('chip').nunique() )        
        cmap = cm.get_cmap('viridis')
        #sel_data = self.data[['chip','half','channel','channeltype','adc_stdd','toa_efficiency','Toa_vref']].copy()
        sel_data = self.data[['chip','channel','channeltype','adc_stdd','toa_efficiency','Toa_vref']].copy()
        unconnectedChannels=[8,17,18,27,
                             36+8,36+17,36+18,36+27]
        sel_data = sel_data[ ~sel_data['channel'].isin(unconnectedChannels) ]
        varlist = {
            'adc' : { 'name': 'adc_stdd', 'label' : 'Noise [ADC counts]' },
            'toa' : { 'name' : 'toa_efficiency', 'label' : 'ToA efficiency' }
        }

        for chip in sel_data.groupby('chip')['chip'].mean():
            chip_data = sel_data[ (sel_data['chip']==chip) & (sel_data['channeltype']==0) ]
            for var in varlist:
                fig, axes = plt.subplots(1,2,figsize=(16,9),sharey=True)
                axes[0].set_ylabel(varlist[var]['label'])
                for ax in axes:
                    ax.set_xlabel(r'TOA vref [DAC]')
                    ax.xaxis.grid(True)

                axes[0].set_title(f'chip{chip}, first half')
                axes[1].set_title(f'chip{chip}, second half')
                for channel in chip_data.groupby('channel')['channel'].mean():
                    data = chip_data.query( 'channel==%s'%(channel) ).sort_values('Toa_vref')
                    #half = int(data.groupby('half')['half'].mean())
                    # print(half)
#                    if half==0:
                    if channel<36:
                       ax=axes[0]
                    else:
                        ax=axes[1]
                    #ax.plot(data['Toa_vref'],data[varlist[var]['name']],marker='o',color=cmap((channel%36)/36.),label=r'Channel %d'%(channel))
                    ax.plot(data['Toa_vref'],data[varlist[var]['name']],marker='o',label=r'Channel %d'%(channel))
                for half in [0,1]:
                    h,l=axes[half].get_legend_handles_labels()
                    axes[half].legend(handles=h,labels=l,loc='upper right',ncol=2,fontsize=8)
                
                plt.savefig(f'{self.odir}/{var}_toa_vref_scan_chip{chip}.png', format='png', bbox_inches='tight') 
                plt.close()

        return
    
    def findVref(self):
        nchip = len( self.data.groupby('chip').nunique() )        

        sel_data = self.data[['chip','channel','channeltype','toa_efficiency','Toa_vref']].copy()
        sel_data = sel_data[ sel_data['channeltype']==0 ] # for simplification
        unconnectedChannels=[8,17,18,27,
                             36+8,36+17,36+18,36+27]
        sel_data = sel_data[ ~sel_data['channel'].isin(unconnectedChannels) ]

        rockeys = []
        with open("%s/initial_full_config.yaml"%(self.odir)) as fin:
            initconfig = yaml.safe_load(fin)
            for key in initconfig.keys():
                if key.find('roc')==0:
                    rockeys.append(key)
        rockeys.sort()
        yaml_dict={}
        for chip in sel_data.groupby('chip')['chip'].mean():
            # if chip+1<len(rockeys):
            #     chip_key_name = rockeys[chip+1]
            if chip<len(rockeys):
                chip_key_name = rockeys[chip]
            yaml_dict[chip_key_name] = {
                'sc' : {
                    'ReferenceVoltage' : { 
                    }
                }
            }
            vrefs={
                0 : { 'Toa_vref' : 0},
                1 : { 'Toa_vref' : 0}
            }
            chip_data = sel_data[ sel_data['chip']==chip ]
            for ch in chip_data.groupby('channel')['channel'].mean():
                df_chn = chip_data.query('channel==%s' % (ch)).sort_values('Toa_vref')
                #sel = df_chn['toa_efficiency']<0.1
                sel = df_chn['toa_efficiency']==0.0
                flat_eff = df_chn[sel]
                non_flat_eff = df_chn[~sel]
                #print(flat_eff)
                #print(non_flat_eff)
                if sel.any() and (~sel).any():
                    sel_after = flat_eff[flat_eff["Toa_vref"]>non_flat_eff["Toa_vref"].max()]
                    #print(sel_after)

                    cur_min = int(sel_after["Toa_vref"].min())
                    print("Channel number", ch)
                    print("Toa vref",cur_min)
                    print("Current value for max",vrefs[int(ch/36)]['Toa_vref'])
                    
                    vrefs[int(ch/36)]['Toa_vref'] = max(vrefs[int(ch/36)]['Toa_vref'],cur_min)
            ## Adding some margin !
            #Decided to add a fixed margin instead of taking the next zero eff entry because the toa vref value should not be dependent on the sampling rate
            vrefs[0]['Toa_vref'] = vrefs[0]['Toa_vref']+6
            vrefs[1]['Toa_vref'] = vrefs[1]['Toa_vref']+6

            print("Vref values")
            print(vrefs)
            yaml_dict[chip_key_name]['sc']['ReferenceVoltage']=vrefs
        with open(self.odir+'/toa_vref.yaml','w') as fout:
            yaml.dump(yaml_dict,fout)
        return yaml_dict
    

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    #parser.add_argument('-i', dest='indir', action='store',help='input directory with root files')
    parser.add_argument('-o', dest='odir', action='store',help='output directory with root files')
        
    args = parser.parse_args()
    #indir = args.indir
    odir = args.odir
    #if not odir:
    #    odir=indir
        
    ana = toa_vref_scan_noinj_analyzer(odir=odir)
    #files = glob.glob(indir+"/*.root")
    files = glob.glob(odir+"/*.root")
        
    for f in files:
        ana.add(f)
    ana.mergeData()

    ana.makePlots()
    ana.findVref()
    
