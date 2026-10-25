import { api } from "../api.js";
import { ActiveStrip, Async, Card, Cols, Fig, Html, Kpis, Section, useApi } from "../ui.jsx";

export default function WhatIf({ ctx }) {
  const s = useApi(() => api.whatif(ctx.activeId), [ctx.activeId, ctx.rev]);
  return <Async s={s}>{(d) => (<>
    <Section title="What-If Simulator" sub="See how the Success Score changes if attendance reaches 80% or skills improve by 10 points." />
    <ActiveStrip s={ctx.activeStudent} />
    <Kpis items={d.kpis} cols={3} />
    <div style={{ height: 12 }} />
    <Cols widths={[1.3, 1]}>
      <Fig fig={d.bar} />
      <div>
        <Card title="📈 Insight"><Html html={d.insight} /></Card>
        <Card title="⏱ Recovery outlook">Estimated recovery time: <b>{d.recovery.weeks} weeks</b><br />Improvement potential: <b>{d.recovery.potential} points</b><br />Recommended plan: {d.recovery.plan}</Card>
        <Fig fig={d.gauge} />
      </div>
    </Cols>
  </>)}</Async>;
}
