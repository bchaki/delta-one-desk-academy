## Learn

Sensitivities tell you what happens if one thing moves. **Value at risk (VaR)** and **stress tests** tell you what happens if many things move together. VaR gives a loss level that should be exceeded rarely under normal conditions. Stress tests apply specific, severe scenarios. A desk needs both: VaR is a daily measure that can be backtested, and stress covers events that history under-represents.

### What VaR says

**VaR at 99% for one day** is the loss that is exceeded on 1% of days, or about 2.5 days in a 250-day year. It is a quantile, not a worst case: it says nothing about how bad the loss is when it is exceeded. VaR is reported as a positive number in currency.

### Parametric VaR

Assume returns are normal. For one position: **VaR = z x |exposure| x daily volatility**, with z = 2.326 at 99%. A 10 million position with 1.5% daily volatility has a one-day VaR of {{ex.var1.expected:,.0f}}. For several positions the volatilities combine through correlation. For two positions: **VaR = z x sqrt((e1 s1)^2 + (e2 s2)^2 + 2 rho e1 e2 s1 s2)**. A 10 million long and a 9 million hedge with volatilities of 1.5% and 1.4% and correlation of 0.9 have a combined VaR of {{ex.var2.expected:,.0f}}, far below the 10 million position alone, which is the effect of hedging. Perfect correlation with equal sizes and opposite signs would give zero.

### Square-root-of-time

Ten-day VaR is estimated as one-day VaR times the square root of ten: {{ex.var10.expected:,.0f}} for the position above. This assumes returns are independent from day to day, which is a reasonable first approximation and a poor one in a trend or a crisis.

### Historical simulation

Instead of assuming normality, apply each of the last 250 days' actual returns to today's positions and read the 1% quantile. It captures fat tails and real correlations, but only those in the window: a calm window gives a low VaR just before a storm. The desk's engine does this on the delta vector with USD returns of each stock or index, using the local price times FX.

### Monte Carlo

Draw many scenarios from a multivariate distribution with the sample covariance, apply them to positions and read the quantile. With a normal distribution and a delta-only book it reproduces parametric VaR; its value is that the machinery extends to non-linear products. The synthetic engine uses a seeded generator so results are repeatable.

### Expected shortfall

**Expected shortfall (ES)** is the average loss in the tail beyond VaR. Regulators have moved to ES at 97.5% in part because it sees how bad the tail is. For a normal distribution, ES = exposure x volatility x phi(z) / (1 - conf): a 10 million position with 1.5% volatility has ES at 97.5% of {{ex.es.expected:,.0f}}.

### Component and marginal VaR

**Marginal VaR** is the change in portfolio VaR from a small increase in a position. **Component VaR** = position x marginal VaR, and the components add up to total VaR. They tell the trader which positions drive risk, and which add risk or reduce it. A hedge has a negative component.

### Backtesting

Count the days when the loss exceeded the previous day's VaR. At 99% over 250 days the expectation is 2.5. The Basel-style traffic light is **green for 0 to 4 exceptions, yellow for 5 to 9 and red for 10 or more**. Three exceptions is {{ex.light3.expected}} and seven is {{ex.light7.expected}}. Too many exceptions mean the model understates risk. Too few suggest it is too cautious and ties up capital.

### Stress testing

A stress applies a scenario's factor moves to positions: equities by region, FX, dividends, borrow fees and a single-name shock. The scenarios in the academy are stylised after well-known episodes (an equity crash, a rates shock, a March-2020-style liquidity event, a squeeze). Each is labelled illustrative. The result is a PnL by factor and by leg, so you can see whether hedges or client swaps drive it. A **reverse stress** asks the opposite question: what scenario would cause a given loss.

### VaR limits

VaR does not capture what is missing from the data: liquidity, gap risk, the correlation breaks of a crisis. That is why the desk uses VaR with stress, liquidity, concentration and sensitivity limits. No single measure is enough, and the Limits module shows how they combine.

## Worked example

A trader asks how risky the index hedge is.

**Step 1: single position.** 10 million of exposure, 1.5% daily volatility: VaR99 = {{ex.var1.expected:,.0f}}.

**Step 2: with the hedge.** Add a 9 million offsetting position at 1.4% volatility and a correlation of 0.9: VaR falls to {{ex.var2.expected:,.0f}}.

**Step 3: ten days.** Scale the single-position figure by the square root of ten: {{ex.var10.expected:,.0f}}.

**Step 4: tail.** ES at 97.5% of the single position is {{ex.es.expected:,.0f}}, higher than VaR at the same level because it averages the tail.

**Step 5: backtest.** Over the last year there were 3 exceptions: {{ex.light3.expected}}. Seven would be {{ex.light7.expected}}.

**Step 6: stress.** The engine applies an equity crash scenario to the desk's delta by region: the hedged book loses little on equity, but borrow and single-name shocks drive the result.

**Step 7: report.** The TDA includes VaR, ES, top components, the traffic light and the worst stress with its factor split, and notes which assumption would change the picture most.

## Desk reality

**VaR is a model output, not a fact.** Know the window, the confidence and the method before quoting it.

**A calm year makes VaR small.** If the window has no stress, historical VaR is low just when the risk is highest. Stress and ES are the correction.

**Look at the components.** A VaR that doubled because of one position is a different story from one that doubled across the book.

**Exceptions need explanations.** Each exception should have a recorded cause: market move, model gap, data error or position change.
