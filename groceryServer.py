
import os
from flask import Flask, request
import datetime, time
import json
import numpy as np
import splitRows as sr
from PIL import Image, ImageOps
from io import BytesIO
import base64

app = Flask(__name__)
serverip = 'http://makechaos.pythonanywhere.com'
ddir = '/home/makechaos/myGrocList'
fullstats = None
uids = {'ks':0}
# uids = json.load(open(os.path.join(ddir,'data','uids.json'),'r'))

#serverip = 'http://localhost:8000'
#ddir = '.'

dateFormat = '%Y_%m_%d'
alias = {'beet root':'beets','beetroot':'beets'}

def getItemTable(item):
  global fullstats

  txt = ''
  txt += '<h1 align="center">'+str(item)+'</h1>'
  item = fullstats[item]
  txt += '<table align="center">'
  txt += '<tr><th>Date</th><th>Rs/amt</th><th>Amt.</th><th>Store</th></tr>'
  for n in range(len(item['rs'])):
    m = len(item['rs'])-1 - n # show in reverse date order
    txt +='<tr>'
    for k in ['date','rs','amt','store']:
        txt +='<td>'+str(item[k][m])+'</td>'
    txt +='</tr>'
  txt += '</table>'
  return txt

def loadStats():
  global fullstats
  if not type(fullstats)==dict:
    fullstats = json.load( open(os.path.join(ddir,'data','fullstats.json'),'r') )

def saveStats():
  global fullstats

  json.dump(fullstats, open(os.path.join(ddir,'data','fullstats.json'),'w'), indent=2 )

def addToStat(name,cdate,rs,amt,store=''):
  global fullstats

  loadStats()

  if name not in fullstats:
    fullstats[name] = {'rs':[rs], 'amt':[amt], 'date':[cdate], 'store':[store] }
  else:
    fullstats[name]['rs'] += [rs]
    fullstats[name]['amt'] += [amt]
    fullstats[name]['date'] += [cdate]
    fullstats[name]['store'] += [store]

  # order by date
  dt = []
  for m in range(len(fullstats[name]['date'])):
    dt += [ [m, datetime.datetime.strptime( fullstats[name]['date'][m], dateFormat )] ]
  dt.sort(key=lambda x:x[1])
  for m in ['rs','date','store','amt']:
    cp = fullstats[name][m][:]
    for n in range(len(dt)):
      fullstats[name][m][n] = cp[dt[n][0]]

def getRate(stat):
  rates = []
  cdt = datetime.datetime.strptime(stat['date'][0],dateFormat)
  s2d = 1./(24*60*60.)
  for m in range(len(stat['date'])-1):
    ndt = datetime.datetime.strptime(stat['date'][m+1],dateFormat)
    ddt = ndt - cdt
    ddt = (ddt.days + (ddt.seconds+1.)*s2d)
    unit = 1.0
    if stat['amt'][m]>0:
      unit = stat['amt'][m]*1./stat['rs'][m]
    rates += [ unit/ddt ]
    cdt = ndt

  avg = 0
  if len(rates)>0:
    rates.sort()
    avg = rates[ int(len(rates)/2) ] # get the median

  ddt = datetime.datetime.now() - cdt
  unit = 1.0
  if stat['amt'][-1]>0:
    unit = stat['amt'][-1]*1./stat['rs'][-1]
  crate = unit*1./(ddt.days + ddt.seconds*s2d)
  due = '  '
  if crate<avg:
    due = 'Yes'
  else:
    due = 'No '
  return (avg*7, due)

def getDueListTable(uid):
  global fullstats

  loadStats()
  stats = fullstats

  dat = [];
  for k in stats.keys():
    if len(stats[k]['rs'])>2:
      dat += [[k,len(stats[k]['rs'])]]
  dat.sort(key=lambda x:x[1], reverse=True)

  txt = ''
  txt+= '<table align="center">'
  txt+= '<tr><th>Item [count]</th><th>U./wk</th><th>Last buy</th>'
  txt+= '</tr>'
  nent = 0
  for item, cnt in dat:
    nent += 1
    dd = stats[item]['rs']
    (rate, due) = getRate(stats[item])
    if not(due=='Yes'):
      continue
    txt += '<tr><td><a href="%s/item=%s,%s"> %s [%d]</a></td>'%(serverip,uid,item,item,len(dd))
    txt += '<td>%1.1f</td>'%rate
    txt += '<td>%s</td>'%stats[item]['date'][-1]
    txt += '</tr>'
  txt += '</table>'
  return txt

def getGenStatsTable(uid):
  global fullstats

  loadStats()
  stats = fullstats

  dat = [];
  for k in stats.keys():
    dat += [[k,len(stats[k]['rs'])]]
  dat.sort(key=lambda x:x[1], reverse=True)

  txt = ''
  txt+= '<table align="center">'
  txt+= '<tr><th>Item [count]</th><th>Min.</th><th id="toogleButton"></th><th>Max.</th><th>Due (U./wk)</th>'
  txt+= '</tr>'
  nent = 0
  for item, cnt in dat:
    nent += 1
    dd = stats[item]['rs']
    (rate, due) = getRate(stats[item])
    txt += '<tr><td><a href="%s/item=%s,%s"> %s [%d]</a></td>'%(serverip,uid,item,item,len(dd))
    txt += '<td>%d</td>'%(min(dd))
    txt += '<td><div class="barPlot" id="bar%d"'%nent + ' barValues="'+ ','.join(map(lambda x:str(int(x)),dd)) +'"></div>'
    txt += '<td>%d</td>'%(max(dd))
    txt += '<td>%s (%1.1f)</td>'%(due,rate)
    txt += '</tr>'
  txt += '</table>'
  return txt

def getDataTable(dd):
  txt = ''
  txt+= '<table align="center">'
  txt+= '<tr><th>Item</th><th>Rs/Unit</th><th>Amt</th></tr>'
  for item in dd:
    txt += '<tr>'
    txt += '<td>'+item+'</td>'
    txt += '<td>%2.2f'%dd[item][0]['rs']+'</td>'
    txt += '<td>%2.2f'%dd[item][0]['amt']+'</td>'
    txt += '</tr>'
  txt += '</table>'
  return txt

def getDateInfo(dd):
  global fullstats

  loadStats()

  txt = ''
  txt+= '<table align="center">'
  txt+= '<tr><th>Item</th><th>Rs/Un (delta)</th><th>Amt (delta)</th></tr>'
  total = 0
  for item in fullstats:
    for n in range(len(fullstats[item]['date'])):
      if fullstats[item]['date'][n]!=dd:
        continue

      if n>0:
        diffRs = fullstats[item]['rs'][n] - fullstats[item]['rs'][n-1]
        diffAmt = fullstats[item]['amt'][n] - fullstats[item]['amt'][n-1]
      else:
        diffRs = 0
        diffAmt = 0

      if(diffRs>0):
        txt += '<tr style="color:red;">'
      elif(diffRs<0):
        txt += '<tr style="color:green;">'
      else:
        txt += '<tr>'

      txt += '<td>'+item+'</td>'
      txt += '<td>%3d (%3d)'%(fullstats[item]['rs'][n],diffRs)+'</td>'
      txt += '<td>%3d (%3d)'%(fullstats[item]['amt'][n],diffAmt)+'</td>'
      txt += '</tr>'

      total += fullstats[item]['amt'][n]
  txt += '</table>'
  txt = 'Total spend : Rs. %5.0f </br>'%total + txt
  return txt, total

def getDateTable(dd):
  txt, total = getDateInfo(dd)
  return txt

def getDateTotal(dd):
  txt, total = getDateInfo(dd)
  return total

def getStatTable(stat):
  txt = ''
  txt+= '<table align="center">'
  txt+= '<tr><th>Item</th><th>Rs/Unit [%]</th><th>Amt [%]</th></tr>'
  for item in stat.keys():
    if item.find('lastentry')>=0:
      continue
    txt += '<tr><td>'+item+'</td>'
    for val in stat[item]:
      color = '#b55';
      if val[0]<0:
        color = '#5b5'
      txt += '<td style="color:%s;">%2.1f [%2.1f]</td>'%(color,val[0],val[1])
    txt += '</tr>'
  txt += '</table>'
  return txt

def addItems(txt):
  ents = txt.split('{')

  ctime = datetime.datetime.now().strftime(dateFormat)
  for ent in ents:
    if ent.find('date:')>=0:
      ctime = ent.split(':')[1].strip('}').replace('-','_')
      break

  # get the filename for logging
  fname = os.path.join(ddir,'data','updates_'+ctime+'.json')
  if os.access(fname,os.F_OK):
    fd = open(fname,'r')
    items = json.load(fd)
    fd.close()
  else:
    items = dict()

  stats = {}
  cnt = 0
  tot = 0.0
  store = ''
  testing = False
  for ent in ents:
    if len(ent)>0 and ent[-1]=='}':
      vals = ent.strip('}')
      if vals.find('store:')>=0:
        store = vals.split(':')[1]
        if store== 'testdata':
          testing = True
        continue
      if vals.find('date:')>=0:
        continue

      vals = vals.split(',')
      for m in range(len(vals)):
        vals[m] = vals[m].strip()

      if len(vals[1])==0 or len(vals[0])==0:
        continue
      else:
        rs = float(vals[1])

      if len(vals[2])==0:
        amt = 0.0
      else:
        amt = float(vals[2])

      name = vals[0].lower()
      if name in alias:
        name = alias[name]

      entval = {'rs':rs, 'amt':amt, 'date':ctime, 'store':store}
      if name in items.keys():
        items[name] += [entval]
      else:
        items[name] = [entval]

      if name in fullstats and (not testing):
        prevrs = max(1.,fullstats[name]['rs'][-1])
        prevamt = max(1.,fullstats[name]['amt'][-1])
        stats[name] = [[rs-prevrs, (rs-prevrs)/prevrs*100.0],[amt-prevamt, (amt-prevamt)/prevamt*100.0]]
      else:
        stats[name] = [[rs,-1],[amt,-1]]
      addToStat(name,ctime,rs,amt,store)

      cnt += 1
      tot += amt
  if cnt>0 and (not testing):
    saveStats()
    json.dump(items, open(fname,'w'), indent=2)

  return 'Added %d items, total=%2.2f'%(cnt,tot), getStatTable(stats)

def render_html(fil, vars):
  hfile = os.path.join(ddir,'templates',fil)
  if os.access(hfile, os.F_OK):
    fd = open(hfile,'r')
    htm = ''.join(fd.readlines())
    fd.close()
    for var in vars.keys():
      htm = htm.replace('{{'+var+'}}', vars[var])
  else:
    htm = '<html><body><h1>TEMPLATE NOT FOUND:'+fil+'</h1></body></html>'
  return htm

def render_result_withtable(res,uid,serverip,fname):
  vars = {'result':res, 'hostid':serverip, 'fname':fname,'id':uid}
  return render_html('result.html',vars)

def checkUId(uid):
  if uid in uids:
    return True
  else:
    return False

@app.route('/')
def index_land():
  return render_html('index_land.html',{'hostid':serverip,'err':''})

@app.route('/id=<inp>')
def index(inp):
  if not checkUId(inp):
    return render_html('uid_error.html',{'hostid':serverip,'err':''})

  loadStats()
  items = ''
  for item in fullstats:
      items += '["%s", %d],'%(item, fullstats[item]['rs'][-1])
  items = items[:-1]

  return render_html('index.html',{'hostid':serverip,'pastItems':items,'id':inp})

@app.route('/all=<uid>')
def shoAllData(uid):
  #import glob
  global fullstats

  if not checkUId(uid):
    return render_html('uid_error.html',{'hostid':serverip,'err':''})

  loadStats()
  udates = set()
  for item in fullstats:
    udates = udates.union( set( fullstats[item]['date'] ) )
  udates = list(udates)

  udates = map(lambda x: datetime.datetime.strptime(x, dateFormat), udates)
  udates.sort(reverse=True)
  udates = map(lambda x: x.strftime(dateFormat), udates)

  #fils = glob.glob(os.path.join(ddir,'data','updates*.json'))
  txt = ''
  txt += '<table align=center>'
  txt += '<tr><td><a href="'+serverip+'/stats='+uid+'">Item Stats.</a></td><td></td></tr>'
  for fil in udates:
    #bfil = os.path.splitext(os.path.basename(fil))[0]
    txt += '<tr><td><a href="'+serverip+'/fil='+uid+','+fil+'">'+ fil + '</a></td><td> (%d) </td></tr>'%getDateTotal(fil)
  txt += '</table>'
  return render_result_withtable('',uid,serverip,txt)

@app.route('/fil=<inp>')
def shoDate(inp):
  global fullstats

  inp = inp.split(',')
  if len(inp)<2:
    return render_html('uid_error.html',{'hostid':serverip,'err':'invalid input '+str(inp)})
  uid = inp[0]
  inp = ','.join(inp[1:])
  if not checkUId(uid):
    return render_html('uid_error.html',{'hostid':serverip,'err':''})

  loadStats()
  return render_result_withtable('',uid,serverip,getDateTable(inp))

  #dfile = os.path.join(ddir,'data',inp+'.json')
  #if os.access(dfile,os.F_OK):
  #  dd = json.load(open(dfile,'r'))
  #  return render_result_withtable('',uid,serverip,getDataTable(dd))
  #return render_result_withtable('',uid,serverip,'<h2 style="color:red;" align="center">No File '+inp+'</h2>')


@app.route('/stats=<uid>')
def showStat(uid):
  if not checkUId(uid):
    return render_html('uid_error.html',{'hostid':serverip,'err':''})

  return render_result_withtable('',uid,serverip,getGenStatsTable(uid))

@app.route('/due=<uid>')
def showDueList(uid):
  if not checkUId(uid):
    return render_html('uid_error.html',{'hostid':serverip,'err':''})

  return render_result_withtable('',uid,serverip,getDueListTable(uid))


@app.route('/graph=<inp>')
def getGraphData(inp):
  global fullstats

  inp = inp.split(',')
  if len(inp)<2:
    return render_html('uid_error.html',{'hostid':serverip,'err':'invalid input '+str(inp)})
  uid = inp[0]
  if not checkUId(uid):
    return render_html('uid_error.html',{'hostid':serverip,'err':''})

  loadStats()
  items = fullstats.keys()
  items.sort(key=lambda x:-len(fullstats[x]['rs']))
  items = [item+'(%d)'%len(fullstats[item]['rs']) for item in items]
  items = ['all','Total']+items
  itemsTxt = '\n'.join(map(lambda x:'<option value="%s">%s</option>'%(x,x), items))
  if len(inp[1])==0:
    return render_html('graph.html',{'hostid':serverip,'items':itemsTxt,'uid':uid})

  iitem = inp[1]
  meas  = 'rs'
  if len(inp)>2:
    meas = inp[2]
  res = []
  if iitem=='all':
    for item in fullstats:
      lres = {'name':item, 'legendText':item, 'type':'line', 'data':[]}
      for n in range(len(fullstats[item]['date'])):
        dt = fullstats[item]['date'][n].replace('_','-')
        if meas=='quant':
          y = (fullstats[item]['amt'][n]+1e-5)/(fullstats[item]['rs'][n]+1e-5)
        else:
          y = fullstats[item][meas][n]
        lres['data'] += [{'x':dt,'y':y}]
      res += [lres]
  elif iitem=='Total':
    lres = {'name':iitem, 'legendText':iitem, 'type':'line', 'data':[]}
    total = {}
    for item in fullstats.keys():
        ent = fullstats[item]
        N = len(ent['rs'])
        for n in range(N):
            dt = ent['date'][n].replace('_','-')
            amt = ent['amt'][n]
            if dt in total.keys():
                total[dt] += amt
            else:
                total[dt] = amt
    sitems = [[dt,datetime.datetime.strptime(dt, '%Y-%m-%d')] for dt in total.keys()]
    sitems.sort(key=lambda x:x[1])
    for item in sitems:
        dt = item[0]
        lres['data'] += [{'x':dt, 'y':total[dt]}]
    res += [lres]
  else:
    item = iitem.split('(')[0]
    lres = {'name':item, 'legendText':item, 'type':'line', 'data':[]}
    for n in range(len(fullstats[item]['date'])):
      dt = fullstats[item]['date'][n].replace('_','-')
      if meas=='quant':
        y = (fullstats[item]['amt'][n]+1e-5)/(fullstats[item]['rs'][n]+1e-5)
      else:
        y = fullstats[item][meas][n]
      lres['data'] += [{'x':dt,'y':y}]
    res += [lres]
  return json.dumps(res)


@app.route('/item=<inp>')
def showItem(inp):
  global fullstats

  inp = inp.split(',')
  if len(inp)<2:
    return render_html('uid_error.html',{'hostid':serverip,'err':'invalid input '+str(inp)})
  uid = inp[0]
  inp = ','.join(inp[1:])
  if not checkUId(uid):
    return render_html('uid_error.html',{'hostid':serverip,'err':''})

  loadStats()
  if inp in fullstats:
    return render_result_withtable('',uid,serverip,getItemTable(inp))
  return render_result_withtable('',uid,serverip,'<h2 style="color:red;" align="center">No Item found '+inp+'</h2>')

@app.route('/addlist=<inp>')
def addlist(inp):

  inp = inp.split(',')
  if len(inp)<2:
    return render_html('uid_error.html',{'hostid':serverip,'err':'invalid input '+str(inp)})
  uid = inp[0]
  inp = ','.join(inp[1:])
  if not checkUId(uid):
    return render_html('uid_error.html',{'hostid':serverip,'err':''})

  res, fname = addItems(inp)
  return render_result_withtable(res,uid,serverip,fname)

@app.route('/uploader', methods = ['GET', 'POST'])
def uploader():
  global fullstats

  if request.method == 'POST':
    f = request.files['file']
    fname = 'tmp.jpg'
    f.save(os.path.join(ddir,'data',fname))

    return render_html('uploadDone.html',{'fname':fname})

@app.route('/rowImagePage/<fname>')
def rowImagePage(fname):
    t1 = time.time()
    img = Image.open(os.path.join(ddir,'data',fname)).convert(mode='L')
    t2 = time.time()
    inpTime = (t2-t1)

    t1 = time.time()
    fl, rowSplits = sr.getRows(img)
    t2 = time.time()
    rowTime = (t2-t1)

    loadStats()
    items = '"'+'", "'.join(fullstats.keys())+'"'

    t1 = time.time()
    imdata = ''
    for im in rowSplits:
      im = (im.astype(float)-np.min(im))*255/(np.max(im)-np.min(im))
      im = im.astype(np.uint8)
      img = Image.fromarray(im,mode='L')
      img = img.resize((330,50))
      #img = ImageOps.equalize(img)
      #img = ImageOps.autocontrast(img , cutoff=20)
      barr = getImageByteData(img)
      barr = barr.getvalue()
      imdata += ", 'data:image/png;base64,%s'"%(base64.b64encode(barr).decode('utf-8'))
    imdata = '['+imdata[1:]+']'
    t2 = time.time()
    imgTime = (t2-t1)
    info = ' input=%2.3f, splitting=%2.3f, images=%2.3f (s)'%(inpTime, rowTime, imgTime)
    info = ''
    return render_html('index-rowimage.html',{'hostid':serverip,'pastItems':items,'id':'ks','rowImages':imdata,'info':info})

def getImageByteData(image):
  # save image content to byte container and return
  byte_io = BytesIO()
  image.save(byte_io, 'PNG')
  return byte_io

'''
@app.route('/rowimage')
def getRowImage():
  global rowSplits, rowCur

  if rowCur<len(rowSplits):
    barr = getImageByteData(Image.fromarray(rowSplits[rowCur],mode='L'))
    rowCur += 1
    barr = barr.getvalue()
    imdata = 'data:image/png;base64,'+base64.b64encode(barr).decode('utf-8')
    return imdata
'''

#if __name__ == '__main__':
#  addItems('{carrot,12,1}{beet,3,4}')
#  app.run(host='0.0.0.0',port=8000,debug=True)