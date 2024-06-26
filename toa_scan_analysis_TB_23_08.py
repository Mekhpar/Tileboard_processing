from level0.analyzer import *
from scipy.optimize import curve_fit
import glob
import numpy as np
import scipy.optimize
from nested_dict import nested_dict
import pandas as pd

class toa_scan_analyzer(analyzer):

    def erfunc(self,z,a,b):
    	return b*scipy.special.erfc(z-a)

    def fit(self,x,y,p):
        try:
            args, cov = scipy.optimize.curve_fit(self.erfunc,x,y,p0=p)
            return args
        except:
            print("Fit cannot be found")
            return p

    def erfunc_trim(self,z,a,b):
        return b*scipy.special.erfc(a-z)

    def fit_trim(self,x,y,p):
        try:
            args, cov = scipy.optimize.curve_fit(self.erfunc_trim,x,y,p0 = p)
            return args
        except:
            print("Fit cannot be found")
            return p

    
    ### added May 2023, input from Jose: 
    
    def makePlot_calib(self,suffix="",config_ns_charge=None, thres=0.95):
        nchip = len( self.data.groupby('chip').nunique() )        
        data = self.data[['chip','channel','channeltype','Calib', 'gain', 'toa_efficiency','toa_stdd','injectedChannels']].copy()   # s added
        inj_chan =data.injectedChannels.unique()   # s added
        # inj_chan =data.injectedChannel.unique()
        # inj_chan=range(2)
        
        inj_chan = [0,30,42,46,36,66] #Small number for debugging
        print("inj_chan: ",inj_chan)

        if config_ns_charge != None:
            if config_ns_charge == 'fC':
                conv_val = 1000
            else:
                conv_val = 1
            data["charge"] = conv_val * ((1.6486* data['Calib'])/4095 + 0.0189)*((3*(1 - data["gain"])) + data["gain"]*120)


        for chip in range(nchip):
            # plt.figure(1)
            fig, axs = plt.subplots(2,2,figsize=(15,10),sharey = False,constrained_layout = True)
            min_charge = []
            channels_toa = []
            for chan in inj_chan:
                # chans= [chan,chan+18,chan+36,chan+36+18]
                #hans= [chan,chan+36]
                #for ch in chans:
                ch = chan
                ax = axs[0,0] if ch < 36 else axs[0,1]
                sel0 = data.chip == chip
                sel0 &= data.channel == ch
                sel0 &= data.channeltype == 0
                sel0 &= data.injectedChannels == chan    # s added
                sel0 &= data.toa_efficiency > thres
                df_sel0 = data[sel0]
                if len(df_sel0.toa_efficiency) > 0:
                    channels_toa = np.append(channels_toa,ch)
                    '''
                    if config_ns_charge != None:
                        min_charge = np.append(min_charge,np.min(df_sel0.charge))
                    else:
                        min_charge = np.append(min_charge,np.min(df_sel0.Calib_dac_2V5))
                    '''
                    min_charge = np.append(min_charge,np.min(df_sel0.Calib))
                sel = data.chip == chip
                sel &= data.channel == ch
                sel &= data.channeltype == 0
                sel &= data.injectedChannels == chan    # s added
                df_sel = data[sel]
                '''
                if config_ns_charge != None:
                    prof = df_sel.groupby("charge")["toa_efficiency"].sum()
                else:
                    prof = df_sel.groupby("Calib")["toa_efficiency"].sum()
                '''    
                prof = df_sel.groupby("Calib")["toa_efficiency"].sum()    
                
                '''
                if config_ns_charge != None:
                    print("Ch: ", ch)
                    ax.plot(df_sel.charge,df_sel.toa_efficiency,".-", label = "ch%i" %(ch))
                    # ax.plot(df_sel.charge,df_sel.toa_efficiency,".-")
                    ax.set_xlabel("charge [{}]".format(config_ns_charge))
                else:
                    ax.plot(df_sel.Calib,df_sel.toa_efficiency,".-", label = "ch%i" %(ch))
                    ax.set_xlabel("Calib")
                '''
                ax.plot(df_sel.Calib,df_sel.toa_efficiency,".-", label = "ch%i" %(ch))
                ax.set_xlabel("Calib")
                
                print("Channel number", ch)
                #print(df_sel.toa_efficiency)
                #Values to find the range of the turnover (non constant slope), this is similar to how the phase was found for calculating the rise and fall widths, or finding the fitting range of Vrefinv because it was not the whole range
                toa_chan_max = 0.8*df_sel.toa_efficiency.max()
                if df_sel.toa_efficiency.min() < 0.2*df_sel.toa_efficiency.max():
                    toa_chan_min = 0.1*df_sel.toa_efficiency.max()
                else:
                    toa_chan_min = 1.2*df_sel.toa_efficiency.min()
                
                print(toa_chan_max,toa_chan_min)
                cal_max_1 = df_sel[df_sel.toa_efficiency < toa_chan_max].Calib.max()
                cal_max_2 = df_sel[df_sel.toa_efficiency >= toa_chan_max].Calib.min()
                toa_max_1 = df_sel[df_sel.Calib == cal_max_1].toa_efficiency.values[0]
                toa_max_2 = df_sel[df_sel.Calib == cal_max_2].toa_efficiency.values[0]
                print("Max point of turnover", cal_max_1)
                #print("Min point of turnover", cal_min_1, cal_min_2)
                
                cal_min_1 = df_sel[df_sel.toa_efficiency <= toa_chan_min].Calib.max()
                cal_min_2 = df_sel[df_sel.toa_efficiency > toa_chan_min].Calib.min()
                toa_min_1 = df_sel[df_sel.Calib == cal_min_1].toa_efficiency.values[0]
                toa_min_2 = df_sel[df_sel.Calib == cal_min_2].toa_efficiency.values[0]
                
                print("Max point of turnover", cal_max_1, cal_max_2)
                print("Min point of turnover", cal_min_1, cal_min_2)
                print("Max point of turnover", toa_max_1, toa_max_2)
                print("Min point of turnover", toa_min_1, toa_min_2)

                toa_slope_max = (toa_max_2-toa_max_1)/(cal_max_2-cal_max_1)
                print(toa_slope_max)
                toa_max_final = cal_max_2 - (toa_max_2-toa_chan_max)/toa_slope_max
                print(toa_max_final)
                
                toa_slope_min = (toa_min_2-toa_min_1)/(cal_min_2-cal_min_1)
                print(toa_slope_min)
                toa_min_final = cal_min_2 - (toa_min_2-toa_chan_min)/toa_slope_min
                print(toa_min_final)
                
                turnover_point = (toa_max_final+toa_min_final)/2
                print("Final turnover point",turnover_point)
                print()
                
                ax.set_ylabel("toa eff")
                ax.legend(ncol=3, loc = "lower right",fontsize=8)
                ax.grid(True,"both","x")
                
                ax = axs[1,0] if ch < 36 else axs[1,1]
                '''
                if config_ns_charge != None:
                    ax.plot(df_sel.charge, df_sel.toa_stdd,".")
                    ax.set_xlabel("charge [{}]".format(config_ns_charge))
                else:
                    ax.plot(df_sel.Calib, df_sel.toa_stdd,".")
                    ax.set_xlabel("Calib")
                '''
                ax.plot(df_sel.Calib, df_sel.toa_stdd,".")
                ax.set_xlabel("Calib")

                ax.set_ylabel("toa noise")
                ax.grid(True,"both","x")    
            plt.savefig("%s/1_toa_vs_charge_chip%d_%s.png"%(self.odir,chip,suffix))

            plt.figure(figsize = (12,5),facecolor='white')

            plt.plot(channels_toa,min_charge,"o")
            
            if config_ns_charge != None:
                plt.ylabel("charge [{}]".format(config_ns_charge), fontsize = 30)
            else:
                plt.ylabel("Calib", fontsize = 30)
            plt.xlabel("Channels", fontsize = 30)
            plt.grid()
            plt.tick_params(axis='x', labelsize=28)
            plt.tick_params(axis='y', labelsize=28)
                    
            plt.savefig("%s/1_channel_vs_mintoa_thres%.2f_chip%d_%s.png"%(self.odir,thres,chip,suffix),bbox_inches='tight')
            calib_dac_min = np.mean(min_charge)

        return calib_dac_min   
        
   
    ### end Jose's input

    
    
    def makePlot(self,suffix=""):
        nchip = len( self.data.groupby('chip').nunique() )        
        data = self.data[['chip','channel','channeltype','half','Toa_vref', 'toa_efficiency','toa_stdd','injectedChannels']].copy()
        toa_vrefs = data.Toa_vref.unique()
        inj_chan =data.injectedChannels.unique()

        for chip in range(nchip):
            fig, axs = plt.subplots(2,2,figsize=(15,10),sharey = False,constrained_layout = True)
            for chan in inj_chan:
                chans= [chan,chan+18,chan+36,chan+36+18]
                for ch in chans:
                    ax = axs[0,0] if ch < 36 else axs[0,1]
                    sel = data.chip == chip
                    sel &= data.channel == ch
                    sel &= data.channeltype == 0
                    sel &= data.injectedChannels == chan
                    df_sel = data[sel]
                    prof = df_sel.groupby("Toa_vref")["toa_efficiency"].sum()
                    try:
                        args = int(df_sel[df_sel.toa_efficiency < 0.2].groupby("Toa_vref")["toa_efficiency"].sum().index.min()) ## plus simple
                    except:
                        continue
                    ax.plot(df_sel.Toa_vref,df_sel.toa_efficiency,".-", label = "ch%i (%i)" %(ch,args))
                    ax.set_ylabel("toa eff")
                    ax.set_xlabel("Toa_vref")
                    ax.legend(ncol=3, loc = "lower right",fontsize=8)

                    ax = axs[1,0] if ch < 36 else axs[1,1]
                    ax.plot(df_sel.Toa_vref, df_sel.toa_stdd,".")
                    ax.set_ylabel("toa noise")
            plt.savefig("%s/1_toa_thr_chip%d_%s.png"%(self.odir,chip,suffix))
            

    def makePlot_trim(self):
        nchip = len( self.data.groupby('chip').nunique() )        
        data = self.data[['chip','channel','channeltype','half','trim_toa','toa_efficiency','injectedChannels']].copy()

        trim_toas = data.trim_toa.unique()
        inj_chan =data.injectedChannels.unique()
        for chip in range(nchip):
            fig, axs = plt.subplots(1,2, figsize=(15,8))
            for chan in inj_chan:
                chans= [chan,chan+18,chan+36, chan+36+18]
                for ch in chans:
                    ax = axs[0] if ch < 36 else axs[1]
                    sel = data.chip == chip
                    sel &= data.channel == ch
                    sel &= data.channeltype == 0
                    sel &= data.injectedChannels == chan
                    df_sel = data[sel]
                    prof = df_sel.groupby("trim_toa")["toa_efficiency"].sum()
                    try:
                        args = int(df_sel[df_sel.toa_efficiency < 0.2].groupby("trim_toa")["toa_efficiency"].sum().index.max()) ## plus simple
                    except:
                        args = 0
                    ax.plot(prof.index,prof.values,".-",label="ch%i (%i)" %(ch,args))
                    ax.set_ylabel("toa eff")
                    ax.set_xlabel("trim_toa")
                    ax.legend(ncol=3,loc="lower right",fontsize=10)
            plt.savefig("%s/trim_toa_thr_chip%d.png"%(self.odir,chip))

    def determineToa_vref(self):
        inj_chan =self.data.injectedChannels.unique()
        nchip = len( self.data.groupby('chip').nunique() )
        data = self.data[['chip','channel','channeltype','Toa_vref', 'toa_efficiency','injectedChannels']].copy()
        nestedConf = nested_dict()
        
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
                mean_0 = []
                mean_1 = []
                for chan in inj_chan:
                    chans= [chan,chan+18,chan+36,chan+36+18]
                    for ch in chans:
                        sel = data.chip == chip
                        sel &= data.channel == ch
                        sel &= data.channeltype == 0
                        sel &= data.injectedChannels == chan
                        sel &= data.toa_efficiency < 0.2
                        df_sel = data[sel]
                        prof = df_sel.groupby("Toa_vref")["toa_efficiency"].sum()
                        try:
                            args = int(prof.index.min())  ### PLUS SIMPLE !!!!!!!!!
                        except:
                            continue
                        if ch < 36:
                            mean_0.append(args)
                        else:
                            mean_1.append(args)
                mean = int(1.0*sum(mean_0)/len(mean_0))
                print("Toa_Vref for half0 is %i" %mean)
                nestedConf[chip_key_name]['sc']['ReferenceVoltage'][int(0)] = { 'Toa_vref' : mean }
                mean = int(1.0*sum(mean_1)/len(mean_1))
                print("Toa_Vref for half1 is %i" %mean)
                nestedConf[chip_key_name]['sc']['ReferenceVoltage'][int(1)] = { 'Toa_vref' : mean }
            else :
                print("WARNING : optimised Toa_vref will not be saved for ROC %d"%(chip))
        return nestedConf

    def determineToa_trim(self):
        inj_chan =self.data.injectedChannels.unique()
        nchip = len( self.data.groupby('chip').nunique() )
        data = self.data[['chip','channel','channeltype','injectedChannels','trim_toa', 'toa_efficiency']].copy()
        yaml_dict = {}
        rockeys = []
        with open("%s/initial_full_config.yaml"%(self.odir)) as fin:
            initconfig = yaml.safe_load(fin)
            for key in initconfig.keys():
                if key.find('roc')==0:
                    rockeys.append(key)
            rockeys.sort()

        trim_toas = data.trim_toa.unique()
        for chip in range(nchip):
            if chip<len(rockeys):
                chip_key_name = rockeys[chip]
                yaml_dict[chip_key_name] = {
                'sc' : {
                'ch' : { 
                }
                }
                }
                for chan in inj_chan:
                    chans= [chan,chan+18,chan+36, chan+36+18]    
                    for ch in chans:
                        sel = data.chip == chip
                        sel &= data.channel == ch
                        sel &= data.channeltype == 0
                        sel &= data.injectedChannels == chan
                        sel &= data.toa_efficiency < 0.2
                        df_sel = data[sel]
                        prof = df_sel.groupby("trim_toa")["toa_efficiency"].sum()
                        try:
                            alpha = int(prof.index.max()) ## plus simple
                        except:
                            alpha = 0
                        if alpha < 0:
                            alpha = 0
                        elif alpha > 63:
                            alpha = 63
                        print()
                        print(ch,alpha)
                        yaml_dict[chip_key_name]['sc']['ch'][int(ch)] = { 'trim_toa' : int( alpha ) }
            else :
                print("WARNING : optimised trim_toa will not be saved for ROC %d"%(chip))
        print(yaml_dict)
        with open(self.odir+'/trimmed_toa.yaml','w') as fout:
                yaml.dump(yaml_dict,fout)

        return yaml_dict
        
    
    
    



if __name__ == "__main__":

    #if len(sys.argv) == 2:
        #indir = sys.argv[1]
        #odir = sys.argv[1]
    odir = "/home/hgcal/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/data/TB3/vreftoa_scurvescan/test_20240625_171153_/TB3_D8_11/"
    toa_threshold_analyzer = toa_scan_analyzer(odir=odir)
    
    folders = glob.glob(odir+"PreampInjection_scan_TB3_D8_11_*/")
    df_ = []
    for folder in folders:
        print("Current folder name", folder)        
        files = glob.glob(folder+"/injection_scan*.root")
        for f in files[:]:
            df_summary = uproot3.open(f)['runsummary']['summary'].pandas.df()
            df_.append(df_summary)
    toa_threshold_analyzer.data = pd.concat(df_)
    toa_threshold_analyzer.makePlot_calib(config_ns_charge='pC', thres=0.95)
    
    '''
    files = glob.glob(indir+"/toa_threshold_scan*.root")
    print(files)

    for f in files:
        toa_threshold_analyzer.add(f)

    toa_threshold_analyzer.mergeData()
    toa_threshold_analyzer.makePlots()
    '''
    #else:
    #    print("No argument given")
