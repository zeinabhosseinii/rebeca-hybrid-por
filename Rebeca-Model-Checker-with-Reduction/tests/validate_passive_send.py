#!/usr/bin/env python3
"""Compile the template's passive-send selector and test rejection boundaries."""
from pathlib import Path
import re,subprocess,tempfile
root=Path(__file__).resolve().parents[1]
s=(root/'src/main/resources/vtl/timedrebeca/analyzer/FTTSPatchTemplate.vm').read_text()
a=s.index('int TimedModelChecker::choosePassiveSendAlternative');b=s.index('\n}\n',a)+3
f=s[a:b].replace('$isolatedLocalAllowed','allowed').replace('$maxMsgIdPlusOne','4')
for name in ('pSafe','pPassive','pTarget','pMessage','pIndependent'):
 f=re.sub(r'    static const (?:bool|int) '+name+r'.*?\n    };','',f,flags=re.S)
assert '$' not in f
source=r'''
#include <cassert>
#include <iostream>
#include <cstring>
using namespace std;
typedef int TIME_TYPE;const int REBEC_COUNT=3,MAX_TIME=999;
bool allowed=true,pSafe[3][4]={},pPassive[3][4]={},pIndependent[3][4][4]={};
int pTarget[3][4],pMessage[3][4];
struct Actor {
 int maxParamLength=0,maxQueueLength=4,now=0,priority=7;
 unsigned char messageQueue[4]={};int executionTime[4]={};
 int deadline[4]={MAX_TIME,MAX_TIME,MAX_TIME,MAX_TIME};int messagePriorities[4]={9,9,9,9};
 int getNow(){return now;}int getPriority(){return priority;}const char* getName(){return "R";}
};
struct State{int stateID=1;}state;
class TimedModelChecker {
public:
 Actor actors[3];Actor* rebecs[3]={&actors[0],&actors[1],&actors[2]};
 struct Node{State* state;int currentTime;}current{&state,0};int alternatives=2;
 int getNumberOfAlternatives(int,int){return alternatives;}
 int choosePassiveSendAlternative(int r,TIME_TYPE execTime);
 TimedModelChecker(){actors[0].messageQueue[0]=1;actors[0].messageQueue[1]=2;}
};
FUNCTION
void reset(){
 allowed=true;memset(pSafe,0,sizeof(pSafe));memset(pPassive,0,sizeof(pPassive));
 memset(pIndependent,0,sizeof(pIndependent));
 for(int i=0;i<3;i++)for(int m=0;m<4;m++)pTarget[i][m]=pMessage[i][m]=-1;
 pSafe[0][1]=pSafe[0][2]=true;pPassive[1][1]=pPassive[2][1]=true;
 pTarget[0][1]=1;pTarget[0][2]=2;pMessage[0][1]=pMessage[0][2]=1;
 pIndependent[0][1][2]=pIndependent[0][2][1]=true;
}
int main(){
 reset();TimedModelChecker c;assert(c.choosePassiveSendAlternative(0,0)==0);
 allowed=false;assert(c.choosePassiveSendAlternative(0,0)==-1);allowed=true;
 pIndependent[0][1][2]=pIndependent[0][2][1]=false;assert(c.choosePassiveSendAlternative(0,0)==-1);reset();
 pSafe[0][2]=false;assert(c.choosePassiveSendAlternative(0,0)==-1);reset();
 pPassive[1][1]=false;assert(c.choosePassiveSendAlternative(0,0)==-1);reset();
 pTarget[0][1]=0;assert(c.choosePassiveSendAlternative(0,0)==-1);reset();
 c.actors[1].messageQueue[0]=1;c.actors[2].messageQueue[0]=1;
 assert(c.choosePassiveSendAlternative(0,0)==-1); // both candidate destinations occupied
 c.actors[2].messageQueue[0]=0;
 assert(c.choosePassiveSendAlternative(0,0)==1); // can choose the other empty destination
 c.actors[1].messageQueue[0]=0;
 c.actors[1].maxQueueLength=1;assert(c.choosePassiveSendAlternative(0,0)==-1);c.actors[1].maxQueueLength=4;
 c.actors[2].messageQueue[0]=3;assert(c.choosePassiveSendAlternative(0,0)==-1);c.actors[2].messageQueue[0]=0;
 c.actors[1].maxParamLength=1;assert(c.choosePassiveSendAlternative(0,0)==-1);c.actors[1].maxParamLength=0;
 c.actors[0].deadline[1]=MAX_TIME-1;assert(c.choosePassiveSendAlternative(0,0)==-1);c.actors[0].deadline[1]=MAX_TIME;
 c.actors[0].executionTime[1]=1;assert(c.choosePassiveSendAlternative(0,0)==-1);c.actors[0].executionTime[1]=0;
 c.actors[1].priority=8;assert(c.choosePassiveSendAlternative(0,0)==-1);c.actors[1].priority=7;
 c.actors[1].messagePriorities[1]=8;assert(c.choosePassiveSendAlternative(0,0)==-1);c.actors[1].messagePriorities[1]=9;
 c.actors[0].messageQueue[2]=2;c.alternatives=3;c.actors[2].maxQueueLength=2;
 assert(c.choosePassiveSendAlternative(0,0)==-1); // aggregate sends do not fit
 c.actors[0].messageQueue[2]=0;c.alternatives=2;c.actors[2].maxQueueLength=4;
 c.alternatives=1;assert(c.choosePassiveSendAlternative(0,0)==-1);c.alternatives=2;
 c.actors[0].messageQueue[1]=1;assert(c.choosePassiveSendAlternative(0,0)==-1);
 cout<<"PASS: passive sends, active/conflicting/occupied targets, queue bounds, time, priorities and fallback"<<endl;
}
'''.replace('FUNCTION',f)
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp)/'passive.cpp';p.write_text(source)
 for opt in ('-O0','-O2'):
  subprocess.run(['g++','-std=c++11',opt,'-Wall','-Wextra','-Werror',str(p),'-o',str(Path(tmp)/'test')],check=True)
  subprocess.run([str(Path(tmp)/'test')],check=True)
