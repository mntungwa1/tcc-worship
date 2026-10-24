/* Shared background layer; retain a looping video while text slides change. */
function tccBackground(root, theme) {
  const doc=root.ownerDocument||document;
  const background=theme.background_media;
  if(!background?.src){root.replaceChildren();return;}
  for(const child of Array.from(root.children)){
    if(child.className!=='background-media'&&child.className!=='background-shade')child.remove();
  }
  let media=root.querySelector('.background-media');
  if(media&&(media.getAttribute('src')!==background.src||media.tagName!==(background.kind==='video'?'VIDEO':'IMG'))){media.remove();media=null;}
  if(!media){
    media=doc.createElement(background.kind==='video'?'video':'img');
    media.className='background-media';media.src=background.src;
    Object.assign(media.style,{position:'absolute',inset:'0',width:'100%',height:'100%',objectFit:'cover',zIndex:'0',pointerEvents:'none'});
    if(background.kind==='video'){media.muted=true;media.autoplay=true;media.loop=true;media.playsInline=true;}
    else media.alt='';
    root.append(media);
    if(background.kind==='video')media.play().catch(()=>{});
  }
  let shade=root.querySelector('.background-shade');
  if(!shade){shade=doc.createElement('div');shade.className='background-shade';root.append(shade);}
  Object.assign(shade.style,{position:'absolute',inset:'0',background:'#000',opacity:String(theme.background_overlay??0.45),zIndex:'1',pointerEvents:'none'});
}

/* Keep projector windows connected when Streamlit recreates the controller iframe. */
function createTccOutputBridge(options, host = window) {
  const session = options.session;
  const token = Date.now().toString(36) + Math.random().toString(36).slice(2);
  const channelName = 'tcc-worship-output-' + session + '-v2';
  let channel = null, published = false, sequence = 0;
  const handles = {projector:null, stage:null};
  const seen = {projector:0, stage:0};
  try { channel = new host.BroadcastChannel(channelName); } catch (_) {}
  function status() {
    if (options.onStatus) options.onStatus(Date.now()-seen.projector < 5000);
  }
  function message(data) {
    if (data.session !== session) return;
    if (data.type === 'presence' || data.type === 'snapshot') {
      seen[data.mode] = Date.now(); status();
    }
    if (data.type === 'snapshot' && data.to === token && data.packet && !published && data.mode === 'projector') {
      options.onRestore(data.packet);
    }
    if (data.type === 'navigate') options.onNavigate(data.action);
    if(data.type==='capture-service'&&options.getWorkspace&&channel){
      channel.postMessage({type:'service-snapshot',session,to:data.from,workspace:options.getWorkspace()});
    }
  }
  if (channel) {
    channel.onmessage = event => message(event.data);
    channel.postMessage({type:'hello',session,from:token});
  }
  const timer = host.setInterval(status, 2000);
  function envelope(packet) { return {...packet, tag:token+'-'+(++sequence)}; }
  function publish(packet) {
    published = true;
    const data = envelope(packet);
    for (const mode of ['projector','stage']) {
      const w = handles[mode];
      try { if (w && !w.closed && w.tccOutput) { w.tccOutput.render(data); seen[mode]=Date.now(); } } catch (_) {}
    }
    if (channel) channel.postMessage({type:'render',session,packet:data});
    status();
  }
  function open(stage) {
    const mode = stage ? 'stage' : 'projector';
    const name = 'TCC_Worship_' + session + '_' + mode;
    let w = handles[mode];
    try { if (w && !w.closed) { w.focus(); } else { w = host.open('', name, 'popup,width=1280,height=720'); } }
    catch (_) { w = null; }
    if (!w) { options.onError('Allow pop-ups to open the projector window.'); return; }
    try {
      if (!w.tccOutput || w.tccOutput.session !== session || w.tccOutput.version!==2) {
        if(w.tccOutput?.dispose)w.tccOutput.dispose();
        w.document.open();
        w.document.write('<!doctype html><html><head><meta charset="utf-8"><title>TCC Worship</title><style>'+options.css+'</style></head><body class="'+(stage?'stage-mode':'output-mode')+'"><div id="external" class="screen"></div><div id="stage" class="stage"></div><div id="output-tools"><button id="full">Full screen</button><button id="sound">Enable sound / Play</button></div></body></html>');
        w.document.close();
        const script = w.document.createElement('script');
        script.textContent = tccBackground.toString()+'\n('+tccProjectorRuntime.toString()+')('+JSON.stringify({session,mode,channelName})+');';
        w.document.body.append(script);
      }
      handles[mode] = w;
      seen[mode] = Date.now();
      const previous = w.tccOutput.snapshot();
      if (previous && !published && !stage) options.onRestore(previous);
      w.tccOutput.onNavigate = options.onNavigate;
      w.tccOutput.render(envelope(options.getPacket()));
      status();
    } catch (_) { options.onError('Could not reconnect to the projector. Close the old projector window once, then open it again.'); }
  }
  function media(action) {
    const command = {type:'media',session,action,tag:token+'-'+(++sequence)};
    try { const w=handles.projector; if(w&&!w.closed&&w.tccOutput) w.tccOutput.media(command); } catch (_) {}
    if (channel) channel.postMessage(command);
  }
  function close() { host.clearInterval(timer); if(channel) channel.close(); }
  host.addEventListener('pagehide', close, {once:true});
  return {publish,open,media,close};
}

function tccProjectorRuntime(config) {
  const host = window, doc = document;
  let channel=null, packet=null, mediaTag=null;
  try { channel = new BroadcastChannel(config.channelName); } catch (_) {}
  const root = doc.getElementById(config.mode==='stage'?'stage':'external');
  function fit(el,maximum) {
    let size=Math.min(maximum,root.clientWidth/15); el.style.fontSize=size+'px';
    while(size>14&&(el.scrollHeight>el.clientHeight+1||el.scrollWidth>el.clientWidth+1)) el.style.fontSize=(--size)+'px';
  }
  function stageText() {
    root.replaceChildren(); if(!packet)return;
    const title=doc.createElement('small'); title.textContent=packet.title+' • '+new Date().toLocaleTimeString()+(packet.blank?' • BLACKOUT':'');root.append(title);
    const body=doc.createElement('div');body.textContent=packet.slide?.text||packet.item?.title||'Ready';root.append(body);
    const next=doc.createElement('small');next.textContent='NEXT: '+packet.next;root.append(next);
  }
  function render(next) {
    if(packet?.tag===next.tag)return;
    packet=next;
    if(config.mode==='stage'){stageText();return;}
    root.style.background=packet.theme.background;
    if(packet.blank||!packet.item){root.replaceChildren();return;}
    if(packet.item.kind==='video'){
      root.replaceChildren();const v=doc.createElement('video');v.className='foreground-video';v.src=packet.item.src;v.controls=true;v.loop=false;root.append(v);
    }else if(packet.item.kind==='image'||packet.slide?.src){
      root.replaceChildren();const im=doc.createElement('img');im.src=packet.slide?.src||packet.item.src;im.alt=packet.item.title;root.append(im);
    }else{
      tccBackground(root,packet.theme);
      const words=doc.createElement('div');words.className='words';words.style.position='relative';words.style.zIndex='2';words.dir='auto';words.textContent=packet.slide?.text||'';root.append(words);
      const credit=doc.createElement('div');credit.className='credit';credit.style.zIndex='3';credit.textContent=packet.item.credit||'';root.append(credit);
      host.requestAnimationFrame(()=>fit(words,packet.theme.font_size));
    }
  }
  function media(command) {
    if(config.mode!=='projector'||command.tag===mediaTag)return;mediaTag=command.tag;
    const v=root.querySelector('.foreground-video');if(!v)return;
    if(command.action==='restart')v.currentTime=0;
    if(command.action==='toggle'){if(v.paused)v.play().catch(()=>{});else v.pause();}
  }
  function navigate(action) {
    if(channel)channel.postMessage({type:'navigate',session:config.session,action});
    else if(host.tccOutput.onNavigate)host.tccOutput.onNavigate(action);
  }
  host.tccOutput={session:config.session,version:2,render,media,snapshot:()=>packet,onNavigate:null,dispose:()=>{host.clearInterval(timer);if(channel)channel.close();}};
  doc.getElementById('full').onclick=()=>doc.documentElement.requestFullscreen().catch(()=>{});
  doc.getElementById('sound').onclick=()=>{const v=root.querySelector('.foreground-video');if(v){v.muted=false;v.play().catch(()=>{});}};
  host.addEventListener('keydown',event=>{
    if(['INPUT','TEXTAREA'].includes(event.target.tagName))return;
    if(event.key==='ArrowRight'||event.key===' '){event.preventDefault();navigate('next');}
    if(event.key==='ArrowLeft'){event.preventDefault();navigate('previous');}
    if(event.key.toLowerCase()==='b')navigate('blackout');
  });
  host.addEventListener('resize',()=>root.querySelectorAll('.words').forEach(el=>fit(el,packet?.theme.font_size||54)));
  if(channel)channel.onmessage=event=>{
    const data=event.data;if(data.session!==config.session)return;
    if(data.type==='render')render(data.packet);
    if(data.type==='media')media(data);
    if(data.type==='hello')channel.postMessage({type:'snapshot',session:config.session,mode:config.mode,to:data.from,packet});
  };
  const timer=host.setInterval(()=>{
    if(config.mode==='stage')stageText();
    if(channel)channel.postMessage({type:'presence',session:config.session,mode:config.mode});
  },1000);
  host.addEventListener('pagehide',()=>{host.clearInterval(timer);if(channel)channel.close();},{once:true});
}

if(typeof module!=='undefined'&&module.exports)module.exports={createTccOutputBridge,tccBackground};
