#!/usr/bin/env python3
"""
Generate synthetic monthly state-level data from 2021-01 to 2026-01
and write to data/state_month.csv (overwrites existing file).

This creates plausible variation with seasonality, trend and noise.
"""
import csv
from datetime import datetime
import math
import random
import os

STATE_INFO = [
    (1,'AL','Alabama'),(2,'AK','Alaska'),(4,'AZ','Arizona'),(5,'AR','Arkansas'),(6,'CA','California'),
    (8,'CO','Colorado'),(9,'CT','Connecticut'),(10,'DE','Delaware'),(11,'DC','District of Columbia'),(12,'FL','Florida'),
    (13,'GA','Georgia'),(15,'HI','Hawaii'),(16,'ID','Idaho'),(17,'IL','Illinois'),(18,'IN','Indiana'),
    (19,'IA','Iowa'),(20,'KS','Kansas'),(21,'KY','Kentucky'),(22,'LA','Louisiana'),(23,'ME','Maine'),
    (24,'MD','Maryland'),(25,'MA','Massachusetts'),(26,'MI','Michigan'),(27,'MN','Minnesota'),(28,'MS','Mississippi'),
    (29,'MO','Missouri'),(30,'MT','Montana'),(31,'NE','Nebraska'),(32,'NV','Nevada'),(33,'NH','New Hampshire'),
    (34,'NJ','New Jersey'),(35,'NM','New Mexico'),(36,'NY','New York'),(37,'NC','North Carolina'),(38,'ND','North Dakota'),
    (39,'OH','Ohio'),(40,'OK','Oklahoma'),(41,'OR','Oregon'),(42,'PA','Pennsylvania'),(44,'RI','Rhode Island'),
    (45,'SC','South Carolina'),(46,'SD','South Dakota'),(47,'TN','Tennessee'),(48,'TX','Texas'),(49,'UT','Utah'),
    (50,'VT','Vermont'),(51,'VA','Virginia'),(53,'WA','Washington'),(54,'WV','West Virginia'),(55,'WI','Wisconsin'),
    (56,'WY','Wyoming')
]

def months_range(start_ym, end_ym):
    s = datetime.strptime(start_ym+'-01','%Y-%m-%d')
    e = datetime.strptime(end_ym+'-01','%Y-%m-%d')
    months = []
    cur = s
    while cur <= e:
        months.append(cur.strftime('%Y-%m'))
        # advance month
        year = cur.year + (cur.month // 12)
        month = cur.month % 12 + 1
        cur = datetime(year, month, 1)
    return months

def synthetic_population(fips):
    # Simple deterministic population bucket by fips to generate variety
    base = 400_000
    pop = base + (fips * 220_000)  # results between ~600k and ~12M
    return pop

def generate():
    months = months_range('2021-01','2026-01')
    rows = []
    random.seed(42)

    for fips, abbr, name in STATE_INFO:
        population = synthetic_population(fips)
        # state specific baseline per-100k monthly rate (varies moderately)
        base_per_100k = 35 + (fips % 7) * 3  # between ~35 and ~55
        # small state factor
        state_noise = (random.random() - 0.5) * 0.12

        for i, m in enumerate(months):
            # seasonality: sinusoidal factor (peak mid-year)
            season = 1 + 0.12 * math.sin(2*math.pi*(i%12)/12)
            # small upward trend over 5 years
            trend = 1 + (i / (len(months)-1)) * 0.06
            # monthly incidents per 100k
            per100k = base_per_100k * season * trend * (1 + state_noise)
            incidents = int(round((population/100000.0) * per100k + random.gauss(0, max(1,(population/100000.0)*5))))
            incidents = max(0, incidents)
            # clearance rate typically much lower (e.g., 8% ± 5%)
            clr_rate = max(0.02, min(0.28, 0.12 + (random.random()-0.5)*0.1 + (0.01*(fips%3))))
            clearances = int(round(incidents * clr_rate))

            rows.append((m, fips, abbr, name, incidents, clearances, population))

    outdir = os.path.join(os.path.dirname(__file__), '..', 'data')
    os.makedirs(outdir, exist_ok=True)
    outpath = os.path.join(outdir, 'state_month.csv')
    with open(outpath, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['month','state_fips','state_abbr','state_name','offenses','clearances','population'])
        for r in rows:
            w.writerow(r)

    print(f'Wrote {len(rows)} rows to {outpath}')

if __name__ == '__main__':
    generate()
