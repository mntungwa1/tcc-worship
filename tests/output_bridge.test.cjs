const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const {createTccOutputBridge}=require('../output_bridge.js');

function environment(){
 const channels=[],windows=new Map();let created=0;
 class Channel{
  constructor(name){this.name=name;channels.push(this);}
  postMessage(data){for(const peer of [...channels])if(peer!==this&&!peer.closed&&peer.name===this.name)peer.onmessage?.({data});}
  close(){this.closed=true;}
 }
 function element(tag){return {tagName:tag.toUpperCase(),style:{},children:[],clientWidth:1280,clientHeight:720,scrollHeight:100,scrollWidth:100,
  append(child){this.children.push(child);child.parentElement=this;this.onappend?.(child);},
  replaceChildren(){this.children=[];},querySelector(tag){return this.children.find(x=>x.tagName===tag.toUpperCase())||null;},querySelectorAll(){return this.children.filter(x=>x.className==='words');}};}
 function popup(){
  const nodes={};for(const id of ['external','stage','full','sound'])nodes[id]=element('div');
  const listeners={};
  const w={closed:false,focus(){this.focusCount=(this.focusCount||0)+1;},setInterval(){return 1;},clearInterval(){},addEventListener(name,fn){listeners[name]=fn;},requestAnimationFrame(fn){fn();}};
  const doc={open(){},write(){},close(){},getElementById(id){return nodes[id];},createElement:element,body:element('body'),documentElement:{requestFullscreen(){return Promise.resolve();}}};
  w.document=doc;w.nodes=nodes;
  doc.body.onappend=script=>vm.runInNewContext(script.textContent,{window:w,document:doc,BroadcastChannel:Channel,Date});
  return w;
 }
 function host(){return {BroadcastChannel:Channel,setInterval(){return 1;},clearInterval(){},addEventListener(){},open(url,name){let w=windows.get(name);if(!w||w.closed){w=popup();windows.set(name,w);created++;}return w;}};}
 return {host,windows,created:()=>created};
}

function controller(env,session='church-one'){
 let state={item:{id:'one',title:'First song',kind:'song',credit:''},slide:{text:'First lyric'},slideIndex:0,blank:false,theme:{background:'#101d35',font_size:54},title:'Service',next:'Next lyric'};
 let restores=0;
 const bridge=createTccOutputBridge({session,css:'',getPacket:()=>state,onRestore:packet=>{state=packet;restores++;},onNavigate(){},onStatus(){},onError:message=>{throw Error(message);}},env.host());
 return {bridge,set(packet){state={...state,...packet};},get:()=>state,restores:()=>restores};
}

test('Open projector reuses one window and live songs update it',()=>{
 const env=environment(),desk=controller(env);
 desk.bridge.open(false);desk.bridge.open(false);
 assert.equal(env.created(),1);
 const output=[...env.windows.values()][0];
 assert.equal(output.tccOutput.snapshot().slide.text,'First lyric');
 desk.set({item:{id:'two',title:'Second song',kind:'song'},slide:{text:'Second lyric'}});
 desk.bridge.publish(desk.get());
 assert.equal(output.tccOutput.snapshot().slide.text,'Second lyric');
 desk.bridge.open(false);assert.equal(env.created(),1);
});

test('A refreshed controller restores and updates the same open projector without reopening',()=>{
 const env=environment(),first=controller(env);first.bridge.open(false);
 const output=[...env.windows.values()][0];first.bridge.close();
 const refreshed=controller(env);
 assert.equal(refreshed.restores(),1);
 assert.equal(refreshed.get().slide.text,'First lyric');
 refreshed.set({slide:{text:'Song after desk refresh'}});refreshed.bridge.publish(refreshed.get());
 assert.equal(output.tccOutput.snapshot().slide.text,'Song after desk refresh');
 refreshed.bridge.open(false);assert.equal(env.created(),1);
});

test('Stage and projector are separate, closed outputs reopen, and sessions stay isolated',()=>{
 const env=environment(),desk=controller(env);desk.bridge.open(false);desk.bridge.open(true);
 assert.equal(env.created(),2);
 const another=controller(env,'another-church');another.bridge.open(false);assert.equal(env.created(),3);
 const output=[...env.windows.values()][0];output.closed=true;desk.bridge.open(false);assert.equal(env.created(),4);
});
