"use client"

import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { DECISION_META, RISK_META } from "@/lib/pipeline/display"
import type { FinalDecision, RiskLevel } from "@/lib/pipeline/types"

const RISK_ORDER: RiskLevel[] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
const DECISION_ORDER: FinalDecision[] = [
  "NORMAL",
  "FINANCIAL_EXCEPTION",
  "ML_REVIEW",
  "AI_ESCALATED_REVIEW",
  "CONFIRMED_HIGH_PRIORITY",
]

function ChartCard({
  title,
  hint,
  children,
}: {
  title: string
  hint: string
  children: React.ReactNode
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-4 md:p-5">
      <div className="mb-1 flex items-baseline justify-between gap-3">
        <h2 className="text-sm font-semibold">{title}</h2>
        <span className="text-xs text-muted-foreground">{hint}</span>
      </div>
      {children}
    </div>
  )
}

function TooltipBox({
  label,
  value,
}: {
  label: string
  value: number
}) {
  return (
    <div className="rounded-md border border-border bg-popover px-3 py-2 text-xs shadow-md">
      <div className="font-medium text-popover-foreground">{label}</div>
      <div className="font-mono text-muted-foreground">{value} transactions</div>
    </div>
  )
}

export function DecisionChart({
  counts,
}: {
  counts: Record<FinalDecision, number>
}) {
  const data = DECISION_ORDER.map((d) => ({
    key: d,
    label: DECISION_META[d].short,
    value: counts[d],
    fill: DECISION_META[d].chartColor,
  }))

  return (
    <ChartCard title="Decision breakdown" hint="How each agent verdict resolved">
      <ResponsiveContainer width="100%" height={220}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 4, right: 16, bottom: 0, left: 4 }}
          barCategoryGap={8}
        >
          <XAxis type="number" hide />
          <YAxis
            type="category"
            dataKey="label"
            width={96}
            tick={{ fill: "var(--muted-foreground)", fontSize: 12 }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            cursor={{ fill: "var(--muted)", opacity: 0.4 }}
            content={({ active, payload }) =>
              active && payload && payload.length ? (
                <TooltipBox
                  label={payload[0].payload.label}
                  value={payload[0].payload.value}
                />
              ) : null
            }
          />
          <Bar dataKey="value" radius={[4, 4, 4, 4]} maxBarSize={26}>
            {data.map((d) => (
              <Cell key={d.key} fill={d.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  )
}

export function RiskDonut({
  counts,
}: {
  counts: Record<RiskLevel, number>
}) {
  const data = RISK_ORDER.map((r) => ({
    key: r,
    label: RISK_META[r].label,
    value: counts[r],
    fill: `var(--${RISK_META[r].token})`,
  })).filter((d) => d.value > 0)

  const total = data.reduce((s, d) => s + d.value, 0)

  return (
    <ChartCard title="Risk distribution" hint="Assigned risk level per transaction">
      <div className="flex items-center gap-4">
        <div className="relative">
          <ResponsiveContainer width={180} height={180}>
            <PieChart>
              <Pie
                data={data}
                dataKey="value"
                nameKey="label"
                innerRadius={54}
                outerRadius={80}
                paddingAngle={2}
                strokeWidth={0}
              >
                {data.map((d) => (
                  <Cell key={d.key} fill={d.fill} />
                ))}
              </Pie>
              <Tooltip
                content={({ active, payload }) =>
                  active && payload && payload.length ? (
                    <TooltipBox
                      label={payload[0].payload.label}
                      value={payload[0].payload.value}
                    />
                  ) : null
                }
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
            <span className="font-mono text-xl font-semibold tabular-nums">{total}</span>
            <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
              scored
            </span>
          </div>
        </div>
        <ul className="flex-1 space-y-2">
          {data.map((d) => (
            <li key={d.key} className="flex items-center justify-between text-sm">
              <span className="flex items-center gap-2">
                <span
                  className="size-2.5 rounded-sm"
                  style={{ backgroundColor: d.fill }}
                />
                {d.label}
              </span>
              <span className="font-mono tabular-nums text-muted-foreground">
                {d.value}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </ChartCard>
  )
}
