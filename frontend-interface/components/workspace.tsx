"use client"

import { useState } from "react"
import { ListChecks, Table2, Workflow } from "lucide-react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { PriorityQueue } from "@/components/priority-queue"
import { TransactionExplorer } from "@/components/transaction-explorer"
import { PipelineArchitecture } from "@/components/pipeline-architecture"
import type { PipelineSummary, Transaction } from "@/lib/pipeline/types"

export function Workspace({
  transactions,
  queue,
  summary,
}: {
  transactions: Transaction[]
  queue: Transaction[]
  summary: PipelineSummary
}) {
  const [tab, setTab] = useState("queue")
  const [inspectId, setInspectId] = useState<string | undefined>(undefined)

  return (
    <Tabs value={tab} onValueChange={setTab} className="gap-4">
      <TabsList className="h-auto flex-wrap justify-start gap-1 bg-card p-1">
        <TabsTrigger value="queue" className="gap-1.5">
          <ListChecks className="size-4" aria-hidden />
          Review queue
          <span className="ml-1 rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
            {queue.length}
          </span>
        </TabsTrigger>
        <TabsTrigger value="explorer" className="gap-1.5">
          <Table2 className="size-4" aria-hidden />
          Transaction explorer
        </TabsTrigger>
        <TabsTrigger value="pipeline" className="gap-1.5">
          <Workflow className="size-4" aria-hidden />
          Pipeline
        </TabsTrigger>
      </TabsList>

      <TabsContent value="queue">
        <PriorityQueue
          queue={queue}
          onInspect={(id) => {
            setInspectId(id)
            setTab("explorer")
          }}
        />
      </TabsContent>

      <TabsContent value="explorer">
        <TransactionExplorer
          key={inspectId ?? "default"}
          transactions={transactions}
          initialId={inspectId}
        />
      </TabsContent>

      <TabsContent value="pipeline">
        <PipelineArchitecture summary={summary} />
      </TabsContent>
    </Tabs>
  )
}
