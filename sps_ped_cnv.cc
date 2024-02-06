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

void sps_ped_cnv(int phase)
{
 int chan_canv_max = 16; 
 TFile *f = new TFile(Form("Tileboard_files/46V_LED_scan/sampling_scan%i.root",phase));
 TTree *hgcroc = (TTree *)f->Get("unpacker_data/hgcroc");

 TFile *f_1 = new TFile("pedestal_run_46V_SiPM_bias.root");
 TTree *hgcroc_ped = (TTree *)f_1->Get("unpacker_data/hgcroc");

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

 string hist_string = "Comparison of sps and pedestal values for channel " + entry_filter_string + " half " + half_string + " phase " + phase_string;
 TH1F* hist = new TH1F("hist",hist_string.c_str(), 1000, 0, 1000);
 TH1F* hist_dnl = new TH1F("hist_dnl",hist_string.c_str(), 1000, 0, 1000);
 
 TH1F* hist1 = new TH1F("hist1",hist_string.c_str(), 1000, 0, 1000);
 TH1F* hist1_dnl = new TH1F("hist1_dnl",hist_string.c_str(), 1000, 0, 1000);

 TString cutstring = "channel == " + entry_filter_string;
 TString halfcutstring = "half == " + half_string;

 TCut cutch = cutstring.Data();
 TCut cuthalf = halfcutstring.Data();
 
 TCut cut_corr = "corruption == 0";

  c1->cd(chan_canv);
    std::cout << "Reached section " << chan_canv << std::endl;
    ///*
  (hgcroc)->Draw("adc>>hist",cutch && cuthalf && cut_corr);
  (hgcroc)->Draw("adc+1>>hist_dnl",cutch && cuthalf && cut_corr); //Effectively shifting the histogram to the right by one bin
    
  hist->Add(hist_dnl);
  for(int xbins=0;xbins<hist->GetXaxis()->GetNbins();xbins++)
  {
  hist->SetBinContent(xbins+1,hist->GetBinContent(xbins+1)/2.);
  }

  hist->Draw("");
  int events_0 = hist->Integral(0.,1000.);

    TH1F* h_sps = (TH1F*) gROOT->FindObject("hist");
    h_sps->SetLineColor(kBlue);    
    int bin_min = h_sps->FindFirstBinAbove(0,1);
    int bin_max = h_sps->FindLastBinAbove(0,1);
 
    float sps_max = h_sps->GetMaximum();
  (hgcroc_ped)->Draw("adc>>hist1",cutch && cuthalf && cut_corr);
  (hgcroc_ped)->Draw("adc+1>>hist1_dnl",cutch && cuthalf && cut_corr); //Effectively shifting the histogram to the right by one bin
    
  hist1->Add(hist1_dnl);
  for(int xbins1=0;xbins1<hist1->GetXaxis()->GetNbins();xbins1++)
 {
  hist1->SetBinContent(xbins1+1,hist1->GetBinContent(xbins1+1)/2.);
 }

  hist1->Draw("");
  int events_1 = hist1->Integral(0.,1000.);

    TH1F* h_ped = (TH1F*) gROOT->FindObject("hist1");
    h_ped->SetLineColor(kRed);
    int bin_min_ped = h_ped->FindFirstBinAbove(0,1);
    int bin_max_ped = h_ped->FindLastBinAbove(0,1);

    float ped_max = h_ped->GetMaximum();

    float norm_fact = sps_max/ped_max;
    h_ped->Scale(norm_fact,"nosw2");    
    //h_ped->Scale(0.3);
    hist->GetXaxis()->SetRange(std::min(bin_min,bin_min_ped)-20,std::max(bin_max,bin_max_ped)+20);
    hist->Draw("");
    hist1->Draw("same");
  hist->GetXaxis()->SetTitle("ADC counts");
  hist->SetStats(0);
  //c1->BuildLegend();
  auto legend = new TLegend (.6, .8, .9, .9);
  legend->AddEntry(hist,Form("SPS for %i events",events_0), "l");
  legend->AddEntry(hist1,Form("Pedestal distribution for %i events",events_1), "l");
  legend->SetTextSize(0.02);
  legend->Draw();

}
    
    string Entry_index_time_gen ="Sps_plots/46V_LED_scan/Comparison of SPS and pedestal values for canvas "+ canvas_string + " for phase "+ phase_string + ".pdf";
    c1 -> Print(Entry_index_time_gen.c_str()); //Copy canvas to pdf
    c1->Close();
    
}
//f->Close();
}
