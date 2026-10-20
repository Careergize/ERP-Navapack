"""Bounded, data-only workbook reader. No formula evaluation or macros."""
import csv
import io
import posixpath
import zipfile
from xml.etree import ElementTree as ET
from rest_framework.exceptions import ValidationError

MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 2000
MAX_CELLS = 100000
NS = {'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def read_source(content, filename):
    if len(content) > MAX_BYTES:
        raise ValidationError({'file':'Maximum upload is 5 MiB.'})
    try:
        if filename.lower().endswith('.csv'):
            records = list(csv.reader(io.StringIO(content.decode('utf-8-sig'))))
            return table_rows('CSV', records)
        if not filename.lower().endswith('.xlsx'):
            raise ValueError('Only UTF-8 CSV or XLSX supported; export legacy XLS explicitly.')
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            infos = archive.infolist()
            if len(infos) > 300 or sum(i.file_size for i in infos) > 20 * MAX_BYTES:
                raise ValueError('Workbook exceeds expanded size limit.')
            names = set(archive.namelist())
            if len(names) != len(infos) or any(i.flag_bits & 1 for i in infos):
                raise ValueError('Encrypted or duplicate ZIP entries are not accepted.')
            if any('vbaProject' in n or 'externalLinks/' in n for n in names):
                raise ValueError('Macros and external links are not accepted.')
            def xml(name):
                raw = archive.read(name)
                if b'<!DOCTYPE' in raw or b'<!ENTITY' in raw:
                    raise ValueError('XML declarations are prohibited.')
                return ET.fromstring(raw)
            strings = []
            if 'xl/sharedStrings.xml' in names:
                strings = [''.join(t.text or '' for t in si.iterfind('.//s:t',NS)) for si in xml('xl/sharedStrings.xml')]
            rels = {r.attrib['Id']:r.attrib['Target'] for r in xml('xl/_rels/workbook.xml.rels')}
            result = []
            cell_count = 0
            for sheet in xml('xl/workbook.xml').findall('s:sheets/s:sheet',NS):
                rel = sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
                target = rels[rel]
                path = posixpath.normpath(target.lstrip('/') if target.startswith('/') else 'xl/' + target)
                if not path.startswith('xl/worksheets/'):
                    raise ValueError('Unsupported worksheet path.')
                records = []
                numbers = []
                for row in xml(path).findall('s:sheetData/s:row',NS):
                    values = {}
                    for cell in row.findall('s:c',NS):
                        cell_count += 1
                        if cell_count > MAX_CELLS: raise ValueError('Too many cells.')
                        if cell.find('s:f',NS) is not None: raise ValueError('Formula cells require a values-only export.')
                        letters = ''.join(c for c in cell.attrib['r'] if c.isalpha())
                        col = 0
                        for c in letters: col = col * 26 + ord(c.upper()) - 64
                        if col < 1 or col > 100: raise ValueError('Maximum 100 columns.')
                        value = cell.findtext('s:v','',NS)
                        if cell.attrib.get('t') == 's': value = strings[int(value)]
                        elif cell.attrib.get('t') == 'inlineStr': value = ''.join(t.text or '' for t in cell.iterfind('.//s:t',NS))
                        elif cell.attrib.get('t') == 'e': raise ValueError('Workbook contains an error cell.')
                        values[col-1] = value
                    if values:
                        records.append([values.get(i,'') for i in range(max(values)+1)])
                        numbers.append(int(row.attrib['r']))
                result += table_rows(sheet.attrib['name'],records,numbers)
                if len(result)>MAX_ROWS: raise ValueError('Maximum 2000 data rows.')
            if not result: raise ValueError('No data rows.')
            return result
    except (ValueError, UnicodeError, zipfile.BadZipFile, KeyError, IndexError, ET.ParseError, csv.Error) as exc:
        raise ValidationError({'file':str(exc)[:240]})


def table_rows(sheet, records, numbers=None):
    if len(records) < 2: raise ValueError('A header and data rows are required.')
    headers = [v.strip() for v in records[0]]
    if len(headers)>100 or any(not h for h in headers) or len(set(headers))!=len(headers):
        raise ValueError('Provide unique nonblank column headers, maximum 100.')
    result=[]
    for i,row in enumerate(records[1:],2):
        if not any(v.strip() for v in row): continue
        if len(row)>len(headers): raise ValueError('Row has more values than headers.')
        result.append({'sheet':sheet,'row_number':numbers[i-1] if numbers else i,'raw':dict(zip(headers,row+['']*(len(headers)-len(row))))})
        if len(result)>MAX_ROWS: raise ValueError('Maximum 2000 data rows.')
    if not result: raise ValueError('No data rows.')
    return result
