from level0.analyzer import *
from scipy.optimize import curve_fit
import glob
import numpy as np
import scipy.optimize
from nested_dict import nested_dict
import pandas as pd
#import miscellaneous_analysis_functions as analysis_misc

import analysis.level0.miscellaneous_analysis_functions as analysis_misc
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
    def get_turnover(self,df_sel):
        toa_chan_max = 0.8*df_sel.toa_efficiency.max()
        if df_sel.toa_efficiency.min() < 0.2*df_sel.toa_efficiency.max():
            toa_chan_min = 0.1*df_sel.toa_efficiency.max()
        else:
            toa_chan_min = 1.2*df_sel.toa_efficiency.min()
        
        cal_max_1 = df_sel[df_sel.toa_efficiency < toa_chan_max].Calib.max()
        cal_max_2 = df_sel[df_sel.toa_efficiency >= toa_chan_max].Calib.min()
        toa_max_1 = df_sel[df_sel.Calib == cal_max_1].toa_efficiency.values[0]
        toa_max_2 = df_sel[df_sel.Calib == cal_max_2].toa_efficiency.values[0]
        
        cal_min_1 = df_sel[df_sel.toa_efficiency <= toa_chan_min].Calib.max()
        cal_min_2 = df_sel[df_sel.toa_efficiency > toa_chan_min].Calib.min()
        toa_min_1 = df_sel[df_sel.Calib == cal_min_1].toa_efficiency.values[0]
        toa_min_2 = df_sel[df_sel.Calib == cal_min_2].toa_efficiency.values[0]
        '''
        print("Max point of turnover", cal_max_1, cal_max_2)
        print("Min point of turnover", cal_min_1, cal_min_2)
        print("Max point of turnover", toa_max_1, toa_max_2)
        print("Min point of turnover", toa_min_1, toa_min_2)
        '''
        toa_slope_max = (toa_max_2-toa_max_1)/(cal_max_2-cal_max_1)
        toa_max_final = cal_max_2 - (toa_max_2-toa_chan_max)/toa_slope_max
        #print(toa_max_final)
        
        toa_slope_min = (toa_min_2-toa_min_1)/(cal_min_2-cal_min_1)
        #print(toa_slope_min)
        toa_min_final = cal_min_2 - (toa_min_2-toa_chan_min)/toa_slope_min
        #print(toa_min_final)
        
        turnover_point = (toa_max_final+toa_min_final)/2
        #print("Final turnover point",turnover_point)
        #print()
        return turnover_point
    
    #Separate function that will be called for each channel for all trim toas because this is more convenient than having a 2D array
    
    def filter_bad_curves_turnover(self,df_sel,channel,trimtoa_dict,trimtoa_val):
        turn_pt_noise = -1 #Potentially to not be used for fitting purposes for each channel
        slope_factor = 1200 #1200 is a factor determined from png measurements and the limits of turnover will also be decided according to the scales in this png
        flag = 0            
        
        toa_noise_max = df_sel.toa_stdd.max()
        print("Max noise",toa_noise_max)
        print("Swing values", df_sel.toa_efficiency.max(),df_sel.toa_efficiency.min())
        
        if df_sel.toa_efficiency.max()-df_sel.toa_efficiency.min()<=0.3:
            print("Region too flat to find turnover point")
                    
        else:
            #Plot only if it is 'good' i.e. not flat

            for i in range(2,len(df_sel)):
                #slope = (df_sel['toa_efficiency'].values[i] - df_sel['toa_efficiency'].values[i-1])/(df_sel['Calib'].values[i] - df_sel['Calib'].values[i-1])
                
                y2 = df_sel['toa_efficiency'].values[i]
                y1 = df_sel['toa_efficiency'].values[i-1]
                x2 = df_sel['Calib'].values[i]
                x1 = df_sel['Calib'].values[i-1]
                
                y0 = df_sel['toa_efficiency'].values[i-2]
                x0 = df_sel['Calib'].values[i-2]
                
                slope = ((y2-y1)/(x2-x1))*slope_factor
                prev_slope = ((y1-y0)/(x1-x0))*slope_factor
                
                angle = np.arctan(slope)*180/3.14
                angle_prev = np.arctan(prev_slope)*180/3.14

                if (angle >=80) & (angle <=90) & (angle_prev >= -10) & (angle_prev <= angle): #potentially a turnover point
                    turn_pt_noise = x1
                    flag = 1
                    break
            
            print("Possible calib turnover", turn_pt_noise)
            prev_toa_max = -1
            for channel_key in trimtoa_dict.keys():
                #if channel_key.find("ch_"+str(channel))==0: 
                if channel_key == "ch_"+str(channel):
                #This means the channel has been populated already and there are previous (smaller) trimtoa values for which the turnovers can be compared with the current value
                    current_toa_key = ""
                    for trimtoa_key in trimtoa_dict[channel_key].keys():
                        if trimtoa_key.find("trim_toa_")==0:
                            trimtoa = int(analysis_misc.get_num_string(trimtoa_key,'trim_toa_'))
                            if trimtoa == trimtoa_val:
                                print("Current value has already been calculated, ignore this")
                            else:
                                if trimtoa_dict[channel_key][trimtoa_key] != -1:
                                    prev_toa_max = max(trimtoa,prev_toa_max) #Here also we are assuming going in ascending order
                                    current_toa_key = trimtoa_key
            
                    print("Current maximum of trimtoa values", prev_toa_max)
                    print("Corresponding key for previous max trimtoa value",current_toa_key)
                    if prev_toa_max!=-1:
                        if (trimtoa_val > prev_toa_max) & (turn_pt_noise < trimtoa_dict[channel_key][current_toa_key]):
                        #This is the case that is almost certainly likely to happen, because the glob.glob function returns the folder names in ‘lexicographic’ order by default, which means that it will be looping over ascending order of trimtoa values provided the folders are named correctly
                            pass
                        
                        else:
                            print("Curve has too many glitches to find turnover point")
                            turn_pt_noise = -1
                            flag = 0
                            
                #Since this above condition is already there, skipping the noise condition altogether since it is not very convenient to find a maxima and ensure that it is a true maximum in that region, and likely the noise will be quite large if the slope of the toa_eff/toa is large        
                
        return flag, turn_pt_noise
    

    def makePlot_calib(self,trimtoa_value,trimtoa_turnover:dict,suffix="",config_ns_charge=None, thres=0.95):
        nchip = len( self.data.groupby('chip').nunique() )        
        data = self.data[['chip','channel','channeltype','Calib', 'gain', 'toa_efficiency','toa_stdd','injectedChannels']].copy()   # s added
        inj_chan =data.injectedChannels.unique()   # s added
        # inj_chan =data.injectedChannel.unique()
        # inj_chan=range(2)
        
        #inj_chan = [6,12,23,28,54,56] #Small number for debugging
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
            #fig1, axs1 = plt.subplots(2,2,figsize=(15,10),sharey = False,constrained_layout = True)
            min_charge = []
            channels_toa = []
            for chan in inj_chan:
                # chans= [chan,chan+18,chan+36,chan+36+18]
                #hans= [chan,chan+36]
                #for ch in chans:
                ch = chan
                ax = axs[0,0] if ch < 36 else axs[0,1]
                #ax1 = axs1[0,0] if ch < 36 else axs1[0,1]
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
                #ax1.plot(df_sel.Calib,df_sel.toa_efficiency,".-", label = "ch%i" %(ch))
                #ax1.set_xlabel("Calib")
                
                print("Channel number", ch)
                #print(df_sel.toa_efficiency)
                #Values to find the range of the turnover (non constant slope), this is similar to how the phase was found for calculating the rise and fall widths, or finding the fitting range of Vrefinv because it was not the whole range
                #turn_pt = self.get_turnover(df_sel)
                #print("Turnover point from toa efficiency curves", turn_pt)
                
                #New and hopefully better turnover condition which relies on the noise of the toa rather than the toa efficiency value
                plt_flag, calib_turn = self.filter_bad_curves_turnover(df_sel,chan,trimtoa_turnover,trimtoa_value)
                print("Plotting flag",plt_flag)
                print("Turnover point at the beginning of the slope", calib_turn)
                print()

                trimtoa_turnover = analysis_misc.set_key_dict(trimtoa_turnover,['ch_'+str(chan)],['trim_toa_'+str(trimtoa_value)],[int(calib_turn)])
                if plt_flag == 1:
                    ax.plot(df_sel.Calib, df_sel.toa_efficiency,".-", label = "ch%i" %(ch))
                    ax.set_xlabel("Calib")
                
                ax.set_ylabel("toa eff")
                ax.legend(ncol=3, loc = "lower right",fontsize=8)
                ax.grid(True,"both","x")
                '''
                ax1.set_ylabel("toa eff")
                ax1.legend(ncol=3, loc = "lower right",fontsize=8)
                ax1.grid(True,"both","x")
                '''
                ax = axs[1,0] if ch < 36 else axs[1,1]
                #ax1 = axs1[1,0] if ch < 36 else axs1[1,1]
                '''
                if config_ns_charge != None:
                    ax.plot(df_sel.charge, df_sel.toa_stdd,".")
                    ax.set_xlabel("charge [{}]".format(config_ns_charge))
                else:
                    ax.plot(df_sel.Calib, df_sel.toa_stdd,".")
                    ax.set_xlabel("Calib")
                '''
                if plt_flag == 1:
                    ax.plot(df_sel.Calib, df_sel.toa_stdd,".")
                    ax.set_xlabel("Calib")

                #ax1.plot(df_sel.Calib, df_sel.toa_stdd,".")
                #ax1.set_xlabel("Calib")
                
                
                ax.set_ylabel("toa noise")
                ax.grid(True,"both","x")    

                #ax1.set_ylabel("toa noise")
                #ax1.grid(True,"both","x")    
            plt.savefig("%s/1_toa_vs_charge_filtered_chip%d_%s.png"%(self.odir,chip,suffix))

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

        return trimtoa_turnover   
        
   
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
        
def make_trimtoa_dict(odir_main): 
    trimtoa_folders = glob.glob(odir_main+"trim_toa_*/")
    trimtoa_turnover = dict()
    
    for odir in trimtoa_folders:
        print("Current trimtoa folder", odir)
        toa_threshold_analyzer = toa_scan_analyzer(odir=odir)
        
        trimtoa_value = int(analysis_misc.get_num_string(odir,'trim_toa_')) #Have to extract the value from the folder name since it is not stored in the root file in chip params
        print("Value of trimtoa for current folder", trimtoa_value)
        
        folders = glob.glob(odir+"PreampInjection_scan_*/")
        df_ = []
        for folder in folders:
            print("Current folder name", folder)        
            files = glob.glob(folder+"/injection_scan*.root")
            for f in files[:]:
                df_summary = uproot3.open(f)['runsummary']['summary'].pandas.df()
                df_.append(df_summary)
        toa_threshold_analyzer.data = pd.concat(df_)
        trimtoa_turnover = toa_threshold_analyzer.makePlot_calib(trimtoa_value,trimtoa_turnover,config_ns_charge='pC', thres=0.95)
        print()
        print()
        
    print("final dict")
    print(trimtoa_turnover)
    with open(odir_main+"trimtoa_turnover.yaml",'w') as file:
        yaml.dump(trimtoa_turnover,file,sort_keys=False)
        
    



if __name__ == "__main__":

    #if len(sys.argv) == 2:
        #indir = sys.argv[1]
        #odir = sys.argv[1]
        
    configFile = "/home/hgcal/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/configs/sipm_roc0_onbackup0_gainconv4_debug_D8_10_Vrefinv_Vreftoa.yaml"
    odir_main = "/home/hgcal/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/data/TB3_D8_10/vreftoa_scurvescan_3/"
    #make_trimtoa_dict(odir_main)
    #'''
    with open(configFile) as f:
        cfg = yaml.safe_load(f)

    try:
        with open(odir_main+"trimtoa_turnover.yaml",'r') as file:
            trimtoa_fits = yaml.safe_load(file)
                        
    except FileNotFoundError:
        make_trimtoa_dict(odir_main)
        with open(odir_main+"trimtoa_turnover.yaml",'r') as file:
            trimtoa_fits = yaml.safe_load(file)
                    
    print("channel keys", trimtoa_fits.keys())
    fig, axes = plt.subplots(1,2,figsize=(16,9),sharey=False)
    target_calib = 150
    for channel_key in trimtoa_fits.keys():
        if channel_key.find("ch_")==0:
            channel = int(analysis_misc.get_num_string(channel_key,'ch_'))
            print("Channel for threshold curve fitting",channel)
            
            ax = axes[0] if channel < 36 else axes[1]
            ax.set_ylabel(f'CalibDAC')
            ax.set_xlabel(r'trimtoa')
            ax.xaxis.grid(True)
            
            trimtoa_arr = []
            calib_arr = []
            for trimtoa_key in trimtoa_fits[channel_key].keys():
                if trimtoa_key.find("trim_toa_")==0:
                    trimtoa = int(analysis_misc.get_num_string(trimtoa_key,'trim_toa_'))
                    if trimtoa_fits[channel_key][trimtoa_key] != -1:
                        trimtoa_arr = np.append(trimtoa_arr,trimtoa)
                        calib_arr = np.append(calib_arr,trimtoa_fits[channel_key][trimtoa_key])
                    
            print("trimtoa values for fitting",trimtoa_arr)
            print("calib values for fitting",calib_arr)
        
        ax.scatter( trimtoa_arr, calib_arr,marker='o', label="Ch "+str(channel))
        
        #Default value
        for rocId in cfg.keys():
            if rocId.find('roc_s')==0:
                cfg[rocId]['sc']['ch'][channel]['trim_toa'] = 0
        
        if (len(trimtoa_arr) == len(calib_arr)) & (len(calib_arr)>1):
            slope_init = (calib_arr[0] - calib_arr[1])/(trimtoa_arr[0] - trimtoa_arr[1])
            popt, pcov = scipy.optimize.curve_fit(lambda x,a,b:a*x+b, trimtoa_arr, calib_arr, p0=[slope_init,calib_arr[0]])
            print("Slope and intercept",popt[0],popt[1])
            ax.plot(trimtoa_arr,popt[0]*trimtoa_arr+popt[1])
            
            trimtoa_target = int((target_calib-popt[1])/popt[0])
            if trimtoa_target < 0:
                trimtoa_target = 0
            elif trimtoa_target > 63:
                trimtoa_target = 63

            for rocId in cfg.keys():
                if rocId.find('roc_s')==0:
                    cfg[rocId]['sc']['ch'][channel]['trim_toa'] = trimtoa_target
            
            print("trim toa value to be written to yaml config file", trimtoa_target)
        else:
            print("Insufficient points for the fit!!")
            
        print()

        h, l = ax.get_legend_handles_labels()
        #ax.legend(handles, labels)
        #ax.legend(handles=h,labels=l,loc='lower left',ncol=3,fontsize=8,bbox_to_anchor=(0.3, -0.5))
        ax.legend(handles=h,labels=l,loc='upper right',ncol=3,fontsize=8)
    plt.savefig(f'{odir_main}/calib_trimtoa_linear_fit.png', format='png', bbox_inches='tight') 
            
    with open(configFile+"_trimtoa.yaml", "w") as o:
        yaml.dump(cfg, o)
    print("Saved new config file as:"+configFile+"_trimtoa.yaml")   
    '''    
    '''
    files = glob.glob(indir+"/toa_threshold_scan*.root")
    print(files)

    for f in files:
        toa_threshold_analyzer.add(f)

    toa_threshold_analyzer.mergeData()
    toa_threshold_analyzer.makePlots()
    #'''
    #else:
    #    print("No argument given")
