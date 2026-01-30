#!/usr/bin/env python3
"""
prepare_state_month.py

간단한 변환기: 원본 CSV(사건 단건 레벨 또는 다양한 컬럼 구조)를
월별-주별 집계(`data/state_month.csv`)로 변환합니다.

입력 파일은 최소 다음 중 일부 컬럼을 가져야 합니다:
 - 날짜: 'month'(YYYY-MM) 또는 'date' (YYYY-MM-DD 등)
 - 주 식별: 'state_fips' or 'state_abbr' or 'state_name'
 - 사건 수: 'offenses' 또는 'count' 등
 - 검거 수: 'clearances' 또는 'clearance' 등
 - (선택) population

사용법:
  python3 scripts/prepare_state_month.py input.csv > data/state_month.csv

출력 컬럼:
  month,state_fips,state_abbr,state_name,offenses,clearances,population

"""
import sys
import csv
from collections import defaultdict
from datetime import datetime

# 기본 주 매핑: state name -> (fips int, abbr)
STATE_MAP = {
    'Alabama': (1,'AL'),'Alaska':(2,'AK'),'Arizona':(4,'AZ'),'Arkansas':(5,'AR'),
    'California':(6,'CA'),'Colorado':(8,'CO'),'Connecticut':(9,'CT'),'Delaware':(10,'DE'),
    'District of Columbia':(11,'DC'),'Florida':(12,'FL'),'Georgia':(13,'GA'),'Hawaii':(15,'HI'),
    'Idaho':(16,'ID'),'Illinois':(17,'IL'),'Indiana':(18,'IN'),'Iowa':(19,'IA'),
    'Kansas':(20,'KS'),'Kentucky':(21,'KY'),'Louisiana':(22,'LA'),'Maine':(23,'ME'),
    'Maryland':(24,'MD'),'Massachusetts':(25,'MA'),'Michigan':(26,'MI'),'Minnesota':(27,'MN'),
    'Mississippi':(28,'MS'),'Missouri':(29,'MO'),'Montana':(30,'MT'),'Nebraska':(31,'NE'),
    'Nevada':(32,'NV'),'New Hampshire':(33,'NH'),'New Jersey':(34,'NJ'),'New Mexico':(35,'NM'),
    'New York':(36,'NY'),'North Carolina':(37,'NC'),'North Dakota':(38,'ND'),'Ohio':(39,'OH'),
    'Oklahoma':(40,'OK'),'Oregon':(41,'OR'),'Pennsylvania':(42,'PA'),'Rhode Island':(44,'RI'),
    'South Carolina':(45,'SC'),'South Dakota':(46,'SD'),'Tennessee':(47,'TN'),'Texas':(48,'TX'),
    'Utah':(49,'UT'),'Vermont':(50,'VT'),'Virginia':(51,'VA'),'Washington':(53,'WA'),
    'West Virginia':(54,'WV'),'Wisconsin':(55,'WI'),'Wyoming':(56,'WY')
}

# abbrev -> fips
ABBR_TO_FIPS = {v[1]:k for k,v in STATE_MAP.items()}
# also invert for name lookup
NAME_TO_INFO = {k:(v[0],v[1]) for k,v in STATE_MAP.items()}

def detect_column(row, candidates):
    for c in candidates:
        if c in row and row[c] != "":
            return c
    return None

def to_month(val):
    if not val: return None
    val = val.strip()
    # already YYYY-MM
    try:
        if len(val) == 7 and val[4] == '-':
            datetime.strptime(val, '%Y-%m')
            return val
        # try parse full date
        dt = datetime.fromisoformat(val)
        return dt.strftime('%Y-%m')
    except Exception:
        # try common formats
        for fmt in ('%m/%d/%Y','%Y/%m/%d','%m/%Y','%b %Y'):
            try:
                dt = datetime.strptime(val, fmt)
                return dt.strftime('%Y-%m')
            except Exception:
                continue
    return None

def main(infile, outfile):
    r = csv.DictReader(infile)

    # detect useful columns
    date_col = detect_column(r.fieldnames, ['month','date','incident_date','reported_date'])
    fips_col = detect_column(r.fieldnames, ['state_fips','fips'])
    abbr_col = detect_column(r.fieldnames, ['state_abbr','state','abbr'])
    name_col = detect_column(r.fieldnames, ['state_name','state_name_full','state_full','state_name_raw'])
    off_col = detect_column(r.fieldnames, ['offenses','offense_count','count','incidents','n'])
    clr_col = detect_column(r.fieldnames, ['clearances','clearance','clearance_count','clearances_count'])
    pop_col = detect_column(r.fieldnames, ['population','pop','state_population'])

    if not date_col:
        print('ERROR: Could not detect date/month column in input', file=sys.stderr)
        sys.exit(2)
    if not (fips_col or abbr_col or name_col):
        print('ERROR: Could not detect state identifier column (fips/abbr/name)', file=sys.stderr)
        sys.exit(2)

    agg = defaultdict(lambda: {'offenses':0,'clearances':0,'population':0,'name':None,'abbr':None,'fips':None})

    for row in r:
        month = to_month(row.get(date_col,'').strip())
        if not month: continue

        # determine fips/abbr/name
        fips = None; abbr = None; name = None
        if fips_col and row.get(fips_col):
            try:
                fips = int(float(row[fips_col]))
            except Exception:
                fips = None
        if abbr_col and (not fips):
            candidate = row.get(abbr_col,'').strip()
            if candidate:
                candidate = candidate.upper()
                if candidate in ABBR_TO_FIPS:
                    fips = ABBR_TO_FIPS[candidate]
                    abbr = candidate
        if name_col and (not fips):
            candidate = row.get(name_col,'').strip()
            if candidate in NAME_TO_INFO:
                fips, abbr = NAME_TO_INFO[candidate]
                name = candidate

        # if we have abbr but no name, try to set name from mapping
        if abbr and not name:
            for nm,(fp,ab) in NAME_TO_INFO.items():
                if ab == abbr:
                    name = nm; break

        # if fips resolved but name empty, fill
        if fips and not name:
            for nm,(fp,ab) in NAME_TO_INFO.items():
                if fp == fips:
                    name = nm; abbr = ab if abbr else ab; break

        key = (month, fips if fips is not None else abbr)
        off = int(float(row.get(off_col,0) or 0)) if off_col else 0
        clr = int(float(row.get(clr_col,0) or 0)) if clr_col else 0
        pop = int(float(row.get(pop_col,0) or 0)) if pop_col else 0

        agg[key]['offenses'] += off
        agg[key]['clearances'] += clr
        # keep max population observed for the group
        if pop and pop > agg[key]['population']:
            agg[key]['population'] = pop
        if name: agg[key]['name'] = name
        if abbr: agg[key]['abbr'] = abbr
        if fips: agg[key]['fips'] = fips

    # write output
    writer = csv.writer(outfile)
    writer.writerow(['month','state_fips','state_abbr','state_name','offenses','clearances','population'])

    # sort by month then fips/abbr
    def sort_key(k):
        month, idv = k
        s1 = month
        s2 = idv if idv is not None else ''
        return (s1, str(s2))

    for key in sorted(agg.keys(), key=sort_key):
        month, idv = key
        rec = agg[key]
        fips = rec.get('fips') or (idv if isinstance(idv,int) else '')
        abbr = rec.get('abbr') or ''
        name = rec.get('name') or ''
        writer.writerow([month, fips, abbr, name, rec['offenses'], rec['clearances'], rec['population']])

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python3 scripts/prepare_state_month.py INPUT.csv > data/state_month.csv', file=sys.stderr)
        sys.exit(1)
    infile = open(sys.argv[1], newline='', encoding='utf-8')
    main(infile, sys.stdout)