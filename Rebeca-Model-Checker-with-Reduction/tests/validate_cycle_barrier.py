#!/usr/bin/env python3
from pathlib import Path
import tempfile,subprocess
from run_cycle_barriers import ROOT, generate

def helpers(directory, model, tracked):
 generate(model,model.stem,'aria_ast',directory)
 source=(directory/'TimedModelChecker.cpp').read_text()
 names=['isPorCandidateFull','isPorSuccessorAllowed']
 if tracked:
  names.insert(1,'closesPartialCycle')
 functions=[]
 for name in names:
  start=source.index('bool TimedModelChecker::'+name)
  end=source.index('\n}\n',start)+3
  functions.append(source[start:end])
 return '\n'.join(functions)

source=r'''
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <algorithm>
#include <cassert>
using namespace std;using TIME_TYPE=int;const int REBEC_COUNT=2,NEW_STATE=1;
struct Actor{int messageQueue[3]={1,0,0},executionTime[3]={},now=0,priority=0;int getNow(){return now;}int getPriority(){return priority;}} actors[2];
struct TimedBFSState{int openCount=0;bool porFullExpanded=false;} state, target, intermediate;
struct Current{TimedBFSState* state;} current{&state};
struct TimedModelChecker{
 struct PorCandidate{int actor,messageId;const char* proof;vector<int> alternatives;};
 Actor* rebecs[2]={&actors[0],&actors[1]};int _porResult=0;TimedBFSState* _porResultState=&state;int alternatives=1;
 int getNumberOfAlternatives(int,int){return alternatives;}
 unordered_map<TimedBFSState*, vector<TimedBFSState*> > partialSuccessors;
 bool closesPartialCycle(TimedBFSState*) const;
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
 assert(c.isPorSuccessorAllowed(false)==TRACKED);
 assert(c.isPorSuccessorAllowed(true));
 c._porResultState=&target;
 assert(!c.isPorSuccessorAllowed(false));
 c.partialSuccessors[&target]={};
 assert(c.isPorSuccessorAllowed(false)==TRACKED);
 c.partialSuccessors[&target]={&intermediate};
 c.partialSuccessors[&intermediate]={&state};
 assert(!c.isPorSuccessorAllowed(false));
 c.partialSuccessors.erase(&intermediate);
 assert(c.isPorSuccessorAllowed(false)==TRACKED);
#endif
 TimedModelChecker::PorCandidate candidate={0,1,"test",{0}};
 assert(!c.isPorCandidateFull(candidate,0,0));actors[1].messageQueue[0]=0;
 assert(c.isPorCandidateFull(candidate,0,0));c.alternatives=2;
 assert(!c.isPorCandidateFull(candidate,0,0));candidate.alternatives.push_back(1);
 assert(c.isPorCandidateFull(candidate,0,0));actors[1].messageQueue[0]=1;actors[1].executionTime[0]=2;
 assert(c.isPorCandidateFull(candidate,0,0));actors[1].executionTime[0]=0;
 assert(!c.isPorCandidateFull(candidate,0,0));
}
'''
with tempfile.TemporaryDirectory() as d:
 d=Path(d)
 for model,tracked in ((ROOT/'tests/fixtures/PartialLoop.rebeca',True),
                       (ROOT/'tests/fixtures/QuiescenceFuturePending.rebeca',False)):
  code=helpers(d/model.stem,model,tracked)
  (d/'test.cpp').write_text(source.replace('FUNCTIONS',code).replace('TRACKED',str(tracked).lower()))
  for opt in ('-O0','-O2'):
   for flags in ([],['-DPOR_LEGACY_PROVISO']):
    subprocess.run(['g++','-std=c++11',opt,*flags,str(d/'test.cpp'),'-o',str(d/'test')],check=True)
    subprocess.run([str(d/'test')],check=True)
print('PASS: generated proviso helpers, real partial cycle, full barrier, and conservative gates')
