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
#include <TSystem.h>
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

void ped_corr(string title_path)
{
  int chan_canv_max = 16; 
 
 //TFile *f_1 = new TFile("20231121_191651_pedrun_bad.root");
 //TFile *f_1 = new TFile("pedestal_run_46V_SiPM_bias.root");
 string title = "Extended_ped_run/Feb_05_1406/" + title_path + ".root";
 TFile *f_1 = new TFile(title.c_str());
 TTree *hgcroc_ped = (TTree *)f_1->Get("unpacker_data/hgcroc");
  int chan, half_board;
for(int num_canv=1;num_canv<=5;num_canv++)
{
  
  TCanvas *c1 = new TCanvas("c1","Graph Draw Options", 200,10,600,400); //represents coordinates of start and end points of canvas
  c1->Divide(4,4); //16 in 1 canvas
  
  for(int chan_canv=1;chan_canv<=chan_canv_max;chan_canv++)
{
 chan = ((num_canv-1)*chan_canv_max+chan_canv-1)%39;
 half_board = ((num_canv-1)*chan_canv_max+chan_canv-1)/39;
 
 std::cout << "Channel number is " << chan << " Half board is " << half_board << std::endl;
 string hist_string = "Corrupted pedestals for channel " + std::to_string(chan) + " half " + std::to_string(half_board);
 TH1F* hist0 = new TH1F("hist0",hist_string.c_str(), 1000, 0, 1000);
 TH1F* hist0_dnl = new TH1F("hist0_dnl",hist_string.c_str(), 1000, 0, 1000);
 
 TH1F* hist1 = new TH1F("hist1",hist_string.c_str(), 1000, 0, 1000);
 TH1F* hist1_dnl = new TH1F("hist1_dnl",hist_string.c_str(), 1000, 0, 1000);

 TString cutstring = "channel == " + std::to_string(chan);
 TString halfcutstring = "half == " + std::to_string(half_board);

 TCut cutch = cutstring.Data();
 TCut cuthalf = halfcutstring.Data();
 
 TCut cut_corr = "corruption == 0";
 TCut cut_corr1 = "corruption != 0";

  c1->cd(chan_canv);
    std::cout << "Reached section " << chan_canv << std::endl;

  (hgcroc_ped)->Draw("adc>>hist0",cutch && cuthalf && cut_corr);
  (hgcroc_ped)->Draw("adc+1>>hist0_dnl",cutch && cuthalf && cut_corr); //Effectively shifting the histogram to the right by one bin
  
  
  hist0->Add(hist0_dnl);
  for(int xbins=0;xbins<hist0->GetXaxis()->GetNbins();xbins++)
 {
  hist0->SetBinContent(xbins+1,hist0->GetBinContent(xbins+1)/2.);
 }
 
  hist0->Draw("");
  
  int events_0 = hist0->Integral(0.,1000.);
  //std::cout << "Number of events in uncorrupted peak " << hist0->Integral(0.,1000.) << std::endl;
  TH1F* h_sps = (TH1F*) gROOT->FindObject("hist0");
  h_sps->SetLineColor(kBlue);    
  int bin_min = h_sps->FindFirstBinAbove(0,1);
  int bin_max = h_sps->FindLastBinAbove(0,1);

  float sps_max = h_sps->GetMaximum();

  (hgcroc_ped)->Draw("adc>>hist1",cutch && cuthalf && cut_corr1);
  (hgcroc_ped)->Draw("adc+1>>hist1_dnl",cutch && cuthalf && cut_corr1); //Effectively shifting the histogram to the right by one bin
    
  hist1->Add(hist1_dnl);
  for(int xbins1=0;xbins1<hist1->GetXaxis()->GetNbins();xbins1++)
 {
  hist1->SetBinContent(xbins1+1,hist1->GetBinContent(xbins1+1)/2.);
 }

  hist1->Draw("");
  int events_1 = hist1->Integral(0.,1000.);
  //std::cout << "Number of events in corrupted peak " << hist1->Integral(0.,1000.) << std::endl;
  TH1F* h_ped = (TH1F*) gROOT->FindObject("hist1");
  h_ped->SetLineColor(kRed);
  int bin_min_ped = h_ped->FindFirstBinAbove(0,1);
  int bin_max_ped = h_ped->FindLastBinAbove(0,1);

  float ped_max = h_ped->GetMaximum();

  float norm_fact = sps_max/ped_max;
  //h_ped->Scale(norm_fact,"nosw2");    
  //h_ped->Scale(0.3);
  if(events_1>0)
  {
  hist0->GetXaxis()->SetRange(std::min(bin_min,bin_min_ped)-20,std::max(bin_max,bin_max_ped)+20);
  hist0->Draw("");
  hist1->Draw("same");
  }
  else if(events_1==0)
  {
   hist0->GetXaxis()->SetRange(bin_min-20,bin_max+20);
  hist0->Draw("");
  }

  hist0->GetXaxis()->SetTitle("ADC counts");
  hist0->SetStats(0);
  //c1->BuildLegend();
  auto legend = new TLegend (.68, .8, .9, .9);
  legend->AddEntry(hist0,Form("Uncorrupted Pedestal peak (%i events)",events_0), "l");
  legend->AddEntry(hist1,Form("Corrupted Pedestal peak (%i events)",events_1), "l");
  legend->SetTextSize(0.015);
  legend->Draw();
}  

 const std::string output = "Extended_ped_Plots/Feb_05_1406/" + title_path;

   int dir_flag = gSystem->mkdir(output.c_str()); //makes directory, otherwise will return a -1 flag

    string Entry_index_time_gen = output + "/Pedestal peak corruption check for canvas "+ std::to_string(num_canv) + ".pdf";
    c1 -> Print(Entry_index_time_gen.c_str()); //Copy canvas to pdf
    c1->Close();
   
}
}

void ped_corr_cnv()
{
  std::string title;
TSystemDirectory dir("Extended_ped_run/Feb_05_1406/", "Extended_ped_run/Feb_05_1406/");
 TList *files = dir.GetListOfFiles();
  if (files) 
  {
     TSystemFile *file;
      TIter next(files);
       while ((file=(TSystemFile*)next())) 
       { 
        title = file->GetName();
     std::cout << "Name of title " << title << std::endl;
     if(title.find("ped.root")!=std::string::npos)
     {
      std::string arg = title.substr(0,23);
      std::cout << "Name of argument " << arg << std::endl;
      ped_corr(arg);
     }

       }
       }  
  /*const char* entry;
  std::cout << (char*)gSystem->GetDirEntry(dirp) << std::endl;
  while((entry) == (char*)gSystem->GetDirEntry(dirp))
  {
     title = entry;
     std::string arg = title.substr(23,5);
     std::cout << "Name of title " << title << std::endl;
     std::cout << "Name of argument " << arg << std::endl;
  }*/
 gApplication->Terminate();   
}

