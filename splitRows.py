import numpy as np

def unitTest(fname='bill.JPG'):
  from PIL import Image
  import matplotlib.pyplot as plt

  img = Image.open('bill2.jpg').convert(mode='L')
  fl, splits = getRows(img)

  plt.imshow(np.fliplr(np.transpose(np.array(img))),cmap='gray')
  for f in fl:
    plt.plot([0,splits[0].shape[1]],[f,f],'r')
  plt.show()


def getRows(img, reduceLines=0.75, splitBill=True):
  arr = np.array(img)
  # rotate image if needed
  if arr.shape[1]>arr.shape[0]:
    print('rotate image..',arr.shape)
    arr = np.fliplr(np.transpose(arr))

  cols = np.sum(arr,axis=1)
  # use fft to remove low-freq comp
  nLowFreq = 2
  ff = np.fft.fft(cols)
  ff[:(nLowFreq+1)] = 0
  ff[-nLowFreq:] = 0
  hh = np.real(np.fft.ifft(ff))

  # detect row limits by zero crossings
  #hh = hh - np.mean(hh)
  #hh = (hh-np.min(hh))/(np.max(hh)-np.min(hh))
  thresh = 0
  th = np.copy(hh)
  th[th>thresh] = 1
  th[th<1] = 0
  th = np.diff(th)
  nn = np.where(th==1)[0]
  if False:
    plt.plot(hh)
    plt.plot([0,len(hh)],[thresh,thresh],'r')
    plt.plot(nn,np.ones((len(nn),1)),'kx')
    plt.figure()

  fl = nn
  if reduceLines:
    # combine rows that are too close
    kk = np.where(np.diff(nn)>1)[0]
    ll = []
    n1 = 0
    for n in kk:
      if n==n1:
        continue
      ll += [int(np.mean(nn[n1:n]))]
      n1 = n
    # discard limits that lead too small gap (by median)
    medWin = np.median(np.diff(ll))
    winTresh = medWin*reduceLines
    # print('winThresh',winTresh)
    fl = [ll[0]]
    for l in ll[1:]:
      if (l-fl[-1])>=winTresh:
        fl += [l]

    medWin = int(np.median(np.diff(fl)))
    while( fl[-1]< arr.shape[0] ):
      fl += [ min(fl[-1]+medWin,arr.shape[0]) ]

  splits = None
  if splitBill:
    gap = 10
    overlap = 20
    shift = gap+overlap*2
    barr = np.zeros((arr.shape[0]+len(fl)*shift,arr.shape[1]),arr.dtype)
    splits = []
    pl = 0
    for n, l in enumerate(fl):
      n1 = max(0, pl - overlap)
      n2 = min(arr.shape[0], l+overlap)
      splits += [ arr[n1:n2,:] ]
      barr[n1+n*shift:n2+n*shift,:] = splits[-1]
      pl = l

  return fl, splits

if __name__ == '__main__':
  unitTest()
