// Renders line drawings (assembled, section, exploded) of a GLB assembly with joint.html.
// Serve this folder first:  python3 -m http.server 8911   (put model.glb next to joint.html)
// Then:  JOBS=jobs_example.json JDIR=out MODEL=model.glb node render_drawings.js [job_id]
// Needs Node + playwright (Chromium). Writes out/<job>_<view>.png and out/meta.json.
const JD=process.env.JDIR||'out';const MODEL=process.env.MODEL||'m.glb';const PORT=process.env.PORT||8911;
const {chromium}=require('playwright');const fs=require('fs');(async()=>{
const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const p=await b.newPage();p.on('pageerror',e=>console.log('E',e.message));
await p.goto(`http://localhost:${PORT}/joint.html?model=${encodeURIComponent(MODEL)}`);
await p.waitForFunction(()=>window.READY,null,{timeout:90000});
await p.evaluate(()=>{window.LINE=true;window.LW=1;window.SS=2;window.VEC=true;window.MINC=40;});
const jobs=JSON.parse(fs.readFileSync(process.env.JOBS||'jobs_example.json'));const only=process.argv[2];fs.mkdirSync(JD,{recursive:true});const meta=[];
for(const j of jobs){ if(only&&j.id!==only)continue; const o=await p.evaluate(j=>window.render(j),j);
  o.views.forEach((v,i)=>{fs.writeFileSync(`${JD}/${j.id}_${i}.png`,Buffer.from(v.url.split(',')[1],'base64'));delete v.vec;});
  meta.push({id:j.id,title:j.title,legend:o.legend,views:o.views.map((v,i)=>({section:v.section,title:v.title,file:`${JD}/${j.id}_${i}.png`}))});
  console.log(j.id,o.legend.map(l=>l.label+':'+l.n).join(' '));}
fs.writeFileSync(JD+'/meta.json',JSON.stringify(meta,null,1));await b.close();})();
