"use client";

import { formatMoney, formatPercent, formatQuantity, formatSignedMoney, signClass } from "@/lib/format";
import { valuePosition } from "@/lib/portfolio";
import { useTick } from "@/lib/priceStore";
import type { Position } from "@/lib/types";
import { Panel } from "./Panel";

function PositionRow({ position, onSelect }: { position: Position; onSelect: (ticker: string) => void }) {
  const tick = useTick(position.ticker);
  const { price, unrealizedPnl, pnlPercent } = valuePosition(position, tick?.price);
  return (
    <tr
      data-testid={`position-row-${position.ticker}`}
      onClick={() => onSelect(position.ticker)}
      className="h-7 cursor-pointer border-b border-edge/50 hover:bg-raised"
    >
      <td className="px-2 font-semibold">{position.ticker}</td>
      <td className="num px-2 text-right">{formatQuantity(position.quantity)}</td>
      <td className="num px-2 text-right">{formatMoney(position.avg_cost)}</td>
      <td className="num px-2 text-right">{formatMoney(price)}</td>
      <td className={`num px-2 text-right ${signClass(unrealizedPnl)}`}>{formatSignedMoney(unrealizedPnl)}</td>
      <td className={`num px-2 text-right ${signClass(pnlPercent)}`}>{formatPercent(pnlPercent)}</td>
    </tr>
  );
}

export function PositionsTable({
  positions,
  onSelect,
}: {
  positions: Position[];
  onSelect: (ticker: string) => void;
}) {
  return (
    <Panel title="Positions" className="desk:min-h-0">
      <div className="pane-scroll min-h-0 flex-1 overflow-auto" data-testid="positions-table">
        <table className="w-full min-w-[480px] border-collapse">
          <thead className="sticky top-0 bg-pane text-[11px] text-faint">
            <tr className="h-6 border-b border-edge">
              <th scope="col" className="px-2 text-left font-normal">Ticker</th>
              <th scope="col" className="px-2 text-right font-normal">Quantity</th>
              <th scope="col" className="px-2 text-right font-normal">Avg cost</th>
              <th scope="col" className="px-2 text-right font-normal">Price</th>
              <th scope="col" className="px-2 text-right font-normal">Unrealized P&amp;L</th>
              <th scope="col" className="px-2 text-right font-normal">% change</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((position) => (
              <PositionRow key={position.ticker} position={position} onSelect={onSelect} />
            ))}
          </tbody>
        </table>
        {positions.length === 0 ? (
          <p className="p-4 text-center text-dim">
            No positions yet. Use the trade ticket, or ask FinAlly to buy something.
          </p>
        ) : null}
      </div>
    </Panel>
  );
}
