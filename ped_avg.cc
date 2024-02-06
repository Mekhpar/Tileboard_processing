#include "TStyle.h"
#include "TGraph.h"
#include "TGraphErrors.h"
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

void print_vector_dt(vector<Double_t> const &ptrdt, std::ofstream& file_name) //function to print a vector of double (floating point numbers)
{
 for(unsigned int i=0; i<ptrdt.size(); i++)
 {
  file_name << ptrdt.at(i) << ' ';
 }
 file_name << endl;
}

void print_vector_it(vector<Int_t> const &ptrit) //function to print a vector of double (floating point numbers)
{
 for(unsigned int i=0; i<ptrit.size(); i++)
 {
  cout << ptrit.at(i) << ' ';
 }
 cout << endl;
}

void print_vector_vt(vector<vector<Double_t>> const &ptrvt) //function to print a vector of double (floating point numbers)
{
 std::ofstream file("Sorted_event_data_by_channel.txt");
 for(unsigned int i=0; i<ptrvt.size(); i++)
 {
  print_vector_dt(ptrvt.at(i), file);
 }
 file << endl;
 file.close();
}

float* ped_mean(int chan, int half_board, int sipm_bias)
{
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
 TH1F* hist = new TH1F("hist","hist", 1000, 0., 1000.);

TFile *f = new TFile(Form("pedestal_run_%iV_SiPM_bias.root",sipm_bias));
TTree *hgcroc_ped = (TTree *)f->Get("unpacker_data/hgcroc");
//TTree *hgcroc_ped = (TTree *)f->Get("runsummary/summary");

(hgcroc_ped)->Draw("adc>>hist",cutch && cuthalf && cut_corr);
TH1F* h_ped = (TH1F*) gROOT->FindObject("hist");
h_ped->SetLineColor(kRed);
//float ped_mean = h_ped->GetMean();
float ped_mean_dev[3];
ped_mean_dev[0] = h_ped->GetMean();
ped_mean_dev[1] = h_ped->GetRMS();
ped_mean_dev[2] = h_ped->Integral();

//std::cout << "Ped mean for channel " << chan << " in half " << half_board << " is " << ped_mean << std::endl;
return ped_mean_dev;
    /*
    int bin_min_ped = h_ped->FindFirstBinAbove(0,1);
    int bin_max_ped = h_ped->FindLastBinAbove(0,1);

    std::cout << "Channel number is " << chan <<" Bin min ped is " << bin_min_ped << " Bin max ped is " << bin_max_ped << std::endl;
    hist->GetXaxis()->SetRange(bin_min_ped-20,bin_max_ped+20);
    hist->Draw("same");   
    */
}

void ped_avg(int chan_fit, int half_fit)
{
  TCanvas *c1 = new TCanvas("c1","Graph Draw Options", 200,10,600,400); //represents coordinates of start and end points of canvas   
 TGraphErrors *pedestal_dependence = new TGraphErrors();
 int s_ped[5] = {10,20,30,40,46};
 for(int i=0;i<5;i++)
 {
 float* ped_val = ped_mean(chan_fit,half_fit,s_ped[i]);
//pedestal_dependence->SetPoint(i,s_ped[i],ped_val[0]);
pedestal_dependence->SetPoint(i,s_ped[i],ped_val[0]);
std::cout << "Number of events " << ped_val[2] << std::endl;
pedestal_dependence->SetPointError(i,0.,ped_val[1]/sqrt(ped_val[2]-1));

pedestal_dependence->Draw("AP");
pedestal_dependence->SetMarkerStyle(20);
pedestal_dependence->SetMarkerSize(0.5);
pedestal_dependence->SetMarkerColor(kBlue);

 }

 stringstream j_chan;
 string chan_str;
 j_chan << chan_fit;
 j_chan >> chan_str;

 stringstream j_half;
 string half_str;
 j_half << half_fit;
 j_half >> half_str;
TH1F *hist_iv = pedestal_dependence->GetHistogram();
//hist_iv->GetYaxis()->SetRangeUser(0.,600.);
hist_iv->GetXaxis()->SetTitle("SiPM bias (in V)");
hist_iv->GetYaxis()->SetTitle("Average pedestal over ~10000 events (in ADC counts)");
string iv_title = "Zoomed Variation of pedestal values vs sipm bias for channel " + chan_str + " half " + half_str;
hist_iv->SetTitle(iv_title.c_str());
hist_iv->Draw("same");

string Entry_index_time_gen = "Ped_IV_Plots/Jan_25/Channel " + chan_str + " half " + half_str + " variation of zoomed pedestal values vs sipm bias.pdf";
c1 -> Print(Entry_index_time_gen.c_str()); //Copy canvas to pdf
c1->Close();
gApplication->Terminate();

}
