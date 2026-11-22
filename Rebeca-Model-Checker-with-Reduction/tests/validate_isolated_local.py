#!/usr/bin/env python3
"""Compile the actual online selector with generated metadata fixtures; no full graph."""
from pathlib import Path
import re
import subprocess
import tempfile
root=Path(__file__).resolve().parents[1]
text=(root/'src/main/resources/vtl/timedrebeca/analyzer/FTTSPatchTemplate.vm').read_text()
a=text.index('int TimedModelChecker::chooseIsolatedLocalAlternative');b=text.index('\n}\n',a)+3
function=text[a:b].replace('$isolatedLocalAllowed','localAllowed').replace('$maxMsgIdPlusOne','4')
function=re.sub(r'    static const bool localSafe.*?\n    };','',function,flags=re.S)
function=re.sub(r'    static const bool localIndependent.*?\n    };','',function,flags=re.S)
assert '$' not in function
source=r'''
#include <cassert>
#include <iostream>
using namespace std;
typedef int TIME_TYPE;
const int REBEC_COUNT=2,MAX_TIME=999;
bool localAllowed=true,localSafe[2][4]={},localIndependent[2][4][4]={};
struct Actor {
 int maxParamLength=0,maxQueueLength=4,now=0;
 unsigned char messageQueue[4]={1,2,0,0};
 int executionTime[4]={},deadline[4]={MAX_TIME,MAX_TIME,MAX_TIME,MAX_TIME};
 int getNow(){return now;} const char* getName(){return "A";}
};
struct State{int stateID=1;} state;
class TimedModelChecker {
public:
 Actor actors[2];Actor* rebecs[2]={&actors[0],&actors[1]};
 struct Node {State* state;int currentTime;} current{&state,0};
 int alternatives=2;
 int getNumberOfAlternatives(int,int){return alternatives;}
 int chooseIsolatedLocalAlternative(int r,TIME_TYPE execTime);
 TimedModelChecker(){actors[1].messageQueue[0]=0;}
};
FUNCTION
int main(){
 localSafe[0][1]=localSafe[0][2]=true;
 localIndependent[0][1][2]=localIndependent[0][2][1]=true;
 TimedModelChecker c;
 assert(c.chooseIsolatedLocalAlternative(0,0)==0);
 localAllowed=false;assert(c.chooseIsolatedLocalAlternative(0,0)==-1);localAllowed=true;
 localIndependent[0][1][2]=localIndependent[0][2][1]=false;
 assert(c.chooseIsolatedLocalAlternative(0,0)==-1);
 localIndependent[0][1][2]=localIndependent[0][2][1]=true;
 localSafe[0][2]=false;assert(c.chooseIsolatedLocalAlternative(0,0)==-1);localSafe[0][2]=true;
 c.actors[1].messageQueue[0]=1;assert(c.chooseIsolatedLocalAlternative(0,0)==-1);c.actors[1].messageQueue[0]=0;
 c.actors[0].maxParamLength=1;assert(c.chooseIsolatedLocalAlternative(0,0)==-1);c.actors[0].maxParamLength=0;
 c.actors[0].executionTime[1]=1;assert(c.chooseIsolatedLocalAlternative(0,0)==-1);c.actors[0].executionTime[1]=0;
 c.actors[0].deadline[1]=MAX_TIME-1;assert(c.chooseIsolatedLocalAlternative(0,0)==-1);c.actors[0].deadline[1]=MAX_TIME;
 c.actors[0].now=1;assert(c.chooseIsolatedLocalAlternative(0,0)==-1);c.actors[0].now=0;
 c.current.currentTime=1;assert(c.chooseIsolatedLocalAlternative(0,0)==-1);c.current.currentTime=0;
 c.alternatives=1;assert(c.chooseIsolatedLocalAlternative(0,0)==-1);c.alternatives=2;
 c.actors[0].messageQueue[1]=1;assert(c.chooseIsolatedLocalAlternative(0,0)==-1);
 c.actors[0].messageQueue[1]=9;assert(c.chooseIsolatedLocalAlternative(0,0)==-1);
 cout<<"PASS: independent distinct handlers and conservative online fallback boundaries"<<endl;
}
'''.replace('FUNCTION',function)
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp)/'local.cpp';p.write_text(source)
 for opt in ['-O0','-O2']:
  subprocess.run(['g++','-std=c++11',opt,'-Wall','-Wextra','-Werror',str(p),'-o',str(Path(tmp)/'test')],check=True)
  subprocess.run([str(Path(tmp)/'test')],check=True)
