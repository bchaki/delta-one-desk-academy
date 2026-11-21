## Learn

Limits, controls and conduct are the rules that keep a trading desk safe. **Limits** cap how much risk the desk can take. **Controls** are the checks that make sure the numbers and processes are right. **Conduct** is how people behave: with clients, with information and with the market. All three matter to a TDA, who sees the limit report every morning, runs many of the controls and is trusted with sensitive information.

### Limits: soft and hard

Each limit has two levels. A **soft limit** triggers escalation: the desk head and risk are told, and the trader explains. A **hard limit** is a stop: the position must be reduced, or a documented exception approved by someone senior. The illustrative set in `config/desk.yaml` includes net delta, gross notional, one-day 99% VaR, single-name position as a share of ADV, days to liquidate and top-five concentration. Each metric is compared in absolute value with its soft and hard limits, and **utilisation** is the value as a share of the hard limit. For a net delta of 3,000,000 against a soft limit of 2,000,000 and a hard limit of 5,000,000, the status is {{ex.limits.expected.0.status}} with a utilisation of {{ex.limits.expected.0.utilisation:.0%}}. A VaR of 3,500,000 against a hard limit of 3,000,000 is a {{ex.limits.expected.1.status}} breach at {{ex.limits.expected.1.utilisation:.0%}} of the limit.

### What a breach process looks like

A breach is not a disaster, but the process is strict. **Detect** (the report flags it). **Notify** (risk, the desk head, sometimes the client coverage). **Explain** (what moved: a position, a market move, a data error). **Decide** (reduce, hedge or seek a temporary excess approval). **Record** (the cause, the decision and the time). **Follow up** (check the limit is back within bounds and whether the limit itself is right). Passive breaches, from market moves with no trading, are treated differently from active breaches, but both are recorded.

### Controls

**Pre-trade controls**: limit checks, locate checks, restricted-list checks, ticket validation. **Real-time controls**: intraday limit monitors, price alerts, order-size alerts. **End-of-day controls**: price checks, PnL explain, reconciliations. **Periodic controls**: independent price verification, access reviews, documentation reviews. The principle of **three lines of defence** applies: the desk owns its risk and controls (first line), risk and compliance oversee them (second), and internal audit tests them independently (third).

### Information barriers

A Delta One desk sees **client flow**: who is buying what, how big, and how financed. This is confidential and may be market-sensitive. **Information barriers** (also called Chinese walls) separate parts of the bank so that confidential information from one side, such as corporate finance or research, does not reach trading or sales. Within the desk, client positions are shared on a need-to-know basis. A TDA who mentions a client's large position to someone who does not need it is creating a conduct problem.

### Market abuse: compliance cases

Market abuse rules prohibit trading on inside information and manipulating the market. The following are taught as **cases to recognise and refuse**, never as techniques. **Front-running**: trading ahead of a known client order for your own benefit. It uses confidential knowledge of client flow and is a breach of duty. **Spoofing**: entering orders you do not intend to execute to move the price, then trading against the move. It is prohibited and has been prosecuted. **Market manipulation at the close or in a squeeze**: acting to move prices or lock supply to harm others. **Insider dealing**: trading on non-public price-sensitive information. **Dividend-tax schemes** such as cum-ex, treated in the SBL cases module. The common thread is that each uses a position of trust or technical access to gain unfairly, and surveillance systems look for the patterns.

### What to do if you see something

If you suspect misconduct, **stop**, **do not tip off** the person, **record** what you saw, and **escalate** to compliance or through the whistleblowing channel. Do not investigate on your own, and do not delete anything. Retaliation against those who report is itself a breach, and regulators treat people who stay silent harshly.

### Personal conduct

Personal account dealing rules require pre-approval and holding periods for staff. Gifts and entertainment are logged and capped. Communication happens on recorded channels: a conversation on a personal phone about a trade is a finding. Conflicts of interest, such as a relative at a client, are declared.

### Records

Regulators require records of orders, trades, communications and approvals, kept for years and retrievable. A TDA's log of breaks, overrides and approvals is part of that record. An approval given verbally and never written down did not happen.

## Worked example

Read the desk's limit report on a busy morning.

**Step 1: net delta.** 3,000,000 against a soft limit of 2,000,000: status {{ex.limits.expected.0.status}}, {{ex.limits.expected.0.utilisation:.0%}} of the hard limit. Escalate to the desk head and ask which trade did it.

**Step 2: VaR.** 3,500,000 against 3,000,000 hard: status {{ex.limits.expected.1.status}}. This is a breach: notify risk immediately.

**Step 3: days to liquidate.** 2 days against a soft limit of 3: within limit.

**Step 4: explain.** The VaR jump came from a large new swap hedge not yet matched by its swap leg, a booking lag rather than risk.

**Step 5: decide.** The swap is booked, VaR falls below the soft limit, and risk records a short technical breach with the cause.

**Step 6: conduct moment.** A sales colleague asks for the client's position size "for context". You check that they are on the client's coverage list before sharing anything.

**Step 7: record.** You log the breach, the cause, the time of resolution and the person who approved the temporary excess.

## Desk reality

**Report early.** A breach reported by the desk is a process working. A breach found by risk is a conversation.

**Know the escalation chain by name.** In a breach you need phone numbers, not an org chart.

**Written beats verbal.** Approvals, overrides and exceptions need a record. If it is not written, it did not happen.

**Culture is what you do when no one is watching.** The cases above are rare, but small decisions about information and records are daily.
