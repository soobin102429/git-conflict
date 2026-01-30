#!/usr/bin/env python3
"""
Generate demographic aggregate CSVs and a Sankey JSON from `data/state_month.csv`.

Approach:
- Use the global distributions provided (hardcoded from user's message) as priors.
- For each state-month, distribute `offenses` proportionally into locations, weapons, offenses-linked categories.
- Aggregate across all months+states to a US-level Sankey (Location -> Weapon -> Offense).
- Also output simple US-level age and sex CSVs (for charts) based on provided totals.

Outputs:
 - data/sankey_us.json  (nodes, links for sankey)
 - data/age_us.csv
 - data/sex_us.csv

Note: these are synthetic aggregations based on provided distributions, for visualization only.
"""
import csv
import json
from collections import defaultdict
import os

# --- distributions from user message (counts) ---
OFFENDER_AGE = {
    '20-29':804232,'30-39':780177,'40-49':433988,'10-19':379813,'Unknown':329673,'50-59':237879,
    '60-69':101324,'70-79':23753,'0-9':5057,'80-89':5002,'90-Older':2193
}
OFFENDER_SEX = {'Male':2265464,'Female':696299,'Unknown':137568,'Not Specified':301008}

LOCATION = {
  'Residence/Home':1920229,'Highway/Road/Alley/Street/Sidewalk':778700,'Parking/Drop Lot/Garage':208198,
  'Other/Unknown':104201,'Hotel/Motel/Etc.':58147,'Bar/Nightclub':51384,'Convenience Store':44552,'Restaurant':43244,
  'Park/Playground':42564,'School-Elementary/Secondary':39755,'Service/Gas Station':37900,'Jail/Prison/Penitentiary/Corrections Facility':37571,
  'Drug Store/Doctor\'s Office/Hospital':29118,'Commercial/Office Building':25180,'Field/Woods':18333,'Grocery/Supermarket':17968,
  'Department/Discount Store':16358,'Specialty Store':15675,'Air/Bus/Train Terminal':13889,'Government/Public Building':13150,
  'Shelter-Mission/Homeless':7752,'School-College/University':6634,'Shopping Mall':6059,'School/College':4838,'Camp/Campground':4726,
  'Liquor Store':4683,'Church/Synagogue/Temple/Mosque':4588,'Construction Site':4279,'Tribal Lands':3365,'Lake/Waterway/Beach':3364,
  'Rental Storage Facility':3348,'Gambling Facility/Casino/Race Track':2788,'Community Center':2691,'Arena/Stadium/Fairgrounds/Coliseum':2375,
  'Industrial Site':2164,'Daycare Facility':1918,'Bank/Savings and Loan':1843,'Auto Dealership New/Used':1705,'Amusement Park':1363,
  'Abandoned/Condemned Structure':1323,'Dock/Wharf/Freight/Modal Terminal':1155,'Rest Area':1115,'Farm Facility':747,'ATM Separate from Bank':274,
  'Military Installation':241,'Cyberspace':0,'Not Specified':0
}

WEAPON = {
  'Handgun':727729,'Personal Weapons':704067,'Knife/Cutting Instrument':575271,'Firearm':452701,'Other':353407,
  'Blunt Object':346097,'Motor Vehicle/Vessel':188325,'Asphyxiation':106723,'None':91762,'Unknown':74937,'Rifle':62245,
  'Other Firearm':35673,'Shotgun':23723,'Handgun (Automatic)':20102,'Firearm (Automatic)':10960,'Fire/Incendiary Device':8483,
  'Drugs/Narcotics/Sleeping Pills':5927,'Poison':4036,'Rifle (Automatic)':3439,'Explosives':2198,'Other Firearm (Automatic)':827,
  'Shotgun (Automatic)':319
}

OFFENSE_LINK = {
 'Destruction/Damage/Vandalism of Property':217365,'Weapon Law Violations':178345,'Simple Assault':111621,'Drug/Narcotic Violations':49326,
 'Kidnapping/Abduction':47586,'Burglary/Breaking & Entering':39455,'All Other Larceny':28077,'Intimidation':22377,'Drug Equipment Violations':20798,
 'Motor Vehicle Theft':12542,'Robbery':11276,'Murder and Nonnegligent Manslaughter':9322,'Stolen Property Offenses':8164,'Shoplifting':8136,
 'Theft From Motor Vehicle':6488,'Theft From Building':6303,'Criminal Sexual Contact':4127,'Arson':3466,'False Pretenses/Swindle/Confidence Game':2472,
 'Animal Cruelty':2140,'Impersonation':1399,'Theft of Motor Vehicle Parts or Accessories':1084,'Counterfeiting/Forgery':1012,'Rape':860,
 'Pocket-picking':729,'Purse-snatching':661,'Pornography/Obscene Material':627,'Identity Theft':594,'Credit Card/Automated Teller Machine Fraud':570,
 'Extortion/Blackmail':436,'Negligent Manslaughter':415,'Statutory Rape':356,'Human Trafficking, Commercial Sex Acts':251,'Sodomy':203,
 'Assisting or Promoting Prostitution':196,'Embezzlement':174,'Bribery':167,'Prostitution':131,'Human Trafficking, Involuntary Servitude':106,
 'Sexual Assault With An Object':101,'Wire Fraud':64,'Purchasing Prostitution':58,'Incest':54,'Hacking/Computer Invasion':27,'Theft From Coin-Operated Machine or Device':19,
 'Flight to Avoid Prosecution':16,'Operating/Promoting/Assisting Gambling':14,'Federal Liquor Offenses':10,'Welfare Fraud':6,'Betting/Wagering':5,'Gambling Equipment Violation':4,
 'Failure to Register as a Sex Offender':2,'Smuggling Aliens':2,'Illegal Entry into the United States':1
}

def normalize(d):
    total = sum(d.values())
    if total == 0:
        return {k:0 for k in d}
    return {k: v/total for k,v in d.items()}

def main():
    # read state_month.csv
    inpath = os.path.join(os.path.dirname(__file__), '..', 'data', 'state_month.csv')
    rows = []
    with open(inpath, newline='', encoding='utf-8') as f:
        r = csv.DictReader(f)
        for rec in r:
            rows.append({'month':rec['month'],'fips':rec['state_fips'],'abbr':rec['state_abbr'],'name':rec['state_name'],'offenses':int(rec['offenses'])})

    loc_p = normalize(LOCATION)
    weap_p = normalize(WEAPON)
    off_p = normalize(OFFENSE_LINK)

    # Sankey aggregation: Location -> Weapon -> Offense totals across all rows
    link_agg = defaultdict(float)
    nodes_set = set()

    total_offenses = sum(r['offenses'] for r in rows)

    for rec in rows:
        O = rec['offenses']
        if O <= 0: continue
        for loc, pl in loc_p.items():
            loc_count = O * pl
            for weap, pw in weap_p.items():
                weap_count = loc_count * pw
                for off, po in off_p.items():
                    cnt = weap_count * po
                    if cnt <= 0: continue
                    key1 = (loc, weap)
                    key2 = (weap, off)
                    link_agg[key1] += cnt
                    link_agg[key2] += cnt
                    nodes_set.add(loc); nodes_set.add(weap); nodes_set.add(off)

    # produce nodes list and links
    nodes = [{'id':n} for n in sorted(nodes_set)]
    links = []
    for (src,tgt), val in link_agg.items():
        links.append({'source': src, 'target': tgt, 'value': int(round(val))})

    outdir = os.path.join(os.path.dirname(__file__), '..', 'data')
    with open(os.path.join(outdir,'sankey_us.json'),'w',encoding='utf-8') as f:
        json.dump({'nodes':nodes,'links':links,'total_offenses': total_offenses}, f, indent=2)

    # Write US-level age/sex CSVs (proportional to totals)
    with open(os.path.join(outdir,'age_us.csv'),'w',newline='',encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['age','count'])
        for k,v in OFFENDER_AGE.items(): w.writerow([k,v])

    with open(os.path.join(outdir,'sex_us.csv'),'w',newline='',encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['sex','count'])
        for k,v in OFFENDER_SEX.items(): w.writerow([k,v])

    print('Wrote sankey_us.json, age_us.csv, sex_us.csv')

if __name__ == '__main__':
    main()
