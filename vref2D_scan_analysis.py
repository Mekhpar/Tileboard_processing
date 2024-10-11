from level0.analyzer import *
from scipy.optimize import curve_fit
import glob,itertools
import seaborn as sns 
import pandas as pd
import copy

#import miscellaneous_analysis_functions as analysis_misc

import analysis.level0.miscellaneous_analysis_functions as analysis_misc

class vref2D_scan_analyzer(analyzer):

    def makePlots(self):
        cmap = cm.get_cmap('YlOrRd')
        sel_data = self.data[['chip','channel','channeltype','adc_mean','adc_stdd','Inv_vref','Noinv_vref','half']].copy()
        df = sel_data.query('channeltype==0').groupby(['chip', 'half', 'Noinv_vref', 'Inv_vref'])[['adc_mean','adc_stdd']].mean()
        df.rename(columns={'adc_mean': 'pedestal', 'adc_stdd': 'noise'}, inplace=True)
        print(df)

        vmax_pedestal = np.nanpercentile(df['pedestal'], 98)
        vmax_noise = np.nanpercentile(df['noise'], 98)
        for chip in df.index.get_level_values('chip').unique():
            ########################
            ## pedestal vs vref 2D #
            ########################
            fig, axes = plt.subplots(1,2,figsize=(18,8),sharey=True)
            fig.suptitle('Vref 2D scan : pedestal')

            for half in 0, 1:
                ax = axes[half]
                plot = df.loc[chip, half].reset_index().pivot('Noinv_vref', 'Inv_vref', 'pedestal')
                h = sns.heatmap(plot, mask=(plot == 0), vmin=0, vmax=vmax_pedestal, ax=ax, cmap=cmap, linewidths=.5)
                h.collections[0].colorbar.set_label("Pedestal [ADC counts]",fontsize=15)
                ax.invert_yaxis()
                ax.tick_params(labelsize=12)
                cax = plt.gcf().axes[-1]
                cax.tick_params(labelsize=12)
                h.set_xlabel(r'Inv_vref',fontsize=15)
                h.set_ylabel(r'Noinv vref',fontsize=15)
                ax.set_title('Half %s' % half)
            plt.savefig('%s/pedestal2D_chip%d.png'%(self.odir,chip))
            

            
            #####################
            ## noise vs vref 2D #
            #####################
            fig, axes = plt.subplots(1,2,figsize=(18,8),sharey=True)
            fig.suptitle('Vref 2D scan : noise')

            for half in 0, 1:
                ax = axes[half]
                plot = df.loc[chip, half].reset_index().pivot('Noinv_vref', 'Inv_vref', 'noise')
                h = sns.heatmap(plot, mask=(plot == 0), vmin=0, vmax=vmax_noise, ax=ax, cmap=cmap, linewidths=.5)
                h.collections[0].colorbar.set_label("Noise [ADC counts]",fontsize=15)
                ax.invert_yaxis()
                ax.tick_params(labelsize=12)
                cax = plt.gcf().axes[-1]
                cax.tick_params(labelsize=12)
                h.set_xlabel(r'Inv_vref',fontsize=15)
                h.set_ylabel(r'Noinv vref',fontsize=15)
                ax.set_title('Half %s' % half)
            plt.savefig('%s/noise2D_chip%d.png'%(self.odir,chip))

    #Copied from the 1D (vrefinv) analysis script

    def fit(self, df,y_arr,x_arr,min_prct,max_prct):
    
        max_df = df[y_arr].max()
        max_df_index = df.index[df[y_arr] == max_df].max()
        min_df = df[ df[y_arr]>0 ][y_arr].min()
        min_df_index = df.index[df[y_arr] == min_df].min()
        
        print("Limits of scan", max_df,min_df)
        df_less = df[y_arr] < max_prct*max_df
        print(df.index)
        print("Printed indices")
        print(df.index > max_df_index)
        print((df[y_arr] < max_prct*max_df) & (df.index > max_df_index))
        imax = df.index[df[y_arr] < max_prct*max_df].min()  # get index of rightmost maximum
        print("Max df index",max_df_index)
        print("Imax indices")
        print(imax)

        imax_new = df.index[(df[y_arr] < max_prct*max_df) & (df.index > max_df_index)].min()
        print(imax_new)

        print("Min df index",min_df_index)
        print("imin indices")
        imin = df.index[df[y_arr] > min_prct*min_df].max()
        print(imin)
        imin_new = df.index[(df[y_arr] > min_prct*min_df) & (df.index < min_df_index)].max()
        print(imin_new)
        
        df_lin = pd.DataFrame()
        #This will take care of both positive (vrefnoinv) and negative (vrefinv) slopes
        #'''
        if imin_new > imax_new:
            df_lin = df[(df.index <= imin_new) & (df.index >= imax_new)]
            
        elif imin_new < imax_new:
            df_lin = df[(df.index >= imin_new) & (df.index <= imax_new)]
        #'''    

        '''
        if imin > imax:
            df_lin = df[(df.index <= imin) & (df.index >= imax)]
            
        elif imin < imax:
            df_lin = df[(df.index >= imin) & (df.index <= imax)]
        '''
        
        xs = df_lin[x_arr]
        
        
        if len(xs.to_list())>0:
            slope_init = (df_lin[y_arr].values[1] - df_lin[y_arr].values[0])/(df_lin[x_arr].values[1] - df_lin[x_arr].values[0])
            offset_init = df_lin[y_arr].values[0] - slope_init*df_lin[x_arr].values[0]
            print(slope_init,offset_init)
            
            #m, b = np.polyfit(xs.to_list(), df[ df[x_arr].isin(xs.to_list()) ][y_arr].to_list(), 1)
            m, b = curve_fit(lambda x,a,b:a*x+b, df_lin[x_arr], df_lin[y_arr], p0=[slope_init,offset_init])
            return xs, m, b
        else:
            return xs,-1,-1

    
    def determine_Vref(self,configFile,odir):
        sel_data = self.data[['chip','channel','channeltype','adc_mean','adc_stdd','Inv_vref','Noinv_vref','half']].copy()
        sel_data = sel_data.sort_values(by=["Noinv_vref","Inv_vref"], ignore_index=True)
        nchip = sel_data['chip'].unique()
        
        with open(configFile) as f:
            cfg = yaml.safe_load(f)
        rockeys = []
        
        nestedConf = nested_dict() #This is for writing to a different file, and not just the final fit values, but the slopes as well (for comparison)

        with open("%s/initial_config.yaml"%(self.odir)) as fin:
            initconfig = yaml.safe_load(fin)
            for key in initconfig.keys():
                if key.find('roc')==0:
                    rockeys.append(key)
        rockeys.sort()
        
        for chip in nchip:
            data_chip = sel_data[sel_data['chip']==chip]
            nhalf = data_chip['half'].unique()
            print("Chip number",chip)
            print("Halves",nhalf) 
            
            df = data_chip.query('channeltype==0').groupby(['chip', 'half', 'Noinv_vref', 'Inv_vref'])[['adc_mean','adc_stdd']].mean()
            df.rename(columns={'adc_mean': 'pedestal', 'adc_stdd': 'noise'}, inplace=True)
            print(df)
            #print(df.index[1][3])
            #print(len(df))
            noinv_vals = data_chip['Noinv_vref'].unique()
            inv_vals = data_chip['Inv_vref'].unique()
            
            #The fixed value at which the individual fits in the other parameter have to be performed (although ideally they should have the same slope)
            noinv_fix = noinv_vals[int(len(noinv_vals)/2)]
            inv_fix = inv_vals[int(len(inv_vals)/2)]
                    
            print(noinv_vals)
            print(inv_vals)
            print(noinv_fix,inv_fix)
            target = 200

            fig, axes = plt.subplots(1,2,figsize=(20,15),sharey=False)
            fig1, axes1 = plt.subplots(1,2,figsize=(20,15),sharey=False)

            if chip<len(rockeys):
                chip_key_name = rockeys[int(chip)] #converted to int as we only have 1 chip for now

            for half in nhalf:
                df_inv_fit = pd.DataFrame()
                df_noinv_fit = pd.DataFrame()
                for i in range(len(df)):
                    if df.index[i][1]==half:
                    
                        if df.index[i][2] == noinv_fix:    
                            df_inv_fit.loc[i,'ped'] = df.pedestal.values[i]
                            df_inv_fit.loc[i,'inv_vals'] = df.index[i][3]

                        if df.index[i][3] == inv_fix:    
                            df_noinv_fit.loc[i,'ped'] = df.pedestal.values[i]
                            df_noinv_fit.loc[i,'noinv_vals'] = df.index[i][2]

                index_inv = np.arange(len(df_inv_fit.index))
                df_inv_fit.index = index_inv
                print(df_inv_fit)

                index_noinv = np.arange(len(df_inv_fit.index))
                df_noinv_fit.index = index_noinv
                print(df_noinv_fit)
                
                print("Finding fit parameters for vrefinv")
                xs_inv, alpha_inv, beta_inv = self.fit( df_inv_fit, 'ped', 'inv_vals',1.05,0.95)
                print(xs_inv)
                print(alpha_inv)
            
                #Plotting 1D variation in vrefinv (vrefnoinv fixed) along with linear fit
                ax = axes[half]
                ax.set_ylabel(r'Pedestal [ADC counts]')
                ax.set_xlabel(r'Inv vref ')
                ax.xaxis.grid(True)

                ax.scatter(df_inv_fit['inv_vals'], df_inv_fit['ped'],marker='o', label='Half_'+str(half))
                ax.plot(xs_inv, alpha_inv[0]*xs_inv + alpha_inv[1])
                ax.set_ylim(0,1023)

                fig.suptitle("pedestal_1D_vs_vrefinv_chip_"+str(chip),y=0.93)
                h, l = ax.get_legend_handles_labels()
                ax.legend(h, l)

                if half == 1:
                    fig.savefig("%s/pedestal_vs_vrefinv_chip%d.png"%(self.odir,chip),format='png',bbox_inches='tight') 
                    plt.close(fig)

                print("Finding fit parameters for vrefnoinv")
                xs_noinv, alpha_noinv, beta_noinv = self.fit( df_noinv_fit, 'ped', 'noinv_vals',1,1)
                print(xs_noinv)
                print(alpha_noinv)

                #Plotting 1D variation in vrefinv (vrefnoinv fixed) along with linear fit
                ax1 = axes1[half]
                ax1.set_ylabel(r'Pedestal [ADC counts]')
                ax1.set_xlabel(r'NoInv vref ')
                ax1.xaxis.grid(True)

                ax1.scatter(df_noinv_fit['noinv_vals'], df_noinv_fit['ped'],marker='o', label='Half_'+str(half))
                ax1.plot(xs_noinv, alpha_noinv[0]*xs_noinv + alpha_noinv[1])
                ax1.set_ylim(0,1023)

                fig1.suptitle("pedestal_1D_vs_vrefnoinv_chip_"+str(chip),y=0.93)
                h, l = ax1.get_legend_handles_labels()
                ax1.legend(h, l)

                if half == 1:
                    fig1.savefig("%s/pedestal_vs_vrefnoinv_chip%d.png"%(self.odir,chip),format='png',bbox_inches='tight') 
                    plt.close(fig1)


                vnoinv_final = noinv_fix #This is just because that was the original value in the config file
                vinv_final = -1
                vinv_fit = (target - alpha_inv[1])/alpha_inv[0]
                print("Value not rounded",vinv_fit)
                if vinv_fit % 1 < 0.5:
                    vinv_final = int(vinv_fit)
                elif vinv_fit % 1 >= 0.5:
                    vinv_final = int(vinv_fit) + 1

                if vinv_final < xs_inv.min():
                    vnoinv_final = int((vinv_final - xs_inv.min())*alpha_inv[0]/alpha_noinv[0]) + noinv_fix
                    vinv_final = xs_inv.min()

                elif vinv_final > xs_inv.max():
                    vnoinv_final = int((vinv_final - xs_inv.max())*alpha_inv[0]/alpha_noinv[0]) + noinv_fix
                    vinv_final = xs_inv.max()

                if (vnoinv_final < xs_noinv.min()) | (vnoinv_final > xs_noinv.max()):
                    vnoinv_final = noinv_fix
                
                print()    
                print("Half value", half)
                print("final value of vinv",vinv_final)
                print("final value of vnoinv",vnoinv_final)

                nestedConf = analysis_misc.set_key_dict(nestedConf,[int(half),'ReferenceVoltage','sc',chip_key_name],['Inv_vref'],[int(vinv_final)])
                nestedConf = analysis_misc.set_key_dict(nestedConf,[int(half),'ReferenceVoltage','sc',chip_key_name],['Inv_slope'],[round(float(alpha_inv[0]),3)])
                nestedConf = analysis_misc.set_key_dict(nestedConf,[int(half),'ReferenceVoltage','sc',chip_key_name],['Inv_y_int'],[round(float(alpha_inv[1]),3)])

                nestedConf = analysis_misc.set_key_dict(nestedConf,[int(half),'ReferenceVoltage','sc',chip_key_name],['Noinv_vref'],[int(vnoinv_final)])
                nestedConf = analysis_misc.set_key_dict(nestedConf,[int(half),'ReferenceVoltage','sc',chip_key_name],['Noinv_slope'],[round(float(alpha_noinv[0]),3)])
                nestedConf = analysis_misc.set_key_dict(nestedConf,[int(half),'ReferenceVoltage','sc',chip_key_name],['Noinv_y_int'],[round(float(alpha_noinv[1]),3)])


                cfg[chip_key_name]['sc']['ReferenceVoltage'][half]['Inv_vref'] = int(vinv_final)
                cfg[chip_key_name]['sc']['ReferenceVoltage'][half]['Noinv_vref'] = int(vnoinv_final)
            
                #nestedConf[chip_key_name]['sc']['ReferenceVoltage'][half]['Inv_vref'] = int(vinv_final)
                #nestedConf[chip_key_name]['sc']['ReferenceVoltage'][half]['Noinv_vref'] = int(vnoinv_final)

                
       
        configFile = configFile.replace('.yaml','')  
        #'''
        print(nestedConf.to_dict())        
        with open(odir+"Vref2D_fit.yaml", "w") as o:
            print(yaml.dump(nestedConf.to_dict(),o))
        
        print("Saved new config file as:"+"Vref2D_fit.yaml")    
        #'''    
        with open(configFile+"_vref2D_full_aligned.yaml", "w") as o:
            yaml.dump(cfg, o)
        
        print("Saved new config file as:"+configFile+"_vref2D_full_aligned.yaml")    
     

