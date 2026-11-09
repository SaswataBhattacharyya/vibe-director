/** Fixed local renderer; inputs are validated JSON and application-owned JSX. */
import {createRequire} from 'node:module';
import {resolve} from 'node:path';
const [runtime,folder,browser]=process.argv.slice(2);
const require=createRequire(resolve(runtime,'package.json'));
const {bundle}=require('@remotion/bundler');
const {selectComposition,renderMedia}=require('@remotion/renderer');
const serveUrl=await bundle({entryPoint:resolve(folder,'entry.jsx'),publicDir:resolve(folder,'assets'),
  webpackOverride:config=>({...config,resolve:{...config.resolve,modules:[resolve(runtime,'node_modules'),'node_modules']}})});
const options={serveUrl,id:'VibeFilm',browserExecutable:browser,chromiumOptions:{gl:'swangle'},logLevel:'warn'};
const composition=await selectComposition(options);
await renderMedia({...options,composition,codec:'h264',outputLocation:resolve(folder,'final.mp4'),concurrency:1});
