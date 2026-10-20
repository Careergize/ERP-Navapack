"""Approved HTTPS DEMO smoke; writes only with explicit --exercise approval reference."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
import uuid


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None  # Never forward credentials/JWT to a redirected destination.


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--api-url', required=True)
    p.add_argument('--instance', required=True)
    p.add_argument('--email', required=True)
    p.add_argument('--password-file', required=True)
    p.add_argument('--exercise', action='store_true')
    p.add_argument('--approval-reference')
    args = p.parse_args()
    base = args.api_url.rstrip('/')
    parsed = urllib.parse.urlsplit(base)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.path != '/api/v1' or parsed.query or parsed.fragment
            or not args.email.endswith('@example.invalid') or (args.exercise and not args.approval_reference)):
        p.error('Explicit HTTPS API/DEMO instance, synthetic account and write approval required.')
    opener = urllib.request.build_opener(NoRedirect())
    token = None
    def request(path, data=None, version=None, key=None):
        headers = {'Accept':'application/json'}
        if token: headers['Authorization'] = 'Bearer '+token
        if data is not None:
            headers['Content-Type']='application/json'; headers['Idempotency-Key']=key or str(uuid.uuid4())
        if version is not None: headers['If-Match']=f'"{version}"'
        req = urllib.request.Request(base+path, data=None if data is None else json.dumps(data).encode(), headers=headers)
        with opener.open(req, timeout=60) as response:
            return json.load(response)
    def pages(path):
        rows=[]
        for page in range(1,1001):
            result=request(path+'?page='+str(page)); rows.extend(result['results'])
            if not result['next']: return rows
        raise RuntimeError('Unexpected pagination size.')
    password = Path(args.password_file).read_text().strip()
    login = request('/auth/login/', {'email':args.email,'password':password}); token=login['access']
    boundary = request('/demo/status/')
    assert boundary == {'environment':'DEMO','instance':str(uuid.UUID(args.instance)),
                        'operational_authority':False,'operational_records_empty':True}
    assert request('/ready/')['status']=='ready'
    if args.exercise:
        variants=pages('/finished-goods/'); materials=pages('/raw-materials/'); warehouses=pages('/inventory/warehouses/')
        chosen=[]
        for variant in variants:
            if variant['name'].startswith('Synthetic ') and (not chosen or variant['unit']==chosen[0]['unit']):
                chosen.append(variant)
            if len(chosen)==2: break
        assert len(chosen)==2 and warehouses
        material=next(m for m in materials if m['name'].startswith('Synthetic ') and m['unit']==chosen[0]['unit'])
        customer=request('/customers/',{'name':'SYNTHETIC HTTPS smoke '+uuid.uuid4().hex[:8],'customer_type':'B2B'})
        data={'currency':'UGX','money_places':2,'rounding':'HALF_UP','discount':'0','terms':'DEMO ONLY',
              'customer':customer['id'],'classification':'B2B','lines':[]}
        for variant in chosen:
            unit=variant['unit']
            data['lines'].append({'variant':variant['id'],'unit':unit,'quantity':'3','unit_price':'10',
                'specifications':'Synthetic HTTPS smoke specification','customisation':'',
                'costing':{'materials':[{'material':material['id'],'unit':unit,'price_unit':unit,'currency':'UGX','quantity':'3','price':'1'}],
                    'processes':[],'waste_percent':'0','rejection_percent':'0','markup_percent':'20','assumption_evidence':'Synthetic smoke input'}})
        doc=request('/commercial/documents/',{'kind':'COSTING','data':data,'reason':'Synthetic HTTPS smoke'})
        for _ in range(2):
            prior=doc
            doc=request('/commercial/documents/'+doc['id']+'/derive/',{'source_revision':doc['revision'],'reason':'Synthetic HTTPS smoke'})
            assert doc['snapshot']['synthetic_source']['sha256']==prior['sha256']
        body={'sales_order_revision':doc['revision'],'warehouse':warehouses[0]['id'],
            'routes':[{'line':i,'stages':['PACKING']} for i in range(2)],'reason':'Synthetic HTTPS smoke'}
        key=str(uuid.uuid4()); job=request('/rehearsal/jobs/',body,key=key)
        assert request('/rehearsal/jobs/',body,key=key)['id']==job['id']
        def command(action, values):
            return request('/rehearsal/jobs/'+job['id']+'/command/',{'action':action,'data':values,'reason':'Synthetic HTTPS smoke'},job['version'])
        def race(_):
            try: command('review',{}); return 200
            except urllib.error.HTTPError as error: return error.code
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(race,range(2)))==[200,412]
        job=request('/rehearsal/jobs/'+job['id']+'/')
        job=command('issue',{'quantity':'6','available_quantity':'6'})
        for line in range(2):
            job=command('start',{'line':line,'stage':'PACKING','machine':'synthetic:https-machine','operator':'synthetic:https-operator','input_quantity':'3'})
            job=command('complete',{'line':line,'stage':'PACKING','output_quantity':'3','waste':'0','rejection':'0'})
        job=command('qc',{'outcome':'FAIL','remarks':'Synthetic failure'})
        try: command('finish',{}); raise AssertionError('Failed QC advanced')
        except urllib.error.HTTPError as error: assert error.code==409
        for action,values in [('qc',{'outcome':'PASS','remarks':'Synthetic reinspection'}),('finish',{}),('dispatch',{})]:
            job=command(action,values)
        assert job['invoice_preview']['payable_total'] is None and job['status']=='DISPATCHED'
        assert request('/rehearsal/jobs/'+job['id']+'/history/')['count']==job['version']
        login=request('/auth/login/',{'email':args.email,'password':password}); token=login['access']
        assert request('/rehearsal/jobs/'+job['id']+'/')['version']==job['version']
    refresh=request('/auth/refresh/',{'refresh':login['refresh']}); token=refresh['access']
    assert request('/demo/status/')['operational_records_empty'] is True
    request('/auth/logout/',{'refresh':refresh['refresh']})
    print('PASS: approved HTTPS DEMO identity, JWT/refresh/logout and zero operational records'+('; exercised full synthetic journey, persistence and concurrency' if args.exercise else '; read-only domain checks'))


if __name__=='__main__':
    try: main()
    except urllib.error.HTTPError as error: raise SystemExit(f'Smoke failed: HTTP {error.code}; credentials and response bodies withheld.')
