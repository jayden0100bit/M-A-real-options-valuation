# Accretion / dilution methodology (Stage 4B)

Code: `src/valuation/accretion.py` (driver `build_stage4.py`). Outputs: `data/processed/accretion_dilution_inputs.csv`
(every input with source and type) and `accretion_dilution_outputs.csv`. Checks: `accretion_*`.

## 1. Inputs and sources

| Group | Item | Value | Type | Source |
|---|---|---|---|---|
| Disney standalone | Total segment operating income FY2018–21 | 15,300 / 17,329 / 18,768 / 20,176 (FY2022 n/a) | reported forecast | May 2018 proxy p.153 ("Disney street forecasts": analyst-based, approved for the advisors' use, **not** prepared by Disney management) |
| | Corporate & unallocated FY2020 | 659, CAGR 4.2% | reported forecast | proxy p.152 (street estimates) |
| | EBITDA FY2018–22 | 17,283 … 23,555 | reported forecast | proxy p.153 |
| | Net interest, NCI, diluted shares FY2018 | −574, −468, 1,507m | reported (held flat: estimate) | Disney FY2018 10-K |
| Acquired business | Revenue, EBITDA (June FY) | Disney forecasts for RemainCo | reported forecast | proxy p.129 |
| | Net interest, interest income, equity income, NCI | −1,205, +39, −563, −257 | reported pro forma (held flat: estimate) | 8-K/A Ex. 99.4 p.4 (FY2018, closing perimeter, Sky removed) |
| | D&A | 2.01% of revenue | estimate | Stage 3 |
| Perimeter | RSN revenue share; RSN sale | 20.8%; ~$11bn | derived; reported | Stage 2; FY2019 10-K |
| Financing | Cash / stock consideration | 35,700 / ~35,000 | reported | closing 8-K12B |
| | New shares | 306.845m (at $114.1801) | reported | closing 8-K12B |
| | Bridge drawn / repaid from acquired cash | 31,100 / 16,100 | reported | FY2019 10-K |
| | Rate on new debt | 3.3% | reported assumption | 8-K/A Ex. 99.3 p.12 (Disney's pro forma) |
| | Original all-stock structure | 515m shares | reported | Dec 2017 release |
| | Planned buybacks (Dec 2017) / programme terminated (Mar 2019) | $10bn + $10bn / yes | guidance / reported | call transcript; FY2019 10-K |
| Purchase accounting | Incremental amortization excl. RSNs | 2,700 a year | derived | FY2019 10-K Note 4: $3.5bn (FY2018) − $0.8bn RSN; $3.1bn (FY2019) − $0.4bn |
| Tax | Rate on all items | 22% | estimate | Stage 3 B |
| Anchor | Disney vs pro forma diluted EPS | FY2018 $8.36 → $5.94; Q1 FY2019 $1.86 → $1.24 | reported (pro forma) | 8-K/A Ex. 99.3 pp.5–6 |

## 2. Model (Disney fiscal years FY2020–FY2022, the first three full years after the 20 Mar 2019 close)

```
Disney NI       = (segment OI - corporate - net interest) x (1 - t) - NCI          [FY2022 segment OI scaled by EBITDA growth: estimate]
RemainCo NI     = (EBITDA - D&A - net interest + interest income + equity income) x (1 - t) - NCI
                  EBITDA and revenue moved to Disney's FY = 0.75 x June FY(t) + 0.25 x June FY(t+1)
                  base excludes RSNs: RemainCo EBIT x (1 - 20.8%)
New debt        = cash consideration - bridge repaid from acquired cash [- RSN proceeds in the base case]
Adjusted NI     = Disney NI + RemainCo NI - interest on new debt x (1 - t) + synergies x (1 - t)
GAAP-basis NI   = Adjusted NI - PPA amortization x (1 - t) - integration costs x (1 - t)
Pro forma shares = Disney shares + new shares;  accretion = pro forma EPS / standalone EPS - 1
```

Cases:
* **Base:** closing financing, RSNs sold and proceeds repaying debt, base synergies.
* **RSNs retained.**
* **No synergies.**
* **Original Dec 2017 all-stock structure:** 515m shares, without and with the $20bn of planned buybacks (debt-funded at 3.3%,
  repurchased at $114.18).

Sensitivities on FY2021:
* synergy realization 0–125%;
* integration-cost overrun 1.0–2.0x;
* financing mix 0–100% cash (total consideration held at $70.7bn);
* new-debt rate 2–6%;
* Disney price for the stock portion $90–130;
* purchase-accounting amortization 50–150%.

## 3. What is not modelled (limitations)
* **Hulu consolidation:** Disney consolidated Hulu at 60%, then 67%, after closing, and NBCU's redeemable NCI is not
  allocated losses. Both sides are carried at equity-method-style figures here.
* **Strategic investments:** content-licensing changes and the Disney+/DTC investment Disney described are not modelled.
  They were later a major EPS driver.
* **Earnings base:** Disney's standalone NI uses analysts' segment forecasts and flat interest, NCI and share count. Disney
  terminated buybacks in March 2019.
* **Tax on the RSN sale:** the RSN proceeds are treated gross; Disney paid ~$7.6bn of combined spin-off and RSN taxes,
  split unknown. The resulting interest saving is an upper bound.
* **Amortization path:** purchase-accounting amortization is held flat; in practice it declines as film step-ups amortize.
* **Events after the forecasts:** the forecasts pre-date COVID-19. Actual FY2020 results are not used and not comparable.
