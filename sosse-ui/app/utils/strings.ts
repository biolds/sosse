// Pluralization
export function plural(n: number): string {
  return n > 1 ? "s" : "";
}

// Add a space if 'a' exists
export function space(a: string, b: string): string {
  return a ? a + " " + b : b;
}

// Short format for durations
export function shortFmt(nbr: number, unit: string): string {
  if (unit === "m" || unit === "s") {
    return nbr.toString().padStart(2, "0") + unit;
  }
  return `${nbr}${unit}`;
}

export function humanShortDatetime(d: number): string {
  const seconds = d % 60;
  const minutes = Math.floor((d % 3600) / 60);
  const hours = Math.floor((d % 86400) / 3600);
  const days = Math.floor((d % 31536000) / 86400);
  const years = Math.floor(d / 31536000);
  const nbrs = [years, days, hours, minutes, seconds];
  const units = ["y", "d", "h", "m", "s"];
  for (let i = 0; i < nbrs.length - 1; i++) {
    if (nbrs[i]) {
      return (
        shortFmt(nbrs[i], units[i]).replace(/^0+/, "") +
        shortFmt(nbrs[i + 1], units[i + 1])
      );
    }
  }
  return `${seconds}s`;
}

// Human-readable duration
export function humanDatetime(
  d: number,
  short = false,
): string | null | undefined {
  if (short) return humanShortDatetime(d);
  let s = "";
  const seconds = d % 60;
  const minutes = Math.floor((d % 3600) / 60);
  const hours = Math.floor((d % 86400) / 3600);
  const days = Math.floor((d % 31536000) / 86400);
  const years = Math.floor(d / 31536000);
  if (years) s = space(s, `${years} year${plural(years)}`);
  if (days) s = space(s, `${days} day${plural(days)}`);
  if (hours) s = space(s, `${hours} hour${plural(hours)}`);
  if (minutes) s = space(s, `${minutes} minute${plural(minutes)}`);
  if (seconds) s = space(s, `${seconds} second${plural(seconds)}`);
  return s;
}

export function parseDurationToSeconds(input: string): number {
  const trimmed = input.trim();
  let days = 0,
    timePart = trimmed;
  if (/^\d+ /.test(trimmed)) {
    const [d, ...rest] = trimmed.split(" ");
    days = parseInt(d, 10);
    timePart = rest.join(" ");
  }
  const [hh, mm, ss] = timePart.split(":").map(Number);
  return days * 86400 + (hh || 0) * 3600 + (mm || 0) * 60 + (ss || 0);
}

// Convert a number to a readable unit (k, M, G, ...)
export function getUnit(n: number): [number, string] {
  const units = ["", "k", "M", "G", "T", "P"];
  let unitNo = 0;
  while (n >= 1000 && unitNo < units.length - 1) {
    unitNo += 1;
    n /= 1000;
  }
  return [10 ** (unitNo * 3), units[unitNo]];
}

export function humanNb(n: number): string {
  const [factor, unit] = getUnit(n);
  return `${Math.round(n / factor)}${unit}`;
}

export function humanFilesize(n: number): string {
  const [factor, unit] = getUnit(n);
  return `${(n / factor).toFixed(1)}${unit}B`;
}
