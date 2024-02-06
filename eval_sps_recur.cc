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
  int n_peaks_found = par_in[0];
 for(int i=0;i<n_peaks_found;i++)
 {
  func_fit->SetParLimits(2*i+3,0.8*par_in[2*i+3],1.5*par_in[2*i+3]);
  func_fit->SetParLimits(2*i+4,0.1*par_in[2*i+4],3*par_in[2*i+4]);
 }
    
 }
 

void eval_sps_recur(int chan,int half_board, int phase)
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
 
 //Background subtraction for peaks which initially have weird fits
 ///*
 hist->GetXaxis()->SetRange(x_pos[0]-0.5,x_pos[nfound-1]+1.5*2.0);
 TH1 *bkg = peakFind->Background(hist, 40, "nosmoothing");
 hist->Add(bkg,-1.);
 nfound = peakFind->Search(hist,2);
 std::cout << "Found new " << nfound << " peaks in the sps" << std::endl;
 //*/

 //Double_t par_x_y_s[3*nfound]; //Each peak has x center of the gaussian, the amplitude corresponding to the center, and the standard deviation
 Double_t gain_init = (x_pos[nfound-1]-x_pos[0])/(nfound-1);//initial guess of gain
 Double_t par_x_y_s[2*nfound+3];
 par_x_y_s[0] = nfound;
 par_x_y_s[1] = gain_init;
 par_x_y_s[2] = x_pos[0]; //Pedestal peak position, other peaks are not required because they can be found from this and gain
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

  fit_par(hist,par_x_y_s); //Setting the parameters and par limits for the first iteration
  ///*
  hist->Fit("function_fit","R","",x_pos[0]-(gain_init/5),x_pos[nfound-1]+1.5*(gain_init/5));
  TF1 *fit_final = hist->GetFunction("function_fit");
  Double_t fit_pars[par_size];
  for(int i=0;i<par_size;i++)
  {
   fit_pars[i] = fit_final->GetParameter(i);
   std::cout << "Fitting parameters directly from function " << fit_pars[i] << std::endl;
  }  
  //*/

  //Possibly a second fit iteration using the fitting parameters as the initial guesses
  /*
 fit_par(hist,fit_pars); //Setting the parameters and par limits for the first iteration
  float xlow = fit_final->GetParameter(2) - fit_final->GetParameter(4);
  float xhigh = fit_final->GetParameter(2) + (nfound-1)*fit_final->GetParameter(1) + fit_final->GetParameter(nfound*2+2);  
  hist->Fit("function_fit","R","",x_pos[0]-(gain_init/5),x_pos[nfound-1]+1.5*(gain_init/5));
  TF1 *fit_1 = hist->GetFunction("function_fit");
  Double_t fit_pars_1[par_size];
  for(int i=0;i<par_size;i++)
  {
   fit_pars_1[i] = fit_1->GetParameter(i);
   std::cout << "Fitting parameters directly from function for second iteration " << fit_pars_1[i] << std::endl;
  }  
  */

  TH1F* h_sps = (TH1F*) gROOT->FindObject("hist");
  h_sps->SetLineColor(kBlue);    
  int bin_min = h_sps->FindFirstBinAbove(0,1);
  int bin_max = h_sps->FindLastBinAbove(0,1);
  float sps_max = h_sps->GetMaximum();

  hist->GetXaxis()->SetRange(1*(bin_min)-20,1*(bin_max)+20);
  //hist->Add(bkg);
  hist->Draw("same");
  hist->GetXaxis()->SetTitle("ADC counts");
  hist->SetStats(0);
  auto legend = new TLegend (.6, .8, .9, .9);
  
  legend->AddEntry(hist,Form("Gain = %f",fit_pars[1]),"");
  legend->AddEntry(hist,Form("Pedestal peak stddev = %f",fit_pars[4]),"");
  legend->AddEntry(hist,Form("First p.e. peak stddev = %f",fit_pars[6]),"");

  legend->SetTextSize(0.02);
  legend->Draw();
  
  /*
  string Entry_index_time_gen = "SPS_Fit_Plots/Jan_22_1855/UMD Channel " + std::to_string(chan) + " half " + std::to_string(half_board) + " phase " + std::to_string(phase) + " fitting of sps.pdf";
  c1 -> Print(Entry_index_time_gen.c_str()); //Copy canvas to pdf
  c1->Close();
  gApplication->Terminate();
  */
}
