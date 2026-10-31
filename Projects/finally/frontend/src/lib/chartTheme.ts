import {
  ColorType,
  CrosshairMode,
  TickMarkType,
  type ChartOptions,
  type DeepPartial,
  type Time,
} from "lightweight-charts";

const pad = (n: number) => String(n).padStart(2, "0");

function localTime(time: Time, withSeconds: boolean): string {
  const date = new Date((time as number) * 1000);
  const base = `${pad(date.getHours())}:${pad(date.getMinutes())}`;
  return withSeconds ? `${base}:${pad(date.getSeconds())}` : base;
}

export const chartOptions: DeepPartial<ChartOptions> = {
  autoSize: true,
  layout: {
    background: { type: ColorType.Solid, color: "#10161f" },
    textColor: "#94a0b0",
    fontFamily: '"Archivo Variable", "Helvetica Neue", Arial, sans-serif',
    fontSize: 11,
    // Attribution is a text link in the main chart pane instead of a logo on the plot.
    attributionLogo: false,
  },
  grid: {
    vertLines: { color: "#1b2431" },
    horzLines: { color: "#1b2431" },
  },
  crosshair: {
    mode: CrosshairMode.Magnet,
    vertLine: { color: "#4a5666", labelBackgroundColor: "#2a3341" },
    horzLine: { color: "#4a5666", labelBackgroundColor: "#2a3341" },
  },
  rightPriceScale: { borderColor: "#2a3341" },
  timeScale: {
    borderColor: "#2a3341",
    timeVisible: true,
    secondsVisible: true,
    // Labels show seconds only when the visible range is short enough to need them.
    tickMarkFormatter: (time: Time, type: TickMarkType) =>
      localTime(time, type === TickMarkType.TimeWithSeconds),
  },
  localization: { timeFormatter: (time: Time) => localTime(time, true) },
  // Both charts always fit their whole series, so panning has nothing to reveal.
  handleScroll: false,
  handleScale: false,
};
