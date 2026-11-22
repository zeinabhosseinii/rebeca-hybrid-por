#!/usr/bin/env python3
from pathlib import Path
import tempfile,subprocess
root=Path(__file__).resolve().parents[1]
s=(root/'src/main/resources/vtl/timedrebeca/analyzer/FTTSPatchTemplate.vm').read_text()
def function(name):
 a=s.index('bool TimedModelChecker::'+name);b=s.index('\n}\n',a)+3;return s[a:b]
code=(function('isPorCandidateFull')+'\n'+function('isPorSuccessorAllowed')).replace('${cycleBarriersAllowed}','allowed').replace('\\#else','#else')
source=r'''
#include <vector>
#include <algorithm>
#include <cassert>
using namespace std;using TIME_TYPE=int;const int REBEC_COUNT=2,NEW_STATE=1;
bool allowed=true;
struct Actor{int messageQueue[3]={1,0,0},executionTime[3]={},now=0,priority=0;int getNow(){return now;}int getPriority(){return priority;}} actors[2];
struct State{int openCount=0;bool porFullExpanded=false;} state;
struct TimedModelChecker{
 struct PorCandidate{int actor,messageId;const char* proof;vector<int> alternatives;};
 Actor* rebecs[2]={&actors[0],&actors[1]};int _porResult=0;State* _porResultState=&state;int alternatives=1;
 int getNumberOfAlternatives(int,int){return alternatives;}
 bool isPorCandidateFull(const PorCandidate&,TIME_TYPE,int);bool isPorSuccessorAllowed(bool);
};
FUNCTIONS
int main(){TimedModelChecker c;
 assert(!c.isPorSuccessorAllowed(false)); // default/unprocessed is NOT a full barrier
 c._porResult=NEW_STATE;assert(c.isPorSuccessorAllowed(false));c._porResult=0;
 state.openCount=1;assert(c.isPorSuccessorAllowed(false));state.openCount=0;
 state.porFullExpanded=true;
#ifdef POR_LEGACY_PROVISO
 assert(!c.isPorSuccessorAllowed(false));assert(!c.isPorSuccessorAllowed(true));
#else
 assert(c.isPorSuccessorAllowed(false));allowed=false;assert(!c.isPorSuccessorAllowed(false));
 assert(c.isPorSuccessorAllowed(true));allowed=true;
#endif
 TimedModelChecker::PorCandidate candidate={0,1,"test",{0}};
 assert(!c.isPorCandidateFull(candidate,0,0));actors[1].messageQueue[0]=0;
 assert(c.isPorCandidateFull(candidate,0,0));c.alternatives=2;
 assert(!c.isPorCandidateFull(candidate,0,0));candidate.alternatives.push_back(1);
 assert(c.isPorCandidateFull(candidate,0,0));actors[1].messageQueue[0]=1;actors[1].executionTime[0]=2;
 assert(c.isPorCandidateFull(candidate,0,0));actors[1].executionTime[0]=0;
 assert(!c.isPorCandidateFull(candidate,0,0));
}
'''.replace('FUNCTIONS',code)
with tempfile.TemporaryDirectory() as d:
 d=Path(d);(d/'test.cpp').write_text(source)
 for opt in ('-O0','-O2'):
  for flags in ([],['-DPOR_LEGACY_PROVISO']):
   subprocess.run(['g++','-std=c++11',opt,*flags,str(d/'test.cpp'),'-o',str(d/'test')],check=True)
   subprocess.run([str(d/'test')],check=True)
print('PASS: actual proviso helpers; default/closed partial rejected, completed barrier gated, exhaustive and legacy controls')
