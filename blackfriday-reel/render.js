// Renders reel.html frame by frame and pipes into ffmpeg -> fixface_blackfriday_reel.mp4
const {chromium}=require('playwright'); const {spawn}=require('child_process'); const path=require('path');
const FPS=30, DUR=21;
(async()=>{
  const ff=spawn('ffmpeg',['-y','-f','image2pipe','-framerate',String(FPS),'-c:v','mjpeg','-i','-',
    '-i','music.wav','-c:v','libx264','-preset','medium','-crf','17','-pix_fmt','yuv420p',
    '-c:a','aac','-b:a','192k','-shortest','-movflags','+faststart','fixface_blackfriday_reel.mp4'],{stdio:['pipe','ignore','inherit']});
  const b=await chromium.launch(); const p=await b.newPage({viewport:{width:1080,height:1920}});
  await p.goto('file://'+path.resolve('reel.html')); await p.evaluate(()=>document.fonts.ready); await p.waitForTimeout(500);
  for(let f=0;f<FPS*DUR;f++){
    await p.evaluate(t=>render(t),f/FPS);
    const buf=await p.screenshot({type:'jpeg',quality:95});
    if(!ff.stdin.write(buf)) await new Promise(r=>ff.stdin.once('drain',r));
  }
  ff.stdin.end(); await b.close();
  ff.on('close',c=>console.log('ffmpeg exit',c));
})();
