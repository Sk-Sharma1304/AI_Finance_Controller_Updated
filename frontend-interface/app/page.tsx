import { DashboardClient } from "@/components/dashboard-client"
import { getSummary, getTransactions, getDataSource } from "@/lib/pipeline"

export default async function Page() {
  const [summary, transactions, source] = await Promise.all([
    getSummary(),
    getTransactions(),
    getDataSource(),
  ])

  return (
    <DashboardClient
      initialTransactions={transactions}
      initialSummary={summary}
      initialSource={source}
    />
  )
}
