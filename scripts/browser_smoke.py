"""Exercise saved/live runs, evidence expansion, error recovery and mobile overflow."""
import json
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

url=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8186'
output=Path('reports/screenshots');output.mkdir(exist_ok=True)
with sync_playwright() as p:
    opts={'headless':True,'args':['--disable-gpu','--disable-dev-shm-usage']}
    if os.getenv('PLAYWRIGHT_CHROMIUM_EXECUTABLE'):
        opts['executable_path']=os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE']
    browser=p.chromium.launch(**opts)
    page=browser.new_page(viewport={'width':1440,'height':1050})
    errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(url);page.wait_for_load_state('networkidle')
    assert page.title()=='Evidence Desk — Drug safety research'
    page.screenshot(path=str(output/'desktop-initial.png'),full_page=True)
    page.get_by_role('button',name='Try a saved example').click()
    page.get_by_text('Saved run · human review needed').wait_for()
    assert page.locator('#answer .claim').count()>0
    page.locator('#answer .citation summary').first.click()
    assert page.locator('#answer .citation[open]').count()==1
    page.screenshot(path=str(output/'desktop-result.png'),full_page=True)
    page.get_by_label('Your research question').fill('Who was enrolled in the ORAL Surveillance trial?')
    page.get_by_role('button',name='Run agent').click()
    page.get_by_text('Live run · human review needed').wait_for(timeout=180000)
    assert page.locator('#answer .claim').count()>0
    page.locator('#trace-panel summary').click()
    assert 'search_evidence' in page.locator('#trace').inner_text()
    page.set_viewport_size({'width':390,'height':844})
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
    page.screenshot(path=str(output/'mobile-result.png'),full_page=True)
    page.route('**/api/ask',lambda route:route.fulfill(status=429,content_type='application/json',body='{"detail":"Test limit reached. Try the saved example."}'))
    page.get_by_role('button',name='Run agent').click()
    page.get_by_text('Test limit reached. Try the saved example.').wait_for()
    assert page.get_by_role('button',name='Run agent').is_enabled()
    page.get_by_role('button',name='Try a saved example').click()
    page.get_by_text('Saved run · human review needed').wait_for()
    assert page.request.get(url+'/app/data/corpus.json').status==404
    assert not errors,errors
    print(json.dumps({'url':url,'checks':['saved actual run','expand citation','live model run','actual tool trace','390px no overflow','429 recovery','raw corpus unavailable','no JavaScript errors']}))
    browser.close()
