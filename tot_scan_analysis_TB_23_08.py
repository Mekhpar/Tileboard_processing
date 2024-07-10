from level0.analyzer import *
from scipy.optimize import curve_fit
import glob
import numpy as np
import scipy.optimize
from nested_dict import nested_dict
#import miscellaneous_analysis_functions as analysis_misc
import copy

import analysis.level0.miscellaneous_analysis_functions as analysis_misc


class tot_scan_analyzer(analyzer):

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
        tot_chan_max = 0.8*df_sel.tot_efficiency.max()
        if df_sel.tot_efficiency.min() < 0.2*df_sel.tot_efficiency.max():
            tot_chan_min = 0.1*df_sel.tot_efficiency.max()
        else:
            tot_chan_min = 1.2*df_sel.tot_efficiency.min()
        
        cal_max_1 = df_sel[df_sel.tot_efficiency < tot_chan_max].Calib.max()
        cal_max_2 = df_sel[df_sel.tot_efficiency >= tot_chan_max].Calib.min()
        tot_max_1 = df_sel[df_sel.Calib == cal_max_1].tot_efficiency.values[0]
        tot_max_2 = df_sel[df_sel.Calib == cal_max_2].tot_efficiency.values[0]
        
        cal_min_1 = df_sel[df_sel.tot_efficiency <= tot_chan_min].Calib.max()
        cal_min_2 = df_sel[df_sel.tot_efficiency > tot_chan_min].Calib.min()
        tot_min_1 = df_sel[df_sel.Calib == cal_min_1].tot_efficiency.values[0]
        tot_min_2 = df_sel[df_sel.Calib == cal_min_2].tot_efficiency.values[0]
        '''
        print("Max point of turnover", cal_max_1, cal_max_2)
        print("Min point of turnover", cal_min_1, cal_min_2)
        print("Max point of turnover", tot_max_1, tot_max_2)
        print("Min point of turnover", tot_min_1, tot_min_2)
        '''
        tot_slope_max = (tot_max_2-tot_max_1)/(cal_max_2-cal_max_1)
        tot_max_final = cal_max_2 - (tot_max_2-tot_chan_max)/tot_slope_max
        #print(tot_max_final)
        
        tot_slope_min = (tot_min_2-tot_min_1)/(cal_min_2-cal_min_1)
        #print(tot_slope_min)
        tot_min_final = cal_min_2 - (tot_min_2-tot_chan_min)/tot_slope_min
        #print(tot_min_final)
        
        turnover_point = (tot_max_final+tot_min_final)/2
        #print("Final turnover point",turnover_point)
        #print()
        return turnover_point
    
    #Separate function that will be called for each channel for all trim tots because this is more convenient than having a 2D array
    def filter_bad_curves_turnover(self,df_sel,channel,trimtot_dict,trimtot_val,par_string):
        turn_pt_noise = -1 #Potentially to not be used for fitting purposes for each channel
        slope_factor = 1200 #1200 is a factor determined from png measurements and the limits of turnover will also be decided according to the scales in this png
        flag = 0            
        
        tot_noise_max = df_sel.tot_stdd.max()
        print("Max noise",tot_noise_max)
        print("Swing values", df_sel.tot_efficiency.max(),df_sel.tot_efficiency.min())
        
        if df_sel.tot_efficiency.max()-df_sel.tot_efficiency.min()<=0.3:
            print("Region too flat to find turnover point")
                    
        else:
            #Plot only if it is 'good' i.e. not flat

            for i in range(2,len(df_sel)):
                #slope = (df_sel['tot_efficiency'].values[i] - df_sel['tot_efficiency'].values[i-1])/(df_sel['Calib'].values[i] - df_sel['Calib'].values[i-1])
                
                y2 = df_sel['tot_efficiency'].values[i]
                y1 = df_sel['tot_efficiency'].values[i-1]
                x2 = df_sel['Calib'].values[i]
                x1 = df_sel['Calib'].values[i-1]
                
                y0 = df_sel['tot_efficiency'].values[i-2]
                x0 = df_sel['Calib'].values[i-2]
                
                slope = ((y2-y1)/(x2-x1))*slope_factor
                prev_slope = ((y1-y0)/(x1-x0))*slope_factor
                
                angle = np.arctan(slope)*180/3.14
                angle_prev = np.arctan(prev_slope)*180/3.14

                if (angle >=80) & (angle <=90) & (angle_prev >= -10) & (angle_prev <= angle): #potentially a turnover point
                    turn_pt_noise = x1
                    flag = 1
                    break
            
            prev_tot_max = -1
            if bool(trimtot_dict)== "True":
                for channel_key in trimtot_dict.keys():
                    #if channel_key.find(key_str+str(channel))==0: 
                    if channel_key == key_str+str(channel):
                    #This means the channel has been populated already and there are previous (smaller) trimtot values for which the turnovers can be compared with the current value
                        current_tot_key = ""
                        for trimtot_key in trimtot_dict[channel_key].keys():
                            if trimtot_key.find(par_string)==0:
                                trimtot = int(analysis_misc.get_num_string(trimtot_key,par_string))
                                if trimtot == trimtot_val:
                                    print("Current value has already been calculated, ignore this")
                                else:
                                    if trimtot_dict[channel_key][trimtot_key] != -1:
                                        prev_tot_max = max(trimtot,prev_tot_max) #Here also we are assuming going in ascending order
                                        current_tot_key = trimtot_key
                
                        print("Current maximum of trimtot values", prev_tot_max)
                        print("Corresponding key for previous max trimtot value",current_tot_key)
                        if prev_tot_max!=-1:
                            if (trimtot_val > prev_tot_max) & (turn_pt_noise < trimtot_dict[channel_key][current_tot_key]):
                            #This is the case that is almost certainly likely to happen, because the glob.glob function returns the folder names in ‘lexicographic’ order by default, which means that it will be looping over ascending order of trimtot values provided the folders are named correctly
                                pass
                            
                            else:
                                print("Curve has too many glitches to find turnover point")
                                turn_pt_noise = -1
                                flag = 0
                                
                    #Since this above condition is already there, skipping the noise condition altogether since it is not very convenient to find a maxima and ensure that it is a true maximum in that region, and likely the noise will be quite large if the slope of the tot_eff/tot is large        
                
        return flag, turn_pt_noise

    #Quick function made to use in the global tot alignment, set trimtot to some default value (0) because it is not relevant here
    #Remember to change the arguments in tot_threshold_scan_preamp (main data taking script consisting of 4 steps) as well
    def calc_turnover(self,trimtot_dict,trimtot_val,par_string):
        nchip = len( self.data_sum.groupby('chip').nunique() )        
        data = self.data_sum[['chip','channel','channeltype','Calib', 'gain', 'tot_efficiency','tot_stdd','injectedChannels']].copy()   # s added
        inj_chan =data.injectedChannels.unique()   # s added
        print("inj_chan: ",inj_chan)

        for chip in range(nchip):
            turn_0 = []
            turn_1 = []

            for chan in inj_chan:
                ch = chan
                #For the moment, calculating the average of turnover points in each half without considering the spread (i.e. assuming they are fairly well aligned channelwise)
                sel = data.chip == chip
                sel &= data.channel == ch
                sel &= data.channeltype == 0
                sel &= data.injectedChannels == chan    # s added
                df_sel = data[sel]

                plt_flag, calib_turn = self.filter_bad_curves_turnover(df_sel,chan,trimtot_dict,trimtot_val,par_string)
                if chan < 36:
                    turn_0 = np.append(turn_0,calib_turn)
                elif chan >=36:
                    turn_1 = np.append(turn_1,calib_turn)
                    
            print("Lengths of turn arrays", len(turn_0),len(turn_1))
            turn_avg_0 = np.mean(turn_0)
            turn_avg_1 = np.mean(turn_1)
            chan_0 = (np.abs(turn_0 - turn_avg_0)).argmin()
            chan_1 = (np.abs(turn_1 - turn_avg_1)).argmin() + 36
            
        return turn_avg_0,turn_avg_1, chan_0, chan_1                

    def makePlot_calib(self,trimtot_value,trimtot_turnover:dict,par_string,suffix="",config_ns_charge=None, thres=0.95):
        nchip = len( self.data.groupby('chip').nunique() )        
        data = self.data[['chip','channel','channeltype','Calib', 'gain', 'tot_efficiency','tot_stdd','injectedChannels']].copy()   # s added
        inj_chan =data.injectedChannels.unique()   # s added
        # inj_chan =data.injectedChannel.unique()
        # inj_chan=range(2)
        
        #inj_chan = [13,28,66] #Small number for debugging
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
            fig1, axs1 = plt.subplots(2,2,figsize=(15,10),sharey = False,constrained_layout = True)
            min_charge = []
            channels_tot = []
            for chan in inj_chan:
                # chans= [chan,chan+18,chan+36,chan+36+18]
                #hans= [chan,chan+36]
                #for ch in chans:
                ch = chan
                ax = axs[0,0] if ch < 36 else axs[0,1]
                ax1 = axs1[0,0] if ch < 36 else axs1[0,1]
                sel0 = data.chip == chip
                sel0 &= data.channel == ch
                sel0 &= data.channeltype == 0
                sel0 &= data.injectedChannels == chan    # s added
                sel0 &= data.tot_efficiency > thres
                df_sel0 = data[sel0]
                if len(df_sel0.tot_efficiency) > 0:
                    channels_tot = np.append(channels_tot,ch)
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
                    prof = df_sel.groupby("charge")["tot_efficiency"].sum()
                else:
                    prof = df_sel.groupby("Calib")["tot_efficiency"].sum()
                '''    
                prof = df_sel.groupby("Calib")["tot_efficiency"].sum()    
                
                '''
                if config_ns_charge != None:
                    print("Ch: ", ch)
                    ax.plot(df_sel.charge,df_sel.tot_efficiency,".-", label = "ch%i" %(ch))
                    # ax.plot(df_sel.charge,df_sel.tot_efficiency,".-")
                    ax.set_xlabel("charge [{}]".format(config_ns_charge))
                else:
                    ax.plot(df_sel.Calib,df_sel.tot_efficiency,".-", label = "ch%i" %(ch))
                    ax.set_xlabel("Calib")
                '''
                ax1.plot(df_sel.Calib,df_sel.tot_efficiency,".-", label = "ch%i" %(ch))
                ax1.set_xlabel("Calib")
                
                print("Channel number", ch)
                #print(df_sel.tot_efficiency)
                #Values to find the range of the turnover (non constant slope), this is similar to how the phase was found for calculating the rise and fall widths, or finding the fitting range of Vrefinv because it was not the whole range
                #turn_pt = self.get_turnover(df_sel)
                #print("Turnover point from tot efficiency curves", turn_pt)
                
                #New and hopefully better turnover condition which relies on the noise of the tot rather than the tot efficiency value
                chan_half = int(chan/36)
                if par_string == "Tot_vref_":
                    chan_arg = chan_half
                elif par_string == "trim_tot_":
                    chan_arg = chan
                plt_flag, calib_turn = self.filter_bad_curves_turnover(df_sel,chan_arg,trimtot_turnover,trimtot_value,par_string)
                print("Plotting flag",plt_flag)
                print("Turnover point at the beginning of the slope", calib_turn)
                print()

                trimtot_turnover = analysis_misc.set_key_dict(trimtot_turnover,[key_str+str(chan_arg)],[par_string + str(trimtot_value)],[int(calib_turn)])
                if plt_flag == 1:
                    ax.plot(df_sel.Calib, df_sel.tot_efficiency,".-", label = "ch%i" %(ch))
                    ax.set_xlabel("Calib")
                
                ax.set_ylabel("tot eff")
                ax.legend(ncol=3, loc = "lower right",fontsize=8)
                ax.grid(True,"both","x")
                #'''
                ax1.set_ylabel("tot eff")
                ax1.legend(ncol=3, loc = "lower right",fontsize=8)
                ax1.grid(True,"both","x")
                #'''
                ax = axs[1,0] if ch < 36 else axs[1,1]
                ax1 = axs1[1,0] if ch < 36 else axs1[1,1]
                '''
                if config_ns_charge != None:
                    ax.plot(df_sel.charge, df_sel.tot_stdd,".")
                    ax.set_xlabel("charge [{}]".format(config_ns_charge))
                else:
                    ax.plot(df_sel.Calib, df_sel.tot_stdd,".")
                    ax.set_xlabel("Calib")
                '''
                if plt_flag == 1:
                    ax.plot(df_sel.Calib, df_sel.tot_stdd,".")
                    ax.set_xlabel("Calib")

                ax1.plot(df_sel.Calib, df_sel.tot_stdd,".")
                ax1.set_xlabel("Calib")
                
                
                ax.set_ylabel("tot noise")
                ax.grid(True,"both","x")    

                ax1.set_ylabel("tot noise")
                ax1.grid(True,"both","x")    
            plt.savefig("%s/1_tot_vs_charge_chip%d_%s.png"%(self.odir,chip,suffix))

            plt.figure(figsize = (12,5),facecolor='white')

            plt.plot(channels_tot,min_charge,"o")
            
            if config_ns_charge != None:
                plt.ylabel("charge [{}]".format(config_ns_charge), fontsize = 30)
            else:
                plt.ylabel("Calib", fontsize = 30)
            plt.xlabel("Channels", fontsize = 30)
            plt.grid()
            plt.tick_params(axis='x', labelsize=28)
            plt.tick_params(axis='y', labelsize=28)
                    
            plt.savefig("%s/1_channel_vs_mintot_thres%.2f_chip%d_%s.png"%(self.odir,thres,chip,suffix),bbox_inches='tight')
            calib_dac_min = np.mean(min_charge)

        return trimtot_turnover   
    
    
    def makePlot_calib_for_MaxADC(self,adc_min=950,suffix=""):
        nchip = len( self.data.groupby('chip').nunique() )        
        #data = self.data[['chip','channel','half','channeltype','Calib', 'gain', 'adc','injectedChannels']].copy()
        data = self.data[['chip','channel','half','Calib', 'gain', 'adc','injectedChannels']].copy()
        inj_chan =data.injectedChannels.unique()

        for chip in range(nchip):
            # plt.figure(1)
            fig, axs = plt.subplots(2,2,figsize=(15,10),sharey = False,constrained_layout = True)
            min_calib = []
            channels_tot = []
            for chan in inj_chan:
                for half in range(2):
                    ax = axs[0,0] if half == 0 else axs[0,1]
                    # ax = axs[half]                   
                    sel = data.chip == chip
                    sel &= data.channel == chan
                    #sel &= data.channeltype == 0
                    sel &= data.half == half
                    sel &= data.injectedChannels == chan
                    sel &= data.adc >= adc_min
                    sel &= data.adc < 1023
                    df_sel = data[sel]
                    if len(df_sel.Calib) > 0:
                        channels_tot = np.append(channels_tot,chan+(36*half))
                        min_calib = np.append(min_calib,np.min(df_sel.Calib))
                    prof = df_sel.groupby("Calib")["adc"].std()
                    x_rms = prof.index
                    y_rms = prof.values
                    ax.plot(df_sel.Calib,df_sel.adc,".-", label = "ch%i" %(chan+(36*half)))
                    ax.set_xlabel("Calib dac 2V5")
                    ax.set_ylabel("ADC")
                    ax.legend(ncol=3, loc = "lower right",fontsize=8)

                    ax = axs[1,0] if half == 0 else axs[1,1]
                    ax.plot(x_rms, y_rms,".")
                    ax.set_xlabel("Calib dac 2V5")
                    ax.set_ylabel("ADC rms")
            
            calib_MaxADC = round(np.mean(min_calib))
            plt.savefig("%s/0_calib2V5_%i_vs_%iadc_chip%d_%s.png"%(self.odir,calib_MaxADC,adc_min,chip,suffix))

        return calib_MaxADC
        
        
    def makePlot(self,suffix="",preffix="1"):
        nchip = len( self.data.groupby('chip').nunique() )        
        if suffix == "noise":
            data = self.data[['chip','channel','Tot_vref','tot_efficiency','injectedChannels']].copy()
            data['half'] = data.apply(lambda x: 0 if x.channel<36 # first half 
                                    else 1, axis=1)
        else:
            data = self.data[['chip','channel','half', 'Tot_vref', 'tot','injectedChannels']].copy()
        tot_vrefs = data.Tot_vref.unique()
        inj_chan =data.injectedChannels.unique()
        halves = data.half.unique()
        for chip in range(nchip):
            fig, axs = plt.subplots(1,2,figsize=(15,10),sharey = False,constrained_layout = True)
            for chan in inj_chan:
                ch = chan
                for half in halves:
                    ax = axs[0] if half == 0 else axs[1]
                    sel = data.chip == chip
                    if suffix == "noise":
                        sel &= data.channel == ch+(36*half)
                    else:
                        sel &= data.channel == ch
                    sel &= data.half == half
                    sel &= data.injectedChannels == chan
                    if suffix == "noise":
                        sel &= data.tot_efficiency > 0
                    else:
                        sel &= data.tot > 0
                    df_sel = data[sel]
                    if suffix == "noise":
                        prof = df_sel.groupby("Tot_vref")["tot_efficiency"].median()
                    else:
                        prof = df_sel.groupby("Tot_vref")["tot"].median()
                    try:
                        args = int(prof.index.max()) #before min
                        # args = int(df_sel.Tot_vref.max()) #before min
                        # args = prof.index[np.argmin(prof.values)]
                    except:
                        continue
                    ax.plot(prof.index,prof.values,".-", label = "ch%i (%i)" %(ch+(36*half),args))
                    # ax.plot(df_sel.Tot_vref,df_sel.tot_median,".-", label = "ch%i (%i)" %(ch,args))
                    if suffix == "noise":
                        ax.set_ylabel("tot efficiency")
                    else:
                        ax.set_ylabel("tot")
                    ax.set_xlabel("Tot_vref")
                    ax.legend(ncol=3, loc = "lower right",fontsize=8)
                            
            plt.savefig("%s/%s_tot_thr_chip%d_%s.png"%(self.odir,preffix,chip,suffix))

    def determineTot_vref(self,suffix="",correction_totvref=0):
        nchip = len( self.data.groupby('chip').nunique() )
        if suffix == "noise":
            data = self.data[['chip','channel','Tot_vref','tot_efficiency','injectedChannels']].copy()
            data['half'] = data.apply(lambda x: 0 if x.channel<36 # first half 
                                    else 1, axis=1)
        else:
            data = self.data[['chip','channel','half', 'Tot_vref', 'tot','injectedChannels']].copy()
        inj_chan =self.data.injectedChannels.unique()
        halves = data.half.unique()
        nestedConf = nested_dict()
        yaml_dict = {}
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
                mean_0 = []
                mean_1 = []
                for chan in inj_chan:
                    for half in halves:
                        sel = data.chip == chip
                        if suffix == "noise":
                            sel &= data.channel == chan + (36*half)
                            sel &= data.tot_efficiency > 0
                        else:
                            sel &= data.tot > 0 # before 400
                            sel &= data.channel == chan
                        sel &= data.half == half
                        sel &= data.injectedChannels == chan
                        df_sel = data[sel]
                        if suffix == "noise":
                            prof = df_sel.groupby("Tot_vref")["tot_efficiency"].sum()
                            tot_efficiency_max = prof.values.max()
                            sel &= data.tot_efficiency == tot_efficiency_max
                            df_sel = data[sel]
                            prof = df_sel.groupby("Tot_vref")["tot_efficiency"].sum()
                        else:
                            prof = df_sel.groupby("Tot_vref")["tot"].median()
                        try:
                            args = int(prof.index.max()) #before min
                            # args = prof.index[np.argmin(prof.values)]
                        except:
                            args = 500
                            continue
                        # if ch < 36:
                        if half == 0:
                            mean_0.append(args)
                        else:
                            mean_1.append(args)
                if len(mean_0)>0:
                    mean = int(1.0*sum(mean_0)/len(mean_0))
                    print("Tot_Vref for half0 is %i" %mean)
                    yaml_dict[chip_key_name]['sc']['ReferenceVoltage'][0] = { 'Tot_vref' : mean - correction_totvref }
                    nestedConf[chip_key_name]['sc']['ReferenceVoltage'][0] = { 'Tot_vref' : mean - correction_totvref}
                else:
                    print("WARNING : optimised Tot_vref will not be saved for half 0 of ROC %d"%(chip))
                if len(mean_1)>0:
                    mean = int(1.0*sum(mean_1)/len(mean_1))
                    print("Tot_Vref for half1 is %i" %mean)
                    yaml_dict[chip_key_name]['sc']['ReferenceVoltage'][1] = { 'Tot_vref' : mean - correction_totvref}
                    nestedConf[chip_key_name]['sc']['ReferenceVoltage'][1] = { 'Tot_vref' : mean - correction_totvref}
                else:
                    print("WARNING : optimised Tot_vref will not be saved for half 1 of ROC %d"%(chip))
            else :
                print("WARNING : optimised Tot_vref will not be saved for ROC %d"%(chip))

        if suffix == "noise":
            with open(self.odir+'/tot_vref_noise+{}.yaml'.format(correction_totvref),'w') as fout:
                yaml.dump(yaml_dict,fout)
        else:
            with open(self.odir+'/tot_vref.yaml','w') as fout:
                yaml.dump(yaml_dict,fout)

        return nestedConf

    def makePlot_trim(self, preffix="2"):
        nchip = len( self.data.groupby('chip').nunique() )        
        data = self.data[['chip','channel', 'half','trim_tot','tot','injectedChannels']].copy()
        trim_tots = data.trim_tot.unique()
        inj_chan =data.injectedChannels.unique()
        halves = data.half.unique()
        for chip in range(nchip):
            fig, axs = plt.subplots(1,2, figsize=(15,8))
            for chan in inj_chan:
                for half in halves:
                    ax = axs[0] if half == 0 else axs[1]
                    sel = data.chip == chip
                    sel &= data.channel == chan
                    sel &= data.half == half
                    sel &= data.injectedChannels == chan
                    sel &= data.tot > 0
                    df_sel = data[sel]
                    prof = df_sel.groupby("trim_tot")["tot"].median()
                    try:
                        args = int(prof.index.min()) #before min
                        # args = prof.index[np.max(np.where(prof.values==-1))]  ########## new unpacker !!!!!!!!!!!!
                        success = 1
                    except:
                        args = 0
                        success = 0
                    ax.plot(prof.index,prof.values,".-",label="ch%i (%i, %i)" %(chan+(36*half),args,success))
                    ax.set_ylabel("tot")
                    ax.set_xlabel("trim_tot")
                    ax.legend(ncol=3,loc="lower right",fontsize=10)
            plt.savefig("%s/%s_trim_tot_thr_chip%d.png"%(self.odir,preffix,chip))
    
    def determineTot_trim(self,correction_tottrim=0):
        nchip = len( self.data.groupby('chip').nunique() )
        print("Main dataframe")
        print(self.data)
        
        #data = self.data[['chip','channel', 'half', 'injectedChannels','trim_tot', 'tot']].copy()
        data = self.data[['chip','channel', 'half', 'injectedChannels','trim_tot', 'tot_median']].copy()
        inj_chan =self.data.injectedChannels.unique()
        halves = data.half.unique()
        yaml_dict = {}
        rockeys = []
        with open("%s/initial_full_config.yaml"%(self.odir)) as fin:
            initconfig = yaml.safe_load(fin)
            for key in initconfig.keys():
                if key.find('roc')==0:
                    rockeys.append(key)
            rockeys.sort()

        trim_tots = data.trim_tot.unique()
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
                    for half in halves:
                        sel = data.chip == chip
                        sel &= data.channel == chan
                        sel &= data.half == half
                        sel &= data.injectedChannels == chan
                        #sel &= data.tot > 0 #before min
                        sel &= data.tot_median > 0 #before min
                        
                        df_sel = data[sel]
                        print(df_sel)
                        prof = df_sel.groupby("trim_tot")["tot_median"].median()
                        try:
                            # alpha = prof.index[np.max(np.where(prof.values==-1))] ############# new unpacker !!!!!!!!!!!
                            alpha = int(prof.index.min()) + correction_tottrim  ###, PLUS SIMPLE !!!!!!!!!
                            print("Channel number",chan)
                            print("Trim tot value optimized",alpha)
                        except:
                            alpha = 0
                        if alpha < 0:
                            alpha = 0
                        elif alpha > 63:
                            alpha = 63
                        print(chan,alpha)
                        yaml_dict[chip_key_name]['sc']['ch'][int(chan+(36*half))] = { 'trim_tot' : int( alpha ) }
                        # yaml_dict[chip_key_name]['sc']['ch'][int(ch)] = { 'trim_tot' : int( alpha ) }
            else :
                print("WARNING : optimised trim_tot will not be saved for ROC %d"%(chip))
        print(yaml_dict)
        with open(self.odir+'/trimmed_tot.yaml','w') as fout:
                yaml.dump(yaml_dict,fout)

        return yaml_dict
        
    '''
    def makePlot_calib(self,NEvents=500,suffix="",config_ns_charge=None):
        nchip = len( self.data.groupby('chip').nunique() )        
        data = self.data[['chip','channel','half','Calib', 'gain', 'tot','injectedChannels']].copy()
        Calib_dac_2V5s = data.Calib.unique()
        halves = data.half.unique()
        gain_val = data.gain.unique()
        inj_chan =data.injectedChannels.unique()
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
            channels_tot = []
            for chan in inj_chan:
                ch = chan
                for half in halves:
                    calib_vals = []
                    tot_counts = []
                    tot_std = []
                    save_min_charge = 0
                    ax = axs[0,0] if half==0 else axs[0,1]
                    for calib_val in Calib_dac_2V5s:
                        charge_val = conv_val * ((1.6486* calib_val)/4095 + 0.0189)*((3*(1 - gain_val[0])) + gain_val[0]*120)
                        sel = data.chip == chip
                        sel &= data.channel == ch
                        sel &= data.half == half
                        sel &= data.injectedChannels == chan
                        sel &= data.Calib == calib_val
                        sel &= data.tot > 0
                        df_sel = data[sel]
                        df_sel_noise = data[sel]
                        prof = df_sel.groupby("Calib")["tot"].std()
                        if config_ns_charge == None:
                            calib_vals = np.append(calib_vals,calib_val)
                        else:
                            calib_vals = np.append(calib_vals,charge_val)
                        if len(df_sel.tot) > 0:
                            tot_counts = np.append(tot_counts,len(df_sel.tot))
                        else:
                            tot_counts = np.append(tot_counts,0)
                        if len(df_sel_noise.tot) > 0:
                            # tot_std = np.append(tot_std,np.mean(df_sel_noise.tot_stdd))
                            tot_std = np.append(tot_std,np.mean(prof.values))
                        else:
                            tot_std = np.append(tot_std,0)
                        if len(df_sel.tot) > NEvents and save_min_charge == 0: #Before len tot > 0 (For 1000 events)
                            channels_tot = np.append(channels_tot,ch+(36*half))
                            if config_ns_charge != None:
                                min_charge = np.append(min_charge,np.min(df_sel.charge.unique()))
                            else:
                                min_charge = np.append(min_charge,np.min(df_sel.calib_val))
                            save_min_charge = 1
                    ax.plot(calib_vals,tot_counts,".-", label = "ch%i" %(ch+(36*half)))
                    if config_ns_charge != None:
                        ax.set_xlabel("charge [{}]".format(config_ns_charge))
                    else:
                        ax.set_xlabel("Calib dac 2V5")
                    ax.set_ylabel("tot counts")
                    ax.legend(ncol=3, loc = "lower right",fontsize=8)

                    ax = axs[1,0] if half==0 else axs[1,1]
                    ax.plot(calib_vals, tot_std,".")
                    if config_ns_charge != None:
                        ax.set_xlabel("charge [{}]".format(config_ns_charge))
                    else:
                        ax.set_xlabel("Calib dac 2V5")
                    ax.set_ylabel("tot noise")
                    
            plt.savefig("%s/4_tot_vs_charge_chip%d_%s.png"%(self.odir,chip,suffix))

            # plt.figure(2)
            plt.figure(figsize = (12,5),facecolor='white')
            plt.plot(channels_tot,min_charge,"o")
            
            if config_ns_charge != None:
                plt.ylabel("charge [{}]".format(config_ns_charge), fontsize = 30)
            else:
                plt.ylabel("Calib dac 2V5", fontsize = 30)
            plt.xlabel("Channels", fontsize = 30)
            plt.grid()
            plt.tick_params(axis='x', labelsize=28)
            plt.tick_params(axis='y', labelsize=28)
                    
            plt.savefig("%s/4_channel_vs_mintot_chip%d_%s.png"%(self.odir,chip,suffix),bbox_inches='tight')
            calib_dac_min = np.mean(min_charge)

        return calib_dac_min
    '''
    ### end Jose's input

def make_trimtot_dict(odir_main,par_string): 
    trimtot_folders = glob.glob(odir_main + par_string + "*/")
    trimtot_turnover = dict()
    
    for odir in trimtot_folders:
        print("Current trimtot folder", odir)
        tot_threshold_analyzer = tot_scan_analyzer(odir=odir)
        
        trimtot_value = int(analysis_misc.get_num_string(odir,par_string)) #Have to extract the value from the folder name since it is not stored in the root file in chip params
        print("Value of trimtot for current folder", trimtot_value)
        
        folders = glob.glob(odir+"PreampInjection_scan_*/")
        df_ = []
        for folder in folders:
            print("Current folder name", folder)        
            files = glob.glob(folder+"/injection_scan*.root")
            for f in files[:]:
                df_summary = uproot3.open(f)['runsummary']['summary'].pandas.df()
                df_.append(df_summary)
        tot_threshold_analyzer.data = pd.concat(df_)
        trimtot_turnover = tot_threshold_analyzer.makePlot_calib(trimtot_value,trimtot_turnover,par_string,config_ns_charge='pC', thres=0.95)
        print()
        print()
        
    print("final dict")
    print(trimtot_turnover)
    trimtot_final = copy.deepcopy(trimtot_turnover)
    print(trimtot_final)
    with open(odir_main + par_string + "turnover.yaml",'w') as file:
        print(yaml.dump(trimtot_final,file,sort_keys=False))


if __name__ == "__main__":

    configFile = "/home/hgcal/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/configs/sipm_roc0_onbackup0_gainconv4_debug_D8_10_Vrefinv_Vreftoa_trimtoa_Vreftot.yaml"

    #odir = "/home/hgcal/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/data/TB3/tot_threshold_scan/run_20240701_105613/2_chan_0/"
    #odir_main = "/home/hgcal/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/data/TB3_D8_10/vreftot_scurvescan_4/"
    odir_main = "/home/hgcal/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/data/TB3_D8_10/global_tot_scurvescan_6/"
    odir = "/home/hgcal/Desktop/Tileboard_DAQ_GitLab_version_2024/DAQ_transactor_new/hexactrl-sw/hexactrl-script/data/TB3_D8_10/vreftot_scurvescan_4/trim_tot_32/"

    #parameter_string = "trim_tot"
    parameter_string = "Tot_vref"
    par_str = parameter_string+"_"
    key_string = "half"
    key_str = key_string+"_"
    with open(configFile) as f:
        cfg = yaml.safe_load(f)
    try:
        with open(odir_main + par_str + "turnover.yaml",'r') as file:
            trimtot_fits = yaml.safe_load(file)
                        
    except FileNotFoundError:
        make_trimtot_dict(odir_main,par_str)
        with open(odir_main + par_str + "turnover.yaml",'r') as file:
            trimtot_fits = yaml.safe_load(file)

    print("channel keys", trimtot_fits.keys())
    fig, axes = plt.subplots(1,2,figsize=(20,15),sharey=False)
    
    #No hard target since global tot alignment has not been done at this stage
    if par_str == "Tot_vref_":
        target_calib = 380
        max_value = 1023
    elif par_str == "trim_tot_":
        target_calib_array = []
        for channel_key in trimtot_fits.keys():
            if channel_key.find(key_str)==0:
                for trimtot_key in trimtot_fits[channel_key].keys():
                    if trimtot_key.find(par_str)==0:
                        trimtot = int(analysis_misc.get_num_string(trimtot_key,par_str))
                        if (trimtot == 32) & (trimtot_fits[channel_key][trimtot_key] != -1):
                            target_calib_array = np.append(target_calib_array,trimtot_fits[channel_key][trimtot_key])
                            
        target_calib = np.median(target_calib_array)
        print("Length of number of points for target",len(target_calib_array))
        max_value = 63
    print("Target calib", target_calib)
    
    for channel_key in trimtot_fits.keys():
        if channel_key.find(key_str)==0:
            channel = int(analysis_misc.get_num_string(channel_key,key_str))
            print("Channel for threshold curve fitting",channel)
            if par_str == "Tot_vref_":
                ax = axes[0] if channel < 1 else axes[1]
                label_ch = "Half "+str(channel)
            elif par_str == "trim_tot_":
                ax = axes[0] if channel < 36 else axes[1]
                label_ch = "Ch "+str(channel)
            ax.set_ylabel(f'CalibDAC')
            ax.set_xlabel(parameter_string)
            ax.xaxis.grid(True)
            
            trimtot_arr = []
            calib_arr = []
            for trimtot_key in trimtot_fits[channel_key].keys():
                if trimtot_key.find(par_str)==0:
                    trimtot = int(analysis_misc.get_num_string(trimtot_key,par_str))
                    if trimtot_fits[channel_key][trimtot_key] != -1:
                        trimtot_arr = np.append(trimtot_arr,trimtot)
                        calib_arr = np.append(calib_arr,trimtot_fits[channel_key][trimtot_key])
                    
            print("trimtot values for fitting",trimtot_arr)
            print("calib values for fitting",calib_arr)
        
        ax.scatter( trimtot_arr, calib_arr,marker='o', label=label_ch)
        
        #Default value
        for rocId in cfg.keys():
            if rocId.find('roc_s')==0:
                cfg[rocId]['sc']['ch'][channel][parameter_string] = 0
        

        min_value = 0
        
        if (len(trimtot_arr) == len(calib_arr)) & (len(calib_arr)>1):
            slope_init = (calib_arr[0] - calib_arr[1])/(trimtot_arr[0] - trimtot_arr[1])
            popt, pcov = scipy.optimize.curve_fit(lambda x,a,b:a*x+b, trimtot_arr, calib_arr, p0=[slope_init,calib_arr[0]])
            print("Slope and intercept",popt[0],popt[1])
            ax.plot(trimtot_arr,popt[0]*trimtot_arr+popt[1])
            
            trimtot_target = int((target_calib-popt[1])/popt[0])
            if trimtot_target < min_value:
                trimtot_target = min_value
            elif trimtot_target > max_value:
                trimtot_target = max_value

            for rocId in cfg.keys():
                if rocId.find('roc_s')==0:
                    cfg[rocId]['sc']['ch'][channel][parameter_string] = trimtot_target
            
            print("trim tot value to be written to yaml config file", trimtot_target)
        else:
            print("Insufficient points for the fit!!")
            
        print()

        h, l = ax.get_legend_handles_labels()
        #ax.legend(handles, labels)
        #ax.legend(handles=h,labels=l,loc='lower left',ncol=3,fontsize=8,bbox_to_anchor=(0.3, -0.5))
        ax.legend(handles=h,labels=l,loc='upper right',ncol=3,fontsize=8)
    plt.savefig(f'{odir_main}/calib_trimtot_linear_fit.png', format='png', bbox_inches='tight') 
            
    with open(configFile+"_trimtot.yaml", "w") as o:
        yaml.dump(cfg, o)
    print("Saved new config file as:"+configFile+"_trimtot.yaml")   

    #tot_threshold_analyzer = tot_scan_analyzer(odir=odir)
    #trimtot_turnover = dict()
    '''
    files = glob.glob(odir+"/tot_trim_scan*.root")
    print(files)

    for f in files:
        tot_threshold_analyzer.add(f)
    
    tot_threshold_analyzer.mergeData()
    '''
    #tot_threshold_analyzer.makePlots()
    #tot_threshold_analyzer.determineTot_trim(correction_tottrim=0)
    
    '''
    folders = glob.glob(odir+"PreampInjection_scan_*/")
    df_ = []
    for folder in folders:
        print("Current folder name", folder)        
        files = glob.glob(folder+"/injection_scan*.root")
        for f in files[:]:
            df_summary = uproot3.open(f)['runsummary']['summary'].pandas.df()
            df_.append(df_summary)
    tot_threshold_analyzer.data = pd.concat(df_)
    trimtot_value = 0
    tot_threshold_analyzer.makePlot_calib(trimtot_value,trimtot_turnover,config_ns_charge='pC',thres=0.95)
    '''

    '''
    if len(sys.argv) == 3:
        indir = sys.argv[1]
        odir = sys.argv[2]

        tot_threshold_analyzer = tot_threshold_scan_analyzer(odir=odir)
        files = glob.glob(indir+"/tot_threshold_scan*.root")
        print(files)

        for f in files:
            tot_threshold_analyzer.add(f)

        tot_threshold_analyzer.mergeData()
        tot_threshold_analyzer.makePlots()

    else:
        print("No argument given")
    '''
