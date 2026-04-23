# 5D Risk Scoring Rubric

## Probability (P) — How likely is this to occur?

| Score | Label | Definition |
|-------|-------|------------|
| 1 | Rare | < 5% chance. Requires multiple unlikely conditions. |
| 2 | Unlikely | 5-20%. Could happen but requires specific circumstances. |
| 3 | Possible | 20-50%. Reasonable to expect under normal conditions. |
| 4 | Likely | 50-80%. More likely to happen than not. |
| 5 | Near-certain | > 80%. Would be surprising if it didn't happen. |

## Impact (I) — How bad is it if it occurs?

| Score | Label | Definition |
|-------|-------|------------|
| 1 | Negligible | Minor inconvenience. Absorbed by normal operations. |
| 2 | Minor | Noticeable but contained. Requires some effort to address. |
| 3 | Moderate | Significant disruption. Requires dedicated response. |
| 4 | Major | Severe damage. Recovery is difficult and costly. |
| 5 | Catastrophic | Existential or irreversible. Threatens the entire endeavor. |

## Velocity (V) — How fast does it hit?

| Score | Label | Definition |
|-------|-------|------------|
| 1 | Slow | Months to manifest. Plenty of time to react. |
| 2 | Gradual | Weeks. Warning signs appear with time to adjust. |
| 3 | Moderate | Days. Requires quick but not immediate response. |
| 4 | Fast | Hours. Very limited reaction window. |
| 5 | Instant | No warning. Impact is immediate upon occurrence. |

## Detectability (D) — How hard to detect early?

| Score | Label | Definition |
|-------|-------|------------|
| 1 | Obvious | Clear, unmissable indicators. Monitoring already in place. |
| 2 | Detectable | Visible with basic attention. Standard checks catch it. |
| 3 | Requires effort | Needs active monitoring or investigation to spot. |
| 4 | Hidden | Only found through deep analysis or specialized tools. |
| 5 | Invisible | No known leading indicators. Discovered only after impact. |

## Reversibility (R) — How hard to undo?

| Score | Label | Definition |
|-------|-------|------------|
| 1 | Trivial | Undo button. Minutes to reverse with no lasting effect. |
| 2 | Easy | Hours to reverse. Minor residual effects. |
| 3 | Moderate | Days/weeks to reverse. Some lasting consequences. |
| 4 | Difficult | Months to recover. Significant lasting damage. |
| 5 | Permanent | Cannot be undone. Damage is irreversible. |

## Composite Score Calculation

**Composite = (P x I) + V + D + R**

| Range | Interpretation |
|-------|---------------|
| 3-8 | Low risk. Monitor but no immediate action needed. |
| 9-16 | Moderate risk. Plan mitigations, track actively. |
| 17-25 | High risk. Prioritize mitigation. Escalate if needed. |
| 26-40 | Critical risk. Immediate action required. May be a blocker. |

The P x I core ranges 1-25. The V + D + R modifiers range 3-15.
A risk with low P x I but high V + D + R is a "sleeper" — unlikely but
devastating and hard to catch if it does occur.
