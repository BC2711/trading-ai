import type { BrokerBalanceItem } from "../../api/brokerApi";
import { EmptyState } from "../table/EmptyState";
import { Card } from "../ui/Card";

export function BrokerBalancePanel({ brokerName, balances }: { brokerName?: string; balances: BrokerBalanceItem[] }) {
  return (
    <Card className="p-0">
      <div className="border-b border-white/10 p-4">
        <h2 className="text-base font-black text-slate-950 dark:text-white">Balance</h2>
        <p className="text-xs font-medium text-slate-500 dark:text-white/50">{brokerName ? `${brokerName} account balances` : "Select a broker"}</p>
      </div>
      {balances.length ? (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[520px] text-sm">
            <thead className="bg-white/20 text-xs uppercase text-slate-500 dark:bg-white/5 dark:text-white/45">
              <tr>
                {["Asset", "Free", "Locked", "Total"].map((header) => (
                  <th key={header} className="border-b border-white/10 px-4 py-3 text-left font-black">{header}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {balances.map((item) => (
                <tr key={item.asset} className="transition hover:bg-white/10 dark:hover:bg-white/5">
                  <td className="border-b border-white/10 px-4 py-4 font-black text-slate-950 dark:text-white">{item.asset}</td>
                  <td className="border-b border-white/10 px-4 py-4 text-slate-700 dark:text-white/70">{item.free.toFixed(6)}</td>
                  <td className="border-b border-white/10 px-4 py-4 text-slate-700 dark:text-white/70">{item.locked.toFixed(6)}</td>
                  <td className="border-b border-white/10 px-4 py-4 text-slate-700 dark:text-white/70">{item.total.toFixed(6)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState title="No balance data" message="Connected brokers will show balances here. Secrets are never displayed." />
      )}
    </Card>
  );
}
