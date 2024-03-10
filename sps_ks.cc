#include "TStyle.h"
#include "TGraph.h"
#include "TH1.h"
#include "TCanvas.h"
#include "TPad.h"
#include "TAxis.h"
#include "TGaxis.h"
#include "TLegend.h"
#include <TMath.h>
#include <TString.h>
#include <vector>
#include <iostream>
#include <sstream>
#include <cmath>
#include <utility>
#include <fstream>
#include <algorithm>
#include <TMultiGraph.h>
#include <typeinfo>

int npeaks_max = 30;
 Double_t multi_gauss(Double_t *x,Double_t *par)
 {
  Double_t func_val =0;
  //std::cout << "Entered function call " <<std::endl;
  for(int p=0; p<par[0]; p++)
  {
   double peak_cont=0.0;
   peak_cont = par[2*p+3]*pow(M_E,-(pow((x[0]-(p*par[1]+par[2])),2)/(2*pow(par[2*p+4],2))));
   func_val += peak_cont; //sigma value = 2 initially
  }
  return func_val;
 }

 
 void fit_par(TH1F* hist_sps, Double_t *par_in)
 {
  int par_size = 2*par_in[0]+3;
  TF1 *func_fit = new TF1("function_fit",multi_gauss,0.,1000.,par_size);
  func_fit->FixParameter(0,par_in[0]);
  for(int i=1;i<par_size;i++)
  {
  func_fit->SetParameter(i,par_in[i]); //Only initial guess parameters, but to easily find those TSpectrum has been used
  }

  func_fit->SetParLimits(2,par_in[2]-par_in[4]/2.,par_in[2]+par_in[4]/2.);
  func_fit->SetParLimits(1,0.5*par_in[1],1.5*par_in[1]);
  //func_fit->SetParLimits(1,0.5*par_in[1],1.2*par_in[1]);
  int n_peaks_found = par_in[0];
 for(int i=0;i<n_peaks_found;i++)
 {
  func_fit->SetParLimits(2*i+3,0.8*par_in[2*i+3],1.5*par_in[2*i+3]);
  func_fit->SetParLimits(2*i+4,0.1*par_in[2*i+4],3*par_in[2*i+4]);
  //func_fit->SetParLimits(2*i+4,0.1*par_in[2*i+4],1.5*par_in[2*i+4]);
 }
    
 }
 


std::vector<float> peakfind(TH1F* hist_sps, float peak_ratio)
{
 //Finding number of peaks and their x positions using TSpectrum
 int npeaks = 20;
 TSpectrum *peakFind = new TSpectrum(npeaks);

 int nfound = peakFind->Search(hist_sps,2,"",peak_ratio);
 //int nfound = peakFind->Search(hist_sps,2); //Potentially bad fit
 std::cout << "Found " << nfound << " peaks in the sps" << std::endl;

 Double_t *xpeaks;
 xpeaks = peakFind->GetPositionX();

 //Get x position (mean) and height of each peak (looping over the set of peaks) to construct a Gaussian around it
 Double_t x_pos[nfound], y_hgt[nfound];
 for(int p=0; p<nfound; p++)
 {
  x_pos[p] = xpeaks[p];  
 }

 std::sort(x_pos,x_pos+nfound);
 for(int p=0; p<nfound; p++)
 {
  int bin_current = hist_sps->GetXaxis()->FindBin(x_pos[p]);
  y_hgt[p] = hist_sps->GetBinContent(bin_current);
 }
  for(int p=0; p<nfound; p++)
 {
  std::cout << "x position of peak " << p << " is " << x_pos[p] << " y position of peak " << p << " is " << y_hgt[p] << std::endl;
 }

 std::vector<float> x_y_pos;
 x_y_pos.push_back(nfound);
 for(int p=0;p<nfound;p++)
 {
  x_y_pos.push_back(x_pos[p]);
 }
 for(int p=0;p<nfound;p++)
 {
 x_y_pos.push_back(y_hgt[p]);
 }

 return x_y_pos;
}



std::vector<float> eval_sps(TH1F* hist_sps, int chan,int half_board, int phase, std::vector<float>*x_y_pos)
{
 int nfound = x_y_pos->at(0);

 float x_pos[nfound], y_hgt[nfound];

 for(int p=1;p<nfound+1;p++)
 {
  x_pos[p-1] = x_y_pos->at(p);
 }

 for(int p=nfound+1;p<2*nfound+1;p++)
 {
 y_hgt[p-nfound-1] = x_y_pos->at(p);
 }

  /*for(int p=1; p<nfound+1; p++)
 {
  std::cout << "Passed x position of peak " << p << " is " << x_y_pos->at(p) << " Passed y position of peak " << p << " is " << x_y_pos->at(p+nfound) << std::endl;
  std::cout << "Type of values " << p << " is " << typeid(x_y_pos->at(p)).name() << " Type of values " << p << " is " << typeid(x_y_pos->at(p+nfound)).name() << std::endl;

 }*/


 Double_t gain_1 = x_pos[1]-x_pos[0];
 Double_t gain_2 = x_pos[2]-x_pos[1];
 Double_t gain_3 = x_pos[3]-x_pos[2];


 //Double_t par_x_y_s[3*nfound]; //Each peak has x center of the gaussian, the amplitude corresponding to the center, and the standard deviation

 //Double_t gain_init = (x_pos[nfound-1]-x_pos[0])/(nfound-1);//initial guess of gain - DO NOT USE THIS - THE SPACING BETWEEN SOME OF THE LAST PEAKS IS QUITE HIGH!!!
 ///*
 Double_t gain_init = gain_1;//modified initial guess of gain, this is according to Malinda's code


 if(nfound>4)
 {
  if(gain_3 <= gain_2 && gain_3 <= gain_1)
  {
   gain_init = gain_3;
  }
  else if(gain_2 <= gain_3 && gain_2 <= gain_1)
  {
   gain_init = gain_2;
  }
  else if(gain_1 <= gain_2 && gain_1 <= gain_3)
  {
   gain_init = gain_1;
  }

 }
 //*/


 std::cout << "Initial guess for gain " << gain_init << std::endl;
 Double_t par_x_y_s[2*nfound+3];
 par_x_y_s[0] = nfound;
 par_x_y_s[1] = gain_init;
 par_x_y_s[2] = x_pos[0]; //Pedestal peak position, other peaks are not required because they can be found from this and gain
 for(int i=0;i<nfound;i++)
 {
   par_x_y_s[2*i+3] = y_hgt[i];
   par_x_y_s[2*i+4] = gain_init/5;
   //par_x_y_s[2*i+4] = gain_init/10;
 }

  int par_size = sizeof(par_x_y_s)/sizeof(Double_t);
  std::cout << "Size of parameter array " << par_size << std::endl;

  fit_par(hist_sps,par_x_y_s); //Setting the parameters and par limits for the first iteration
  ///*
  hist_sps->Fit("function_fit","R","",x_pos[0]-(1.5*gain_init/5),x_pos[nfound-1]+1.5*(gain_init/5));
  TF1 *fit_final = hist_sps->GetFunction("function_fit");
  Double_t fit_pars[par_size];
  int xfit_min = round(x_pos[0]-(1.5*gain_init/5));
  int xfit_max = round(x_pos[nfound-1]+1.5*(gain_init/5));

  for(int i=0;i<par_size;i++)
  {
   fit_pars[i] = fit_final->GetParameter(i);
   //std::cout << "Fitting parameters directly from function " << fit_pars[i] << std::endl;
  }  
  //*/
  
  double chi_2 = fit_final->GetChisquare();
  std::cout << "Chi_2 automated " << chi_2 << std::endl;
  std::cout << "Number of bins used for fitting " << x_pos[nfound-1]+.5*(gain_init/5) - x_pos[0] << std::endl;
  std::cout << "Number of fitting parameters " <<  par_size-1 << std::endl;

  std::vector<float> fit_val;
  /*fit_val.push_back(fit_pars[2]); //Pedestal
  fit_val.push_back(fit_pars[1]); //Gain
  fit_val.push_back(fit_pars[4]); //Pedestal stdddev
  fit_val.push_back(fit_pars[6]); //1 p.e. stddev
  */

  for(int i=0;i<par_size;i++)
  {
   fit_val.push_back(fit_pars[i]);
  }
  fit_val.push_back(chi_2); //Chi_2 value
  fit_val.push_back(xfit_min); //Bin lower limit i.e. from where fitting starts
  fit_val.push_back(xfit_max); //Bin upper limit i.e. where fitting stops
  //fit_val.push_back(par_size-1); //Number of free parameters

  return fit_val;
}


std::vector<float> make_cdf(std::vector<float>*pdf)
{
 std::vector<float> cdf;
 float cm_term=0;
 for(int i=0;i<pdf->size();i++)
 {
  cm_term+=pdf->at(i);
  cdf.push_back(cm_term);
  //std::cout << "Bin size " << i << " Cdf value " << cdf[i] << std::endl;
 }
 //std::cout << "Size of cdf " << cdf.size() << std::endl;
 return cdf;
}


std::vector<float> ks_calc(std::vector<float>*sps_val,std::vector<float>*fit_val, float fit_min, float fit_max, float half_binsize, int chan, int half_board, int phase)
{
 TCanvas *c2 = new TCanvas("c2","Graph Draw Options", 200,10,600,400); //represents coordinates of start and end points of canvas
 string hist_string = "Channel " + std::to_string(chan) + " half " + std::to_string(half_board) + " phase " + std::to_string(phase);

  std::vector<float> sps_cdf = make_cdf(sps_val);
  std::vector<float> fit_cdf = make_cdf(fit_val);
  TH1F* sps_cdf_hist = new TH1F("sps_cdf_hist",hist_string.c_str(), fit_max-fit_min, fit_min+half_binsize, fit_max+half_binsize);
  TH1F* fit_cdf_hist = new TH1F("fit_cdf_hist",hist_string.c_str(), fit_max-fit_min, fit_min+half_binsize, fit_max+half_binsize);

  for(int i=0;i<sps_val->size();i++)
  {
   sps_cdf_hist->SetBinContent(i+1,sps_cdf.at(i));
   fit_cdf_hist->SetBinContent(i+1,fit_cdf.at(i));
  }

 ///*  
 float norm_sps = sps_cdf.at(sps_cdf.size()-1);
 float norm_fit = fit_cdf.at(fit_cdf.size()-1);
 std::cout << "Normalization factors " << norm_sps << " " << norm_fit << std::endl;

 for(int xbins_fit=0;xbins_fit<sps_cdf_hist->GetXaxis()->GetNbins();xbins_fit++)
 {
  sps_cdf_hist->SetBinContent(xbins_fit+1,sps_cdf_hist->GetBinContent(xbins_fit+1)/norm_sps);
  fit_cdf_hist->SetBinContent(xbins_fit+1,fit_cdf_hist->GetBinContent(xbins_fit+1)/norm_fit);
 }

 int nbins_fit = sps_cdf_hist->GetXaxis()->GetNbins();
 Double_t a[nbins_fit], b[nbins_fit];
 float ks_dist = 0.;
 float dist = 0.;
 for(int xbins_fit=0;xbins_fit<sps_cdf_hist->GetXaxis()->GetNbins();xbins_fit++)
 {
  a[xbins_fit] = sps_cdf_hist->GetBinContent(xbins_fit+1);
  b[xbins_fit] = fit_cdf_hist->GetBinContent(xbins_fit+1);
  dist = abs(a[xbins_fit] - b[xbins_fit]);
  //std::cout << "K-S distance for bin " << xbins_fit+fit_min << " " << dist << std::endl;
  ks_dist =  TMath::Max(ks_dist,dist);
  //std::cout << "Current maximum " << ks_dist << std::endl;
 }
   //Double_t alpha = TMath::KolmogorovTest(nbins_fit,a,nbins_fit,b,"D");
  std::cout << "K-S significance value " << ks_dist << std::endl;
  Double_t z = ks_dist*TMath::Sqrt(norm_sps);
  std::cout << "Scaled K-S distance " << z << std::endl;
  float ks_prob = TMath::KolmogorovProb(z);
  std::cout << "K-S probability " << ks_prob << std::endl;
 //*/
  sps_cdf_hist->GetXaxis()->SetRange(fit_min-20,fit_max+20);
  sps_cdf_hist->Draw();
  fit_cdf_hist->Draw("same");
  //sps_cdf_hist->SetLineColor(kRed);
  //fit_cdf_hist->SetLineColor(kBlue);
  sps_cdf_hist->SetStats(0);
  auto legend_cdf = new TLegend (.1, .8, .4, .9);

  legend_cdf->AddEntry(sps_cdf_hist,"SPS value");
  legend_cdf->AddEntry(fit_cdf_hist,"Fit value");


  legend_cdf->SetTextSize(0.02);
  legend_cdf->Draw();
  string Cdf_ks = "SPS_Fit_Plots/46V_LED_scan/KS_plots/UMD Channel " + std::to_string(chan) + " half " + std::to_string(half_board) + " phase " + std::to_string(phase) + " K-S cdf.pdf";
  c2 -> Print(Cdf_ks.c_str()); //Copy canvas to pdf
  c2->Close();

  std::vector<float> ks_fit;
  ks_fit.push_back(ks_dist); //K-S distance
  ks_fit.push_back(ks_prob); //K-S p value
  return ks_fit;
}


void sps_ks(int chan,int half_board, int phase)
{
 //TFile *f = new TFile(Form("Tileboard_files/Oct_02/UMD_5800mV/sampling_scan%i.root",phase));
 TFile *f = new TFile("Tileboard_files/46V_LED_scan/sampling_scan9.root");
 TTree *hgcroc = (TTree *)f->Get("unpacker_data/hgcroc");
  TCanvas *c1 = new TCanvas("c1","Graph Draw Options", 200,10,600,400); //represents coordinates of start and end points of canvas

 TString cutstring = "channel == " + std::to_string(chan);
 TString halfcutstring = "half == " + std::to_string(half_board);

 TCut cutch = cutstring.Data();
 TCut cuthalf = halfcutstring.Data();
 
 TCut cut_corr = "corruption == 0";

 string hist_string = "Channel " + std::to_string(chan) + " half " + std::to_string(half_board) + " phase " + std::to_string(phase);
 TH1F* hist = new TH1F("hist",hist_string.c_str(), 1000, 0, 1000);
 TH1F* hist_1 = new TH1F("hist_1",hist_string.c_str(), 1000, 0, 1000); //Shifting by 1 ADC count for DNL correction 
 (hgcroc)->Draw("adc>>hist",cutch && cuthalf && cut_corr);
 (hgcroc)->Draw("adc+1>>hist_1",cutch && cuthalf && cut_corr); //Effectively shifting the histogram to the right by one bin
 ///*
 hist->Add(hist_1);
 for(int xbins=0;xbins<hist->GetXaxis()->GetNbins();xbins++)
 {
  hist->SetBinContent(xbins+1,hist->GetBinContent(xbins+1)/2.);
 }
 //*/
 hist->Draw("");

  TH1F* h_sps = (TH1F*) gROOT->FindObject("hist");
  h_sps->SetLineColor(kBlue);    
  int bin_min = h_sps->FindFirstBinAbove(0,1);
  int bin_max = h_sps->FindLastBinAbove(0,1);
  float sps_max = h_sps->GetMaximum();

 std::vector<float> x_pos;
 float peak_ratio_init = 0.02;
 x_pos = peakfind(hist,peak_ratio_init);

 std::vector<float> good_fit;
 good_fit = eval_sps(hist,chan,half_board,phase,&x_pos);
  float peak_ratio_final = peak_ratio_init;

 ///*
 float diff_ped = good_fit.at(2) - bin_min;
 std::cout << "Difference between fitted and 'true' pedestal is " << diff_ped << std::endl;
 std::cout << "Fitted gain "<< good_fit.at(1) << std::endl;
 int flag=0;
 float peak_ratio[3] = {0.015,0.01,0.005};

 int i=0;
 while(diff_ped>0.9*good_fit.at(1))
 {
  std::cout << "Potentially need to perform the fit again because the pedestal is wrong" << std::endl;
  std::cout << "Finding peaks and performing fit for " << peak_ratio[i] << std::endl;
  x_pos = peakfind(hist,peak_ratio[i]);
  good_fit = eval_sps(hist,chan,half_board,phase,&x_pos);
  diff_ped = good_fit.at(2) - bin_min;
 std::cout << "Difference between fitted and 'true' pedestal is " << diff_ped << std::endl;
 std::cout << "Fitted gain "<< good_fit.at(1) << std::endl;
 peak_ratio_final = peak_ratio[i];
 i++;
 if(i>=3)
 {
  break;
 }
 }
//*/
 std::cout << "Final peak ratio for fitting " << peak_ratio_final << std::endl;

 for(int i=0;i<good_fit.size();i++)
 {
  std::cout << "Returned fit vector " << good_fit[i] << std::endl;
 }


 Double_t fit_first[good_fit.size()-3];
 for(int i=0;i<good_fit.size()-3;i++)
 {
  fit_first[i] = good_fit[i];
 }
 
 std::vector<float> sps_val, fit_val;
  int fit_min = good_fit[good_fit.size()-2];
  //int fit_min = bin_min; //Extending to the real minimum to get the true picture of where the pedestal is
  int fit_max = good_fit[good_fit.size()-1];

  float half_binsize = 0.5;
 for(int i=fit_min;i<fit_max;i++)
 {
  Double_t i_arg = (i+half_binsize)*1.0;
  //std::cout << "Bin number " << i << std::endl;
  //std::cout << "SPS value " << hist->GetBinContent(i+1) << " Fit value " << multi_gauss(&i_arg,fit_first) << std::endl;
  sps_val.push_back(hist->GetBinContent(i+1));
  fit_val.push_back(multi_gauss(&i_arg,fit_first));
 }
 
  std::cout << "Array sizes for cdf " << sps_val.size() << " " << fit_val.size() << std::endl;

  /*hist->GetXaxis()->SetRange(1*(bin_min)-20,1*(bin_max)+20);
  hist->Draw("same");
  hist->GetXaxis()->SetTitle("ADC counts");
  hist->SetStats(0);*/
  TH1F* sps_cdf_hist = new TH1F("sps_cdf_hist",hist_string.c_str(), fit_max-fit_min, fit_min+half_binsize, fit_max+half_binsize);
  TH1F* fit_cdf_hist = new TH1F("fit_cdf_hist",hist_string.c_str(), fit_max-fit_min, fit_min+half_binsize, fit_max+half_binsize);
  for(int i=0;i<sps_val.size();i++)
  {
   sps_cdf_hist->SetBinContent(i+1,sps_val.at(i));
   fit_cdf_hist->SetBinContent(i+1,fit_val.at(i));
  }
  sps_cdf_hist->SetLineColor(kRed);
  fit_cdf_hist->SetLineColor(kBlue);

  sps_cdf_hist->GetXaxis()->SetRange(fit_min-20,fit_max+20);
  sps_cdf_hist->Draw();
  fit_cdf_hist->Draw("same");
  sps_cdf_hist->SetStats(0);
  auto legend = new TLegend (.6, .8, .9, .9);

  std::cout << good_fit[0] << " " << good_fit[1] << " " << good_fit[2] << " " << good_fit[3] << std::endl;
  legend->AddEntry(sps_cdf_hist,"SPS value");
  legend->AddEntry(fit_cdf_hist,"Fit value");

  legend->SetTextSize(0.02);
  legend->Draw();
  string Pdf_fit = "SPS_Fit_Plots/46V_LED_scan/PDF_plots/UMD Channel " + std::to_string(chan) + " half " + std::to_string(half_board) + " phase " + std::to_string(phase) + " SPS fit.pdf";
  c1 -> Print(Pdf_fit.c_str()); //Copy canvas to pdf

  std::vector<float> ks_fit_1;
  ks_fit_1 = ks_calc(&sps_val,&fit_val,fit_min,fit_max,half_binsize,chan,half_board,phase);
  ///*
  float peak_ratio_ks[6] = {0.002,0.01,0.02,0.03,0.05,0.07};
  int j = 0;
  while(ks_fit_1.at(1)<0.5)
  {
   std::cout << "K-S probability is small so performing the fit again " << std::endl;
  x_pos = peakfind(hist,peak_ratio_ks[j]);
  good_fit = eval_sps(hist,chan,half_board,phase,&x_pos);
  for(int i=0;i<good_fit.size()-3;i++)
  {
    fit_first[i] = good_fit[i];
  }

  fit_val.clear();
  for(int i=fit_min;i<fit_max;i++)
  {
    Double_t i_arg = (i+half_binsize)*1.0;
    fit_val.push_back(multi_gauss(&i_arg,fit_first));
  }

  ks_fit_1 = ks_calc(&sps_val,&fit_val,fit_min,fit_max,half_binsize,chan,half_board,phase);
  std::cout << "New probability value " << ks_fit_1.at(1) << std::endl;
  peak_ratio_final = peak_ratio_ks[j];
  std::cout << "Peak ratio for this fit " << peak_ratio_final << std::endl;
  j++;
  if(j>=6)
  {
    break;
  }
   
  }
  //*/

  good_fit.push_back(peak_ratio_final);
  std::cout << "K-s Fit size " << ks_fit_1.size() << std::endl;
  good_fit.push_back(ks_fit_1.at(0));
  good_fit.push_back(ks_fit_1.at(1));

  string Root_file_string = "Root_fit_files/46V_LED_scan/Ch_"+std::to_string(chan)+"_hf_"+std::to_string(half_board)+"_new_ks.root";
  TFile *file = TFile::Open(Root_file_string.c_str(),"recreate");
  TTree *Fit_param = new TTree("Fit_param","Fit parameter values");
  Fit_param->Print();
   
  float values/*, val_errors*/;
  Fit_param->Branch("Values", &(values),good_fit.size());
  //Fit_param->Branch("Val_errors", &(val_errors),2*nfound+3);
  
  for(int i=0;i<good_fit.size();i++)
  {
   values = good_fit.at(i);
   //val_errors = fit_final->GetParError(i);
   Fit_param->Fill();
  }

  Fit_param->Print();
  Fit_param->Write();

  ///*
  gApplication->Terminate();
  //*/

}
