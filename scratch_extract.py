import zipfile
import xml.etree.ElementTree as ET

docx_path = r'c:\Users\matel\Desktop\Cosas\Programacion\Projects\hemogramas-proyectoICC\Carlos & Edwin - Anteproyecto Documentacion.docx'

z = zipfile.ZipFile(docx_path)
tree = ET.parse(z.open('word/document.xml'))
ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

with open(r'c:\Users\matel\Desktop\Cosas\Programacion\Projects\hemogramas-proyectoICC\extracted_doc.txt', 'w', encoding='utf-8') as f:
    for p in tree.findall('.//w:p', ns):
        texts = []
        for t in p.findall('.//w:t', ns):
            if t.text:
                texts.append(t.text)
        line = ''.join(texts).strip()
        if line:
            f.write(line + '\n')

print("Done. Written to extracted_doc.txt")
