from level0.analyzer import *
from scipy.optimize import curve_fit
from lmfit import Parameters,minimize, fit_report
from scipy.stats import chisquare

import glob,itertools
import seaborn as sns 
import pandas as pd
import copy
import matplotlib

#import miscellaneous_analysis_functions as analysis_misc

import analysis.level0.miscellaneous_analysis_functions as analysis_misc

class vref2D_scan_analyzer(analyzer):

    def makePlots(self):
        #cmap = cm.get_cmap('YlOrRd')
        cmap = matplotlib.colormaps['YlOrRd']
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

    def lin_fit(params,x,y):
        m = params['m']
        c = params['c']
        y_diff = m*x + c -y
        return y_diff

    def fit(self, df,y_arr,x_arr,min_prct,max_prct,chip,half,zero_slope_limit):
    
        #Plotting LH and RH derivative of all the points (not just linear region)
        y_cur = df[y_arr]
        x_cur = df[x_arr]

        y_lh = df.shift(1,axis=0)[y_arr]
        x_lh = df.shift(1,axis=0)[x_arr]

        y_rh = df.shift(-1,axis=0)[y_arr]
        x_rh = df.shift(-1,axis=0)[x_arr]
        '''
        print("Data frames for left and right handed derivatives")
        print(y_cur)
        print(x_cur)
        print(y_lh)
        print(x_lh)
        print(y_rh)
        print(x_rh)
        '''
        df['lh_slope'] = (y_cur-y_lh)/(x_cur-x_lh)
        df['rh_slope'] = (y_cur-y_rh)/(x_cur-x_rh)

        print("Lh and Rh derivatives")
        print(df['lh_slope'])
        print(df['rh_slope'])

        #==================================================================Plotting the left and right handed derivatives==============================================================
        
        fig, axes = plt.subplots(1,2,figsize=(30,15),sharey=False)  
        ax = axes[0]
        ax.xaxis.grid(True)
        ax.yaxis.grid(True)
        print("x axis for plotting lh derivative")
        
        ax.scatter(df[~df['lh_slope'].isna()][x_arr], df[~df['lh_slope'].isna()]['lh_slope']) 

        ax = axes[1]
        ax.xaxis.grid(True)
        ax.yaxis.grid(True)

        ax.scatter(df[~df['rh_slope'].isna()][x_arr], df[~df['rh_slope'].isna()]['rh_slope'])

        fig.savefig("%s/derivative_vs_%s_chip_%d_half_%d.png"%(self.odir,x_arr,chip,half),format='png',bbox_inches='tight') 

        #=============================================================================================================================================================================


        #==================================================================Putting flat region and slope constraints==============================================================

        #This removes all slopes close to 0, which means that the fairly flat region generally found at the beginning and end of vrefinv scan will not be included in the fit
        #This condition is also relaxed, so that only points that are flat on both sides are considered
        df_lin_mod = df[(abs(df['rh_slope'])>=zero_slope_limit) | (abs(df['lh_slope'])>=zero_slope_limit)]

        med_lin_slope = df_lin_mod['rh_slope'].median()
        #Probably only taking one type of derivative here (the right handed one)
        print("Median for the non flat region in rh",med_lin_slope) #Obviously median of lh slopes is the same as the median of the rh slopes
        print("Limits of slope considered for linear region",0.7*med_lin_slope,1.3*med_lin_slope)
        #mask_lh = abs(df_lin_mod['lh_slope']-med_lin_slope) < 0.2*abs(med_lin_slope)
        #mask_rh = abs(df_lin_mod['rh_slope']-med_lin_slope) < 0.2*abs(med_lin_slope)

        #0.2 is changed to 0.3 to include edge cases and anyway we are having an extra intercept condition as well
        mask_lh = abs(df_lin_mod['lh_slope']-med_lin_slope) < 0.3*abs(med_lin_slope)
        mask_rh = abs(df_lin_mod['rh_slope']-med_lin_slope) < 0.3*abs(med_lin_slope)

        #This is just to make sure the right intercept is assigned to a point
        mask_strict_lh = abs(df_lin_mod['lh_slope']-med_lin_slope) < 0.2*abs(med_lin_slope)
        mask_strict_rh = abs(df_lin_mod['rh_slope']-med_lin_slope) < 0.2*abs(med_lin_slope)

        mask_suppl_lh = abs(df_lin_mod['lh_slope']-med_lin_slope) < abs(df_lin_mod['rh_slope']-med_lin_slope)
        mask_suppl_rh = abs(df_lin_mod['rh_slope']-med_lin_slope) < abs(df_lin_mod['lh_slope']-med_lin_slope)

        print("Non flat region")
        print(df_lin_mod)
        print(mask_lh|mask_rh)
        #print(mask_lh & mask_rh)

        #df_lin_mod = df_lin_mod[(mask_lh) & (mask_rh)]
        #print("Final linear region",df_lin_mod)

        df_lin_slope = df_lin_mod[(mask_lh) | (mask_rh)]
        #df_lin_slope = df_lin_mod[(mask_lh) & (mask_rh)]
        print("Derivative selected linear region")
        print(df_lin_slope)

        #=============================================================================================================================================================================


        #==================================================================Left and right handed intercept calculation==============================================================
        df_lin_slope['lh_intercept'] = df_lin_slope[y_arr] - df_lin_slope['lh_slope']*df_lin_slope[x_arr]
        df_lin_slope['rh_intercept'] = df_lin_slope[y_arr] - df_lin_slope['rh_slope']*df_lin_slope[x_arr]

        print("Intercepts with lh and rh slopes")
        print(df_lin_slope['lh_intercept'])
        print(df_lin_slope['rh_intercept'])
        #=============================================================================================================================================================================


        #==================================================================Plotting the left and right handed intercepts==============================================================

        fig, axes = plt.subplots(1,2,figsize=(30,15),sharey=False)  
        ax = axes[0]
        ax.xaxis.grid(True)
        ax.yaxis.grid(True)
        print("x axis for plotting lh intercept")
        
        ax.scatter(df_lin_slope[~df_lin_slope['lh_intercept'].isna()][x_arr], df_lin_slope[~df_lin_slope['lh_intercept'].isna()]['lh_intercept']) 

        ax = axes[1]
        ax.xaxis.grid(True)
        ax.yaxis.grid(True)

        ax.scatter(df_lin_slope[~df_lin_slope['rh_intercept'].isna()][x_arr], df_lin_slope[~df_lin_slope['rh_intercept'].isna()]['rh_intercept'])

        fig.savefig("%s/intercept_vs_%s_chip_%d_half_%d.png"%(self.odir,x_arr,chip,half),format='png',bbox_inches='tight') 

        #=============================================================================================================================================================================


        #======================================================================Combo intercept calculation============================================================================
        df_inter = df_lin_slope.copy()

        df_inter['combo_intercept'] = df_lin_slope['rh_intercept'] #First populate and then replace the problematic values
        '''
        print("Left intercept required")
        print((mask_strict_lh)&~(mask_strict_rh))
        print("Right intercept required")
        print(~(mask_strict_lh)&(mask_strict_rh))

        print("Supplementary masks for slope comparison")
        print(mask_suppl_lh)
        print(mask_suppl_rh)
        '''
        
        #print(df_inter)
        df_inter.loc[(mask_strict_lh)&~(mask_strict_rh)&(mask_rh),'combo_intercept'] = df_lin_slope['lh_intercept']
        df_inter.loc[(mask_strict_lh)&~(mask_strict_rh)&(mask_rh),'net_mask'] = 'edge of linear region (right slope between 20 and 30%)'
        
        df_inter.loc[~(mask_strict_lh)&(mask_lh)&(mask_strict_rh),'combo_intercept'] = df_lin_slope['rh_intercept']
        df_inter.loc[~(mask_strict_lh)&(mask_lh)&(mask_strict_rh),'net_mask'] = 'edge of linear region (left slope between 20 and 30%)'


        df_inter.loc[(mask_strict_lh)&(mask_strict_rh)&(mask_suppl_lh),'combo_intercept'] = df_lin_slope['lh_intercept']
        df_inter.loc[(mask_strict_lh)&(mask_strict_rh)&(mask_suppl_lh),'net_mask'] = 'good linear region (both slopes within 20%)'

        df_inter.loc[(mask_strict_lh)&(mask_strict_rh)&(mask_suppl_rh),'combo_intercept'] = df_lin_slope['rh_intercept']
        df_inter.loc[(mask_strict_lh)&(mask_strict_rh)&(mask_suppl_rh),'net_mask'] = 'good linear region (both slopes within 20%)'


        df_inter.loc[(mask_lh)&~(mask_rh),'combo_intercept'] = df_lin_slope['lh_intercept']
        df_inter.loc[(mask_lh)&~(mask_rh),'net_mask'] = 'Edge of flat region (right slope outside 30%)'
        df_inter.loc[~(mask_lh)&(mask_rh),'combo_intercept'] = df_lin_slope['rh_intercept']
        df_inter.loc[~(mask_lh)&(mask_rh),'net_mask'] = 'Edge of flat region (left slope outside 30%)'

        print("Combo intercept and Category of point")
        print(df_inter)

        #=============================================================================================================================================================================


        #======================================================================Combo intercept plotting===============================================================================
        fig, axes = plt.subplots(1,1,figsize=(15,15),sharey=False)  
        ax = axes
        ax.xaxis.grid(True)
        ax.yaxis.grid(True)
        print("x axis for plotting combo intercept")
        
        ax.scatter(df_inter[~df_inter['combo_intercept'].isna()][x_arr], df_inter[~df_inter['combo_intercept'].isna()]['combo_intercept']) 
        plt.gca().set_ylim(bottom=0)
        fig.savefig("%s/combo_intercept_vs_%s_chip_%d_half_%d.png"%(self.odir,x_arr,chip,half),format='png',bbox_inches='tight') 

        #=============================================================================================================================================================================

        #==================================================================Putting flat region and value constraints==================================================================

        med_intercept = df_inter['combo_intercept'].median()
        #Probably only taking one type of derivative here (the right handed one)
        print("Median for the non flat region in rh",med_intercept) #Obviously median of lh slopes is the same as the median of the rh slopes
        print("Limits of intercept considered for linear region",0.9*med_intercept,1.1*med_intercept)

        #Putting more stringent limits here because the y intercept values are a little large
        df_lin = df_inter[abs(df_inter['combo_intercept']-med_intercept) < 0.1*abs(med_intercept)]

        print("Final linear region")
        print(df_lin)

        #=============================================================================================================================================================================
        '''
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
        if imin_new > imax_new:
            df_lin = df[(df.index <= imin_new) & (df.index >= imax_new)]
            
        elif imin_new < imax_new:
            df_lin = df[(df.index >= imin_new) & (df.index <= imax_new)]
        '''

        '''  
        lin_two_slope = pd.DataFrame()
        if x_arr == 'inv_vals': #Just for debugging
            
            print("Supposed dataframe for fitting")
            print(df_lin)
            #Try to remove outlier points here
            for i in df_lin.index:
                for j in df_lin.index:
                    if j>=i: #Skipping to avoid overcounting
                        continue
                    lin_two_slope['pt_1'] = j
                    lin_two_slope['pt_2'] = i
                    
                    y_i = df_lin.loc[df_lin.index == i,y_arr].values[0]
                    y_j = df_lin.loc[df_lin.index == j,y_arr].values[0]
                    x_i = df_lin.loc[df_lin.index == i,x_arr].values[0]
                    x_j = df_lin.loc[df_lin.index == j,x_arr].values[0]

                    print("Indices",i,j)
                    print("y and x coordinates",y_i,y_j,x_i,x_j)
                    lin_two_slope['slope'] = (y_i - y_j)/(x_i - x_j)
                    print((y_i - y_j)/(x_i - x_j))

            print()
            print("Dataframe for combo of slopes")
            print(lin_two_slope)
            print()
        '''
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

            #Old method for fitting
            m, b = curve_fit(lambda x,a,b:a*x+b, df_lin[x_arr], df_lin[y_arr], p0=[slope_init,offset_init])

            df_exp = m[0]*xs + m[1]
            chi = chisquare(df_lin[y_arr],f_exp=df_exp)
            print("Chi square and p value",chi,chi[0],chi[1])
            print(df_lin[y_arr])
            print(df_exp)
            # Defining the various parameters
            '''
            params = Parameters()
            params.add('m', value = slope_init)
            # Intercept is made fixed at 0.0 value
            params.add('c', value = offset_init)

            print("Initial guesses of m and c",slope_init,offset_init)
            x = df_lin[x_arr].to_numpy()
            y = df_lin[y_arr].to_numpy()
            print(x)
            print(y)
            print("Type of the arrays used for fitting",type(x),type(y))

            # Calling the minimize function. Args contains the x and y data.
            fitted_params = minimize(self.lin_fit, params, args=(x,y))
            #fitted_params = minimize(self.lin_fit(params['m'],params['c'],x,y))

            # Getting the fitted values
            m = fitted_params.params['m'].value
            c = fitted_params.params['c'].value    

            # Printing the fitted values
            print('The slope (m) is ', m)
            print('The intercept (c) is ', c)

            # Pretty printing all the statistical data
            print(fit_report(fitted_params))

            #Trying new method for fitting from lmfit since we want chi squared
            '''
            return xs, m, b
            #return xs, m, c
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
            
            df = data_chip.query('channeltype==0').groupby(['chip', 'half', 'Noinv_vref', 'Inv_vref'])[['adc_mean','adc_stdd']].median()
            #df = data_chip.query('channeltype==0').groupby(['chip', 'half', 'Noinv_vref', 'Inv_vref'])[['adc_mean','adc_stdd']].mean()
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

            fig, axes = plt.subplots(1,2,figsize=(30,15),sharey=False)
            fig1, axes1 = plt.subplots(1,2,figsize=(20,15),sharey=False)

            if chip<len(rockeys):
                chip_key_name = rockeys[int(chip)] #converted to int as we only have 1 chip for now

            for half in nhalf:
            #for half in [0]:
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
                xs_inv, alpha_inv, beta_inv = self.fit( df_inv_fit, 'ped', 'inv_vals', 1.05, 0.95, chip, half, 0.05)
                print(xs_inv)
                print(alpha_inv)
                #print(beta_inv) #Extra from lmfit
            
                #Plotting 1D variation in vrefinv (vrefnoinv fixed) along with linear fit
                ax = axes[half]
                ax.set_ylabel(r'Pedestal [ADC counts]')
                ax.set_xlabel(r'Inv vref ')
                ax.xaxis.grid(True)

                ax.scatter(df_inv_fit['inv_vals'], df_inv_fit['ped'],marker='o', label='Half_'+str(half))
                ax.plot(xs_inv, alpha_inv[0]*xs_inv + alpha_inv[1])

                #ax.plot(xs_inv, alpha_inv*xs_inv + beta_inv)
                ax.set_ylim(0,1023)

                fig.suptitle("pedestal_1D_vs_vrefinv_chip_"+str(chip),y=0.93)
                h, l = ax.get_legend_handles_labels()
                ax.legend(h, l)


                target_array = []
                target_x = []

                max_val = int(df_inv_fit['inv_vals'].max())
                min_val = int(df_inv_fit['inv_vals'].min())

                ax.set_xticks(range(min_val,max_val,50))
                ax.set_xticklabels(range(min_val,max_val,50),fontsize=8)

                for k in range(max_val - min_val):
                    target_x.append(k+min_val)
                    target_array.append(target)

                ax.plot(target_x, target_array,'k--')

                if half == 1:
                    fig.savefig("%s/pedestal_vs_vrefinv_chip%d.png"%(self.odir,chip),format='png',bbox_inches='tight') 
                    plt.close(fig)

                print("Finding fit parameters for vrefnoinv")
                xs_noinv, alpha_noinv, beta_noinv = self.fit( df_noinv_fit, 'ped', 'noinv_vals', 1, 1, chip, half, 0.002)
                print(xs_noinv)
                print(alpha_noinv)
                #print(beta_noinv) #Extra from lmfit

                #Plotting 1D variation in vrefinv (vrefnoinv fixed) along with linear fit
                ax1 = axes1[half]
                ax1.set_ylabel(r'Pedestal [ADC counts]')
                ax1.set_xlabel(r'NoInv vref ')
                ax1.xaxis.grid(True)

                ax1.scatter(df_noinv_fit['noinv_vals'], df_noinv_fit['ped'],marker='o', label='Half_'+str(half))
                ax1.plot(xs_noinv, alpha_noinv[0]*xs_noinv + alpha_noinv[1])

                #ax.plot(xs_noinv, alpha_noinv*xs_noinv + beta_noinv)
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

                #vinv_fit = (target - beta_inv)/alpha_inv
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

                nestedConf = analysis_misc.set_key_dict(nestedConf,[int(half),'ReferenceVoltage','sc',chip_key_name],['Inv_vref','Inv_slope','Inv_y_int','Noinv_vref','Noinv_slope','Noinv_y_int'],
                [int(vinv_final),round(float(alpha_inv[0]),3),round(float(alpha_inv[1]),3),int(vnoinv_final),round(float(alpha_noinv[0]),3),round(float(alpha_noinv[1]),3)])

                #nestedConf = analysis_misc.set_key_dict(nestedConf,[int(half),'ReferenceVoltage','sc',chip_key_name],['Inv_vref','Inv_slope','Inv_y_int','Noinv_vref','Noinv_slope','Noinv_y_int'],
                #[int(vinv_final),round(float(alpha_inv),3),round(float(beta_inv),3),int(vnoinv_final),round(float(alpha_noinv),3),round(float(beta_noinv),3)])

                nestedConf = analysis_misc.set_key_dict(nestedConf,['sc','chip_'+str(chip),'target_full'],['half_'+str(half)],
                [round(float(target),3)])

                cfg[chip_key_name]['sc']['ReferenceVoltage'][half]['Inv_vref'] = int(vinv_final)
                cfg[chip_key_name]['sc']['ReferenceVoltage'][half]['Noinv_vref'] = int(vnoinv_final)
            
                #nestedConf[chip_key_name]['sc']['ReferenceVoltage'][half]['Inv_vref'] = int(vinv_final)
                #nestedConf[chip_key_name]['sc']['ReferenceVoltage'][half]['Noinv_vref'] = int(vnoinv_final)

                
       
        configFile = configFile.replace('.yaml','')  
        #'''
        print(nestedConf.to_dict())        
        with open(odir+"Vref2D_fit.yaml", "w") as o:
            print(yaml.dump(nestedConf.to_dict(),o,sort_keys=False))
        
        print("Saved new config file as:"+"Vref2D_fit.yaml")    
        #'''    
        '''
        with open(configFile+"_vref2D_full_aligned.yaml", "w") as o:
            yaml.dump(cfg, o)
        
        print("Saved new config file as:"+configFile+"_vref2D_full_aligned.yaml")    
        '''

