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

void sps_cnv(int phase)
{
 int chan_canv_max = 16; 
 TFile *f = new TFile(Form("Tileboard_files/Feb_01_1615/sampling_scan%i.root",phase));
 //TFile *f = new TFile("20231219_151439_sampling_scan9.root"); //- very good sps, 45.2 V external but slow control bias is still ~43.8 V (same as with adapter)
 //TFile *f = new TFile("20231219_153632_sampling_scan9.root"); //ok sps, 44 V external, but internal is 42.7 V
 //TFile *f = new TFile("20231219_232651_sampling_scan25.root");
 //TFile *f = new TFile("20231219_233956_sampling_scan25.root");
 TTree *hgcroc = (TTree *)f->Get("unpacker_data/hgcroc");

  int chan, half_board;
 stringstream j_s_3;
 string phase_string;
 j_s_3 << phase;
 j_s_3 >> phase_string;


for(int num_canv=1;num_canv<=5;num_canv++)
{
  
 stringstream j_s;
 string canvas_string;
 j_s << num_canv;
 j_s >> canvas_string;

  TCanvas *c1 = new TCanvas("c1","Graph Draw Options", 200,10,600,400); //represents coordinates of start and end points of canvas
  c1->Divide(4,4); //16 in 1 canvas
  
  for(int chan_canv=1;chan_canv<=chan_canv_max;chan_canv++)
{
 chan = ((num_canv-1)*chan_canv_max+chan_canv-1)%39;
 half_board = ((num_canv-1)*chan_canv_max+chan_canv-1)/39;
 
 std::cout << "Channel number is " << chan << " Half board is " << half_board << std::endl;

 stringstream j_s_1;
 string entry_filter_string;
 j_s_1 << chan;
 j_s_1 >> entry_filter_string;

 stringstream j_s_2;
 string half_string;
 j_s_2 << half_board;
 j_s_2 >> half_string;

 string hist_string = "SPS for channel " + entry_filter_string + " half " + half_string + " phase " + phase_string;
 TH1F* hist = new TH1F("hist",hist_string.c_str(), 1000, 0, 1000);
 TH1F* hist_1 = new TH1F("hist_1",hist_string.c_str(), 1000, 0, 1000);

 TString cutstring = "channel == " + entry_filter_string;
 TString halfcutstring = "half == " + half_string;

 TCut cutch = cutstring.Data();
 TCut cuthalf = halfcutstring.Data();
 
 TCut cut_corr = "corruption == 0";

  c1->cd(chan_canv);
  //TFile *f = new TFile(Form("Tileboard_files/Oct_02/UMD_5800mV/sampling_scan%i.root",i));
  //TFile *f = new TFile(Form("Tileboard_files/UMDTBT_5800mV_10062023_ver1/sampling_scan%i.root",i));
    std::cout << "Reached section " << chan_canv << std::endl;
    ///*
    (hgcroc)->Draw("adc>>hist",cutch && cuthalf && cut_corr);
  (hgcroc)->Draw("adc+1>>hist_1",cutch && cuthalf && cut_corr); //Effectively shifting the histogram to the right by one bin
    
  //Actual correction
  
  hist->Add(hist_1);
  for(int xbins=0;xbins<hist->GetXaxis()->GetNbins();xbins++)
 {
  hist->SetBinContent(xbins+1,hist->GetBinContent(xbins+1)/2.);
 }

  hist->Draw("");
  


    TH1F* h_sps = (TH1F*) gROOT->FindObject("hist");
    h_sps->SetLineColor(kBlue);    
    int bin_min = h_sps->FindFirstBinAbove(0,1);
    int bin_max = h_sps->FindLastBinAbove(0,1);
 
    float sps_max = h_sps->GetMaximum();
    hist->GetXaxis()->SetRange(bin_min-20,bin_max+20);
    hist->Draw("same");
    hist->GetXaxis()->SetTitle("ADC counts");
    hist->SetStats(0);


}
    
    string Entry_index_time_gen ="Sps_plots/Feb_01_1615/SPS with DNL correction for canvas "+ canvas_string + " for phase " + phase_string + ".pdf";
    c1 -> Print(Entry_index_time_gen.c_str()); //Copy canvas to pdf
    c1->Close();
    
}
//f->Close();
}
