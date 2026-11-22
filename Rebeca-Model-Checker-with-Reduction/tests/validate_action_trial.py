#!/usr/bin/env python3
"""Run the actual candidate trial loop: a rejected first action must not hide the next."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
s=(root/'src/main/resources/vtl/timedrebeca/analyzer/FTTSPatchTemplate.vm').read_text()
a=s.index('            for (size_t ci = 0; ci < candidates.size()')
b=s.index('        }\n        if (!reductionApplied)',a)
loop=s[a:b]
source=r'''
#include <vector>
#include <cassert>
#include <iostream>
using namespace std;
using TIME_TYPE=int;const int MAX_TIME=999,NEW_STATE=1;
struct Actor{unsigned char messageQueue[2]={1,2};int deadline[2]={999,999};const char* getName(){return "A";}const char* activeAction(){return "Run";}} actor;
struct Shift{int shift=0;};
struct State{int stateID=1,openCount=0,rebsIndex=0;Shift shiftTimes[1];} state,closed;
struct Current{State* state;int stateActiveBundleNumber=0,currentTime=0;} current;
struct DeadlineMissedException{DeadlineMissedException(const char*,Actor*){}};
struct PorCandidate{int actor,messageId;const char* proof;vector<int> alternatives;};
struct Checker{
 Actor* rebecs[1]={&actor};int calls=0,_porResult=0;bool doubleBranches=false;State* _porResultState=&closed;
 bool isEquivalentQueueAlternative(int,int){return false;}
 bool isPorCandidateFull(const PorCandidate&,int,int){return false;}
 bool isPorSuccessorAllowed(bool full){return full||(_porResult & NEW_STATE)||_porResultState->openCount>0;}
 void changeOrder(int,int k){if(k==1)swap(actor.messageQueue[0],actor.messageQueue[1]);}
 long executeRebec(int){calls++;_porResult=(actor.messageQueue[0]==2 || (doubleBranches && calls%2==0))?NEW_STATE:0;return doubleBranches && calls%2==1?1:0;}
 void unmarshalRebecs(int,int){actor.messageQueue[0]=1;actor.messageQueue[1]=2;}
 bool run(){int r=0,currentTime=0,highestPriority=0;bool reductionApplied=false,fullExpansion=false;
  vector<PorCandidate> candidates={{0,1,"test_certificate",{0}},{0,2,"test_certificate",{1}}};
  LOOP
  return reductionApplied;
 }
};
int main(){current.state=&state;Checker c;assert(c.run());assert(c.calls==2);Checker nd;nd.doubleBranches=true;assert(nd.run());assert(nd.calls==4);}
'''.replace('LOOP',loop)
with tempfile.TemporaryDirectory() as d:
 d=Path(d);p=d/'test.cpp';p.write_text(source)
 for opt in ('-O0','-O2'):
  for flags in ([],['-DPOR_DIAGNOSTICS']):
   subprocess.run(['g++','-std=c++11',opt,*flags,str(p),'-o',str(d/'test')],check=True)
   subprocess.run([str(d/'test')],check=True)
print('PASS: actual trial loop rejects closed first action and accepts the later certified action')
