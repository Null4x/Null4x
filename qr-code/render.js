// Renders qr_card.html -> fixface_qr_card.png and fixface_qr.svg -> fixface_qr.png
const {chromium}=require('playwright'); const path=require('path'); const fs=require('fs');
(async()=>{
  const b=await chromium.launch();
  const p=await b.newPage({viewport:{width:1600,height:2000},deviceScaleFactor:2});
  await p.goto('file://'+path.resolve('qr_card.html')); await p.evaluate(()=>document.fonts.ready); await p.waitForTimeout(300);
  await p.screenshot({path:'fixface_qr_card.png'});
  const q=await b.newPage({viewport:{width:1200,height:1200},deviceScaleFactor:2});
  const svg=fs.readFileSync('fixface_qr.svg','utf8');
  await q.setContent(`<html><head><link rel="stylesheet" href="file://${path.resolve('fonts/fonts.css')}"><style>body{margin:0}</style></head><body>${svg}</body></html>`);
  await q.evaluate(()=>document.fonts.ready); await q.waitForTimeout(300);
  await q.screenshot({path:'fixface_qr.png',omitBackground:true});
  await b.close();
})();
