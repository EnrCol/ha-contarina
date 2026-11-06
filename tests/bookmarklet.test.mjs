import assert from 'node:assert/strict';
import fs from 'node:fs';
import { test } from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync(new URL('../tools/contarina_token_bookmarklet.js', import.meta.url), 'utf8');
const bookmarklet = fs.readFileSync(new URL('../tools/BOOKMARKLET.txt', import.meta.url), 'utf8').trim();
const nowMs = 1780000000000;
function fakeJwt(expiresMinutes = 35) {
  const exp = Math.floor(nowMs / 1000) + 60 * expiresMinutes;
  return ['eyJhbGciOiJIUzI1NiJ9', Buffer.from(JSON.stringify({exp, note:'\u00e8'})).toString('base64url'), 'signature'].join('.');
}
async function run({cookie=`accessToken=${fakeJwt()}`, host='sol.servizicontarina.it', protocol='https:', clipboardFails=false}={}) {
  const alerts=[], prompts=[], writes=[];
  const context = {
    window:{location:{hostname:host, protocol}, alert:x=>alerts.push(x), prompt:(label,value)=>{prompts.push({label,value});return value;}},
    document:{cookie}, navigator:{clipboard:{writeText:async value=>{if(clipboardFails)throw Error('blocked');writes.push(value);}}},
    atob, TextDecoder, Uint8Array, decodeURIComponent, Date:{now:()=>nowMs}, JSON, Number, Math,
  };
  await vm.runInNewContext(source,context,{timeout:1000});
  return {alerts,prompts,writes};
}

test('bookmarklet is a local javascript URL and matches readable source',()=>{
  assert.ok(bookmarklet.startsWith('javascript:'));
  assert.equal(bookmarklet,'javascript:'+source.split('\n').map(s=>s.trim()).join(' ').trim());
  assert.doesNotMatch(source,/\bfetch\s*\(|XMLHttpRequest|sendBeacon|location\.href\s*=/);
});
test('SOL valid token is copied and never shown in success alert', async()=>{
  const jwt=fakeJwt(); const result=await run({cookie:`other=x; accessToken=${jwt}; another=y`});
  assert.deepEqual(result.writes,[jwt]);
  assert.equal(result.prompts.length,0);
  assert.ok(result.alerts[0].includes('copiato'));
  assert.ok(!result.alerts[0].includes(jwt));
});
test('wrong origin and protocol never copy', async()=>{
  for (const options of [{host:'evil.example'},{protocol:'http:'}]) {
    const x=await run(options); assert.equal(x.writes.length,0);assert.equal(x.prompts.length,0);
  }
});
test('missing, invalid and expired token are refused', async()=>{
  for (const cookie of ['a=b','accessToken=garbage',`accessToken=${fakeJwt(-1)}`]) {
    const x=await run({cookie});assert.equal(x.writes.length,0);assert.ok(x.alerts.length);
  }
});
test('clipboard blocked yields manual prompt only on authenticated SOL',async()=>{
  const jwt=fakeJwt();const x=await run({clipboardFails:true,cookie:`accessToken=${jwt}`});
  assert.equal(x.writes.length,0);assert.equal(x.prompts[0].value,jwt);
});