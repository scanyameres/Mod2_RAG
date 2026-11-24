# Sample knowledge base

Thirteen short, **invented** regulations for testing the app until real documents arrive. The State of Velmar and the Municipality of Altenbruck do not exist; the values are plausible but not taken from any real code, so the files can be committed and shared.

Each sub-folder is a document type (the ids of `categories.toml`).

## Load it

Either upload the files on the **Knowledge base** page, type by type, or copy everything and rebuild:

```bat
xcopy sample_data data\library /E /I /Y
```

then **Knowledge base → Rebuild index** (about 120 passages, so the embedding cost is negligible). This README is copied along but ignored: only files inside the type folders are indexed.

## Documents

| Type (folder) | File | Short | What it regulates |
|---|---|---|---|
| `general_building` | `Velmar_Building_Code_VBC.pdf` (3 pages) | VBC | Definitions of the building kinds, order of precedence, room heights, sanitary rooms in general, standard parking space, materials, guardrails, stairs |
| `general_building` | `Velmar_Parking_Ordinance_VPO.md` | VPO | Number of car and bicycle spaces per use, dimensions next to walls, trees, mixed use, transitional rule |
| `housing` | `Housing_Standards_Regulation_HSR.md` | HSR | Dwellings: bathroom size, ventilation, materials and safety; extras for apartment buildings and for detached houses |
| `housing` | `Shared_Facilities_Guideline_SFG.txt` | SFG | Non-binding recommendations: shared garages, laundry, bicycle and waste rooms |
| `business` | `Workplace_Premises_Regulation_WPR.md` | WPR | Offices: room size and height, number of toilets, ventilation, floors, safety |
| `business` | `Retail_Premises_Regulation_RPR.md` | RPR | Stores by size class: sales rooms, customer toilets, ventilation, floors, customer parking, exits |
| `fire_safety` | `Fire_Safety_Regulation_FSR.pdf` (3 pages) | FSR | Building classes, material fire classes, structure, escape routes, ventilation ducts, alarms |
| `fire_safety` | `Garage_Fire_Safety_Guideline_GFG.md` | GFG | Garage classes, fire resistance, smoke extraction, exits, charging points, storage |
| `energy_accessibility` | `Accessible_Building_Regulation_ABR.md` | ABR | Accessible parking spaces and sanitary rooms, where they are required, exceptions |
| `energy_accessibility` | `Energy_Efficiency_Regulation_EER.md` | EER | U-values, heat recovery, charging for electric vehicles, solar duty |
| `local_zones` | `Altenbruck_Zone_A_Agricultural_Area_Statute.md` | Zone A | Farms only; unsealed parking, timber and earth tones, own wastewater treatment |
| `local_zones` | `Altenbruck_Zone_B_Urban_Growth_Area_Statute.md` | Zone B | Dense quarter; fewer parking spaces, windowless bathrooms, green roofs |
| `local_zones` | `Altenbruck_Zone_C_Historic_Protection_Area_Statute.pdf` (2 pages) | Zone C | Old Town; traditional materials, no visible parking or vents, lower room height allowed |

The formats differ on purpose: Markdown headings, numbered headings in a text file (`2.1 Dimensions`), and PDFs with `Part` / `Chapter` / `Art.` / `§` headings and page numbers. The three PDFs cannot be edited by hand; to change a value there, add a Markdown document or ask for a new PDF.

## Same question, different answer

Expected answers, to compare with what the app says when document types are switched on or off.

| Question | With these types on | Expected answer |
|---|---|---|
| How big is a parking space? | General | 2.50 m × 5.00 m; parallel to the lane 2.30 m × 6.00 m (VBC Art. 12); next to one wall 2.65 m wide, between two walls 2.90 m (VPO Art. 4) |
| | + Business | Customer spaces of stores: 2.70 m × 5.00 m (RPR Art. 6) |
| | + Energy and accessibility | Accessible spaces: 3.50 m × 5.00 m (ABR Art. 2) |
| How many car spaces for an apartment building with 20 dwellings? | General | 22 = 20 + 2 visitor spaces (VPO Art. 2) |
| | + Local zones, Zone A | Not permitted at all (§ 2) |
| | + Local zones, Zone B | 16 (22 less 30 % = 15.4, rounded up; the cap of 0.8 per dwelling is also 16). Within 400 m of a tram stop: 11 (§ 4) |
| | + Local zones, Zone C | 22, but spaces that cannot be built are replaced by EUR 9,000 each (§ 5) |
| How many car spaces for an office with 1,000 m²? | General | 25 (1 per 40 m²). 34 if the application was submitted before 1 January 2025 (VPO Art. 7) |
| | + Local zones, Zone B | 18 (25 less 30 % = 17.5); near a tram stop 13 |
| How many car spaces for a store with 600 m² of sales area? | General | 20 (1 per 30 m²) |
| | + Local zones | Zone B: 14, near a tram stop 10. Zone C: such a store is not permitted (maximum 300 m², § 7). Zone A: only farm shops up to 100 m² |
| What ventilation does a bathroom need? | General only | A window or mechanical ventilation; no figures (VBC Art. 8) |
| | + Housing | Window of 0.4 m² or extract of 40 m³/h (bathroom), 20 m³/h (toilet room); windowless only with a fan (HSR Art. 4) |
| | + Business | Toilet rooms 11 m³/h per m², washrooms 15 m³/h per m² (WPR Art. 4); customer toilets at least 30 m³/h per toilet (RPR Art. 4) |
| | + Fire safety | Fire dampers where ducts cross fire-rated walls; shut-off device per storey for several dwellings (FSR Art. 9) |
| | + Local zones | Zone B: fan controlled by humidity. Zone C: no outlet in the street facade, no new bathroom window to the street |
| What is the minimum room height? | General | 2.40 m habitable rooms, 2.20 m sanitary rooms and corridors (VBC Art. 5) |
| | + Business | Offices 2.50 / 2.75 / 3.00 m by room size (WPR Art. 2); sales rooms 3.00 m, small shops 2.50 m (RPR Art. 2) |
| | + Local zones | Zone B: 4.00 m on ground floors along main streets. Zone C: 2.20 m for existing rooms in buildings from before 1950 |
| Does my shop need customer toilets? | Business | Up to 400 m² of sales area: no. Above: one for women, one for men, one accessible (RPR Art. 3) |
| | + Local zones | Zone A: farm shops need none. Zone B: above 800 m² they must be open to the public |

## Built-in difficulties

Things in the documents that an assistant can get wrong:

- **Rules that override each other.** Special regulations beat the general code, zone statutes beat both on design, heights, uses and parking, but never on fire safety (VBC Art. 3; FSR Art. 1; Zone C § 8).
- **Thresholds.** "Up to 400 m²" against "more than 400 m²" (stores); 100 m² and 1,000 m² (garages); 140 m² of living area (second parking space); "every full 10 dwellings" (visitor spaces: 19 dwellings give 1, not 2).
- **A recommendation that looks like a rule.** The SFG is not binding (garage height 2.10 m, ramp 15 %), while the GFG is binding.
- **An old value that still applies sometimes.** Offices: 1 space per 30 m² for applications before 2025, which is also the current ratio for stores.
- **The same number with different meanings.** 2.20 m (three different room-height rules), 0.90 m (guardrail, door width, space beside a toilet), 30 (minutes, percent, m² per space, metres to an exit), 40 (m³/h and m² per space).
- **Different words for the same thing.** Apartment complex / apartment building; store / shop / retail premises; bathroom / toilet room / sanitary room / washroom.
- **Answers that need two or three documents.** Solar duty (EER Art. 5) against the solar ban in Zone C § 3; mixed-use buildings (VBC Art. 2, VPO Art. 6); customer toilets do not count as staff toilets (RPR Art. 3, WPR Art. 3); the driveway as second parking space (HSR Art. 8, VPO Art. 2).
- **Questions with no answer in the knowledge base.** Hotels (the HSR points to an Accommodation Premises Regulation that is not included), buildings above 22 m (High-Rise Directive, not included), schools, restaurants, swimming pools, the Parking Ordinance of 2009.
