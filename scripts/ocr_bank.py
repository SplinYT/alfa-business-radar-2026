"""Optional reproducible import of original scanned PDFs. Needs Poppler/Tesseract + rus/eng."""
import argparse,concurrent.futures,hashlib,json,os,subprocess,tempfile
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('output');a=p.parse_args()
 os.environ['OMP_THREAD_LIMIT']='1'
 def convert(pdf):
  rows=[]
  with tempfile.TemporaryDirectory() as tmp:
   prefix=Path(tmp)/'p'
   subprocess.run(['pdftoppm','-r','150','-png',str(pdf),str(prefix)],check=True)
   for img in sorted(Path(tmp).glob('*.png')):
    page=int(img.stem.split('-')[-1]);text=subprocess.check_output(['tesseract',str(img),'stdout','-l','rus+eng'],stderr=subprocess.DEVNULL).decode()
    rows.append(dict(id=f'{pdf.stem}:{page}',document=pdf.name,page=page,text=text,ocr=True,sha256=hashlib.sha256(pdf.read_bytes()).hexdigest()))
  return rows
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  rows=[r for group in pool.map(convert,sorted(Path(a.input).glob('*.pdf'))) for r in group]
 Path(a.output).write_text(json.dumps(rows,ensure_ascii=False))
 print(f'{len(rows)} pages')
if __name__=='__main__':main()
