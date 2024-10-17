import zmq, datetime,  os, subprocess, sys, yaml, glob, math
from time import sleep
import myinotifier,util
import analysis.level0.pedestal_scan_analysis as analyzer
import zmq_controler as zmqctrl
from nested_dict import nested_dict
import uproot
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sb
import miscellaneous_functions as misc_func
from scipy.optimize import curve_fit

#import miscellaneous_analysis_functions as analysis_misc
import analysis.level0.miscellaneous_analysis_functions as analysis_misc

def make_plots(channel,configFile, odir, ped_analyzer): #Heat map, here there will be only one channel per plot (the shape is expected to be pretty much the same for all channels anyway)
    #expandAllChannels.expandAllChannels(configFile,output)
    nestedConf = nested_dict()
    with open(configFile) as f:
        cfg = yaml.safe_load(f)
    
    trim_dacb_fit_total = pd.DataFrame()
    trim_dacb_initial = pd.DataFrame()
    bad_channels_total = pd.DataFrame()
    nchip = ped_analyzer.data['chip'].unique()
    for chip in nchip:
        bad_channels_list = []
        print("ROC number",chip)
        channel_chip = ped_analyzer.data[ped_analyzer.data['chip']==chip].copy()

        channel_chip = channel_chip.sort_values(by=["sign_dac","dacb","trim_inv"], ignore_index=True)
        trim_dacb_initial = pd.concat([trim_dacb_initial,channel_chip])
        #print(channel_chip[(channel_chip['dacb']==0) & (channel_chip['trim_inv']==0)])
        #print(channel_chip)

        channel_chip.loc[channel_chip['sign_dac']==1,'sign_dacb'] = channel_chip['dacb'].apply(lambda x: -1*x)
        channel_chip.loc[channel_chip['sign_dac']==0,'sign_dacb'] = channel_chip['dacb'].apply(lambda x: x)

        channel_chip = channel_chip[~((channel_chip['dacb']==0) & (channel_chip['sign_dac']==1))]

        dacb_val = channel_chip['dacb'].unique()
        sign_dacb_val = channel_chip['sign_dacb'].unique()
        trim_val = channel_chip['trim_inv'].unique()
        print("dacb values", dacb_val) 
        print("signed dacb values",sign_dacb_val)
        print(len(channel_chip['dacb']))
        print("triminv values",trim_val)  

        #print(channel_chip)
        print(channel_chip['sign_dac'])
        print(channel_chip['dacb'])
        print(channel_chip['sign_dacb'])
        print(channel_chip['trim_inv'])
        #'''
        column_headers_old = list(channel_chip.columns.values)
        print("The Column Header old:", column_headers_old)    
        grad_trim_high = 2.5
        grad_trim_low = 0.5

        grad_dacb_high = 8
        grad_dacb_low = 0.5

        nestedConf = nested_dict() #This is for writing to a different file, and not just the final fit values, but the slopes as well (for comparison)

        nhalf = channel_chip['half'].unique()
        print("Number of halves",nhalf)
        for half in nhalf:
        #for half in [1]:
            channel_half = channel_chip[(channel_chip['half']==half) & (channel_chip['channeltype']==0)]
            print("First cut half array")
            print(channel_half)
            #channel_target = channel_half[(channel_half['trim_inv']==32) & (channel_half['sign_dacb']==0)].set_index('channel')
            print(trim_val[int(len(trim_val)/2)])
            channel_target = channel_half[(channel_half['trim_inv']==trim_val[int(len(trim_val)/2)]) & (channel_half['sign_dacb']==0)].set_index('channel')

            #Noise check
            '''
            for channel in channel_target.index:
                channel_target.loc[channel,'noise_0'] = int(len(channel_half[(channel_half['channel']==channel) & (channel_half['adc_stdd'] <=0.1)]))
                #print(channel_half[(channel_half['channel']==channel)]['adc_stdd'])
                #''' '''
            print(channel_target['noise_0'])
            '''
            #Comparing the gradients instead of doing a fit and calculating chi_squared
            for i in range(0,min(len(trim_val),len(dacb_val))):
                channel_target['dacb_'+str(i)+'_cut'] = channel_half[(channel_half['trim_inv']==trim_val[0]) & (channel_half['sign_dacb']==sign_dacb_val[i])].set_index('channel')['adc_mean']
                channel_target['trim_'+str(i)+'_cut'] = channel_half[(channel_half['trim_inv']==trim_val[i]) & (channel_half['sign_dacb']==dacb_val[0])].set_index('channel')['adc_mean']  
                channel_target = channel_target.astype({'trim_'+str(i)+'_cut':float, 'dacb_'+str(i)+'_cut':float})

            #Leaving this in for the moment as this is just something that is being calculated
            print("Channel target array without initial guesses of slopes")
            print(channel_target)        
            
            channel_target['trim_grad_1'] = (channel_target['trim_3_cut']-channel_target['trim_0_cut'])/(trim_val[3]-trim_val[0])
            channel_target['dacb_grad_1'] = (channel_target['dacb_3_cut']-channel_target['dacb_0_cut'])/(dacb_val[3]-dacb_val[0])
                
            print("Channel target array with initial guesses of slopes")
            print(channel_target)        
            #In this case, this is the y intercept of triminv
            channel_target['offset_init_trim'] = channel_target['trim_1_cut'] - trim_val[1]*channel_target['trim_grad_1']
            channel_target['offset_init_dacb'] = channel_target['dacb_1_cut'] - dacb_val[1]*channel_target['dacb_grad_1']
                    
            print("Channel target array with initial guesses of slopes and offsets")
            print(channel_target)        
            
            #Cuts for filtering out bad channels        
            channel_cut = channel_target[(channel_target['trim_grad_1'] > grad_trim_low*4/4) & (channel_target['trim_grad_1'] < grad_trim_high*4/4) & (channel_target['dacb_grad_1'] > grad_dacb_low*4/4) & (channel_target['dacb_grad_1'] < grad_dacb_high*4/4)]
            #channel_cut = channel_cut[channel_cut['noise_0'] == 0]
            #2nd cut for comparing 3 different gradients

            print(channel_cut)
            #print(channel_cut!=channel_target)
            merged_df=pd.merge(channel_cut, channel_target, how='right', indicator=True)
            df=merged_df[merged_df['_merge']=='right_only']
            print("Initial index",df)
            #final_df.set_index(final_df.index+36*half)
            final_df = df.copy()
            final_df['channel_nos'] = df.index+36*half
            print("Rows that fail the gradient and noise cuts")
            print(final_df)
            bad_channels_total = pd.concat([bad_channels_total, final_df])
            #print(bad_channels_total)
            
            target = channel_target[channel_target['trim_grad_1']>0]['adc_mean'].median()
            print(target)

            channel_mod = channel_cut.copy()
            #for channel in channel_cut.index:

            channel_fit = pd.DataFrame()
            channel_fit.index = channel_half['channel'].unique()
            channel_fit['dacb_fit'] = 0
            channel_fit['signdac'] = 0

            #channel_fit.trim = channel_mod[channel_mod['sign_dacb'] == dacb_val[0]]

            #Using fitting instead of this but the trim_grad_1 will be used as the initial guess
            #Using this only for comparison with the fit value
            #channel_fit['trim_sub'] = (target-channel_target['offset_init_trim'])/channel_target['trim_grad_1'] #Warning 4

            #putting a for loop for now
            print("Channel target index",channel_target.index)
            print("Channel fit index",channel_fit.index)
            for channel in channel_fit.index:
                print()
                fig, axes = plt.subplots(1,1,figsize=(20,15),sharey=False)
                ax = axes
                trim_dacb_opt = pd.DataFrame()
                #trim_dacb_opt.loc[:, ["opt_dacb","opt_val","opt_trim"]] = np.nan
                #'''
                min_opt_dacb = []
                min_opt_val = []
                min_opt_trim = []
                #'''
                for i in range(0,max(len(dacb_val),len(trim_val))):
                    try:
                        chan_trim_plot = channel_half[(channel_half['channel']==channel) & (channel_half['sign_dacb'] == sign_dacb_val[i])]
                        chan_dacb_plot = channel_half[(channel_half['channel']==channel) & (channel_half['trim_inv'] == trim_val[i])]
                        chan_dacb_plot_fit = channel_half[(channel_half['channel']==channel) & (channel_half['trim_inv'] == trim_val[i]) & (channel_half['sign_dac'] == 0)]

                        #Additional potential cut on chan_trim_plot - taking points only in multiples of 3 so as not to mess up the fit
                        #chan_trim_plot = chan_trim_plot[chan_trim_plot['trim_inv'] % 3 == 0]
                        #'''
                        print("Channel number",channel)
                        print("Dacb value fixed", chan_trim_plot)
                        print("Triminv value fixed",chan_dacb_plot)
                        #'''
                        ax.xaxis.grid(True)
                        ax.yaxis.grid(True)
                        #print("DACB values limits",int(sign_dacb_val.min()),int(sign_dacb_val.max()))
                        ax.set_xticks(range(min(int(sign_dacb_val.min()),int(trim_val.min())),max(int(sign_dacb_val.max()),int(trim_val.max())),4))
                        #ax.set_yticks(range(0,int(inj_data.time.max()),25))

                        ax.set_xticklabels(range(min(int(sign_dacb_val.min()),int(trim_val.min())),max(int(sign_dacb_val.max()),int(trim_val.max())),4),fontsize=4)


                        ax.scatter(chan_trim_plot.trim_inv, chan_trim_plot.adc_mean)
                        ax.scatter(chan_dacb_plot.sign_dacb, chan_dacb_plot.adc_mean)

                        slope_init_trim = channel_target.loc[channel_target.index==channel,'trim_grad_1'].values[0]
                        offset_init_trim = channel_target.loc[channel_target.index==channel,'offset_init_trim'].values[0]
                        print("Initial guesses of fitting parameters for triminv",slope_init_trim,offset_init_trim)
                        m_trim, b_trim = curve_fit(lambda x,a,b:a*x+b, chan_trim_plot.trim_inv, chan_trim_plot.adc_mean, p0=[slope_init_trim,offset_init_trim])
                        print("Final fitting parameters for triminv", m_trim[0], m_trim[1] )

                        ax.plot(chan_trim_plot.trim_inv, m_trim[0]*chan_trim_plot.trim_inv + m_trim[1])

                        chan_opt = chan_trim_plot.copy()
                        chan_opt['opt_min_trim'] = m_trim[0]*chan_trim_plot.trim_inv + m_trim[1] - target
                        print("Minimum optimized values")
                        print(chan_opt['opt_min_trim'])
                        print("Dacb value",sign_dacb_val[i])
                        print("Least functional value for this dacb value",abs(chan_opt['opt_min_trim']).min())
                        print("Best triminv value for this dacb value")
                        trim_opt = chan_opt.loc[abs(chan_opt['opt_min_trim']) == abs(chan_opt['opt_min_trim']).min(),'trim_inv'].values[0]
                        print(trim_opt)

                        min_opt_dacb = np.append(min_opt_dacb,sign_dacb_val[i])
                        min_opt_val = np.append(min_opt_val,abs(chan_opt['opt_min_trim']).min())
                        min_opt_trim = np.append(min_opt_trim,trim_opt)

                        slope_init_dacb = channel_target.loc[channel_target.index==channel,'dacb_grad_1'].values[0]
                        j = i+1
                        #offset_init_dacb = channel_target.loc[channel_target.index==channel,'dacb_'+str(j)+'_cut'].values[0] - dacb_val[1]*slope_init_dacb
                        offset_init_dacb = channel_target.loc[channel_target.index==channel,'offset_init_dacb'].values[0]
                        print("Initial guesses of fitting parameters for dacb",slope_init_dacb,offset_init_dacb)
                        m_dacb, b_dacb = curve_fit(lambda x,a,b:a*x+b, chan_dacb_plot_fit.sign_dacb, chan_dacb_plot_fit.adc_mean, p0=[slope_init_dacb,offset_init_dacb])
                        print("Final fitting parameters for dacb", m_dacb[0], m_dacb[1] )
                        
                        ax.plot(chan_dacb_plot_fit.sign_dacb, m_dacb[0]*chan_dacb_plot_fit.sign_dacb + m_dacb[1])
                        target_array = []
                        target_x = []
                        min_val = min(int(sign_dacb_val.min()),int(trim_val.min()))
                        max_val = max(int(sign_dacb_val.max()),int(trim_val.max()))
                        print("Minimum and maximum values on axis",min_val,max_val, max_val - min_val)
                        for k in range(max_val - min_val):
                            target_x.append(k+min_val)
                            target_array.append(target)
                        #Horizontal line indicating the target on the y axis (i.e. pedestal)
                        print("target array done")
                        ax.plot(target_x, target_array,'k--')
                        print("target array plotted - line parallel to x")

                        if i == 0:
                            channel_fit.loc[channel_fit.index==channel,'trim_grad'] = m_trim[0]
                            channel_fit.loc[channel_fit.index==channel,'dacb_grad'] = m_dacb[0]

                            #This is for the purpose of checking whether the scaling of triminv/dacb slopes and calculating directly from the dacb equation gives the same compensating value of dacb
                            channel_fit.loc[channel_fit.index==channel,'trim_intcpt'] = m_trim[1]
                            channel_fit.loc[channel_fit.index==channel,'dacb_intcpt'] = m_dacb[1]

                            channel_fit.loc[channel_fit.index==channel,'trim'] = (target-m_trim[1])/m_trim[0]

                            #channel_fit.loc[channel_fit.index==channel,'trim_sub'] = (target-channel_target.loc[channel_fit.index==channel,'offset_init_trim'])/channel_target.loc[channel_fit.index==channel,'trim_grad_1']

                            nestedConf = analysis_misc.set_key_dict(nestedConf,[int(channel),'ch','half_'+str(half),'sc','chip_'+str(chip)],['trim_grad'],[float(m_trim[0])])
                            nestedConf = analysis_misc.set_key_dict(nestedConf,[int(channel),'ch','half_'+str(half),'sc','chip_'+str(chip)],['trim_offset'],[float(m_trim[1])])
                            nestedConf = analysis_misc.set_key_dict(nestedConf,[int(channel),'ch','half_'+str(half),'sc','chip_'+str(chip)],['dacb_grad'],[float(m_dacb[0])])
                            nestedConf = analysis_misc.set_key_dict(nestedConf,[int(channel),'ch','half_'+str(half),'sc','chip_'+str(chip)],['dacb_offset'],[float(m_dacb[1])])

                            nestedConf = analysis_misc.set_key_dict(nestedConf,[int(channel),'ch','half_'+str(half),'sc','chip_'+str(chip)],['trim_fit_init'],[float(channel_fit.loc[channel_fit.index==channel,'trim'])])
                            #nestedConf = analysis_misc.set_key_dict(nestedConf,[int(channel),'ch','half_'+str(half),'sc','chip_'+str(chip)],['trim_fit_sub'],[float(channel_fit.loc[channel_fit.index==channel,'trim_sub'])])

                    except IndexError:
                        #Since we know that len(trim_val) is more
                        #chan_trim_plot = channel_half[(channel_half['channel']==channel) & (channel_half['sign_dacb'] == sign_dacb_val[i])]
                        chan_dacb_plot = channel_half[(channel_half['channel']==channel) & (channel_half['trim_inv'] == trim_val[i])]
                        chan_dacb_plot_fit = channel_half[(channel_half['channel']==channel) & (channel_half['trim_inv'] == trim_val[i]) & (channel_half['sign_dac'] == 0)]

                        #'''
                        print("Channel number",channel)
                        #print("Dacb value fixed", chan_trim_plot)
                        print("Triminv value fixed",chan_dacb_plot)
                        #'''
                        ax.xaxis.grid(True)
                        ax.yaxis.grid(True)
                        #print("DACB values limits",int(sign_dacb_val.min()),int(sign_dacb_val.max()))
                        ax.set_xticks(range(min(int(sign_dacb_val.min()),int(trim_val.min())),max(int(sign_dacb_val.max()),int(trim_val.max())),4))
                        #ax.set_yticks(range(0,int(inj_data.time.max()),25))

                        ax.set_xticklabels(range(min(int(sign_dacb_val.min()),int(trim_val.min())),max(int(sign_dacb_val.max()),int(trim_val.max())),4),fontsize=4)


                        #ax.scatter(chan_trim_plot.trim_inv, chan_trim_plot.adc_mean)
                        ax.scatter(chan_dacb_plot.sign_dacb, chan_dacb_plot.adc_mean)
                        
                        slope_init_dacb = channel_target.loc[channel_target.index==channel,'dacb_grad_1'].values[0]
                        j = i+1
                        #offset_init_dacb = channel_target.loc[channel_target.index==channel,'dacb_'+str(j)+'_cut'].values[0] - dacb_val[1]*slope_init_dacb
                        offset_init_dacb = channel_target.loc[channel_target.index==channel,'offset_init_dacb'].values[0]
                        print("Initial guesses of fitting parameters for dacb",slope_init_dacb,offset_init_dacb)
                        m_dacb, b_dacb = curve_fit(lambda x,a,b:a*x+b, chan_dacb_plot_fit.sign_dacb, chan_dacb_plot_fit.adc_mean, p0=[slope_init_dacb,offset_init_dacb])
                        print("Final fitting parameters for dacb", m_dacb[0], m_dacb[1] )
                        
                        ax.plot(chan_dacb_plot_fit.sign_dacb, m_dacb[0]*chan_dacb_plot_fit.sign_dacb + m_dacb[1])
                        target_array = []
                        target_x = []
                        min_val = min(int(sign_dacb_val.min()),int(trim_val.min()))
                        max_val = max(int(sign_dacb_val.max()),int(trim_val.max()))
                        print("Minimum and maximum values on axis",min_val,max_val, max_val - min_val)
                        for k in range(max_val - min_val):
                            target_x.append(k+min_val)
                            target_array.append(target)
                        #Horizontal line indicating the target on the y axis (i.e. pedestal)
                        print("target array done")
                        ax.plot(target_x, target_array,'k--')
                        print("target array plotted - line parallel to x")

                fig.savefig("%s/Dacb_plots/pedestal_vs_triminv_dacb_channel_%d_sign_dacb_%d.png"%(odir,channel,dacb_val[0]),format='png',bbox_inches='tight') 
                #trim_dacb_opt = pd.concat([trim_dacb_opt, min_opt_dacb.tolist()])
                
                '''
                if len(channel_fit.loc[channel_fit.index==channel,'trim'].values)==1:
                    if (channel_fit.loc[channel_fit.index==channel,'trim'].values[0] > 64) | (channel_fit.loc[channel_fit.index==channel,'trim'].values[0] < 0):
                        trim_dacb_opt['opt_dacb'] = min_opt_dacb.tolist()
                        trim_dacb_opt['opt_val'] = min_opt_val.tolist()
                        trim_dacb_opt['opt_trim'] = min_opt_trim.tolist()

                        print("Optimized values")
                        print(trim_dacb_opt)


                        print("Final optimized dacb value",trim_dacb_opt.loc[trim_dacb_opt['opt_val'] == trim_dacb_opt['opt_val'].min(),'opt_dacb'].values[0])
                        print("Final optimized triminv value",trim_dacb_opt.loc[trim_dacb_opt['opt_val'] == trim_dacb_opt['opt_val'].min(),'opt_trim'].values[0])
                        print("Original value of trim",channel_fit.loc[channel_fit.index==channel,'trim'])

                        channel_fit.loc[channel_fit.index==channel,'trim'] = trim_dacb_opt.loc[trim_dacb_opt['opt_val'] == trim_dacb_opt['opt_val'].min(),'opt_trim'].values[0]
                        channel_fit.loc[channel_fit.index==channel,'dacb_fit'] = trim_dacb_opt.loc[trim_dacb_opt['opt_val'] == trim_dacb_opt['opt_val'].min(),'opt_dacb'].values[0]
                '''

                #This chunk is now done for all channels, irrespective of whether it saturates or not (just for debugging related to the dacb problem)
                trim_dacb_opt['opt_dacb'] = min_opt_dacb.tolist()
                trim_dacb_opt['opt_val'] = min_opt_val.tolist()
                trim_dacb_opt['opt_trim'] = min_opt_trim.tolist()

                print("Optimized values")
                print(trim_dacb_opt)


                print("Final optimized dacb value",trim_dacb_opt.loc[trim_dacb_opt['opt_val'] == trim_dacb_opt['opt_val'].min(),'opt_dacb'].values[0])
                print("Final optimized triminv value",trim_dacb_opt.loc[trim_dacb_opt['opt_val'] == trim_dacb_opt['opt_val'].min(),'opt_trim'].values[0])
                print("Original value of trim",channel_fit.loc[channel_fit.index==channel,'trim'])

                channel_fit.loc[channel_fit.index==channel,'trim'] = trim_dacb_opt.loc[trim_dacb_opt['opt_val'] == trim_dacb_opt['opt_val'].min(),'opt_trim'].values[0]
                channel_fit.loc[channel_fit.index==channel,'dacb_fit'] = trim_dacb_opt.loc[trim_dacb_opt['opt_val'] == trim_dacb_opt['opt_val'].min(),'opt_dacb'].values[0]

            #print(trim)
            print("Final trim and dacb fits before rounding off (includes the dacb-trim optimization)")
            
            print(channel_fit.trim)
            print(channel_fit.dacb_fit)
            
            #Default values for dacb and sign_dac before calculating triminv limits

            channel_mod_2 = channel_fit[(channel_fit['trim']!=-np.inf)&(channel_fit['trim']!=np.inf)].copy()
            channel_mod_3 = channel_mod_2.copy()

            #Rounding off to the nearest integer for triminv
            channel_mod_3.loc[channel_mod_3['trim'] % 1 < 0.5,'trim'] = channel_mod_2['trim'].apply(lambda x: math.floor(x)) #Warning 5
            #channel_cut.loc[channel_cut['trim'] % 1 < 0.5,'trim'] = channel_cut.loc[channel_cut['trim'] % 1 < 0.5,'trim'].apply(lambda x: math.floor(x))
            channel_mod_3.loc[channel_mod_3['trim'] % 1 >= 0.5,'trim'] = channel_mod_2['trim'].apply(lambda x: math.ceil(x)) #Warning 6

            channel_mod_4 = channel_mod_3.copy()

            channel_mod_4.loc[channel_mod_4['dacb_fit'] < 0, 'signdac'] = 1 #Warning 9
            channel_mod_4.loc[channel_mod_4['dacb_fit'] < 0, 'dacb_fit'] = -channel_mod_3['dacb_fit']

            channel_mod_5 = channel_mod_4.copy()

            #Rounding off to the nearest integer for dacb
            #Now not necessary since here dacb will be an integer by default because of the way the points are chosen

            #channel_mod_5.loc[channel_mod_5['dacb_fit'] % 1 < 0.5,'dacb_fit'] = channel_mod_4['dacb_fit'].apply(lambda x: math.floor(x)) #Warning 11
            #channel_mod_5.loc[channel_mod_5['dacb_fit'] % 1 >= 0.5,'dacb_fit'] = channel_mod_4['dacb_fit'].apply(lambda x: math.ceil(x)) #Warning 12

            channel_mod_5.loc[abs(channel_mod_5['dacb_fit']) > 63 , 'dacb_fit'] = 0

            trim_dacb_fit_total = pd.concat([trim_dacb_fit_total,channel_mod_5])
            
            for channel in channel_mod_5.index:
                cfg["roc_s0"]["sc"]["ch"][channel]["trim_inv"] = int(channel_mod_5.loc[channel,'trim'])
                cfg["roc_s0"]["sc"]["ch"][channel]["dacb"] = int(channel_mod_5.loc[channel,'dacb_fit'])
                cfg["roc_s0"]["sc"]["ch"][channel]["sign_dac"] = int(channel_mod_5.loc[channel,'signdac'])
            
        print(nestedConf.to_dict())        
        with open(odir+"triminv_fit.yaml", "w") as o:
            print(yaml.dump(nestedConf.to_dict(),o))
        
        print("Saved new config file as:"+"triminv_fit.yaml")    

        
        print("ROC number", str(chip))
        for index,row in bad_channels_total.iterrows():
            bad_channels_list.append(row['channel_nos'])
        nestedConf['bad_channels']['chip'+str(chip)]['ch'] = bad_channels_list
        #'''
    
    #'''
    print(trim_dacb_fit_total)
    trim_dacb_fit_total.to_csv(os.path.join(odir,"trim_dacb_fit.csv"))
    
    print(trim_dacb_initial)
    trim_dacb_initial.to_csv(os.path.join(odir,"trim_dacb.csv"))
    
    print(bad_channels_total)
    
    # changed by anurag
    filename = 'bad_channels.yaml'
    directory = os.path.join(odir, filename) 
             
    with open(directory,'w') as file:
        print(yaml.dump(nestedConf.to_dict(),file,sort_keys=False))
        print("Written to yaml file")

    #data frame cut for deciding first pedestal target half wise
    configFile0 = configFile[:configFile.find(".yaml")]
    
    with open(configFile0+"_triminv_D8_12_new_fit_dacb.yaml", "w") as o:
        yaml.dump(cfg, o)
    print("Saved new config file as:"+configFile0+"_triminv_D8_12_new_fit_dacb.yaml")   
    #'''
    
def main():

    parser = misc_func.options_run() # This will be constant for every test irrespective of the type of test
    parser.add_argument("-p", "--outputConfig", action="store", dest="output", help="output base directory")
    
    #(options, args) = parser.parse_args()
    options = parser.parse_args()
    print(options)
    
    # ================= changes made by anurag ================
    if options.odir == './data':
        print ('odir', options.odir)
        raise FileNotFoundError("Please provide an odir, ./data is not a valid output directory for this analysis")
    else:
        odir = options.odir

    # ================= changes made by anurag ================
    ped_analyzer = analyzer.pedestal_scan_analyzer(odir=odir)
    files = glob.glob(odir + "/pedestal_scan*.root")
    print(files)

    for f in files:
        ped_analyzer.add(f)

    ped_analyzer.mergeData()
    print(ped_analyzer.data)
    
    make_plots(1,options.configFile, odir, ped_analyzer)
    
if __name__ == "__main__":
    main()
