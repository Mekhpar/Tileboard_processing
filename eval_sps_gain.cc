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
int npeaks_max = 30;
 Double_t multi_gauss(Double_t *x,Double_t *par)
 {
  Double_t func_val =0;
  //std::cout << "Entered function call " <<std::endl;
  for(int p=0; p<par[0]; p++)
  {
   //func_val += y_hgt[p]*pow(M_E,-(pow(x-x_pos[p],2)/2)); //sigma value = 2 initially
   double peak_cont=0.0;
   {
   //peak_cont = par[p+5]*pow(M_E,-(pow((x[0]-(p*par[1]+par[2])),2)/sqrt(pow(par[3],2)+p*pow(par[4],2))));
   peak_cont = par[2*p+3]*pow(M_E,-(pow((x[0]-(p*par[1]+par[2])),2)/(2*pow(par[2*p+4],2))));
   func_val += peak_cont; //sigma value = 2 initially
   }
  }
  return func_val;
 }

float fit_sps(int chan,int half_board, int sipm_bias)
{

 TFile *f = new TFile(Form("Tileboard_files/%iV_LED_scan/sampling_scan9.root",sipm_bias));
 //TFile *f = new TFile("Tileboard_files/Jan_22_1855/sampling_scan9.root");
 TTree *hgcroc = (TTree *)f->Get("unpacker_data/hgcroc");

 stringstream j_s_1;
 string entry_filter_string;
 j_s_1 << chan;
 j_s_1 >> entry_filter_string;

 stringstream j_s_2;
 string half_string;
 j_s_2 << half_board;
 j_s_2 >> half_string;

 TString cutstring = "channel == " + entry_filter_string;
 TString halfcutstring = "half == " + half_string;

 TCut cutch = cutstring.Data();
 TCut cuthalf = halfcutstring.Data();
 
 TCut cut_corr = "corruption == 0";

 string hist_string = "Channel_" + entry_filter_string + "_half_" + half_string + "_phase_9";
 TH1F* hist = new TH1F("hist",hist_string.c_str(), 1000, 0, 1000);
 TH1F* hist_1 = new TH1F("hist_1",hist_string.c_str(), 1000, 0, 1000); //Shifting by 1 ADC count for DNL correction 
 (hgcroc)->Draw("adc>>hist",cutch && cuthalf && cut_corr);
 (hgcroc)->Draw("adc+1>>hist_1",cutch && cuthalf && cut_corr); //Effectively shifting the histogram to the right by one bin
 hist->Add(hist_1);
 for(int xbins=0;xbins<hist->GetXaxis()->GetNbins();xbins++)
 {
  hist->SetBinContent(xbins+1,hist->GetBinContent(xbins+1)/2.);
 }

 hist->Draw("");


 //Finding number of peaks and their x positions using TSpectrum
 int npeaks = 20;
 TSpectrum *peakFind = new TSpectrum(npeaks);

 int nfound = peakFind->Search(hist,2);
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
  int bin_current = hist->GetXaxis()->FindBin(x_pos[p]);
  y_hgt[p] = hist->GetBinContent(bin_current);
 }
  for(int p=0; p<nfound; p++)
 {
  std::cout << "x position of peak " << p << " is " << x_pos[p] << " y position of peak " << p << " is " << y_hgt[p] << std::endl;
 }
 /*hist->GetXaxis()->SetRange(x_pos[0],x_pos[nfound]);
 TH1 *bkg = peakFind->Background(hist, 40, "nosmoothing");
 hist->Add(bkg,-1.);
 nfound = peakFind->Search(hist,2);
 std::cout << "Found new " << nfound << " peaks in the sps" << std::endl;
 */

 //Double_t par_x_y_s[3*nfound]; //Each peak has x center of the gaussian, the amplitude corresponding to the center, and the standard deviation
 Double_t gain_init = (x_pos[nfound-1]-x_pos[0])/(nfound-1);//initial guess of gain
 Double_t par_x_y_s[2*nfound+3];
 par_x_y_s[0] = nfound;
 par_x_y_s[1] = gain_init;
 par_x_y_s[2] = x_pos[0]; //Pedestal peak position, other peaks are not required because they can be found from this and gain
 //par_x_y_s[3] = gain_init/5;//sigma_0
 //par_x_y_s[4] = gain_init/20;//sigma_1
 for(int i=0;i<nfound;i++)
 {
   par_x_y_s[2*i+3] = y_hgt[i];
   par_x_y_s[2*i+4] = gain_init/5;
 }

  int par_size = sizeof(par_x_y_s)/sizeof(Double_t);
  std::cout << "Size of parameter array " << par_size << std::endl;
  Double_t x_arg = 470;
  //std::cout << multi_gauss(&x_pos[4],par_x_y_s) << std::endl;
  std::cout << multi_gauss(&x_arg,par_x_y_s) << std::endl;

  
  TF1 *func_fit = new TF1("function_fit",multi_gauss,0.,1000.,par_size);
  func_fit->FixParameter(0,par_x_y_s[0]);
  for(int i=1;i<par_size;i++)
  {
  func_fit->SetParameter(i,par_x_y_s[i]); //Only initial guess parameters, but to easily find those TSpectrum has been used
  }

  func_fit->SetParLimits(2,par_x_y_s[2]-par_x_y_s[4]/2.,par_x_y_s[2]+par_x_y_s[4]/2.);
  func_fit->SetParLimits(1,0.5*par_x_y_s[1],1.5*par_x_y_s[1]);
 for(int i=0;i<nfound;i++)
 {
  func_fit->SetParLimits(2*i+3,0.8*par_x_y_s[2*i+3],1.5*par_x_y_s[2*i+3]);
  func_fit->SetParLimits(2*i+4,0.1*par_x_y_s[2*i+4],3*par_x_y_s[2*i+4]);
 }
  ///*
  func_fit->Draw();
  
  hist->Fit("function_fit");
    TH1F* h_sps = (TH1F*) gROOT->FindObject("hist");
  h_sps->SetLineColor(kBlue);    
  int bin_min = h_sps->FindFirstBinAbove(0,1);
  int bin_max = h_sps->FindLastBinAbove(0,1);
  float sps_max = h_sps->GetMaximum();

  hist->GetXaxis()->SetRange(1*(bin_min)-20,1*(bin_max)+20);
  hist->Draw("same");
  
  TF1 *fit_final = hist->GetFunction("function_fit");
  float gain_fit = fit_final->GetParameter(1);
  return gain_fit;  
  //bkg->SetLineColor(kOrange);
  //bkg->Draw("same");
  //*/

}

  void eval_sps_gain(int chan_fit, int half_fit/*,int sipm_sps*/)
  {
    int s_b[4] = {44,45,46,47};
    float s_internal[4] = {40.95,41.94,42.91,43.91};
   //std::cout << "gain for " << sipm_sps << " V " << fit_sps(chan_fit,half_fit,sipm_sps) << std::endl;
   TGraph *gain_dependence = new TGraph();
   for(int i=0;i<4;i++)
   {
    std::cout << "Bias value is " << s_b[i] << " V" << std::endl;
    //std::cout << "gain for " << s_b[i] << " V " << fit_sps(chan_fit,half_fit,s_b[i]) << std::endl;
    //gain_dependence->SetPoint(i,s_b[i],fit_sps(chan_fit,half_fit,s_b[i]));
    gain_dependence->SetPoint(i,s_internal[i],fit_sps(chan_fit,half_fit,s_b[i]));
    gain_dependence->Draw("AP");
    gain_dependence->SetMarkerStyle(20);
    gain_dependence->SetMarkerSize(0.5);
    gain_dependence->SetMarkerColor(kBlue);
   }
 stringstream j_chan;
 string chan_str;
 j_chan << chan_fit;
 j_chan >> chan_str;

 stringstream j_half;
 string half_str;
 j_half << half_fit;
 j_half >> half_str;

    TF1  *f1 = new TF1("f1","[0]*x+[1]",30,50);
    gain_dependence->Fit(f1);
    //std::cout << "Slope " << [0] << " y-intercept " << [1] << std::endl;
    TH1F *hist_ov = gain_dependence->GetHistogram();
    hist_ov->GetXaxis()->SetTitle("SiPM bias (in V)");
    hist_ov->GetYaxis()->SetTitle("Gain from sps fit (in ADC counts)");
    string bkdn_title = "Breakdown voltage calculation for channel " + chan_str + " half " + half_str + " from extrapolation of gain vs sipm bias";
    hist_ov->SetTitle(bkdn_title.c_str());
    hist_ov->Draw("same");
    TF1 *fit_overvoltage = gain_dependence->GetFunction("f1");
    float bkdn_v = -(fit_overvoltage->GetParameter(1))/fit_overvoltage->GetParameter(0);
    std::cout << "Breakdown voltage " << bkdn_v << std::endl;
  }
