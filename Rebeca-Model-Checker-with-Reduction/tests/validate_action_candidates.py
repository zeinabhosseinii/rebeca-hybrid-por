#!/usr/bin/env python3
"""Compile the actual candidate collector; reject unsupported method splitting."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[1]
s=(root/'src/main/resources/vtl/timedrebeca/analyzer/FTTSPatchTemplate.vm').read_text()
a=s.index('std::vector<TimedModelChecker::PorCandidate> TimedModelChecker::collectPorCandidates')
b=s.index('\n}\n',a)+3
function=s[a:b]
source=r'''
#include <vector>
#include <cassert>
#include <cstring>
using namespace std;
typedef int TIME_TYPE;
struct Actor { unsigned char messageQueue[5]={1,2,3,0,0}; } actor;
class TimedModelChecker {
public:
 struct PorCandidate {int actor,messageId;const char* proof;vector<int> alternatives;};
 Actor* rebecs[1]={&actor};vector<int> local,passive;bool global=true;int count=3;
 int next(vector<int>& set,int start){for(int k:set)if(k>=start)return k;return -1;}
 int chooseIsolatedLocalAlternative(int,TIME_TYPE,int first){return next(local,first);}
 int choosePassiveSendAlternative(int,TIME_TYPE,int first){return next(passive,first);}
 bool areAllActiveAlternativesSafe(int,TIME_TYPE){return global;}
 int getNumberOfAlternatives(int,TIME_TYPE){return count;}
 vector<PorCandidate> collectPorCandidates(int,TIME_TYPE);
};
FUNCTION
int main(){
 TimedModelChecker c;c.local={0,2};
 auto v=c.collectPorCandidates(0,0);assert(v.size()==2);
 assert(v[0].messageId==1 && v[0].alternatives==vector<int>({0}));
 assert(v[1].messageId==3 && v[1].alternatives==vector<int>({2}));
 // A rejected first certificate need not discard the later certified action.
 int selected=-1;for(auto& candidate:v){bool proviso=candidate.messageId!=1;if(proviso){selected=candidate.messageId;break;}}
 assert(selected==3);
 c.local.clear();c.passive={1,2};v=c.collectPorCandidates(0,0);
 assert(v.size()==2 && strcmp(v[0].proof,"passive_send")==0);
 c.passive.clear();v=c.collectPorCandidates(0,0);
 assert(v.size()==1 && v[0].messageId==0 && strcmp(v[0].proof,"unsplit_actor_union")==0);
 assert(v[0].alternatives==vector<int>({0,1,2}));
 c.global=false;assert(c.collectPorCandidates(0,0).empty());
 c.global=true;actor.messageQueue[1]=actor.messageQueue[2]=1;
 v=c.collectPorCandidates(0,0);
 assert(v.size()==1 && v[0].messageId==1);
 // Same method does not imply same parameters: keep ALL queue outcomes here.
 assert(v[0].alternatives==vector<int>({0,1,2}));
}
'''.replace('FUNCTION',function)
with tempfile.TemporaryDirectory() as d:
 d=Path(d);p=d/'test.cpp';p.write_text(source)
 for opt in ('-O0','-O2'):
  subprocess.run(['g++','-std=c++11',opt,'-Wall','-Wextra','-Werror',str(p),'-o',str(d/'test')],check=True)
  subprocess.run([str(d/'test')],check=True)
print('PASS: explicit actions, all certified candidates, later selection, actor-union fallback and retained branches')
