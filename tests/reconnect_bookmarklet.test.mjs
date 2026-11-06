import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { test } from 'node:test';
import vm from 'node:vm';

const tpl = execFileSync('python3', ['-c',
  "import importlib.util,sys;s=importlib.util.spec_from_file_location('p','custom_components/contarina/pairing.py');m=importlib.util.module_from_spec(s);sys.modules['p']=m;s.loader.exec_module(m);sys.stdout.write(m.BOOKMARKLET_TEMPLATE)"],
  {encoding: 'utf8'});
const HA = 'http://homeassistant.local:8123';
const code = tpl.replace('__HA_ORIGIN__', JSON.stringify(HA));
const nowMs = 1780000000000;
const jwt = (min = 30) => ['eyJhbGciOiJIUzI1NiJ9',
  Buffer.from(JSON.stringify({exp: Math.floor(nowMs / 1000) + 60 * min})).toString('base64url'), 'sig'].join('.');

function run({cookie = `accessToken=${jwt()}`, host = 'sol.servizicontarina.it', protocol = 'https:'} = {}) {
  const alerts = [];
  const location = {hostname: host, protocol, href: 'https://' + host + '/'};
  vm.runInNewContext(code, {location, document: {cookie}, alert: x => alerts.push(x),
    atob, decodeURIComponent, JSON, Date: {now: () => nowMs}}, {timeout: 1000});
  return {alerts, href: location.href};
}

test('valid SOL session navigates to HA receive page with token in fragment only', () => {
  const t = jwt();
  const r = run({cookie: `a=b; accessToken=${t}; c=d`});
  assert.equal(r.href, `${HA}/api/contarina/reconnect/receive#${t}`);
  assert.equal(r.alerts.length, 0);
});
test('wrong host or protocol never navigates', () => {
  for (const o of [{host: 'evil.example'}, {protocol: 'http:'}]) {
    const r = run(o); assert.ok(!r.href.startsWith(HA)); assert.equal(r.alerts.length, 1);
  }
});
test('missing, malformed or expiring token never navigates', () => {
  for (const cookie of ['x=y', 'accessToken=garbage', `accessToken=${jwt(1)}`, `accessToken=${jwt(-5)}`]) {
    const r = run({cookie}); assert.ok(!r.href.startsWith(HA)); assert.equal(r.alerts.length, 1);
  }
});
test('template holds no secret', () => {
  assert.doesNotMatch(tpl, /state|flow_id|fetch\(|XMLHttpRequest|sendBeacon/);
});
