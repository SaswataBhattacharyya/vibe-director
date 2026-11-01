import { test, expect } from '@playwright/test';

for (const operation of ['suggestion', 'recovery']) test(`late ${operation} response cannot affect a different field`, async ({ page }) => {
  await page.route('**/api/**', route => route.fulfill({status:404,json:{detail:'No fixture'}}));
  await page.goto('/');
  await page.evaluate(async operation => {
    const entry=await (await fetch('/src/main.tsx')).text();
    const reactUrl=entry.match(/from "([^"]*\/react\.js[^\"]*)"/)[1];
    const domUrl=entry.match(/from "([^"]*\/react-dom_client\.js[^\"]*)"/)[1];
    const {default: React} = await import(reactUrl);
    const {default: ReactDOM} = await import(domUrl);
    const {default: Edit} = await import('/src/SelectionMicroEdit.tsx');
    if (operation === 'recovery') localStorage.setItem('vibe-field-edit:review:prompt:revision:first', JSON.stringify({payload:{
      idempotency_key:'pending',field_text:'A shot opens.',start_codepoint:2,end_codepoint:6,expected_text:'shot',instruction:'Slow it down.'}}));
    document.getElementById('root').style.display='none';
    const element=document.createElement('div'); element.style.padding='40px'; document.body.appendChild(element);
    function Fixture() {
      const [field,setField]=React.useState('first');
      const [value,setValue]=React.useState('A shot opens.');
      window.reviewSwitchField=()=>setField('second');
      return React.createElement(Edit,{label:'Review field',value,surface:'prompt',workspaceId:'review',revisionId:'revision',fieldKey:field,onChange:setValue});
    }
    ReactDOM.createRoot(element).render(React.createElement(Fixture));
  }, operation);
  let release;
  const pending=new Promise(resolve=>{release=resolve;});
  let started;
  const received=new Promise(resolve=>{started=resolve;});
  const path=operation==='recovery' ? '**/api/story/field-edit-requests/by-key/pending' : '**/api/story/workspaces/review/field-edit-proposals';
  await page.route(path,async route=>{started(); await pending; await route.fulfill({status:500,json:{detail:'Late error from first field'}});});
  const field=page.getByRole('textbox',{name:'Review field',exact:true});
  if(operation==='suggestion') {
    await field.focus(); await field.press('Home'); await field.press('ArrowRight'); await field.press('ArrowRight');
    for(let i=0;i<4;i++) await field.press('Shift+ArrowRight');
    await page.getByLabel('Instruction for Review field').fill('Slow it down.');
    await page.getByRole('button',{name:'Suggest edit',exact:true}).click();
  } else await page.getByRole('button',{name:'Check status',exact:true}).click();
  await received;
  await page.evaluate(()=>window.reviewSwitchField());
  await expect(page.getByLabel('Instruction for Review field')).toHaveCount(0);
  await field.focus(); await field.press('Home'); await field.press('ArrowRight'); await field.press('ArrowRight');
  for(let i=0;i<4;i++) await field.press('Shift+ArrowRight');
  await expect(page.getByLabel('Instruction for Review field')).toBeVisible();
  const response=page.waitForResponse(response=>response.url().includes(operation==='recovery'?'field-edit-requests':'field-edit-proposals'));
  release(); await response;
  await expect(page.getByText('Late error from first field',{exact:true})).toHaveCount(0);
  await expect(page.getByLabel('Instruction for Review field')).toHaveValue('');
});
