/** Private MCP client. Only the two host-defined join operations are exposed. */
import {readFile, writeFile, rename} from 'node:fs/promises';
import {createReadStream} from 'node:fs';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {join, resolve} from 'node:path';
import {pathToFileURL} from 'node:url';

const [runtime, folder, operation] = process.argv.slice(2);
if (!runtime || !folder || !['prepare', 'render'].includes(operation)) throw Error('Invalid MCP join operation');
const requireRuntime = createRequire(join(resolve(runtime), 'apps/mcp-server/package.json'));
const {Client} = await import(pathToFileURL(requireRuntime.resolve('@modelcontextprotocol/sdk/client/index.js')));
const {StdioClientTransport} = await import(pathToFileURL(requireRuntime.resolve('@modelcontextprotocol/sdk/client/stdio.js')));
const plan = JSON.parse(await readFile(join(folder, 'request.json'), 'utf8'));
const journalPath = join(folder, `${operation}.json`);
let journal;
try {journal = JSON.parse(await readFile(journalPath, 'utf8'));}
catch (error) {if (error.code !== 'ENOENT') throw error; journal = {stage:'new'};}
const digest = async path => {
  const hash=createHash('sha256');
  for await(const chunk of createReadStream(path))hash.update(chunk);
  return hash.digest('hex');
};
const save = async value => {
  journal = {...journal,...value};
  await writeFile(`${journalPath}.tmp`, JSON.stringify(journal));
  await rename(`${journalPath}.tmp`, journalPath);
};
const client = new Client({name:'vibe-kdenlive-join',version:'1.0.0'});
const transport = new StdioClientTransport({command:process.execPath,
  args:[join(runtime,'apps/mcp-server/dist/cli.js'),'--root',folder,'--client-id','vibe-kdenlive-join'],
  cwd:runtime, stderr:'pipe', env:{...process.env,QT_QPA_PLATFORM:'offscreen'}});
transport.stderr?.on('data',data=>process.stderr.write(data));
const call = async (name, args={}) => {
  const result = await client.callTool({name,arguments:args},undefined,{timeout:60000});
  if(result.isError || !result.structuredContent?.ok) throw Error(`${name}: ${JSON.stringify(result.structuredContent ?? result.content)}`);
  return result.structuredContent.data;
};
const wait = async id => {
  const deadline=Date.now()+3600000;
  while(Date.now()<deadline){
    const result=await call('job_get',{jobId:id});
    if(result.status==='succeeded')return result;
    if(['failed','cancelled'].includes(result.status))throw Error(`MCP job ${result.status}: ${result.error ?? ''}`);
    await new Promise(done=>setTimeout(done,500));
  }
  await call('job_cancel',{jobId:id});
  throw Error('MCP render exceeded one hour');
};
let closing=false;
const close = async () => {
  if(closing)return;closing=true;
  try{if(journal.jobId && journal.stage!=='complete')await call('job_cancel',{jobId:journal.jobId});}
  finally{await client.close();await transport.close();}
};
process.on('SIGTERM',()=>void close().finally(()=>process.exit(130)));
process.on('SIGINT',()=>void close().finally(()=>process.exit(130)));
try {
  await client.connect(transport);
  const catalog=await client.listTools();
  for(const name of ['project_create','media_import','timeline_add_clips','project_get','preview_submit',
    'render_submit','job_get','job_cancel','job_verify','interchange_export']){
    if(!catalog.tools.some(tool=>tool.name===name))throw Error(`Required MCP tool missing: ${name}`);
  }
  if(journal.stage==='complete'){
    if(await digest(journal.result.outputPath)!==journal.result.outputSha256)throw Error('Completed MCP output changed; prepare a new proposal.');
    console.log(JSON.stringify(journal.result));
  }else{
    if(journal.stage==='pending')throw Error('Recovery required: external operation acknowledgement was lost. Inspect this execution project; no mutation was repeated.');
    let project;
    if(operation==='prepare'){
      if(journal.stage!=='new' && !journal.jobId)throw Error('Recovery required: inspect partially prepared MCP project.');
      if(journal.stage==='new'){
        await save({stage:'pending',operation:'project_create'});
        project=await call('project_create',{path:join(folder,'project'),name:'Vibe reviewed clip join',
          settings:{fps:{numerator:plan.fps,denominator:1},width:plan.width,height:plan.height,audioSampleRate:48000}});
        await save({projectId:project.id,revision:project.revision,operation:'media_import'});
        const imported=await call('media_import',{projectId:project.id,expectedRevision:project.revision,
          paths:plan.sources.map(source=>join(folder,source.path)),mode:'managed'});
        await save({revision:imported.revision,operation:'timeline_add_clips'});
        const edited=await call('timeline_add_clips',{projectId:project.id,expectedRevision:imported.revision,
          requests:imported.imported.map((asset,index)=>({assetId:asset.id,
            sourceIn:Math.round(plan.clips[index].start*plan.fps),sourceOut:Math.round(plan.clips[index].end*plan.fps),linkedAv:true})),
          options:{mode:'append'}});
        await save({revision:edited.revision,operation:'preview_submit'});
        const job=await call('preview_submit',{projectId:project.id,kind:'range',
          start:Math.max(0,Math.round((plan.clips[0].end-plan.clips[0].start-1)*plan.fps)),
          end:Math.min(Math.round(plan.clips.reduce((s,c)=>s+c.end-c.start,0)*plan.fps),
            Math.round((plan.clips[0].end-plan.clips[0].start+1)*plan.fps))});
        await save({stage:'waiting',jobId:job.id});
      }else await call('project_open',{path:join(folder,'project')});
      const job=await wait(journal.jobId);
      const result={projectId:journal.projectId,revision:journal.revision,jobId:job.id,outputPath:job.outputPath,outputSha256:await digest(job.outputPath)};
      await save({stage:'complete',result});
      console.log(JSON.stringify(result));
    }else{
      const prepared=JSON.parse(await readFile(join(folder,'prepare.json'),'utf8'));
      project=await call('project_open',{path:join(folder,'project')});
      if(project.revision!==prepared.revision || project.id!==prepared.projectId)throw Error('MCP project changed after preview; review a new proposal.');
      if(journal.stage==='new'){
        await save({stage:'pending',operation:'render_submit'});
        const job=await call('render_submit',{projectId:project.id,profileId:'youtube-1080p',outputName:'final'});
        await save({stage:'waiting',jobId:job.id});
      }
      const job=await wait(journal.jobId);
      const verification=await call('job_verify',{jobId:job.id});
      if(!verification.valid)throw Error(`MCP verification failed: ${JSON.stringify(verification.diagnostics)}`);
      const editable=await call('interchange_export',{projectId:project.id,format:'kdenlive',outputName:'editable'});
      const result={projectId:project.id,revision:project.revision,jobId:job.id,outputPath:job.outputPath,outputSha256:await digest(job.outputPath),verification,editable};
      await save({stage:'complete',result});
      console.log(JSON.stringify(result));
    }
  }
}finally{await close();}
