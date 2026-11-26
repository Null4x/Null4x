// usage: node render.js <name>   e.g. fixface_qr | fixface_site_qr
// <name>_card.html -> <name>_card.png ;  <name>.svg -> <name>.png
const {chromium}=require('playwright'); const path=require('path'); const fs=require('fs');
const name=process.argv[2]||'fixface_qr';
(async()=>{
  const b=await chromium.launch();
  const p=await b.newPage({viewport:{width:1600,height:2000},deviceScaleFactor:2});
  await p.goto('file://'+path.resolve(name+'_card.html')); await p.evaluate(()=>document.fonts.ready); await p.waitForTimeout(300);
  await p.screenshot({path:name+'_card.png'});
  const q=await b.newPage({viewport:{width:1200,height:1200},deviceScaleFactor:2});
  await q.setContent(`<html><body style="margin:0">${fs.readFileSync(name+'.svg','utf8')}</body></html>`);
  await q.screenshot({path:name+'.png'});
  await b.close();
})();
